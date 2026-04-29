import random
from html import escape
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command
from database.db_manager import db  # Импортируем готовый экземпляр
from data.runtime_state import runtime_state
from data.constants import CAT_STATUSES
from data.texts import (
    MEOW_SUCCESS_VARIANTS,
    MEOW_FAILURE_VARIANTS,
    MEOW_CRITICAL_VARIANTS,
    MEOW_FUMBLE_VARIANTS,
    MEOW_COOLDOWN_VARIANTS,
    HUNT_SUCCESS_VARIANTS,
    HUNT_FAILURE_VARIANTS,
    HUNT_CRITICAL_VARIANTS,
    HUNT_FUMBLE_VARIANTS,
    HUNT_COOLDOWN_VARIANTS,
)
from services.game_utils import (
    format_cooldown,
    get_life_stage,
    get_telegram_cat_name,
    sync_cat_name_if_needed,
    touch_current_user,
)
from services.progression import get_grow_cost, get_life_xp_required, get_progress_percent

router = Router()

MEOW_COMMAND = "meow"
HUNT_COMMAND = "hunt"
MEOW_CHANCE_BY_LIFE = {
    1: 8,
    2: 15,
    3: 22,
    4: 28,
    5: 35,
    6: 42,
    7: 50,
    8: 60,
    9: 70,
}
MEOW_COOLDOWN_BY_LIFE = {
    1: 90,
    2: 80,
    3: 70,
    4: 50,
    5: 55,
    6: 50,
    7: 45,
    8: 40,
    9: 35,
}
MEOW_CLASS_CHANCE_BONUS = {
    "thief": 5,
    "assassin": 2,
    "support": 0,
    "warrior": 0,
}
MEOW_CLASS_REWARD_BONUS = {
    "support": 3,
    "warrior": 2,
    "thief": 0,
    "assassin": 0,
}
MEOW_CLASS_CRIT_BONUS = {
    "thief": 3,
    "assassin": 2,
    "support": 0,
    "warrior": 0,
}
MEOW_CLASS_FUMBLE_REDUCTION = {
    "warrior": 3,
    "thief": 1,
    "assassin": 1,
    "support": 0,
}
HUNT_CHANCE_BY_LIFE = {
    1: 35,
    2: 42,
    3: 49,
    4: 55,
    5: 61,
    6: 66,
    7: 71,
    8: 76,
    9: 80,
}
HUNT_COOLDOWN_BY_LIFE = {
    1: 120,
    2: 110,
    3: 100,
    4: 75,
    5: 80,
    6: 70,
    7: 65,
    8: 60,
    9: 50,
}
HUNT_CLASS_CHANCE_BONUS = {
    "assassin": 6,
    "thief": 3,
    "support": 2,
    "warrior": 0,
}
HUNT_CLASS_REWARD_BONUS = {
    "support": 1,
    "assassin": 1,
    "thief": 0,
    "warrior": 0,
}

