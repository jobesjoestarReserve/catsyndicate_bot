from html import escape

from aiogram import F, Router, types
from aiogram.filters import Command

from database.db_manager import db
from services.crafting import (
    BUFF_LABELS,
    RESOURCE_LABELS,
    SLOT_LABELS,
    format_cost,
    format_recipe_category,
    get_category_recipe_ids,
    get_consumable_effect,
    get_equipment_slot,
    get_item,
    get_recipe,
    get_recipe_id,
    get_slot_item_names,
)
from services.game_utils import touch_current_user
from services.text_aliases import (
    CRAFT_ALIASES,
    EQUIP_PREFIXES,
    GEAR_ALIASES,
    USE_ITEM_PREFIXES,
    is_alias,
    parse_prefixed_arg,
)
from services.ui import craft_home_keyboard, gear_keyboard, recipe_keyboard

router = Router()


def get_args(message: types.Message) -> list[str]:
    return (message.text or "").split()[1:]


def get_named_arg(message: types.Message, prefixes: set[str]) -> str | None:
    prefixed = parse_prefixed_arg(message.text, prefixes)
    if prefixed is not None:
        return prefixed
    args = get_args(message)
    return " ".join(args) if args else None


def format_missing_resource(name: str, needed: int, available: int) -> str:
    label = RESOURCE_LABELS.get(name, name)
    return (
        f"Не хватает ресурса: <b>{label}</b>.\n"
        f"Нужно: <b>{needed}</b>, есть: <b>{available}</b>."
    )


def format_craft_home() -> str:
    return (
        "🛠 <b>Кузница Синдиката</b>\n\n"
        "Выбери раздел. Рецепты собираются кнопками, без ручного ввода id."
    )


async def craft_recipe_for_user(user_id: int, recipe_id: str) -> tuple[str, bool]:
    recipe = get_recipe(recipe_id)
    if not recipe:
        return "Такого рецепта нет. Вернись в кузницу и выбери кнопку.", False

    result = await db.craft_inventory_item(
        user_id=user_id,
        cost=recipe["cost"],
        item_name=recipe["name"],
        item_type=recipe["type"],
    )
    if not result["ok"]:
        return format_missing_resource(result["missing"], result["needed"], result["available"]), False

    amount_text = ""
    if recipe["type"] == "consumable":
        amount_text = f"\nВ запасе: <b>{result['amount']}</b> шт."
    return (
        f"✅ <b>Собрано:</b> {escape(recipe['name'])}\n"
        f"Цена: {format_cost(recipe['cost'])}"
        f"{amount_text}"
    ), True


