from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("inv"))
async def cmd_inventory(message: types.Message):
    # Здесь в будущем будет запрос к таблице inventory
    await message.answer("🎒 <b>Ваш инвентарь пуст</b>\n(Здесь будут мыши и артефакты)", parse_mode="HTML")