def get_meow_chance(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    chance = MEOW_CHANCE_BY_LIFE[life_stage] + MEOW_CLASS_CHANCE_BONUS.get(cat_class, 0)
    return min(85, chance)


def get_meow_cooldown(user) -> int:
    life_stage = get_life_stage(user)
    return MEOW_COOLDOWN_BY_LIFE[life_stage]


def roll_meow_reward(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    base_min = 4 + life_stage * 2
    base_max = 14 + life_stage * 5
    return random.randint(base_min, base_max) + MEOW_CLASS_REWARD_BONUS.get(cat_class, 0)


def get_meow_crit_chance(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    chance = 4 + life_stage + MEOW_CLASS_CRIT_BONUS.get(cat_class, 0)
    return min(18, chance)


def get_meow_fumble_chance(user) -> int:
    cat_class = user["cat_class"] or "none"
    chance = 10 - MEOW_CLASS_FUMBLE_REDUCTION.get(cat_class, 0)
    return max(4, chance)


def roll_meow_penalty(user) -> int:
    life_stage = get_life_stage(user)
    return random.randint(2, 8 + life_stage * 2)


def get_hunt_chance(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    chance = HUNT_CHANCE_BY_LIFE[life_stage] + HUNT_CLASS_CHANCE_BONUS.get(cat_class, 0)
    return min(90, chance)


def get_hunt_cooldown(user) -> int:
    life_stage = get_life_stage(user)
    return HUNT_COOLDOWN_BY_LIFE[life_stage]


def get_hunt_crit_chance(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    bonus = 3 if cat_class == "assassin" else 0
    return min(20, 5 + life_stage + bonus)


def get_hunt_fumble_chance(user) -> int:
    cat_class = user["cat_class"] or "none"
    return 5 if cat_class == "warrior" else 10


def roll_hunt_reward(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    base_min = max(1, life_stage // 2)
    base_max = 2 + life_stage
    return random.randint(base_min, base_max) + HUNT_CLASS_REWARD_BONUS.get(cat_class, 0)

def is_real_file_id(file_id: str) -> bool:
    return bool(file_id and not file_id.startswith("FILE_ID_"))


async def answer_with_optional_photo(message: types.Message, photo_id: str, text: str):
    if is_real_file_id(photo_id):
        return await message.answer_photo(
            photo=photo_id,
            caption=text,
            parse_mode="HTML"
        )
    return await message.answer(text, parse_mode="HTML")

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await db.get_user(message.from_user.id)
    # Твой добытый file_id
    CATERPILLAR_ID = "CgACAgQAAxkBAAM_ae8C6qS_WOvOItIPpYjBzbQZrQ8AAk4ZAALdzQlS_ZW4sgFq3t47BA"

    if not user:
        await db.register_user(message.from_user.id, get_telegram_cat_name(message))
        await message.answer_animation(
            animation=CATERPILLAR_ID,
            caption=(
                f"🐱Добро пожаловать в Синдикат!\n\n"
                f"Твой статус: {CAT_STATUSES[1]}\n"
                "Воруй рыбов через /meow и расти в иерархии."
            ),
            parse_mode="HTML"
        )
    else:
        await touch_current_user(message, user)
        cat_name = await sync_cat_name_if_needed(message, user)
        status = CAT_STATUSES.get(user['life_stage'], "Ветеран")
        await message.answer(f"Мияу, {status} {escape(cat_name)}!")

@router.message(Command("meow"))
async def cmd_meow(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала /start")

    await touch_current_user(message, user)
    now = datetime.now()
    available_at = await db.get_cooldown(user_id, MEOW_COMMAND)
    if runtime_state.cooldowns_enabled and available_at and available_at > now:
        remaining = int((available_at - now).total_seconds())
        cooldown_text = format_cooldown(remaining)
        cooldown_message = random.choice(MEOW_COOLDOWN_VARIANTS).format(cooldown=cooldown_text)
        return await message.answer(
            cooldown_message,
            parse_mode="HTML"
        )

    chance = get_meow_chance(user)
    cooldown_seconds = get_meow_cooldown(user)
    fish_caught = roll_meow_reward(user)
    success = random.randint(1, 100) <= chance
    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, MEOW_COMMAND, now + timedelta(seconds=cooldown_seconds))

    if success:
        is_critical = random.randint(1, 100) <= get_meow_crit_chance(user)
        if is_critical:
            fish_caught = fish_caught * 2 + get_life_stage(user)
            variant = random.choice(MEOW_CRITICAL_VARIANTS)
            result_text = variant["text"]
            result_title = "💎 <b>Критический успех!</b>"
            image_id = variant["image"]
        else:
            variant = random.choice(MEOW_SUCCESS_VARIANTS)
            result_text = variant["text"]
            result_title = "🎯 <b>Успех!</b>"
            image_id = variant["image"]

        await db.update_balance(user_id, fish_caught)
        await answer_with_optional_photo(
            message,
            image_id,
            (
                f"{result_text}\n\n"
                f"{result_title} Ты стащил <b>{fish_caught}</b> 🐟.\n"
                f"Шанс операции: <b>{chance}%</b>"
            )
        )
    else:
        is_fumble = random.randint(1, 100) <= get_meow_fumble_chance(user)
        balance = user["balance"] or 0
        variant = random.choice(MEOW_FAILURE_VARIANTS)

        if is_fumble:
            fish_lost = min(balance, roll_meow_penalty(user))
            if fish_lost:
                await db.update_balance(user_id, -fish_lost)
                penalty_text = f"\nШтраф: <b>{fish_lost}</b> 🐟"
            else:
                penalty_text = "\nШтрафовать нечего: в карманах только шерсть."
            variant = random.choice(MEOW_FUMBLE_VARIANTS)
            result_text = variant["text"]
            result_title = "💥 <b>Критический провал!</b>"
            image_id = variant["image"]
        else:
            penalty_text = ""
            result_text = variant["text"]
            result_title = "❌ Провал."
            image_id = variant["image"]
        
        await answer_with_optional_photo(
            message,
            image_id,
            (
                f"{result_text}\n\n"
                f"{result_title}{penalty_text}\n"
                f"Шанс операции был: <b>{chance}%</b>"
            )
        )

@router.message(Command("hunt"))
async def cmd_hunt(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала /start")

    await touch_current_user(message, user)
    now = datetime.now()
    available_at = await db.get_cooldown(user_id, HUNT_COMMAND)
    if runtime_state.cooldowns_enabled and available_at and available_at > now:
        remaining = int((available_at - now).total_seconds())
        cooldown_text = format_cooldown(remaining)
        cooldown_message = random.choice(HUNT_COOLDOWN_VARIANTS).format(cooldown=cooldown_text)
        return await message.answer(cooldown_message, parse_mode="HTML")

    chance = get_hunt_chance(user)
    reward = roll_hunt_reward(user)
    success = random.randint(1, 100) <= chance
    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, HUNT_COMMAND, now + timedelta(seconds=get_hunt_cooldown(user)))

    if success:
        is_critical = random.randint(1, 100) <= get_hunt_crit_chance(user)
        if is_critical:
            reward = reward * 2 + 1
            variant = random.choice(HUNT_CRITICAL_VARIANTS)
            intro = variant["text"]
            image_id = variant["image"]
        else:
            intro = random.choice(HUNT_SUCCESS_VARIANTS)
            image_id = None

        await db.update_mice_count(user_id, reward)
        text = (
            f"{intro}\n\n"
            f"✅ Добыча: <b>{reward}</b> 🐭\n"
            f"Шанс охоты: <b>{chance}%</b>"
        )

        if is_critical:
            return await answer_with_optional_photo(message, image_id, text)

        return await message.answer(
            text,
            parse_mode="HTML"
        )

    mice_count = user["mice_count"] or 0
    lost_mouse = mice_count > 0 and random.randint(1, 100) <= get_hunt_fumble_chance(user)
    if lost_mouse:
        await db.update_mice_count(user_id, -1)
        variant = random.choice(HUNT_FUMBLE_VARIANTS)
        intro = variant["text"]
        extra = "\nПотеря: <b>1</b> 🐭"
        image_id = variant["image"]
    else:
        intro = random.choice(HUNT_FAILURE_VARIANTS)
        extra = ""
        image_id = None

    text = (
        f"{intro}\n\n"
        f"❌ Охота провалена.{extra}\n"
        f"Шанс охоты был: <b>{chance}%</b>"
    )

    if lost_mouse:
        return await answer_with_optional_photo(message, image_id, text)

    await message.answer(
        text,
        parse_mode="HTML"
    )


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user: return

    await touch_current_user(message, user)
    cat_name = await sync_cat_name_if_needed(message, user)
    life_xp = user["life_xp"] or 0
    required_xp = get_life_xp_required(user["life_stage"])
    progress = get_progress_percent(user["life_stage"], life_xp)
    next_life_text = "MAX" if user["life_stage"] >= 9 else f"{life_xp}/{required_xp} XP ({progress}%)"
    grow_cost_text = "Вознесение скоро" if user["life_stage"] >= 9 else f"{get_grow_cost(user)} 🐟"
    
    text = (
        f"📊 <b>ДОСЬЕ СИНДИКАТА</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 Кот: <code>{escape(cat_name)}</code>\n"
        f"🐾 Жизнь: <b>{user['life_stage']}/9</b>\n"
        f"💰 Баланс: <b>{user['balance']} рыбов</b>\n"
        f"🐭 Мыши: <b>{user['mice_count'] or 0}</b>\n"
        f"📈 Шанс кражи: <b>{get_meow_chance(user)}%</b>\n"
        f"🎯 Шанс охоты: <b>{get_hunt_chance(user)}%</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"📚 Опыт жизни: <b>{next_life_text}</b>\n"
        f"💡 Попытка роста стоит: <code>{grow_cost_text}</code>\n"
        f"Используй /grow чтобы стать круче."
    )
    # Здесь можно прикрепить ту самую крутую картинку Синдиката
    await message.answer(text, parse_mode="HTML")

@router.message(Command("reset_me"))
async def cmd_reset(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, есть ли вообще кто-то
    user = await db.get_user(user_id)
    
    if user:
        await db.delete_user(user_id)
        await message.answer(
            "⚠️ <b>Профиль Синдиката аннигилирован!</b>\n"
            "Твои рыбы сгорели, а жизнь обнулилась. Пиши /start, чтобы начать с чистого листа.",
            parse_mode="HTML"
        )
    else:
        await message.answer("А тебя и так нет в списках Синдиката. Нечего удалять!")



