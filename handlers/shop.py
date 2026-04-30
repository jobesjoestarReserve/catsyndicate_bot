from html import escape

from aiogram import F, Router, types
from aiogram.filters import Command

from database.db_manager import db
from services.daily import DAILY_ACTION_SHOP, record_daily_action
from services.crafting import (
    BUFF_LABELS,
    format_recipe_price,
    get_recipe,
    get_recipe_id,
    get_shop_item_ids,
)
from services.game_utils import require_callback_user, require_current_user
from services.text_aliases import SHOP_ALIASES, is_alias
from services.ui import main_menu_keyboard, shop_keyboard

router = Router()


def format_shop_home() -> str:
    lines = []
    for recipe_id in get_shop_item_ids():
        recipe = get_recipe(recipe_id)
        effect = recipe.get("effect")
        lines.append(
            f"<b>{escape(recipe['name'])}</b>\n"
            f"  {escape(recipe['description'])}; цена: {format_recipe_price(recipe)}\n"
            f"  {BUFF_LABELS[effect]}"
        )
    return "🏪 <b>Лавка расходников</b>\n\n" + "\n\n".join(lines)


async def buy_shop_item_for_user(user_id: int, recipe_id: str) -> tuple[str, bool]:
    recipe = get_recipe(recipe_id)
    if not recipe or recipe["type"] != "consumable":
        return "Такого товара в лавке нет.", False

    fish_cost = recipe.get("fish_cost", 0)
    result = await db.buy_inventory_item(
        user_id=user_id,
        item_name=recipe["name"],
        item_type="consumable",
        fish_cost=fish_cost,
        amount=1,
    )
    if not result["ok"]:
        return (
            "🐟 Лавочник подвёл счёты и покачал усами.\n"
            f"Нужно: <b>{result['needed']}</b> 🐟, есть: <b>{result['available']}</b> 🐟.",
            False,
        )
    await record_daily_action(user_id, DAILY_ACTION_SHOP)

    return (
        f"✅ Куплено: <b>{escape(recipe['name'])}</b>\n"
        f"Цена: <b>{fish_cost}</b> 🐟\n"
        f"В запасе: <b>{result['amount']}</b> шт.\n"
        f"Баланс: <b>{result['balance']}</b> 🐟",
        True,
    )


@router.message(F.text == "🏪 Магазин")
@router.message(lambda message: is_alias(message.text, SHOP_ALIASES))
@router.message(Command("shop"))
async def cmd_shop(message: types.Message):
    user = await require_current_user(message)
    if not user:
        return

    await message.answer(
        format_shop_home(),
        parse_mode="HTML",
        reply_markup=shop_keyboard(get_shop_item_ids()),
    )


@router.callback_query(F.data == "shop_home")
async def cb_shop_home(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    await callback.answer()
    await callback.message.edit_text(
        format_shop_home(),
        parse_mode="HTML",
        reply_markup=shop_keyboard(get_shop_item_ids()),
    )


@router.callback_query(F.data.startswith("shop_buy:"))
async def cb_shop_buy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    recipe_id = callback.data.split(":", 1)[1]
    text, ok = await buy_shop_item_for_user(user_id, recipe_id)
    await callback.answer("Куплено" if ok else "Не хватает рыбов", show_alert=not ok)
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("buy"))
async def cmd_buy(message: types.Message):
    user_id = message.from_user.id
    user = await require_current_user(message)
    if not user:
        return

    args = (message.text or "").split()[1:]
    recipe_id = get_recipe_id(" ".join(args)) if args else None
    if not recipe_id:
        return await message.answer(
            "Напиши: <code>/buy Валерьянка</code> или открой <code>магазин</code>.",
            parse_mode="HTML",
            reply_markup=shop_keyboard(get_shop_item_ids()),
        )

    text, _ = await buy_shop_item_for_user(user_id, recipe_id)
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
