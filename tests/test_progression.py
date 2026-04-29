import unittest

from tests.support import install_dependency_stubs

install_dependency_stubs()

from services.progression import (  # noqa: E402
    apply_xp_to_life,
    format_progress_bar,
    get_grow_cost,
    get_grow_success_chance,
    get_life_xp_required,
    get_progress_percent,
)


class ProgressionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
