import random
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import Command

from data.constants import CAT_CLASSES, CAT_STATUSES
from data.runtime_state import runtime_state
from data.texts import GROW_TEXTS
from database.db_manager import db
from services.game_utils import get_active_cooldown_text, get_life_stage, require_callback_user, require_current_user
from services.crafting import get_equipment_bonus
from services.daily import DAILY_ACTION_GROW, record_daily_action
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
from services.crafting import WEAPON_CLASS_LABELS
from services.ui import class_selection_keyboard

router = Router()

CLASS_UNLOCK_LIFE_STAGE = 2


def should_offer_class_selection(user, old_life_stage: int, new_life_stage: int) -> bool:
    return (
        old_life_stage < CLASS_UNLOCK_LIFE_STAGE <= new_life_stage
        and (user["cat_class"] or "none") == "none"
    )


def format_class_unlock_text() -> str:
    return (
        "\n\n🎭 <b>Открыта специализация!</b>\n"
        "Выбери класс кота. Это одноразовое решение: оно откроет классовое оружие и профильные бонусы."
    )


async def choose_class_for_user(user_id: int, user, cat_class: str) -> tuple[str, bool, str]:
    if cat_class not in WEAPON_CLASS_LABELS:
        return "Такого класса нет. Синдикат проверил журнал, печать и подозрительный хвост.", False, "Класс не найден"
    if (user["cat_class"] or "none") != "none":
        return "Класс уже выбран. Синдикат не любит метания между профессиями без отдельной реформы.", False, "Класс уже выбран"
    if (user["life_stage"] or 1) < CLASS_UNLOCK_LIFE_STAGE:
        return "Классы открываются со второй жизни. Сначала подрасти, потом получишь важную шапку с должностью.", False, "Класс ещё закрыт"

    selected = await db.set_cat_class(user_id, cat_class)
    if not selected:
        return "Класс не удалось выбрать. Возможно, он уже выбран или жизнь ещё не доросла до бюрократии.", False, "Класс не выбран"

    return (
        f"🎭 <b>Класс выбран:</b> {CAT_CLASSES[cat_class]}\n"
        "Теперь можно ковать оружие своего класса в кузнице.",
        True,
        "Класс выбран",
    )


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
    user = await require_current_user(message)
    if not user:
        return

    life_stage = get_life_stage(user)
    if life_stage >= 9:
        return await message.answer(
            "👑 Ты уже <b>Дон Мяулеоне</b>. Дальше будет только Вознесение, золотые усы и налоговая паника.",
            parse_mode="HTML",
        )

    now = datetime.now()
    cooldown_text = await get_active_cooldown_text(
        user_id,
        GROW_COMMAND,
        now,
        runtime_state.cooldowns_enabled,
    )
    if cooldown_text:
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
                "Добывай рыбов через <code>мяу</code>, <code>работа</code> или события."
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
    await record_daily_action(user_id, DAILY_ACTION_GROW)

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

    class_keyboard = class_selection_keyboard() if should_offer_class_selection(user, life_stage, new_life_stage) else None
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
            + (format_class_unlock_text() if class_keyboard else "")
            + ("\n🧪 Валерьянка сработала на эту попытку." if grow_buff is not None else "")
        ),
        parse_mode="HTML",
        reply_markup=class_keyboard,
    )


@router.callback_query(F.data.startswith("choose_class:"))
async def cb_choose_class(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    cat_class = callback.data.split(":", 1)[1]
    text, ok, alert = await choose_class_for_user(user_id, user, cat_class)
    await callback.answer(alert, show_alert=not ok)
    if ok:
        await callback.message.edit_text(text, parse_mode="HTML")
