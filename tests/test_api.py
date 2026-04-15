import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.database import Analysis, Base, MessageAnalysis
from backend.models.schemas import AnalysisResult, RedFlag, RiskLevel


def load_main_module():
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

    from backend.services.pipeline import FraudDetectionPipeline

    original_init = FraudDetectionPipeline.__init__

    def fake_init(self):
        self.weights = {}

    FraudDetectionPipeline.__init__ = fake_init
    try:
        if "backend.api.main" in sys.modules:
            return importlib.reload(sys.modules["backend.api.main"])
        return importlib.import_module("backend.api.main")
    finally:
        FraudDetectionPipeline.__init__ = original_init


class StubPipeline:
    def __init__(self):
        self.quick_calls = []
        self.deep_calls = []

    async def quick_check(self, text, has_photos=False, metadata=None):
        self.quick_calls.append(
            {"text": text, "has_photos": has_photos, "metadata": metadata or {}}
        )
        return AnalysisResult(
            risk_score=72,
            risk_level=RiskLevel.HIGH,
            red_flags=[
                RedFlag(
                    category="payment",
                    description="Запрос предоплаты",
                    severity=9,
                )
            ],
            recommendations=["Не переводите деньги"],
            details={
                "component_scores": {"rule_engine": 72, "embedding": 0},
                "is_quick_check": True,
            },
        )

    async def deep_analyze(
        self,
        text,
        photos=None,
        is_forwarded=False,
        forward_info=None,
        quick_result=None,
    ):
        self.deep_calls.append(
            {
                "text": text,
                "photos": photos,
                "is_forwarded": is_forwarded,
                "forward_info": forward_info,
                "quick_result": quick_result,
            }
        )
        return AnalysisResult(
            risk_score=88,
            risk_level=RiskLevel.HIGH,
            red_flags=[
                RedFlag(
                    category="payment",
                    description="Оплата без встречи",
                    severity=10,
                )
            ],
            recommendations=["Прекратите общение"],
            details={
                "component_scores": {
                    "rule_engine": 72,
                    "embedding": 15,
                    "nlp_llm": 91,
                },
                "is_deep_analysis": True,
            },
        )


class AsyncSessionWrapper:
    def __init__(self, session):
        self.session = session

    async def execute(self, stmt):
        return self.session.execute(stmt)

    def add(self, instance):
        self.session.add(instance)

    async def commit(self):
        self.session.commit()

    async def close(self):
        self.session.close()


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.main = load_main_module()
        self.stub_pipeline = StubPipeline()
        self.main.pipeline = self.stub_pipeline

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db_path = Path(db_path)

        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

        async def override_get_db():
            session = self.SessionLocal()
            try:
                yield AsyncSessionWrapper(session)
            finally:
                session.close()

        self.main.app.dependency_overrides[self.main.get_db] = override_get_db
        transport = httpx.ASGITransport(app=self.main.app)
        self.client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.main.app.dependency_overrides.clear()
        self.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()

    async def seed_history_records(self):
        with self.SessionLocal() as session:
            session.add(
                Analysis(
                    user_id=42,
                    url="https://example.com/listing/1",
                    title="Listing One",
                    description="Safe listing",
                    price=2_500_000,
                    currency="UZS",
                    location="Ташкент",
                    risk_score=25,
                    risk_level="low",
                    red_flags=[],
                    recommendations=[],
                    details={"source": "listing"},
                )
            )
            session.add(
                MessageAnalysis(
                    user_id=42,
                    message_text="Срочно переведите деньги",
                    is_forwarded=True,
                    forward_from="scammer",
                    photo_count=0,
                    risk_score=85,
                    risk_level="high",
                    red_flags=[],
                    recommendations=[],
                    details={"analysis_type": "quick_check", "is_quick_check": True},
                )
            )
            session.commit()

    async def test_history_combines_listing_and_message_records(self):
        await self.seed_history_records()

        response = await self.client.get("/api/v1/history/42")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        item_types = {item["type"] for item in payload["history"]}
        self.assertEqual(item_types, {"listing", "message"})

    async def test_stats_include_message_and_listing_records(self):
        await self.seed_history_records()

        response = await self.client.get("/api/v1/stats")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_analyses"], 2)
        self.assertEqual(payload["risk_distribution"]["low"], 1)
        self.assertEqual(payload["risk_distribution"]["high"], 1)
        self.assertGreater(payload["average_risk_score"], 50)

    async def test_quick_endpoint_persists_message_record_with_flag(self):
        response = await self.client.post(
            "/api/v1/analyze-message-quick",
            json={
                "text": "Срочно переведите предоплату",
                "user_id": 777,
                "is_forwarded": False,
                "has_photos": False,
                "has_file": True,
                "file_count": 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["risk_score"], 72)
        self.assertIn("message_id", payload["details"])
        self.assertEqual(len(self.stub_pipeline.quick_calls), 1)

        with self.SessionLocal() as session:
            record = session.get(MessageAnalysis, payload["details"]["message_id"])
            self.assertIsNotNone(record)
            self.assertTrue(record.details["is_quick_check"])
            self.assertEqual(record.details["analysis_type"], "quick_check")

    async def test_deep_endpoint_reuses_quick_result_and_updates_existing_record(self):
        with self.SessionLocal() as session:
            quick_record = MessageAnalysis(
                user_id=555,
                message_text="Срочно переведите деньги на карту",
                is_forwarded=True,
                forward_from="unknown_sender",
                photo_count=0,
                risk_score=70,
                risk_level="high",
                red_flags=[{"category": "payment", "description": "Предоплата", "severity": 9}],
                recommendations=["Не платите"],
                details={
                    "analysis_type": "quick_check",
                    "is_quick_check": True,
                    "component_scores": {"rule_engine": 70, "embedding": 0},
                },
            )
            session.add(quick_record)
            session.commit()
            session.refresh(quick_record)
            message_id = quick_record.id

        response = await self.client.post(
            "/api/v1/analyze-message-deep",
            json={
                "text": "Срочно переведите деньги на карту",
                "user_id": 555,
                "is_forwarded": True,
                "forward_info": {"from_user": "unknown_sender"},
                "message_id": message_id,
                "photos": [],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["risk_score"], 88)
        self.assertEqual(len(self.stub_pipeline.deep_calls), 1)
        self.assertIsNotNone(self.stub_pipeline.deep_calls[0]["quick_result"])
        self.assertTrue(self.stub_pipeline.deep_calls[0]["quick_result"].details["is_quick_check"])

        with self.SessionLocal() as session:
            updated = session.get(MessageAnalysis, message_id)
            self.assertEqual(updated.risk_score, 88)
            self.assertEqual(updated.details["analysis_type"], "deep_analysis")


if __name__ == "__main__":
    unittest.main()
