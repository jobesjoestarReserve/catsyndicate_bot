from html import escape

from aiogram import Router, types
from aiogram.filters import Command

from database.db_manager import db
from data.constants import CAT_STATUSES, CAT_CLASSES
from services.game_utils import get_telegram_cat_name, is_broken_name, require_current_user
from services.progression import format_progress_bar, get_life_xp_required, get_progress_percent
from services.text_aliases import PROFILE_ALIASES, is_alias
from services.ui import main_menu_keyboard

router = Router()


@router.message(lambda message: is_alias(message.text, PROFILE_ALIASES))
@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = await require_current_user(message)
    if not user:
        return

    cat_name = user["cat_name"]
    telegram_name = get_telegram_cat_name(message)
    if is_broken_name(cat_name) or cat_name != telegram_name:
        cat_name = await db.update_cat_name(message.from_user.id, telegram_name)

    status = CAT_STATUSES.get(user["life_stage"], "Ветеран")
    cat_class = CAT_CLASSES.get(user["cat_class"] or "none")

    life_xp = user["life_xp"] or 0
    required_xp = get_life_xp_required(user["life_stage"])
    progress = get_progress_percent(user["life_stage"], life_xp)
    bar = format_progress_bar(progress)
    progress_text = "MAX" if user["life_stage"] >= 9 else f"{life_xp}/{required_xp} XP"

    text = (
        f"👤 <b>Имя:</b> {escape(cat_name)}\n"
        f"🏷 <b>Статус:</b> {status}\n"
        f"🎭 <b>Класс:</b> {cat_class}\n"
        f"💰 <b>Баланс:</b> {user['balance']} 🐟\n\n"
        f"📈 <b>Опыт жизни:</b>\n<code>{bar}</code> {progress}% — <b>{progress_text}</b>\n"
        f"Расти: <code>расти</code>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
