from html import escape

from aiogram import F, Router, types
from aiogram.filters import Command

from database.db_manager import db
from services.crafting import get_equipment_slot, SLOT_LABELS
from services.game_utils import require_callback_user, require_current_user
from services.text_aliases import INVENTORY_ALIASES, is_alias
from services.ui import inventory_keyboard

router = Router()

RESOURCE_LABELS = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}


def format_inventory_text(user, resources, consumables, equipment, equipped) -> str:
    if resources:
        resources_text = "\n".join(
            f"• {escape(RESOURCE_LABELS.get(row['item_name'], row['item_name']))}: <b>{row['amount']}</b>"
            for row in resources
        )
    else:
        resources_text = "Ресурсов пока нет. Для крафта отправь мышей в подвал: <code>подвал</code> или <code>подвал 5</code>."

    consumables_text = (
        "\n".join(f"• {escape(row['item_name'])}: <b>{row['amount']}</b>" for row in consumables)
        if consumables
        else "Расходников пока нет. Собери их в кузнице."
    )
    equipment_text = (
        "\n".join(f"• {escape(row['item_name'])}: <b>{row['amount']}</b>" for row in equipment)
        if equipment
        else "Свободной экипировки нет. Собери броню в кузнице."
    )
    equipped_lines = []
    for row in equipped:
        slot = get_equipment_slot(row["item_name"])
        label = SLOT_LABELS.get(slot, "слот")
        equipped_lines.append(f"• {label}: <b>{escape(row['item_name'])}</b>")
    equipped_text = "\n".join(equipped_lines) if equipped_lines else "Ничего не надето. Нажми кнопку предмета в инвентаре или напиши <code>надеть название</code>."

    return (
        "🎒 <b>Инвентарь Синдиката</b>\n\n"
        f"🐟 Рыбов: <b>{user['balance']}</b>\n"
        f"🐭 Мышей: <b>{user['mice_count'] or 0}</b>\n"
        "💼 Рыбы добываются через <code>работа</code>, ресурсы — через <code>подвал</code>.\n\n"
        "<b>Ресурсы для крафта:</b>\n"
        f"{resources_text}\n\n"
        "<b>Расходники:</b>\n"
        f"{consumables_text}\n\n"
        "<b>Свободная экипировка:</b>\n"
        f"{equipment_text}\n\n"
        "<b>Надето:</b>\n"
        f"{equipped_text}"
    )


async def get_inventory_view(user_id: int, user):
    resources = await db.get_resources(user_id)
    consumables = await db.get_inventory_items(user_id, "consumable")
    equipment = await db.get_inventory_items(user_id, "equipment")
    equipped = await db.get_equipped_items(user_id)
    text = format_inventory_text(user, resources, consumables, equipment, equipped)
    return text, inventory_keyboard(consumables, equipment)


@router.message(F.text == "🎒 Инвентарь")
@router.message(lambda message: is_alias(message.text, INVENTORY_ALIASES))
@router.message(Command("inv"))
async def cmd_inventory(message: types.Message):
    user_id = message.from_user.id
    user = await require_current_user(message)
    if not user:
        return

    text, keyboard = await get_inventory_view(user_id, user)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "open:inv")
async def cb_open_inventory(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    text, keyboard = await get_inventory_view(user_id, user)
    await callback.answer()
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
