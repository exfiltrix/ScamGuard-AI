import os
import unittest
from types import SimpleNamespace


os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKENabcdefghijklmnop")

from backend.bot import telegram_bot as bot_module


class FakeSentMessage:
    def __init__(self, text="", from_user_id=0):
        self.text = text
        self.caption = ""
        self.photo = []
        self.document = None
        self.from_user = SimpleNamespace(id=from_user_id, first_name="Tester")
        self.answers = []
        self.deleted = False
        self.edits = []

    async def answer(self, text, **kwargs):
        sent = FakeSentMessage(text=text, from_user_id=self.from_user.id)
        sent.answer_kwargs = kwargs
        self.answers.append(sent)
        return sent

    async def edit_text(self, text, **kwargs):
        self.text = text
        self.edits.append((text, kwargs))
        return self

    async def delete(self):
        self.deleted = True


class FakeMessage(FakeSentMessage):
    def __init__(
        self,
        *,
        text="",
        caption="",
        photo=None,
        document=None,
        from_user_id=123,
        first_name="Tester",
    ):
        super().__init__(text=text, from_user_id=from_user_id)
        self.caption = caption
        self.photo = photo or []
        self.document = document
        self.from_user = SimpleNamespace(id=from_user_id, first_name=first_name)
        self.forward_from = None
        self.forward_sender_name = None


class FakeCallbackQuery:
    def __init__(self, *, data, user_id=123, message=None):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = message or FakeMessage(from_user_id=user_id)
        self.answers = []

    async def answer(self, text=None, show_alert=False):
        self.answers.append({"text": text, "show_alert": show_alert})


class FakeState:
    def __init__(self):
        self.cleared = False
        self.states = []

    async def clear(self):
        self.cleared = True

    async def set_state(self, state):
        self.states.append(state)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, responses, record_list):
        self._responses = list(responses)
        self._record_list = record_list

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **kwargs):
        self._record_list.append(("GET", url, kwargs))
        return self._responses.pop(0)

    async def post(self, url, **kwargs):
        self._record_list.append(("POST", url, kwargs))
        return self._responses.pop(0)


class BotFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_async_client = bot_module.httpx.AsyncClient
        self.original_send_detailed_result = bot_module.send_detailed_result

    def tearDown(self):
        bot_module.httpx.AsyncClient = self.original_async_client
        bot_module.send_detailed_result = self.original_send_detailed_result

    def install_client(self, *responses):
        recorded_requests = []

        def factory(*args, **kwargs):
            return FakeAsyncClient(responses, recorded_requests)

        bot_module.httpx.AsyncClient = factory
        return recorded_requests

    async def test_history_renders_summary_for_message_records(self):
        requests = self.install_client(
            FakeResponse(
                200,
                {
                    "history": [
                        {
                            "id": 5,
                            "type": "message",
                            "url": "message://5",
                            "summary": "Urgent prepayment request from unknown sender",
                            "risk_score": 88,
                            "risk_level": "high",
                            "created_at": "2026-04-14T16:00:00",
                        }
                    ]
                },
            )
        )
        message = FakeMessage(text="/history", from_user_id=77)

        await bot_module.cmd_history(message)

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0][0], "GET")
        self.assertTrue(message.answers)
        response_text = message.answers[0].text
        self.assertIn("Urgent prepayment request", response_text)
        self.assertNotIn("message://5", response_text)

    async def test_quick_flow_posts_payload_and_offers_deep_analysis(self):
        requests = self.install_client(
            FakeResponse(
                200,
                {
                    "risk_score": 72,
                    "risk_level": "high",
                    "red_flags": [
                        {
                            "severity": 9,
                            "category": "payment",
                            "description": "Advance payment required",
                        }
                    ],
                    "details": {"message_id": 321},
                },
            )
        )
        message = FakeMessage(text="Send the deposit now", from_user_id=55)

        await bot_module.process_message_quick_then_offer_deep(
            message=message,
            text="Send the deposit now",
            photos=["photo-1"],
            is_forwarded=True,
        )

        self.assertEqual(len(requests), 1)
        method, url, kwargs = requests[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/analyze-message-quick"))
        self.assertEqual(
            kwargs["json"],
            {
                "text": "Send the deposit now",
                "user_id": 55,
                "is_forwarded": True,
                "has_photos": True,
                "has_file": False,
                "file_count": 0,
            },
        )
        self.assertEqual(len(message.answers), 3)
        self.assertTrue(message.answers[0].deleted)
        self.assertIn("БЫСТРАЯ ПРОВЕРКА", message.answers[1].text)
        self.assertIn("deep_analysis:321", str(message.answers[2].answer_kwargs["reply_markup"]))

    async def test_deep_analysis_callback_fetches_message_and_runs_analysis(self):
        requests = self.install_client(
            FakeResponse(
                200,
                {
                    "message_text": "Transfer the money now",
                    "photo_count": 0,
                    "is_forwarded": True,
                    "forward_from": "unknown_sender",
                },
            ),
            FakeResponse(
                200,
                {
                    "risk_score": 91,
                    "risk_level": "high",
                    "red_flags": [],
                    "recommendations": ["Block the sender"],
                    "details": {"component_scores": {"nlp_llm": 91}},
                },
            ),
        )

        captured = {}

        async def fake_send_detailed_result(message, result, url, status_msg):
            captured["message"] = message
            captured["result"] = result
            captured["url"] = url
            captured["status_msg"] = status_msg

        bot_module.send_detailed_result = fake_send_detailed_result

        source_message = FakeMessage(from_user_id=88)
        callback = FakeCallbackQuery(data="deep_analysis:42", user_id=88, message=source_message)

        await bot_module.callback_deep_analysis(callback)

        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0][0], "GET")
        self.assertTrue(requests[0][1].endswith("/message/42"))
        self.assertEqual(requests[1][0], "POST")
        self.assertTrue(requests[1][1].endswith("/analyze-message-deep"))
        self.assertEqual(
            requests[1][2]["json"],
            {
                "text": "Transfer the money now",
                "user_id": 88,
                "is_forwarded": True,
                "forward_info": {"from_user": "unknown_sender"},
                "message_id": 42,
                "photos": [],
            },
        )
        self.assertEqual(captured["url"], "Сообщение")
        self.assertEqual(captured["result"]["risk_score"], 91)

    async def test_document_analysis_flags_critical_file(self):
        message = FakeMessage(from_user_id=101)

        await bot_module.analyze_file_with_warning(
            message=message,
            file_name="installer.apk",
            file_ext=".apk",
            file_type="android_app",
            file_size=4096,
            mime_type="application/vnd.android.package-archive",
            caption="Install this app to verify your profile",
        )

        self.assertEqual(len(message.answers), 1)
        result_text = message.answers[0].text
        self.assertIn("Проверка файла", result_text)
        self.assertIn("КРИТИЧЕСКИЙ РИСК", result_text)
        self.assertIn("НЕ УСТАНАВЛИВАЙТЕ", result_text)


if __name__ == "__main__":
    unittest.main()
