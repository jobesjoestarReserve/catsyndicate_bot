import unittest
from unittest.mock import patch

from handlers.mice import roll_mine_result
from data.texts import MINE_CRITICAL_SUCCESS_TEXTS


class MiceTests(unittest.TestCase):
    def test_mine_critical_success_adds_bonus_mice(self):
        user = {"life_stage": 1, "cat_class": "none"}
        rolls = [1, 1, 100, 1, 100, 1, 100, 1, 100]

        with patch("handlers.mice.random.randint", side_effect=rolls):
            result = roll_mine_result(user, mice_sent=4)

        self.assertEqual(result["outcome"], "critical_success")
        self.assertEqual(result["mice_lost"], 0)
        self.assertEqual(result["bonus_mice"], 1)
        self.assertEqual(result["mice_returned"], 5)
        self.assertIn(result["result_text"], MINE_CRITICAL_SUCCESS_TEXTS)


if __name__ == "__main__":
    unittest.main()
