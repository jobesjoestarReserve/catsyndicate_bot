from aiogram import F, Router, types
from aiogram.filters import Command

from database.db_manager import db
from services.crafting import get_equipment_slot, SLOT_LABELS
from services.text_aliases import INVENTORY_ALIASES, is_alias
from services.ui import inventory_keyboard

router = Router()

RESOURCE_LABELS = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}


async def get_inventory_view(user_id: int, user):
    resources = await db.get_resources(user_id)
    consumables = await db.get_inventory_items(user_id, "consumable")
    equipment = await db.get_inventory_items(user_id, "equipment")
    equipped = await db.get_equipped_items(user_id)
    if resources:
        resources_text = "\n".join(
            f"• {RESOURCE_LABELS.get(row['item_name'], row['item_name'])}: <b>{row['amount']}</b>"
            for row in resources
        )
    else:
        resources_text = "Ресурсов пока нет. Для крафта отправь мышей в шахту: <code>/send_mice mine</code>"

    consumables_text = (
        "\n".join(f"• {row['item_name']}: <b>{row['amount']}</b>" for row in consumables)
        if consumables
        else "Расходников пока нет. Собери их через <code>/craft</code>."
    )
    equipment_text = (
        "\n".join(f"• {row['item_name']}: <b>{row['amount']}</b>" for row in equipment)
        if equipment
        else "Свободной экипировки нет. Собери броню через <code>/craft</code>."
    )
    equipped_lines = []
    for row in equipped:
        slot = get_equipment_slot(row["item_name"])
        label = SLOT_LABELS.get(slot, "слот")
        equipped_lines.append(f"• {label}: <b>{row['item_name']}</b>")
    equipped_text = "\n".join(equipped_lines) if equipped_lines else "Ничего не надето. Используй <code>/equip название</code>."

    text = (
        "🎒 <b>Инвентарь Синдиката</b>\n\n"
        f"🐟 Рыбов: <b>{user['balance']}</b>\n"
        f"🐭 Мышей: <b>{user['mice_count'] or 0}</b>\n"
        "💼 Рыбы добываются через <code>/work</code>, ресурсы — через <code>/send_mice mine</code>.\n\n"
        "<b>Ресурсы для крафта:</b>\n"
        f"{resources_text}\n\n"
        "<b>Расходники:</b>\n"
        f"{consumables_text}\n\n"
        "<b>Свободная экипировка:</b>\n"
        f"{equipment_text}\n\n"
        "<b>Надето:</b>\n"
        f"{equipped_text}"
    )
    return text, inventory_keyboard(consumables, equipment)


@router.message(F.text == "🎒 Инвентарь")
@router.message(lambda message: is_alias(message.text, INVENTORY_ALIASES))
@router.message(Command("inv"))
async def cmd_inventory(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала /start")

    await db.touch_user(user_id)
    text, keyboard = await get_inventory_view(user_id, user)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "open:inv")
async def cb_open_inventory(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Сначала /start", show_alert=True)
        return

    await db.touch_user(user_id)
    text, keyboard = await get_inventory_view(user_id, user)
    await callback.answer()
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
