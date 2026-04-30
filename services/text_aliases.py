def normalize_text(text: str | None) -> str:
    return " ".join((text or "").strip().lower().replace("ё", "е").split())


PROFILE_ALIASES = {
    "мой кот",
    "мой котенок",
    "котенок",
    "профиль",
    "мой профиль",
    "кот",
    "паспорт пушистого подозреваемого",
}

START_ALIASES = {
    "старт",
    "начать",
    "разбудить синдикат",
}

HELP_ALIASES = {
    "помощь",
    "help",
    "что делать",
    "команды",
    "я кот я потерялся",
}

RESET_ALIASES = {
    "сброс",
    "сбросить профиль",
    "удалить профиль",
    "начать заново",
}

STATS_ALIASES = {
    "досье",
    "статы",
    "статистика",
    "мое досье",
}

INVENTORY_ALIASES = {
    "инвентарь",
    "мой инвентарь",
    "рюкзак",
    "мешок",
    "карманы полные шерсти",
}

CRAFT_ALIASES = {
    "кузница",
    "крафт",
    "мастерская",
    "молотком по судьбе",
}

SHOP_ALIASES = {
    "магазин",
    "лавка",
    "товары",
    "расходники",
    "где тут нелегальная валерьянка",
}

WISHLIST_ALIASES = {
    "хотелки",
    "список желаний",
    "мои хотелки",
    "что я хотел купить",
    "предзаказ",
    "лавочник что я хотел",
}

DAILY_ALIASES = {
    "ежедневки",
    "ежедневные задания",
    "дейлики",
    "дейли",
    "задания",
    "план по безобразию",
}

GEAR_ALIASES = {
    "экипировка",
    "шмот",
    "броня",
    "показать модный приговор",
}

EQUIP_PREFIXES = {
    "надеть",
    "экипировать",
}

USE_ITEM_PREFIXES = {
    "использовать",
    "юзнуть",
    "применить",
}

BUY_PREFIXES = {
    "купить",
    "приобрести",
    "взять",
    "отсыпь",
    "заверните",
    "дайте",
    "налейте",
    "продайте",
    "беру",
    "хочу",
    "рыбов на",
    "касса пробей",
    "мне бы",
    "лавочник дай",
    "достать из-под прилавка",
}

MEOW_ALIASES = {
    "мяу",
    "рыбачить",
    "рыба",
    "украсть рыбов",
    "налог на рыбов",
}

HUNT_ALIASES = {
    "охота",
    "на охоту",
    "охотиться",
    "ловить мышей",
    "мыши",
    "операция мышиная тишина",
}

WORK_ALIASES = {
    "работа",
    "работать",
    "на работу",
    "мыши на завод",
}

MINE_ALIASES = {
    "подвал",
    "в подвал",
    "копать",
    "добыча",
    "экспедиция под диван",
}

WORK_RETURN_ALIASES = {
    "завершить работу",
    "проверить работу",
    "вернуть с работы",
    "мыши с работы",
}

MINE_RETURN_ALIASES = {
    "завершить подвал",
    "проверить подвал",
    "вернуть из подвала",
    "мыши из подвала",
    "забрать из подвала",
}

GROW_ALIASES = {
    "расти",
    "рост",
    "прокачка",
    "жрать",
    "стать большим начальником",
}

BITE_ALIASES = {
    "кус",
    "укус",
    "укусить",
    "кусь",
    "дуэль",
    "кусательный протокол",
}

TOP_ALIASES = {
    "топ",
    "рейтинг",
    "авторитет",
}

BOSS_ALIASES = {
    "босс",
    "кус босса",
    "кусь босса",
    "кусать босса",
    "пес",
    "пылесос",
    "робот пылесос",
    "тапок",
    "ударить босса",
}

GRAB_ALIASES = {
    "контейнер",
    "забрать",
    "схватить",
}

EVENT_ALIASES = {
    "событие",
    "ивент",
    "что за кипиш",
}


def is_alias(text: str | None, aliases: set[str]) -> bool:
    return normalize_text(text) in aliases


def is_alias_with_count(text: str | None, aliases: set[str]) -> bool:
    normalized = normalize_text(text)
    if normalized in aliases:
        return True

    parts = normalized.split()
    if len(parts) < 2 or not parts[-1].isdigit():
        return False

    return " ".join(parts[:-1]) in aliases


def parse_prefixed_arg(text: str | None, prefixes: set[str]) -> str | None:
    normalized = normalize_text(text)
    for prefix in sorted(prefixes, key=len, reverse=True):
        if normalized == prefix:
            return ""
        if normalized.startswith(prefix + " "):
            return normalized[len(prefix) + 1:].strip()
    return None
