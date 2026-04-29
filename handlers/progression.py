import random
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.filters import Command

from data.constants import CAT_STATUSES
from data.runtime_state import runtime_state
from data.texts import GROW_TEXTS
from database.db_manager import db
from services.game_utils import format_cooldown, get_life_stage, touch_current_user
from services.crafting import get_equipment_bonus
from services.text_aliases import GROW_ALIASES, is_alias
from services.progression import (
    GROW_COMMAND,
    apply_xp_to_life,
    format_progress_bar,
    get_grow_cooldown,
    get_grow_cost,
    get_grow_crit_chance,
    get_grow_fumble_chance,
    get_grow_success_chance,
    get_life_xp_required,
    get_progress_percent,
    roll_grow_xp,
)

router = Router()


def get_life_xp(user) -> int:
    try:
        return user["life_xp"] or 0
    except (KeyError, IndexError):
        return 0


def format_grow_title(outcome: str) -> str:
    return {
        "critical_success": "🌟 <b>Критический рост!</b>",
        "success": "✅ <b>Рост засчитан.</b>",
        "failure": "⚠️ <b>Рост почти случился.</b>",
        "critical_failure": "💥 <b>Критический конфуз.</b>",
    }[outcome]


def roll_grow_outcome_with_chance(user, success_chance: int) -> str:
    if random.randint(1, 100) <= success_chance:
        if random.randint(1, 100) <= get_grow_crit_chance(user):
            return "critical_success"
        return "success"
    if random.randint(1, 100) <= get_grow_fumble_chance(user):
        return "critical_failure"
    return "failure"


@router.message(lambda message: is_alias(message.text, GROW_ALIASES))
@router.message(Command("grow", "upgrade"))
async def cmd_grow(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала /start")
    await touch_current_user(message, user)

    life_stage = get_life_stage(user)
    if life_stage >= 9:
        return await message.answer(
            "👑 Ты уже <b>Дон Мяулеоне</b>. Дальше будет только Вознесение, золотые усы и налоговая паника.",
            parse_mode="HTML",
        )

    now = datetime.now()
    available_at = await db.get_cooldown(user_id, GROW_COMMAND)
    if runtime_state.cooldowns_enabled and available_at and available_at > now:
        cooldown_text = format_cooldown(int((available_at - now).total_seconds()))
        return await message.answer(
            f"🕰️ Организм ещё переваривает прошлую попытку величия. Ждать: <b>{cooldown_text}</b>.",
            parse_mode="HTML",
        )

    cost = get_grow_cost(user)
    balance = user["balance"] or 0
    if balance < cost:
        return await message.answer(
            (
                f"🐟 Для роста нужно <b>{cost}</b> рыбов, а в миске сейчас <b>{balance}</b>.\n"
                "Добывай рыбов через <code>/meow</code>, <code>/work</code> или события."
            ),
            parse_mode="HTML",
        )

    equipped = await db.get_equipped_items(user_id)
    grow_bonus = get_equipment_bonus(equipped, "grow_chance")
    grow_buff = await db.consume_buff(user_id, "grow_focus")
    grow_chance = min(95, get_grow_success_chance(user) + grow_bonus + (10 if grow_buff is not None else 0))
    outcome = roll_grow_outcome_with_chance(user, grow_chance)
    gained_xp = roll_grow_xp(user, outcome)
    if grow_buff is not None and gained_xp > 0:
        gained_xp = int(gained_xp * 1.1)
    old_life_xp = get_life_xp(user)
    new_life_stage, new_life_xp, promoted = apply_xp_to_life(life_stage, old_life_xp, gained_xp)

    result = await db.apply_grow_result(user_id, cost, new_life_stage, new_life_xp)
    if not result:
        return await message.answer("🐟 Рыбы исчезли из расчётов. Проверь баланс и попробуй ещё раз.")

    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, GROW_COMMAND, now + timedelta(seconds=get_grow_cooldown(user)))

    required = get_life_xp_required(new_life_stage)
    percent = get_progress_percent(new_life_stage, new_life_xp)
    progress_line = (
        "Прогресс жизни: <b>MAX</b>"
        if new_life_stage >= 9
        else f"Прогресс жизни: <code>{format_progress_bar(percent)}</code> <b>{new_life_xp}/{required}</b> XP"
    )
    promoted_text = ""
    if promoted:
        old_status = CAT_STATUSES.get(life_stage, "Старая жизнь")
        new_status = CAT_STATUSES.get(new_life_stage, "Новая жизнь")
        promoted_text = (
            f"\n\n🎉 <b>Новая жизнь!</b>\n"
            f"{old_status} → {new_status}"
        )

    await message.answer(
        (
            f"{format_grow_title(outcome)}\n"
            f"{random.choice(GROW_TEXTS[outcome])}\n\n"
            f"Потрачено: <b>{cost}</b> 🐟\n"
            f"Получено: <b>{gained_xp}</b> XP\n"
            f"Шанс роста: <b>{grow_chance}%</b>\n"
            f"Жизнь: <b>{new_life_stage}/9</b>\n"
            f"{progress_line}\n"
            f"Баланс: <b>{result['balance']}</b> 🐟"
            f"{promoted_text}"
            + ("\n🧪 Валерьянка сработала на эту попытку." if grow_buff is not None else "")
        ),
        parse_mode="HTML",
    )
