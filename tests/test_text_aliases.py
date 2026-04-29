import unittest

from services.text_aliases import (
    MINE_ALIASES,
    MINE_RETURN_ALIASES,
    PROFILE_ALIASES,
    START_ALIASES,
    EQUIP_PREFIXES,
    USE_ITEM_PREFIXES,
    WORK_ALIASES,
    WORK_RETURN_ALIASES,
    is_alias,
    is_alias_with_count,
    normalize_text,
    parse_prefixed_arg,
)


class TextAliasTests(unittest.TestCase):
    def test_normalize_text_handles_case_spaces_and_yo(self):
        self.assertEqual(normalize_text("  Мой   КотЁнок "), "мой котенок")

    def test_profile_alias_accepts_human_phrase(self):
        self.assertTrue(is_alias("Мой котёнок", PROFILE_ALIASES))
        self.assertTrue(is_alias("мой профиль", PROFILE_ALIASES))
        self.assertFalse(is_alias("мой котенок сегодня устал", PROFILE_ALIASES))

    def test_start_alias_accepts_plain_text_start(self):
        self.assertTrue(is_alias("Старт", START_ALIASES))

    def test_counted_alias_accepts_amount_suffix(self):
        self.assertTrue(is_alias_with_count("Работа 5", WORK_ALIASES))
        self.assertTrue(is_alias_with_count("Подвал 4", MINE_ALIASES))
        self.assertFalse(is_alias_with_count("Работа пять", WORK_ALIASES))

    def test_mouse_return_aliases_are_split_by_job_type(self):
        self.assertTrue(is_alias("Завершить работу", WORK_RETURN_ALIASES))
        self.assertTrue(is_alias("вернуть с работы", WORK_RETURN_ALIASES))
        self.assertTrue(is_alias("Завершить подвал", MINE_RETURN_ALIASES))
        self.assertTrue(is_alias("вернуть из подвала", MINE_RETURN_ALIASES))

    def test_item_action_prefixes_extract_localized_names(self):
        self.assertEqual(parse_prefixed_arg("Надеть Шлем из фольги", EQUIP_PREFIXES), "шлем из фольги")
        self.assertEqual(parse_prefixed_arg("Использовать Валерьянка", USE_ITEM_PREFIXES), "валерьянка")


if __name__ == "__main__":
    unittest.main()
