import random
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.filters import Command

from database.db_manager import db
from data.runtime_state import runtime_state
from data.texts import WORK_CLASS_LABELS, WORK_CLASS_PROFILES
from services.crafting import get_equipment_bonus
from services.game_utils import format_cooldown, get_life_stage, touch_current_user
from services.mouse_jobs import format_job_duration
from services.text_aliases import MINE_ALIASES, WORK_ALIASES, is_alias_with_count

router = Router()

WORK_COMMAND = "work"
SEND_MICE_COMMAND = "send_mice"
RESOURCE_NAMES = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}

WORK_COOLDOWN_BY_LIFE = {
    1: 150,
    2: 140,
    3: 130,
    4: 110,
    5: 100,
    6: 90,
    7: 80,
    8: 70,
    9: 60,
}
MINE_COOLDOWN_BY_LIFE = {
    1: 180,
    2: 170,
    3: 160,
    4: 140,
    5: 125,
    6: 115,
    7: 100,
    8: 90,
    9: 75,
}
WORK_CLASS_REWARD_BONUS = {
    "support": 2,
    "warrior": 1,
    "thief": 0,
    "assassin": 0,
}
MINE_CLASS_RESOURCE_BONUS = {
    "support": 1,
    "warrior": 1,
    "thief": 0,
    "assassin": 0,
}

def parse_positive_count(message: types.Message, default=1, max_value=25):
    parts = (message.text or "").split()
    if len(parts) < 2:
        return default

    try:
        count = int(parts[-1])
    except ValueError:
        return None

    if count <= 0:
        return None
    return min(count, max_value)


def parse_send_mice_args(message: types.Message):
    parts = (message.text or "").split()
    if is_alias_with_count(message.text, MINE_ALIASES):
        return "mine", parse_positive_count(message, default=1, max_value=25)
    if len(parts) < 2:
        return None, 1

    action = parts[1].lower()
    if len(parts) < 3:
        return action, 1

    try:
        count = int(parts[2])
    except ValueError:
        return action, None

    if count <= 0:
        return action, None
    return action, min(count, 25)


def get_work_cooldown(user) -> int:
    life_stage = get_life_stage(user)
    return WORK_COOLDOWN_BY_LIFE[life_stage]


def get_mine_cooldown(user) -> int:
    life_stage = get_life_stage(user)
    return MINE_COOLDOWN_BY_LIFE[life_stage]


def format_not_enough_mice_for_work(needed: int, current: int) -> str:
    return (
        f"🐭 Для <b>/work</b> нужна мышиная бригада. "
        f"Нужно <b>{needed}</b>, сейчас в подчинении <b>{current}</b>.\n"
        "Сначала добудь мышей через <code>/hunt</code>, потом отправляй их за рыбами."
    )


def format_not_enough_mice_for_mine(needed: int, current: int) -> str:
    return (
        f"🐭 Для <b>/send_mice mine</b> нужны мыши-добытчики. "
        f"Нужно <b>{needed}</b>, сейчас в подчинении <b>{current}</b>.\n"
        "Сначала поймай мышей через <code>/hunt</code>, потом отправляй их за шерстью, металлом и мусором."
    )


def get_work_profile(user):
    cat_class = user["cat_class"] or "none"
    return cat_class if cat_class in WORK_CLASS_PROFILES else "none"


def get_work_outcome(user):
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    crit_success = 4 + life_stage
    crit_failure = max(4, 12 - life_stage)
    if cat_class == "assassin":
        crit_success += 3
    if cat_class in ("warrior", "support"):
        crit_failure = max(2, crit_failure - 2)
    if cat_class == "thief":
        crit_success += 1
        crit_failure += 2

    roll = random.randint(1, 100)
    if roll <= crit_success:
        return "critical_success"
    if roll >= 101 - crit_failure:
        return "critical_failure"

    failure_chance = max(8, 26 - life_stage * 2)
    if cat_class == "thief":
        failure_chance += 7
    if cat_class in ("warrior", "support"):
        failure_chance -= 4
    return "failure" if random.randint(1, 100) <= failure_chance else "success"


