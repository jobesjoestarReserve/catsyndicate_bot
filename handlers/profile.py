from aiogram import Router, types
from aiogram.filters import Command
from database.db_manager import db
from data.constants import CAT_STATUSES, CAT_CLASSES

router = Router()

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user: return await message.answer("Сначала /start")

    status = CAT_STATUSES.get(user['life_stage'], "Ветеран")
    # Предположим, в БД потом добавим колонку class_name
    cat_class = CAT_CLASSES.get(user.get('class_name', 'none'))
    
    # Расчет прогресса (оставляем твою логику)
    next_level_cost = user['life_stage'] * 500
    progress = min(100, int((user['balance'] / next_level_cost) * 100))
    bar = "🟩" * (progress // 10) + "⬜" * (10 - (progress // 10))

    text = (
        f"👤 <b>Имя:</b> {user['cat_name']}\n"
        f"🎗 <b>Статус:</b> {status}\n"
        f"🎭 <b>Класс:</b> {cat_class}\n"
        f"💰 <b>Баланс:</b> {user['balance']} 🐟\n\n"
        f"📈 <b>Опыт жизни:</b>\n<code>{bar}</code> {progress}%"
    )
    await message.answer(text, parse_mode="HTML")