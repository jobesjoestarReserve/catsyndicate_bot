import unittest

from services.text_aliases import MINE_ALIASES, PROFILE_ALIASES, WORK_ALIASES, is_alias, is_alias_with_count, normalize_text


class TextAliasTests(unittest.TestCase):
    def test_normalize_text_handles_case_spaces_and_yo(self):
        self.assertEqual(normalize_text("  Мой   КотЁнок "), "мой котенок")

    def test_profile_alias_accepts_human_phrase(self):
        self.assertTrue(is_alias("Мой котёнок", PROFILE_ALIASES))
        self.assertTrue(is_alias("мой профиль", PROFILE_ALIASES))
        self.assertFalse(is_alias("мой котенок сегодня устал", PROFILE_ALIASES))

    def test_counted_alias_accepts_amount_suffix(self):
        self.assertTrue(is_alias_with_count("Работа 5", WORK_ALIASES))
        self.assertTrue(is_alias_with_count("Шахта 4", MINE_ALIASES))
        self.assertFalse(is_alias_with_count("Работа пять", WORK_ALIASES))


if __name__ == "__main__":
    unittest.main()