def roll_work_result(user, mice_sent: int):
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    profile = get_work_profile(user)
    outcome = get_work_outcome(user)

    class_reward_bonus = {
        "warrior": 3,
        "support": 1,
        "thief": 5,
        "assassin": 2,
        "none": 0,
    }.get(profile, 0)
    per_mouse_min = 3 + life_stage + class_reward_bonus
    per_mouse_max = 8 + life_stage * 2 + class_reward_bonus
    reward = sum(random.randint(per_mouse_min, per_mouse_max) for _ in range(mice_sent))

    loss_chance = max(5, 24 - life_stage * 2)
    if profile in ("warrior", "support"):
        loss_chance = max(3, loss_chance - 5)
    if profile == "thief":
        loss_chance += 6

    resources = {}
    authority = 0
    if outcome == "critical_success":
        reward = int(reward * 1.9) + mice_sent * (2 + life_stage)
        loss_chance = max(0, loss_chance - 8)
        if profile == "support":
            resources = {"wool": max(1, mice_sent // 2), "trash": max(1, mice_sent // 3)}
        elif profile == "thief":
            resources = {"metal": max(1, mice_sent // 2), "trash": max(1, mice_sent)}
        elif profile == "assassin":
            authority = max(1, 1 + mice_sent // 3)
        elif profile == "warrior":
            reward += mice_sent * 3
    elif outcome == "success":
        reward += mice_sent * WORK_CLASS_REWARD_BONUS.get(cat_class, 0)
        if profile == "support" and random.randint(1, 100) <= 35:
            resources = {"wool": 1}
        elif profile == "thief" and random.randint(1, 100) <= 30:
            resources = {"trash": random.randint(1, 2)}
        elif profile == "assassin" and random.randint(1, 100) <= 25:
            authority = 1
    elif outcome == "failure":
        reward = max(0, int(reward * 0.45))
        loss_chance += 10
    else:
        reward = 0
        loss_chance += 30

    lost = sum(1 for _ in range(mice_sent) if random.randint(1, 100) <= loss_chance)
    if outcome == "critical_failure" and lost == 0:
        lost = 1
    lost = min(mice_sent, lost)

    return {
        "profile": profile,
        "outcome": outcome,
        "reward": reward,
        "mice_returned": mice_sent - lost,
        "mice_lost": lost,
        "resources": resources,
        "authority": authority,
    }


def roll_mine_result(user, mice_sent: int):
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    resource_bonus = MINE_CLASS_RESOURCE_BONUS.get(cat_class, 0)
    resources = {name: 0 for name in RESOURCE_NAMES}

    for _ in range(mice_sent):
        primary = random.choice(tuple(RESOURCE_NAMES.keys()))
        resources[primary] += random.randint(1, 2 + life_stage // 3) + resource_bonus
        if random.randint(1, 100) <= 20 + life_stage * 3:
            resources[random.choice(tuple(RESOURCE_NAMES.keys()))] += 1

    loss_chance = max(4, 24 - life_stage * 2)
    if cat_class == "warrior":
        loss_chance = max(2, loss_chance - 4)
    lost = sum(1 for _ in range(mice_sent) if random.randint(1, 100) <= loss_chance)
    return {name: amount for name, amount in resources.items() if amount > 0}, mice_sent - lost, lost


@router.message(lambda message: is_alias_with_count(message.text, WORK_ALIASES))
@router.message(Command("work"))
async def cmd_work(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала /start")

    mice_sent = parse_positive_count(message, default=1, max_value=25)
    if mice_sent is None:
        return await message.answer("Формат: <code>/work</code> или <code>/work 5</code>", parse_mode="HTML")

    await touch_current_user(message, user)
    available_at = await db.get_cooldown(user_id, WORK_COMMAND)
    now = datetime.now()
    if runtime_state.cooldowns_enabled and available_at and available_at > now:
        remaining = int((available_at - now).total_seconds())
        cooldown_text = format_cooldown(remaining)
        return await message.answer(
            f"🕰️ Мышиная бригада еще считает командировочные. Возвращайся через <b>{cooldown_text}</b>.",
            parse_mode="HTML"
        )

    current_mice = user["mice_count"] or 0
    if current_mice < mice_sent:
        return await message.answer(
            format_not_enough_mice_for_work(mice_sent, current_mice),
            parse_mode="HTML"
        )

    equipped = await db.get_equipped_items(user_id)
    loot_bonus = get_equipment_bonus(equipped, "loot_bonus")
    work_buff = await db.consume_buff(user_id, "work_boost")
    work_result = roll_work_result(user, mice_sent)
    if loot_bonus:
        work_result["reward"] += mice_sent * loot_bonus
    if work_buff is not None:
        work_result["reward"] = int(work_result["reward"] * 1.2)
    reward = work_result["reward"]
    mice_lost = work_result["mice_lost"]

    resources = work_result["resources"]
    authority = work_result["authority"]
    duration = get_work_cooldown(user)
    complete_at = now + timedelta(seconds=duration)

    profile = work_result["profile"]
    outcome = work_result["outcome"]
    profile_label = WORK_CLASS_LABELS.get(profile, WORK_CLASS_LABELS["none"])
    profile_texts = WORK_CLASS_PROFILES.get(profile, WORK_CLASS_PROFILES["thief"])
    result_text = random.choice(profile_texts[outcome])
    title_by_outcome = {
        "critical_success": "🌟 <b>Критический успех смены!</b>",
        "success": "✅ <b>Смена закрыта.</b>",
        "failure": "⚠️ <b>Смена с приключениями.</b>",
        "critical_failure": "💥 <b>Критический провал смены!</b>",
    }
    start_result = await db.start_mouse_job(
        user_id,
        message.chat.id,
        "work",
        {
            "mice_sent": mice_sent,
            "mice_returned": work_result["mice_returned"],
            "mice_lost": mice_lost,
            "reward": reward,
            "resources": resources,
            "authority": authority,
            "profile_label": profile_label,
            "result_text": result_text,
            "title": title_by_outcome[outcome],
            "buff_used": work_buff is not None,
        },
        complete_at,
        mice_sent,
    )
    if not start_result:
        return await message.answer("🐭 Мыши пересчитались и отказались выходить на смену. Попробуй ещё раз.")

    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, WORK_COMMAND, complete_at)

    await message.answer(
        (
            f"🐭 Бригада ушла на работу: <b>{mice_sent}</b> мышей.\n"
            f"Вернутся примерно через <b>{format_job_duration(duration)}</b>.\n"
            f"Мышей дома: <b>{start_result['mice_left']}</b>\n\n"
            "Пока они на смене, они не защищают синдикат."
        ),
        parse_mode="HTML"
    )


@router.message(lambda message: is_alias_with_count(message.text, MINE_ALIASES))
@router.message(Command("send_mice"))
async def cmd_send_mice(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала /start")

    action, mice_sent = parse_send_mice_args(message)
    if action != "mine" or mice_sent is None:
        return await message.answer(
            "Формат: <code>/send_mice mine</code> или <code>/send_mice mine 5</code>",
            parse_mode="HTML"
        )

    await touch_current_user(message, user)
    available_at = await db.get_cooldown(user_id, SEND_MICE_COMMAND)
    now = datetime.now()
    if runtime_state.cooldowns_enabled and available_at and available_at > now:
        remaining = int((available_at - now).total_seconds())
        cooldown_text = format_cooldown(remaining)
        return await message.answer(
            f"⛏️ Подвал еще пылит после прошлого рейда. Новая добыча через <b>{cooldown_text}</b>.",
            parse_mode="HTML"
        )

    current_mice = user["mice_count"] or 0
    if current_mice < mice_sent:
        return await message.answer(
            format_not_enough_mice_for_mine(mice_sent, current_mice),
            parse_mode="HTML"
        )

    equipped = await db.get_equipped_items(user_id)
    loot_bonus = get_equipment_bonus(equipped, "loot_bonus")
    resources, mice_returned, mice_lost = roll_mine_result(user, mice_sent)
    if loot_bonus:
        for name in resources:
            resources[name] += loot_bonus

    duration = get_mine_cooldown(user)
    complete_at = now + timedelta(seconds=duration)

    start_result = await db.start_mouse_job(
        user_id,
        message.chat.id,
        "mine",
        {
            "mice_sent": mice_sent,
            "mice_returned": mice_returned,
            "mice_lost": mice_lost,
            "resources": resources,
        },
        complete_at,
        mice_sent,
    )
    if not start_result:
        return await message.answer("🐭 Мыши передумали спускаться в шахту. Попробуй ещё раз.")

    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, SEND_MICE_COMMAND, complete_at)

    await message.answer(
        (
            f"⛏️ В шахту ушли <b>{mice_sent}</b> мышей.\n"
            f"Вернутся примерно через <b>{format_job_duration(duration)}</b>.\n"
            f"Мышей дома: <b>{start_result['mice_left']}</b>\n\n"
            "Пока добытчики в подвале, они не участвуют в защите."
        ),
        parse_mode="HTML"
    )
