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
    format_durability,
    format_recipe_category,
    get_forging_cost,
    get_forging_create_amount_for_recipe,
    get_category_recipe_ids,
    get_equipment_durability_max,
    get_consumable_effect,
    get_equipment_family_names,
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
            by_slot[slot] = row

    lines = []
    for slot, label in SLOT_LABELS.items():
        item = by_slot.get(slot)
        if item:
            lines.append(f"• {label}: <b>{escape(item['item_name'])}</b>{format_durability(item)}")
        else:
            lines.append(f"• {label}: пусто")

    return "🧥 <b>Экипировка</b>\n\n" + "\n".join(lines)


def can_equip_for_class(user, item_name: str) -> bool:
    item_class = get_equipment_class(item_name)
    return item_class is None or (user["cat_class"] or "none") == item_class


async def equip_item_for_user(user_id: int, user, item_name: str) -> tuple[str, bool, str]:
    slot = get_equipment_slot(item_name)
    if not slot:
        return "Это не экипировка из кузницы. Проверь название в инвентаре или кузнице.", False, "Это не экипировка"
    if not can_equip_for_class(user, item_name):
        return "Это оружие другого класса. Кузница уважает специализацию и немного бюрократию.", False, "Это оружие другого класса"

    equipped = await db.equip_item(user_id, item_name, get_slot_item_names(slot))
    if not equipped:
        return "Такого предмета нет в инвентаре или он уже надет.", False, "Предмета нет в инвентаре"

    return (
        f"🧷 Надето: <b>{escape(item_name)}</b>\nСлот: <b>{SLOT_LABELS[slot]}</b>",
        True,
        "Надето",
    )


async def use_consumable_for_user(user_id: int, item_name: str, include_description: bool = False) -> tuple[str, bool, str]:
    effect = get_consumable_effect(item_name)
    if not effect:
        return "Это не расходник из кузницы. Проверь название в инвентаре или кузнице.", False, "Это не расходник"

    remaining = await db.consume_inventory_item(user_id, item_name, "consumable")
    if remaining is None:
        return "Такого расходника нет в инвентаре.", False, "Расходника нет в инвентаре"

    await db.add_buff(user_id, effect, uses=1)
    item = get_item(item_name)
    description = f"\n\n{escape(item['description'])}" if include_description and item else ""
    return (
        (
            f"🧪 Использовано: <b>{escape(item_name)}</b>\n"
            f"{BUFF_LABELS[effect]}\n"
            f"Осталось расходников: <b>{remaining}</b>"
            f"{description}"
        ),
        True,
        "Использовано",
    )


async def craft_recipe_for_user(user_id: int, recipe_id: str) -> tuple[str, bool]:
    recipe = get_recipe(recipe_id)
    if not recipe:
        return "Такого рецепта нет. Вернись в кузницу и выбери кнопку.", False
    if recipe["type"] != "equipment":
        return "Расходники теперь продаются в лавке. Открой <code>магазин</code>.", False

    outcome = roll_forging_outcome()
    cost = get_forging_cost(recipe, outcome)
    create_amount = get_forging_create_amount_for_recipe(recipe, outcome)
    result = await db.craft_inventory_item(
        user_id=user_id,
        cost=cost,
        item_name=recipe["name"],
        item_type=recipe["type"],
        create_amount=create_amount,
        fish_cost=recipe.get("fish_cost", 0),
        equipment_family_names=get_equipment_family_names(recipe_id),
        target_item_name=recipe["name"],
        target_durability_max=get_equipment_durability_max(recipe_id),
    )
    if not result["ok"]:
        if result.get("already_full"):
            return (
                f"<b>{escape(result['item_name'])}</b> уже целый: "
                f"{format_durability(result)}. Кузница не стала брать ресурсы за лишний ремонт.",
                False,
            )
        if result.get("already_owned"):
            return (
                f"В этой линейке уже есть <b>{escape(result['item_name'])}</b>. "
                "Куй текущий предмет для ремонта или следующий тир для апгрейда.",
                False,
            )
        if result.get("needs_previous"):
            return (
                f"Сначала нужен <b>{escape(result['item_name'])}</b>. "
                "Кузница не перескакивает через ступеньки качества.",
                False,
            )
        return format_missing_resource(result["missing"], result["needed"], result["available"]), False
    await record_daily_action(user_id, DAILY_ACTION_CRAFT)

    amount_text = ""
    if result.get("repaired"):
        amount_text = f"\nПочинено: <b>{escape(result['item_name'])}</b>{format_durability(result)}."
    elif result.get("upgraded"):
        amount_text = f"\nУлучшено: <b>{escape(result['item_name'])}</b>{format_durability(result)}."
    elif recipe["type"] == "equipment" and create_amount > 0:
        amount_text = f"\nПрочность: <b>{format_durability(result).strip()}</b>."
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
    await callback.answer("Кузница отработала" if ok else "Кузница отказалась", show_alert=not ok)
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

    text, ok, alert = await equip_item_for_user(user_id, user, recipe["name"])
    await callback.answer(alert, show_alert=not ok)
    if ok:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=gear_keyboard())


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

    text, ok, alert = await use_consumable_for_user(user_id, recipe["name"])
    await callback.answer(alert, show_alert=not ok)
    if ok:
        await callback.message.answer(text, parse_mode="HTML")


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
    text, _, _ = await equip_item_for_user(user_id, user, item_name)
    await message.answer(text, parse_mode="HTML")


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
    text, _, _ = await use_consumable_for_user(user_id, item_name, include_description=True)
    await message.answer(text, parse_mode="HTML")
