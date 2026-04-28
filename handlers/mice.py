import random
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.filters import Command

from database.db_manager import db
from data.runtime_state import runtime_state
from data.texts import WORK_CLASS_LABELS, WORK_CLASS_PROFILES
from services.game_utils import format_cooldown, get_life_stage, touch_current_user

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

    work_result = roll_work_result(user, mice_sent)
    reward = work_result["reward"]
    mice_returned = work_result["mice_returned"]
    mice_lost = work_result["mice_lost"]
    result = await db.complete_mouse_work(user_id, mice_sent, reward, mice_returned)
    if not result:
        return await message.answer("🐭 Мыши разбежались быстрее бухгалтерии. Попробуй еще раз.")

    resources = work_result["resources"]
    authority = work_result["authority"]
    if resources:
        await db.add_resources(user_id, resources)
    if authority:
        await db.update_authority(user_id, authority)

    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, WORK_COMMAND, now + timedelta(seconds=get_work_cooldown(user)))

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
    lost_text = (
        f"\nПотери бригады: <b>{mice_lost}</b> 🐭"
        if mice_lost
        else "\nБригада вернулась полностью, хотя часть мышей делает вид, что ничего не было."
    )
    resources_text = ""
    if resources:
        resources_text = "\nБонус-ресурсы: " + ", ".join(
            f"{RESOURCE_NAMES[name]} <b>+{amount}</b>"
            for name, amount in resources.items()
        )
    authority_text = f"\nАвторитет: <b>+{authority}</b>" if authority else ""
    await message.answer(
        (
            f"{title_by_outcome[outcome]}\n"
            f"{result_text}\n\n"
            f"Работа: <b>{profile_label}</b>\n"
            f"Отправлено: <b>{mice_sent}</b> 🐭\n"
            f"Добыто: <b>{reward}</b> 🐟"
            f"{lost_text}"
            f"{resources_text}"
            f"{authority_text}\n"
            f"Мышей осталось: <b>{result['mice_count']}</b>\n"
            f"Баланс: <b>{result['balance']}</b> 🐟"
        ),
        parse_mode="HTML"
    )


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

    resources, mice_returned, mice_lost = roll_mine_result(user, mice_sent)
    result = await db.complete_mice_mining(user_id, mice_sent, mice_returned, resources)
    if not result:
        return await message.answer("🐭 Мыши отказались подписывать технику безопасности. Попробуй еще раз.")

    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, SEND_MICE_COMMAND, now + timedelta(seconds=get_mine_cooldown(user)))

    resources_text = "\n".join(
        f"{RESOURCE_NAMES[name].capitalize()}: <b>+{amount}</b>"
        for name, amount in resources.items()
    )
    lost_text = (
        f"\nНе вернулись из шахты: <b>{mice_lost}</b> 🐭"
        if mice_lost
        else "\nВсе добытчики вернулись, кроме чувства собственного достоинства."
    )
    await message.answer(
        (
            f"⛏️ Мыши спустились в подвал и принесли крафтовую добычу.\n\n"
            f"{resources_text}\n"
            f"{lost_text}\n"
            f"Мышей осталось: <b>{result['mice_count']}</b>"
        ),
        parse_mode="HTML"
    )
