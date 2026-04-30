import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from services import game_utils


class FakeDB:
    def __init__(self, available_at=None):
        self.available_at = available_at
        self.calls = []
        self.user = None
        self.touched = []

    async def get_cooldown(self, user_id, command):
        self.calls.append((user_id, command))
        return self.available_at

    async def get_user(self, user_id):
        self.calls.append(("get_user", user_id))
        return self.user

    async def touch_user(self, user_id):
        self.touched.append(user_id)


class FakeCallbackUser:
    id = 42


class FakeCallback:
    def __init__(self):
        self.from_user = FakeCallbackUser()
        self.answers = []

    async def answer(self, text=None, show_alert=None):
        self.answers.append((text, show_alert))


class GameUtilsTests(unittest.IsolatedAsyncioTestCase):
    async def test_active_cooldown_text_returns_none_when_disabled(self):
        fake_db = FakeDB(datetime.now() + timedelta(seconds=30))

        with patch.object(game_utils, "db", fake_db):
            text = await game_utils.get_active_cooldown_text(
                user_id=1,
                command="meow",
                now=datetime.now(),
                cooldowns_enabled=False,
            )

        self.assertIsNone(text)
        self.assertEqual(fake_db.calls, [])

    async def test_active_cooldown_text_formats_future_cooldown(self):
        now = datetime(2026, 4, 30, 12, 0, 0)
        fake_db = FakeDB(now + timedelta(seconds=75))

        with patch.object(game_utils, "db", fake_db):
            text = await game_utils.get_active_cooldown_text(
                user_id=7,
                command="hunt",
                now=now,
            )

        self.assertEqual(text, "1 мин 15 сек")
        self.assertEqual(fake_db.calls, [(7, "hunt")])

    async def test_active_cooldown_text_returns_none_for_expired_cooldown(self):
        now = datetime(2026, 4, 30, 12, 0, 0)
        fake_db = FakeDB(now - timedelta(seconds=1))

        with patch.object(game_utils, "db", fake_db):
            text = await game_utils.get_active_cooldown_text(
                user_id=7,
                command="hunt",
                now=now,
            )

        self.assertIsNone(text)

    async def test_require_callback_user_alerts_when_user_is_missing(self):
        fake_db = FakeDB()
        callback = FakeCallback()

        with patch.object(game_utils, "db", fake_db):
            user = await game_utils.require_callback_user(callback)

        self.assertIsNone(user)
        self.assertEqual(callback.answers, [("Сначала напиши старт", True)])
        self.assertEqual(fake_db.touched, [])

    async def test_require_callback_user_touches_existing_user(self):
        fake_db = FakeDB()
        fake_db.user = {"user_id": 42}
        callback = FakeCallback()

        with patch.object(game_utils, "db", fake_db):
            user = await game_utils.require_callback_user(callback)

        self.assertEqual(user, {"user_id": 42})
        self.assertEqual(callback.answers, [])
        self.assertEqual(fake_db.touched, [42])


if __name__ == "__main__":
    unittest.main()
