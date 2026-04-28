import random

from services.game_utils import get_life_stage

GROW_COMMAND = "grow"

LIFE_XP_REQUIRED = {
    1: 100,
    2: 150,
    3: 225,
    4: 325,
    5: 450,
    6: 600,
    7: 775,
    8: 975,
    9: 0,
}

GROW_COST_BY_LIFE = {
    1: 60,
    2: 90,
    3: 135,
    4: 190,
    5: 260,
    6: 340,
    7: 430,
    8: 540,
    9: 0,
}

GROW_COOLDOWN_BY_LIFE = {
    1: 90,
    2: 100,
    3: 110,
    4: 100,
    5: 115,
    6: 125,
    7: 135,
    8: 145,
    9: 180,
}

GROW_SUCCESS_CHANCE_BY_LIFE = {
    1: 48,
    2: 52,
    3: 56,
    4: 60,
    5: 63,
    6: 66,
    7: 68,
    8: 70,
    9: 0,
}

CLASS_GROW_MODS = {
    "warrior": {"cost_mult": 1.0, "success": 3, "crit": 0, "fumble": -4, "xp_bonus": 4},
    "support": {"cost_mult": 0.85, "success": 2, "crit": 1, "fumble": -2, "xp_bonus": 2},
    "thief": {"cost_mult": 1.0, "success": 0, "crit": 2, "fumble": 2, "xp_bonus": 0},
    "assassin": {"cost_mult": 1.0, "success": 1, "crit": 4, "fumble": 0, "xp_bonus": 1},
    "none": {"cost_mult": 1.0, "success": 0, "crit": 0, "fumble": 0, "xp_bonus": 0},
}


def get_life_xp_required(life_stage: int) -> int:
    return LIFE_XP_REQUIRED.get(max(1, min(9, life_stage)), 0)


def get_grow_cost(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    base = GROW_COST_BY_LIFE[life_stage]
    modifier = CLASS_GROW_MODS.get(cat_class, CLASS_GROW_MODS["none"])
    return max(1, int(base * modifier["cost_mult"]))


def get_grow_cooldown(user) -> int:
    return GROW_COOLDOWN_BY_LIFE[get_life_stage(user)]


def get_grow_success_chance(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    modifier = CLASS_GROW_MODS.get(cat_class, CLASS_GROW_MODS["none"])
    return max(15, min(85, GROW_SUCCESS_CHANCE_BY_LIFE[life_stage] + modifier["success"]))


def get_grow_crit_chance(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    modifier = CLASS_GROW_MODS.get(cat_class, CLASS_GROW_MODS["none"])
    return max(4, min(22, 5 + life_stage + modifier["crit"]))


def get_grow_fumble_chance(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    modifier = CLASS_GROW_MODS.get(cat_class, CLASS_GROW_MODS["none"])
    return max(3, min(20, 15 - life_stage + modifier["fumble"]))


def roll_grow_xp(user, outcome: str) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    modifier = CLASS_GROW_MODS.get(cat_class, CLASS_GROW_MODS["none"])
    base = random.randint(18 + life_stage * 3, 34 + life_stage * 5) + modifier["xp_bonus"]
    if outcome == "critical_success":
        return int(base * 2.2) + life_stage * 3
    if outcome == "success":
        return base
    if outcome == "failure":
        return max(3, base // 4)
    return 0


def roll_grow_outcome(user) -> str:
    if random.randint(1, 100) <= get_grow_success_chance(user):
        if random.randint(1, 100) <= get_grow_crit_chance(user):
            return "critical_success"
        return "success"
    if random.randint(1, 100) <= get_grow_fumble_chance(user):
        return "critical_failure"
    return "failure"


def apply_xp_to_life(life_stage: int, life_xp: int, gained_xp: int) -> tuple[int, int, bool]:
    if life_stage >= 9:
        return 9, life_xp, False

    new_life = life_stage
    new_xp = life_xp + gained_xp
    promoted = False
    while new_life < 9:
        required = get_life_xp_required(new_life)
        if new_xp < required:
            break
        new_xp -= required
        new_life += 1
        promoted = True

    if new_life >= 9:
        new_life = 9
        new_xp = 0
    return new_life, new_xp, promoted


def get_progress_percent(life_stage: int, life_xp: int) -> int:
    required = get_life_xp_required(life_stage)
    if required <= 0:
        return 100
    return max(0, min(100, int((life_xp / required) * 100)))


def format_progress_bar(percent: int) -> str:
    filled = max(0, min(10, percent // 10))
    return "🟩" * filled + "⬜" * (10 - filled)
