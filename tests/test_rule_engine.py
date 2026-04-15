import unittest

from backend.models.schemas import ListingData
from backend.services.rule_engine import RuleEngine


class RuleEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = RuleEngine()

    def test_detects_critical_payment_and_urgency_pattern(self):
        listing = ListingData(
            url="message://1",
            description=(
                "Срочно! Только сегодня. Скиньте предоплату на карту, "
                "адрес после оплаты, без просмотра."
            ),
            metadata={"has_file": False, "file_count": 0},
        )

        risk_score, flags = self.engine.analyze(listing)
        categories = {flag.category for flag in flags}
        descriptions = [flag.description for flag in flags]

        self.assertGreaterEqual(risk_score, 60)
        self.assertIn("payment", categories)
        self.assertIn("urgency", categories)
        self.assertTrue(
            any("оплат" in desc.lower() or "встреч" in desc.lower() for desc in descriptions)
        )

    def test_detects_link_and_file_combination(self):
        listing = ListingData(
            url="message://2",
            description="Перейдите по ссылке https://example.com и откройте файл.",
            metadata={"has_file": True, "file_count": 1},
        )

        risk_score, flags = self.engine.analyze(listing)

        self.assertGreaterEqual(risk_score, 30)
        self.assertTrue(any(flag.category == "attachment" for flag in flags))
        self.assertTrue(
            any("ссылка" in flag.description.lower() and "файл" in flag.description.lower() for flag in flags)
        )

    def test_safe_listing_stays_below_high_risk(self):
        listing = ListingData(
            url="https://example.com/listing/123",
            title="2-комнатная квартира",
            description=(
                "2-комнатная квартира в Мирзо-Улугбекском районе. "
                "Площадь 65 кв.м, 3 этаж, евроремонт, мебель, интернет, договор, залог. "
                "Телефон: +998901234567."
            ),
            price=3_500_000,
            currency="UZS",
            location="Ташкент",
            contact_info={"phones": "+998901234567"},
            metadata={},
        )

        risk_score, flags = self.engine.analyze(listing)
        severe_flags = [flag for flag in flags if flag.severity >= 8]

        self.assertLess(risk_score, 60)
        self.assertEqual(severe_flags, [])


if __name__ == "__main__":
    unittest.main()
