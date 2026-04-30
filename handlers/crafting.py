import random
from html import escape

from aiogram import F, Router, types
from aiogram.filters import Command

from database.db_manager import db
from services.crafting import (
    BUFF_LABELS,
    CRAFT_OUTCOME_TEXTS,
    RESOURCE_LABELS,
    SLOT_LABELS,
    format_cost,
    format_recipe_category,
    get_forging_cost,
    get_forging_create_amount_for_recipe,
    get_category_recipe_ids,
    get_consumable_effect,
    get_equipment_class,
    get_equipment_slot,
    get_item,
    get_recipe,
    get_recipe_id,
    get_slot_item_names,
    get_upgraded_equipment_recipe_id,
    roll_forging_outcome,
)
from services.daily import DAILY_ACTION_CRAFT, record_daily_action
from services.game_utils import require_callback_user, require_current_user
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
    if name == "fish":
        return (
            "Кузнец уважает искусство, но работает за рыбов.\n"
            f"Нужно: <b>{needed}</b> 🐟, есть: <b>{available}</b> 🐟."
        )
    label = RESOURCE_LABELS.get(name, name)
    return (
        f"Не хватает ресурса: <b>{label}</b>.\n"
        f"Нужно: <b>{needed}</b>, есть: <b>{available}</b>."
    )


def format_craft_home() -> str:
    return (
        "🛠 <b>Кузница Синдиката</b>\n\n"
        "Выбери раздел. Здесь куют экипировку и оружие за ресурсы плюс небольшую оплату рыбами."
    )


def format_gear_view(equipped) -> str:
    by_slot = {}
    for row in equipped:
        slot = get_equipment_slot(row["item_name"])
        if slot:
            by_slot[slot] = row["item_name"]

    lines = []
    for slot, label in SLOT_LABELS.items():
        item_name = by_slot.get(slot)
        lines.append(f"• {label}: <b>{escape(item_name)}</b>" if item_name else f"• {label}: пусто")

    return "🧥 <b>Экипировка</b>\n\n" + "\n".join(lines)


def can_equip_for_class(user, item_name: str) -> bool:
    item_class = get_equipment_class(item_name)
    return item_class is None or (user["cat_class"] or "none") == item_class


async def craft_recipe_for_user(user_id: int, recipe_id: str) -> tuple[str, bool]:
    recipe = get_recipe(recipe_id)
    if not recipe:
        return "Такого рецепта нет. Вернись в кузницу и выбери кнопку.", False
    if recipe["type"] != "equipment":
        return "Расходники теперь продаются в лавке. Открой <code>магазин</code>.", False

    outcome = roll_forging_outcome()
    forged_recipe = recipe
    upgraded_equipment_recipe_id = None
    if outcome == "critical_success":
        upgraded_equipment_recipe_id = get_upgraded_equipment_recipe_id(recipe_id)
        if upgraded_equipment_recipe_id:
            forged_recipe = get_recipe(upgraded_equipment_recipe_id)

    cost = get_forging_cost(recipe, outcome)
    create_amount = get_forging_create_amount_for_recipe(recipe, outcome)
    result = await db.craft_inventory_item(
        user_id=user_id,
        cost=cost,
        item_name=forged_recipe["name"],
        item_type=forged_recipe["type"],
        create_amount=create_amount,
        fish_cost=recipe.get("fish_cost", 0),
    )
    if not result["ok"]:
        return format_missing_resource(result["missing"], result["needed"], result["available"]), False
    await record_daily_action(user_id, DAILY_ACTION_CRAFT)

    amount_text = ""
    if upgraded_equipment_recipe_id:
        amount_text = f"\nКачество выросло: <b>{escape(forged_recipe['name'])}</b>."
    elif create_amount > 1:
        amount_text = f"\nБонус ковки: <b>+{create_amount}</b> шт. вместо 1."
    elif recipe["type"] == "consumable" and create_amount > 0:
        amount_text = f"\nВ запасе: <b>{result['amount']}</b> шт."
    elif create_amount <= 0:
        amount_text = "\nПредмет не создан."

    outcome_titles = {
        "critical_success": "🌟 <b>Критический успех ковки!</b>",
        "success": "✅ <b>Ковка удалась.</b>",
        "failure": "⚠️ <b>Ковка провалилась.</b>",
        "critical_failure": "💥 <b>Критический провал ковки!</b>",
    }
    resource_cost_text = "ресурсы сохранены" if not cost else format_cost(cost)
    fish_cost = recipe.get("fish_cost", 0)
    fish_cost_text = f", работа кузнеца: {fish_cost} 🐟" if fish_cost else ""
    return (
        f"{outcome_titles[outcome]}\n"
        f"{random.choice(CRAFT_OUTCOME_TEXTS[outcome])}\n\n"
        f"Рецепт: <b>{escape(recipe['name'])}</b>\n"
        f"Цена: {resource_cost_text}{fish_cost_text}"
        f"{amount_text}"
    ), True


@router.message(F.text == "🛠 Кузница")
@router.message(lambda message: is_alias(message.text, CRAFT_ALIASES))
@router.message(Command("craft"))
async def cmd_craft(message: types.Message):
    user_id = message.from_user.id
    user = await require_current_user(message)
    if not user:
        return

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
    user = await require_callback_user(callback)
    if not user:
        return
    recipe_id = callback.data.split(":", 1)[1]
    text, ok = await craft_recipe_for_user(user_id, recipe_id)
    await callback.answer("Кузница отработала" if ok else "Не хватает ресурсов", show_alert=not ok)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=craft_home_keyboard())


@router.callback_query(F.data.startswith("equip_item:"))
async def cb_equip_item(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    recipe_id = callback.data.split(":", 1)[1]
    recipe = get_recipe(recipe_id)
    if not recipe or recipe["type"] != "equipment":
        await callback.answer("Это не экипировка", show_alert=True)
        return

    item_name = recipe["name"]
    if not can_equip_for_class(user, item_name):
        await callback.answer("Это оружие другого класса", show_alert=True)
        return
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
    user = await require_callback_user(callback)
    if not user:
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
    user = await require_current_user(message)
    if not user:
        return

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
    if not can_equip_for_class(user, item_name):
        return await message.answer("Это оружие другого класса. Кузница уважает специализацию и немного бюрократию.")

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
    user = await require_current_user(message)
    if not user:
        return

    equipped = await db.get_equipped_items(user_id)
    await message.answer(
        format_gear_view(equipped),
        parse_mode="HTML",
        reply_markup=gear_keyboard(),
    )


@router.callback_query(F.data == "open:gear")
async def cb_open_gear(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return
    equipped = await db.get_equipped_items(user_id)

    await callback.answer()
    await callback.message.edit_text(
        format_gear_view(equipped),
        parse_mode="HTML",
        reply_markup=gear_keyboard(),
    )


@router.message(lambda message: parse_prefixed_arg(message.text, USE_ITEM_PREFIXES) is not None)
@router.message(Command("use"))
async def cmd_use(message: types.Message):
    user_id = message.from_user.id
    user = await require_current_user(message)
    if not user:
        return

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
