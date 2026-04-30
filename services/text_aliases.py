def normalize_text(text: str | None) -> str:
    return " ".join((text or "").strip().lower().replace("ё", "е").split())


PROFILE_ALIASES = {
    "мой кот",
    "мой котенок",
    "котенок",
    "профиль",
    "мой профиль",
    "кот",
}

START_ALIASES = {
    "старт",
    "начать",
}

HELP_ALIASES = {
    "помощь",
    "help",
    "что делать",
    "команды",
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
}

CRAFT_ALIASES = {
    "кузница",
    "крафт",
    "мастерская",
}

SHOP_ALIASES = {
    "магазин",
    "лавка",
    "товары",
    "расходники",
}

DAILY_ALIASES = {
    "ежедневки",
    "ежедневные задания",
    "дейлики",
    "дейли",
    "задания",
}

GEAR_ALIASES = {
    "экипировка",
    "шмот",
    "броня",
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

MEOW_ALIASES = {
    "мяу",
    "рыбачить",
    "рыба",
    "украсть рыбов",
}

HUNT_ALIASES = {
    "охота",
    "на охоту",
    "охотиться",
    "ловить мышей",
    "мыши",
}

WORK_ALIASES = {
    "работа",
    "работать",
    "на работу",
}

MINE_ALIASES = {
    "подвал",
    "в подвал",
    "копать",
    "добыча",
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
}

BITE_ALIASES = {
    "укус",
    "укусить",
    "кусь",
    "дуэль",
}

TOP_ALIASES = {
    "топ",
    "рейтинг",
    "авторитет",
}

BOSS_ALIASES = {
    "босс",
    "кусать босса",
    "пес",
}

GRAB_ALIASES = {
    "контейнер",
    "забрать",
    "схватить",
}

EVENT_ALIASES = {
    "событие",
    "ивент",
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
