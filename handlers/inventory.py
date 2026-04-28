from aiogram import Router, types
from aiogram.filters import Command

from database.db_manager import db

router = Router()

RESOURCE_LABELS = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}


@router.message(Command("inv"))
async def cmd_inventory(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала /start")

    await db.touch_user(message.from_user.id)
    resources = await db.get_resources(message.from_user.id)
    if resources:
        resources_text = "\n".join(
            f"• {RESOURCE_LABELS.get(row['item_name'], row['item_name'])}: <b>{row['amount']}</b>"
            for row in resources
        )
    else:
        resources_text = "Ресурсов пока нет. Для крафта отправь мышей в шахту: <code>/send_mice mine</code>"

    await message.answer(
        (
            "🎒 <b>Инвентарь Синдиката</b>\n\n"
            f"🐟 Рыбов: <b>{user['balance']}</b>\n"
            f"🐭 Мышей: <b>{user['mice_count'] or 0}</b>\n"
            "💼 Рыбы добываются через <code>/work</code>, ресурсы — через <code>/send_mice mine</code>.\n\n"
            "<b>Ресурсы для крафта:</b>\n"
            f"{resources_text}"
        ),
        parse_mode="HTML"
    )
