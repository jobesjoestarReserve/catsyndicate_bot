import unittest

from services.text_aliases import (
    BITE_ALIASES,
    BOSS_ALIASES,
    BUY_PREFIXES,
    CRAFT_ALIASES,
    MINE_ALIASES,
    MINE_RETURN_ALIASES,
    EVENT_ALIASES,
    GEAR_ALIASES,
    GROW_ALIASES,
    HUNT_ALIASES,
    INVENTORY_ALIASES,
    MEOW_ALIASES,
    PROFILE_ALIASES,
    DAILY_ALIASES,
    RESET_ALIASES,
    SHOP_ALIASES,
    START_ALIASES,
    EQUIP_PREFIXES,
    HELP_ALIASES,
    USE_ITEM_PREFIXES,
    WORK_ALIASES,
    WORK_RETURN_ALIASES,
    WISHLIST_ALIASES,
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

    def test_help_alias_accepts_plain_text_help(self):
        self.assertTrue(is_alias("Помощь", HELP_ALIASES))
        self.assertTrue(is_alias("что делать", HELP_ALIASES))

    def test_reset_alias_accepts_plain_text_reset(self):
        self.assertTrue(is_alias("сброс", RESET_ALIASES))
        self.assertTrue(is_alias("удалить профиль", RESET_ALIASES))

    def test_shop_alias_accepts_plain_text_shop(self):
        self.assertTrue(is_alias("магазин", SHOP_ALIASES))
        self.assertTrue(is_alias("лавка", SHOP_ALIASES))

    def test_wishlist_alias_accepts_plain_text_wishlist(self):
        self.assertTrue(is_alias("хотелки", WISHLIST_ALIASES))
        self.assertTrue(is_alias("список желаний", WISHLIST_ALIASES))

    def test_boss_alias_accepts_boss_bite_phrases(self):
        self.assertTrue(is_alias("кусь босса", BOSS_ALIASES))
        self.assertTrue(is_alias("пылесос", BOSS_ALIASES))
        self.assertTrue(is_alias("тапок", BOSS_ALIASES))

    def test_daily_alias_accepts_plain_text_daily(self):
        self.assertTrue(is_alias("ежедневки", DAILY_ALIASES))
        self.assertTrue(is_alias("ежедневные задания", DAILY_ALIASES))

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
        self.assertEqual(parse_prefixed_arg("Купить Валерьянка 10", BUY_PREFIXES), "валерьянка 10")
        self.assertEqual(parse_prefixed_arg("Отсыпь кошачья мята max", BUY_PREFIXES), "кошачья мята max")

    def test_absurd_comic_aliases_are_recognized(self):
        cases = [
            ("разбудить синдикат", START_ALIASES),
            ("я кот я потерялся", HELP_ALIASES),
            ("паспорт пушистого подозреваемого", PROFILE_ALIASES),
            ("карманы полные шерсти", INVENTORY_ALIASES),
            ("молотком по судьбе", CRAFT_ALIASES),
            ("где тут нелегальная валерьянка", SHOP_ALIASES),
            ("план по безобразию", DAILY_ALIASES),
            ("показать модный приговор", GEAR_ALIASES),
            ("налог на рыбов", MEOW_ALIASES),
            ("операция мышиная тишина", HUNT_ALIASES),
            ("мыши на завод", WORK_ALIASES),
            ("экспедиция под диван", MINE_ALIASES),
            ("стать большим начальником", GROW_ALIASES),
            ("кусательный протокол", BITE_ALIASES),
            ("что за кипиш", EVENT_ALIASES),
        ]

        for phrase, aliases in cases:
            with self.subTest(phrase=phrase):
                self.assertTrue(is_alias(phrase, aliases))


if __name__ == "__main__":
    unittest.main()
