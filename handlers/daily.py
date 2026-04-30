from aiogram import F, Router, types
from aiogram.filters import Command

from database.db_manager import db
from services.daily import (
    DIFFICULTY_LABELS,
    STREAK_SAVE_LIMIT,
    are_daily_tasks_complete,
    format_daily_reward,
    get_or_create_daily_state,
)
from services.game_utils import require_callback_user, require_current_user
from services.text_aliases import DAILY_ALIASES, is_alias
from services.ui import daily_keyboard, main_menu_keyboard

router = Router()


def format_daily_state(state) -> str:
    difficulty = DIFFICULTY_LABELS.get(state["difficulty"], state["difficulty"])
    save_notice = ""
    if state.get("saved_missed_days"):
        days = state["saved_missed_days"]
        day_word = "день" if days == 1 else "дня"
        save_notice = f"\n🛟 Сейв стрика спас пропущенный {days} {day_word}: {state.get('save_text')}"
    lines = []
    for task in state["tasks"]:
        mark = "✅" if task["current"] >= task["goal"] else "❌"
        lines.append(f"{mark} {task['title']} [{task['current']}/{task['goal']}]")

    status = "получена" if state["claimed"] else "можно забрать" if are_daily_tasks_complete(state["tasks"]) else "в процессе"
    return (
        "📅 <b>Ежедневные задания Синдиката</b>\n\n"
        f"Сложность: <b>{difficulty}</b>\n"
        f"День стрика: <b>{state['streak_day']}</b>\n"
        f"Сейвы стрика: <b>{state.get('streak_saves_remaining', STREAK_SAVE_LIMIT)}/{STREAK_SAVE_LIMIT}</b>\n"
        f"Статус: <b>{status}</b>\n\n"
        + (save_notice + "\n\n" if save_notice else "")
        + "\n".join(lines)
        + "\n\n<b>Награда:</b>\n"
        + format_daily_reward(state["reward"])
    )


@router.message(F.text == "📅 Ежедневки")
@router.message(lambda message: is_alias(message.text, DAILY_ALIASES))
@router.message(Command("daily"))
async def cmd_daily(message: types.Message):
    user_id = message.from_user.id
    user = await require_current_user(message)
    if not user:
        return

    state = await get_or_create_daily_state(user_id)
    await message.answer(
        format_daily_state(state),
        parse_mode="HTML",
        reply_markup=daily_keyboard(are_daily_tasks_complete(state["tasks"]) and not state["claimed"]),
    )


@router.callback_query(F.data == "daily_home")
async def cb_daily_home(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    state = await get_or_create_daily_state(user_id)
    await callback.answer()
    await callback.message.edit_text(
        format_daily_state(state),
        parse_mode="HTML",
        reply_markup=daily_keyboard(are_daily_tasks_complete(state["tasks"]) and not state["claimed"]),
    )


@router.callback_query(F.data == "daily_claim")
async def cb_daily_claim(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    state = await get_or_create_daily_state(user_id)
    result = await db.claim_daily_quest(user_id, state["quest_date"])
    if not result:
        await callback.answer("Награда уже забрана", show_alert=True)
        return
    if not result["ok"]:
        await callback.answer("Не все задания выполнены", show_alert=True)
        return

    claimed = result["state"]
    await callback.answer("Награда забрана")
    await callback.message.answer(
        (
            "🎁 <b>Ежедневная награда забрана!</b>\n\n"
            f"День стрика: <b>{claimed['streak_day']}</b>\n"
            + format_daily_reward(claimed["reward"])
        ),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
