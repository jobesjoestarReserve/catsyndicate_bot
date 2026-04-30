import unittest
from unittest.mock import AsyncMock, patch

from tests.support import install_dependency_stubs

install_dependency_stubs()

from handlers.progression import choose_class_for_user, should_offer_class_selection  # noqa: E402
from services.progression import (  # noqa: E402
    apply_xp_to_life,
    format_progress_bar,
    get_grow_cost,
    get_grow_success_chance,
    get_life_xp_required,
    get_progress_percent,
)
from services.ui import class_selection_keyboard  # noqa: E402


class ProgressionTests(unittest.IsolatedAsyncioTestCase):
    def test_apply_xp_promotes_once_and_carries_remainder(self):
        new_life, new_xp, promoted = apply_xp_to_life(1, 90, 25)

        self.assertEqual(new_life, 2)
        self.assertEqual(new_xp, 15)
        self.assertTrue(promoted)

    def test_apply_xp_caps_at_life_nine(self):
        new_life, new_xp, promoted = apply_xp_to_life(8, 970, 20)

        self.assertEqual(new_life, 9)
        self.assertEqual(new_xp, 0)
        self.assertTrue(promoted)

    def test_progress_percent_is_bounded(self):
        self.assertEqual(get_progress_percent(1, -10), 0)
        self.assertEqual(get_progress_percent(1, 250), 100)
        self.assertEqual(get_progress_percent(9, 0), 100)

    def test_support_class_gets_discounted_grow_cost(self):
        user = {"life_stage": 3, "cat_class": "support"}

        self.assertEqual(get_grow_cost(user), 114)

    def test_grow_success_chance_is_clamped(self):
        user = {"life_stage": 9, "cat_class": "none"}

        self.assertEqual(get_life_xp_required(99), 0)
        self.assertEqual(get_grow_success_chance(user), 15)

    def test_progress_bar_has_stable_width(self):
        self.assertEqual(len(format_progress_bar(0)), 10)
        self.assertEqual(len(format_progress_bar(55)), 10)
        self.assertEqual(len(format_progress_bar(100)), 10)

    def test_class_selection_opens_on_second_life_for_classless_user(self):
        self.assertTrue(should_offer_class_selection({"cat_class": "none"}, old_life_stage=1, new_life_stage=2))
        self.assertFalse(should_offer_class_selection({"cat_class": "none"}, old_life_stage=2, new_life_stage=3))
        self.assertFalse(should_offer_class_selection({"cat_class": "support"}, old_life_stage=1, new_life_stage=2))

    def test_class_selection_keyboard_has_playable_classes_only(self):
        keyboard = class_selection_keyboard()
        callbacks = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        ]

        self.assertIn("choose_class:warrior", callbacks)
        self.assertIn("choose_class:thief", callbacks)
        self.assertIn("choose_class:support", callbacks)
        self.assertIn("choose_class:assassin", callbacks)
        self.assertNotIn("choose_class:none", callbacks)

    async def test_choose_class_for_user_sets_first_class_after_second_life(self):
        user = {"life_stage": 2, "cat_class": "none"}

        with patch("handlers.progression.db.set_cat_class", new=AsyncMock(return_value="support")) as set_class:
            text, ok, alert = await choose_class_for_user(7, user, "support")

        self.assertTrue(ok)
        self.assertEqual(alert, "Класс выбран")
        self.assertIn("Кошечка-Ботаник", text)
        set_class.assert_awaited_once_with(7, "support")

    async def test_choose_class_for_user_blocks_before_second_life(self):
        user = {"life_stage": 1, "cat_class": "none"}

        with patch("handlers.progression.db.set_cat_class", new=AsyncMock()) as set_class:
            text, ok, alert = await choose_class_for_user(7, user, "thief")

        self.assertFalse(ok)
        self.assertEqual(alert, "Класс ещё закрыт")
        self.assertIn("со второй жизни", text)
        set_class.assert_not_awaited()

    async def test_choose_class_for_user_is_one_time_only(self):
        user = {"life_stage": 2, "cat_class": "warrior"}

        with patch("handlers.progression.db.set_cat_class", new=AsyncMock()) as set_class:
            text, ok, alert = await choose_class_for_user(7, user, "thief")

        self.assertFalse(ok)
        self.assertEqual(alert, "Класс уже выбран")
        self.assertIn("уже выбран", text)
        set_class.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
