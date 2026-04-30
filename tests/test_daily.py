import unittest
from datetime import date, timedelta

from services.daily import (
    DAILY_STREAK_SAVE_TEXTS,
    STREAK_SAVE_LIMIT,
    apply_daily_action,
    are_daily_tasks_complete,
    generate_daily_reward,
    generate_daily_tasks,
    format_daily_reward,
    get_daily_difficulty,
    get_streak_day_from_last_claim,
    get_streak_plan_from_last_claim,
)


class DailyQuestTests(unittest.TestCase):
    def test_difficulty_scales_by_streak_day(self):
        self.assertEqual(get_daily_difficulty(1), "easy")
        self.assertEqual(get_daily_difficulty(3), "easy")
        self.assertEqual(get_daily_difficulty(4), "medium")
        self.assertEqual(get_daily_difficulty(9), "medium")
        self.assertEqual(get_daily_difficulty(10), "hard")

    def test_streak_continues_only_from_yesterday(self):
        today = date(2026, 4, 30)

        self.assertEqual(get_streak_day_from_last_claim(today - timedelta(days=1), 6, today), 7)
        self.assertEqual(get_streak_day_from_last_claim(today - timedelta(days=2), 6, today), 1)

    def test_streak_saves_are_limited_per_streak(self):
        today = date(2026, 4, 30)

        continued = get_streak_plan_from_last_claim(today - timedelta(days=1), 6, 3, today)
        self.assertEqual(continued["streak_day"], 7)
        self.assertEqual(continued["saves_remaining"], 3)
        self.assertEqual(continued["saved_missed_days"], 0)

        saved_once = get_streak_plan_from_last_claim(today - timedelta(days=2), 6, 3, today)
        self.assertEqual(saved_once["streak_day"], 7)
        self.assertEqual(saved_once["saves_remaining"], 2)
        self.assertEqual(saved_once["saved_missed_days"], 1)

        saved_twice = get_streak_plan_from_last_claim(today - timedelta(days=3), 6, 3, today)
        self.assertEqual(saved_twice["streak_day"], 7)
        self.assertEqual(saved_twice["saves_remaining"], 1)
        self.assertEqual(saved_twice["saved_missed_days"], 2)

        reset = get_streak_plan_from_last_claim(today - timedelta(days=5), 6, 3, today)
        self.assertEqual(reset["streak_day"], 1)
        self.assertEqual(reset["saves_remaining"], STREAK_SAVE_LIMIT)
        self.assertEqual(reset["saved_missed_days"], 0)
        self.assertTrue(reset["reset"])

    def test_streak_save_texts_have_expected_count(self):
        self.assertEqual(len(DAILY_STREAK_SAVE_TEXTS), 15)

    def test_daily_tasks_are_deterministic_and_scale_count(self):
        today = date(2026, 4, 30)

        self.assertEqual(generate_daily_tasks(10, today, 1), generate_daily_tasks(10, today, 1))
        self.assertEqual(len(generate_daily_tasks(10, today, 1)), 2)
        self.assertEqual(len(generate_daily_tasks(10, today, 4)), 3)
        self.assertEqual(len(generate_daily_tasks(10, today, 10)), 3)

    def test_apply_daily_action_caps_progress_at_goal(self):
        tasks = [{"id": "a", "title": "test", "action": "meow", "goal": 2, "current": 0}]

        updated, changed = apply_daily_action(tasks, "meow", 5)

        self.assertTrue(changed)
        self.assertEqual(updated[0]["current"], 2)
        self.assertTrue(are_daily_tasks_complete(updated))

    def test_daily_rewards_grow_with_difficulty(self):
        easy = generate_daily_reward(1)
        medium = generate_daily_reward(4)
        hard = generate_daily_reward(10)

        self.assertLess(easy["fish"], medium["fish"])
        self.assertLess(medium["fish"], hard["fish"])
        self.assertTrue(hard["items"])

    def test_daily_reward_formats_resource_names_for_players(self):
        text = format_daily_reward({
            "items": [{"item_name": "trash", "item_type": "resource", "amount": 2}],
        })

        self.assertIn("мусор", text)
        self.assertNotIn("trash", text)


if __name__ == "__main__":
    unittest.main()
