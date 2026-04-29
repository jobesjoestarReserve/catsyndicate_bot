import unittest
from datetime import datetime
from unittest.mock import patch

from services import mouse_jobs


class FakeDB:
    def __init__(self):
        self.current_time = None
        self.chat_id = None
        self.user_id = None

    async def get_due_mouse_jobs(self, current_time=None, chat_id=None, user_id=None):
        self.current_time = current_time
        self.chat_id = chat_id
        self.user_id = user_id
        return [
            {
                "id": 1,
                "job_type": "work",
                "user_id": 10,
                "chat_id": 20,
                "payload": {
                    "reward": 7,
                    "mice_returned": 1,
                    "mice_lost": 0,
                    "resources": {},
                    "authority": 0,
                    "title": "done",
                    "result_text": "ok",
                    "profile_label": "test",
                    "mice_sent": 1,
                },
            },
            {
                "id": 2,
                "job_type": "mine",
                "user_id": 10,
                "chat_id": 20,
                "payload": {
                    "mice_returned": 2,
                    "mice_lost": 1,
                    "resources": {"wool": 3},
                },
            },
        ]

    async def complete_mouse_work_job(self, *args):
        return {"mice_count": 4, "balance": 11}

    async def complete_mice_mining_job(self, *args):
        return {"mice_count": 6}


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, parse_mode=None):
        self.messages.append((chat_id, text, parse_mode))


class MouseJobTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_due_mouse_jobs_filters_and_counts_completed_jobs(self):
        fake_db = FakeDB()
        fake_bot = FakeBot()

        with patch.object(mouse_jobs, "db", fake_db):
            completed = await mouse_jobs.complete_due_mouse_jobs(
                fake_bot,
                chat_id=20,
                user_id=10,
            )

        self.assertEqual(completed, 2)
        self.assertEqual(fake_db.chat_id, 20)
        self.assertEqual(fake_db.user_id, 10)
        self.assertIsInstance(fake_db.current_time, datetime)
        self.assertEqual(len(fake_bot.messages), 2)


if __name__ == "__main__":
    unittest.main()
