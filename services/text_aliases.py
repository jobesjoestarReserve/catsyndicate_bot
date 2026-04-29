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

GEAR_ALIASES = {
    "экипировка",
    "шмот",
    "броня",
}

MEOW_ALIASES = {
    "мяу",
    "рыбачить",
    "рыба",
    "украсть рыбов",
}

HUNT_ALIASES = {
    "охота",
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
    "шахта",
    "в шахту",
    "копать",
    "добыча",
}

MOUSE_RETURN_ALIASES = {
    "завершить работу",
    "проверить мышей",
    "вернуть мышей",
    "мыши домой",
    "забрать мышей",
}

GROW_ALIASES = {
    "расти",
    "рост",
    "прокачка",
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