@router.message(F.text == "🛠 Кузница")
@router.message(lambda message: is_alias(message.text, CRAFT_ALIASES))
@router.message(Command("craft"))
async def cmd_craft(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала напиши <code>старт</code>.", parse_mode="HTML")
    await touch_current_user(message, user)

    args = get_args(message)
    if not args:
        return await message.answer(
            format_craft_home(),
            parse_mode="HTML",
            reply_markup=craft_home_keyboard(),
        )

    recipe_id = get_recipe_id(" ".join(args))
    text, _ = await craft_recipe_for_user(user_id, recipe_id)
    await message.answer(text, parse_mode="HTML", reply_markup=craft_home_keyboard())


@router.callback_query(F.data == "craft_home")
async def cb_craft_home(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        format_craft_home(),
        parse_mode="HTML",
        reply_markup=craft_home_keyboard(),
    )


@router.callback_query(F.data.startswith("craft_cat:"))
async def cb_craft_category(callback: types.CallbackQuery):
    category = callback.data.split(":", 1)[1]
    recipe_ids = get_category_recipe_ids(category)
    await callback.answer()
    await callback.message.edit_text(
        format_recipe_category(category),
        parse_mode="HTML",
        reply_markup=recipe_keyboard(recipe_ids),
    )


@router.callback_query(F.data.startswith("craft_make:"))
async def cb_craft_make(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Сначала напиши старт", show_alert=True)
        return
    recipe_id = callback.data.split(":", 1)[1]
    text, ok = await craft_recipe_for_user(user_id, recipe_id)
    await callback.answer("Собрано" if ok else "Не хватает ресурсов", show_alert=not ok)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=craft_home_keyboard())


@router.callback_query(F.data.startswith("equip_item:"))
async def cb_equip_item(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Сначала напиши старт", show_alert=True)
        return

    recipe_id = callback.data.split(":", 1)[1]
    recipe = get_recipe(recipe_id)
    if not recipe or recipe["type"] != "equipment":
        await callback.answer("Это не экипировка", show_alert=True)
        return

    item_name = recipe["name"]
    slot = get_equipment_slot(item_name)
    equipped = await db.equip_item(user_id, item_name, get_slot_item_names(slot))
    if not equipped:
        await callback.answer("Предмета нет в инвентаре", show_alert=True)
        return

    await callback.answer("Надето")
    await callback.message.answer(
        f"🧷 Надето: <b>{escape(item_name)}</b>\nСлот: <b>{SLOT_LABELS[slot]}</b>",
        parse_mode="HTML",
        reply_markup=gear_keyboard(),
    )


@router.callback_query(F.data.startswith("use_item:"))
async def cb_use_item(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Сначала напиши старт", show_alert=True)
        return

    recipe_id = callback.data.split(":", 1)[1]
    recipe = get_recipe(recipe_id)
    if not recipe or recipe["type"] != "consumable":
        await callback.answer("Это не расходник", show_alert=True)
        return

    item_name = recipe["name"]
    effect = recipe["effect"]
    remaining = await db.consume_inventory_item(user_id, item_name, "consumable")
    if remaining is None:
        await callback.answer("Расходника нет в инвентаре", show_alert=True)
        return

    await db.add_buff(user_id, effect, uses=1)
    await callback.answer("Использовано")
    await callback.message.answer(
        (
            f"🧪 Использовано: <b>{escape(item_name)}</b>\n"
            f"{BUFF_LABELS[effect]}\n"
            f"Осталось расходников: <b>{remaining}</b>"
        ),
        parse_mode="HTML",
    )


@router.message(lambda message: parse_prefixed_arg(message.text, EQUIP_PREFIXES) is not None)
@router.message(Command("equip"))
async def cmd_equip(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала напиши <code>старт</code>.", parse_mode="HTML")
    await touch_current_user(message, user)

    item_name = get_named_arg(message, EQUIP_PREFIXES)
    if not item_name:
        return await message.answer(
            "Напиши: <code>надеть название предмета</code>\nПосмотреть экипировку можно фразой <code>экипировка</code>.",
            parse_mode="HTML",
        )

    recipe_id = get_recipe_id(item_name)
    recipe = get_recipe(recipe_id) if recipe_id else None
    item_name = recipe["name"] if recipe else item_name
    slot = get_equipment_slot(item_name)
    if not slot:
        return await message.answer("Это не экипировка из кузницы. Проверь название в инвентаре или кузнице.")

    equipped = await db.equip_item(user_id, item_name, get_slot_item_names(slot))
    if not equipped:
        return await message.answer("Такого предмета нет в инвентаре или он уже надет.")

    await message.answer(
        f"🧷 Надето: <b>{escape(item_name)}</b>\nСлот: <b>{SLOT_LABELS[slot]}</b>",
        parse_mode="HTML",
    )


@router.message(F.text == "🧥 Экипировка")
@router.message(lambda message: is_alias(message.text, GEAR_ALIASES))
@router.message(Command("gear"))
async def cmd_gear(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала напиши <code>старт</code>.", parse_mode="HTML")
    await touch_current_user(message, user)

    equipped = await db.get_equipped_items(user_id)
    by_slot = {}
    for row in equipped:
        slot = get_equipment_slot(row["item_name"])
        if slot:
            by_slot[slot] = row["item_name"]

    lines = []
    for slot, label in SLOT_LABELS.items():
        item_name = by_slot.get(slot)
        lines.append(f"• {label}: <b>{escape(item_name)}</b>" if item_name else f"• {label}: пусто")

    await message.answer(
        "🧥 <b>Экипировка</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=gear_keyboard(),
    )


@router.callback_query(F.data == "open:gear")
async def cb_open_gear(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Сначала напиши старт", show_alert=True)
        return
    equipped = await db.get_equipped_items(user_id)
    by_slot = {}
    for row in equipped:
        slot = get_equipment_slot(row["item_name"])
        if slot:
            by_slot[slot] = row["item_name"]

    lines = []
    for slot, label in SLOT_LABELS.items():
        item_name = by_slot.get(slot)
        lines.append(f"• {label}: <b>{escape(item_name)}</b>" if item_name else f"• {label}: пусто")

    await callback.answer()
    await callback.message.edit_text(
        "🧥 <b>Экипировка</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=gear_keyboard(),
    )


@router.message(lambda message: parse_prefixed_arg(message.text, USE_ITEM_PREFIXES) is not None)
@router.message(Command("use"))
async def cmd_use(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала напиши <code>старт</code>.", parse_mode="HTML")
    await touch_current_user(message, user)

    item_name = get_named_arg(message, USE_ITEM_PREFIXES)
    if not item_name:
        return await message.answer(
            "Напиши: <code>использовать название расходника</code>\nРасходники видны в инвентаре.",
            parse_mode="HTML",
        )

    recipe_id = get_recipe_id(item_name)
    recipe = get_recipe(recipe_id) if recipe_id else None
    item_name = recipe["name"] if recipe else item_name
    effect = get_consumable_effect(item_name)
    if not effect:
        return await message.answer("Это не расходник из кузницы. Проверь название в инвентаре или кузнице.")

    remaining = await db.consume_inventory_item(user_id, item_name, "consumable")
    if remaining is None:
        return await message.answer("Такого расходника нет в инвентаре.")

    await db.add_buff(user_id, effect, uses=1)
    item = get_item(item_name)
    await message.answer(
        (
            f"🧪 Использовано: <b>{escape(item_name)}</b>\n"
            f"{BUFF_LABELS[effect]}\n"
            f"Осталось расходников: <b>{remaining}</b>"
            + (f"\n\n{escape(item['description'])}" if item else "")
        ),
        parse_mode="HTML",
    )
