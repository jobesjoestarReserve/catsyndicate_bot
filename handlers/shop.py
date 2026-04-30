import random
from html import escape

from aiogram import F, Router, types
from aiogram.filters import Command

from data.texts import SHOP_NOT_ENOUGH_FISH_TEXTS, SHOP_STACK_FULL_TEXTS
from database.db_manager import CONSUMABLE_STACK_LIMIT, db
from services.daily import DAILY_ACTION_SHOP, record_daily_action
from services.crafting import get_recipe, get_recipe_id
from services.game_utils import require_callback_user, require_current_user
from services.shop import (
    SHOP_CATEGORIES,
    SHOP_DAILY_LIMIT,
    calculate_sell_amount,
    calculate_shop_amount,
    calculate_shop_cart,
    calculate_shop_total,
    format_shop_catalog_line,
    format_shop_item_line,
    format_shop_today_summary,
    format_shop_transaction_summary,
    format_shop_wishlist,
    get_consumable_amount,
    get_daily_deal_recipe_id,
    get_shop_daily_limit,
    get_shop_reputation,
    get_shop_item_ids_for_category,
    get_shop_unit_price,
    get_sorted_shop_item_ids,
    get_three_for_two_paid_amount,
    get_three_for_two_recipe_id,
    needs_shop_confirmation,
    normalize_shop_date,
)
from services.text_aliases import BUY_PREFIXES, SHOP_ALIASES, WISHLIST_ALIASES, is_alias, parse_prefixed_arg
from services.ui import (
    main_menu_keyboard,
    shop_cart_keyboard,
    shop_confirmation_keyboard,
    shop_item_keyboard,
    shop_keyboard,
    shop_repeat_keyboard,
    shop_wishlist_keyboard,
)

router = Router()



def parse_shop_amount(args: list[str]) -> tuple[str, int | str | None]:
    if not args:
        return "", None
    tail = args[-1].strip().lower()
    if tail == "max":
        return " ".join(args[:-1]), "max"
    if tail.isdigit():
        return " ".join(args[:-1]), max(1, int(tail))
    return " ".join(args), 1




async def get_shop_state(user_id: int) -> tuple[int, list[dict]]:
    user = await db.get_user(user_id)
    balance = (user or {}).get("balance", 0)
    consumables = await db.get_inventory_items(user_id, "consumable")
    return balance, consumables


async def get_daily_limited_remaining(user_id: int, recipe_id: str, today=None) -> int:
    shop_date = normalize_shop_date(today)
    summary = await db.get_shop_transaction_summary(user_id) if getattr(db, "pool", None) is not None else {}
    reputation = get_shop_reputation(summary)
    daily_limit = get_shop_daily_limit(recipe_id, today=shop_date) + reputation["limit_bonus"]
    return await db.get_shop_daily_limited_remaining(user_id, recipe_id, shop_date, daily_limit)


async def decorate_failed_shop_attempt(user_id: int, recipe_id: str, amount: int, reason: str) -> str:
    try:
        suspicious_count = await db.record_shop_suspicious_attempt(user_id, reason, amount)
        await db.add_shop_wishlist_item(user_id, recipe_id, amount, reason)
    except Exception:
        suspicious_count = 0
    lines = ["\n\n📝 Добавил в хотелки: лавочник будет помнить этот странный запрос."]
    if suspicious_count >= 3:
        lines.append("🕵️ Лавочник уже пишет тебя карандашом в подозрительный блокнотик. Без штрафов, но с драмой.")
    return "".join(lines)




async def format_shop_home(user_id: int | None = None, category: str = "all") -> str:
    balance = 0
    consumables = []
    if user_id is not None:
        balance, consumables = await get_shop_state(user_id)

    three_for_two_recipe_id = get_three_for_two_recipe_id()
    cart_items = await db.get_shop_cart(user_id) if user_id is not None else {}
    summary = format_shop_today_summary(cart_items)
    lines = []
    for recipe_id in get_shop_item_ids_for_category(category):
        recipe = get_recipe(recipe_id)
        current_amount = get_consumable_amount(consumables, recipe["name"])
        unit_price = get_shop_unit_price(recipe_id)
        three_for_two_active = recipe_id == three_for_two_recipe_id
        daily_remaining = await get_daily_limited_remaining(user_id, recipe_id) if user_id is not None else get_shop_daily_limit(recipe_id)
        available = calculate_shop_amount(
            recipe,
            "max",
            balance,
            current_amount,
            daily_remaining=daily_remaining,
            unit_price=unit_price,
            three_for_two_active=three_for_two_active,
        )
        lines.append(format_shop_catalog_line(recipe_id, current_amount, available, daily_remaining))
    category_title = SHOP_CATEGORIES.get(category, SHOP_CATEGORIES["all"])[0]
    header = f"🏪 <b>Лавка расходников</b> · {category_title}"
    if user_id is not None:
        header += f"\nБаланс: <b>{balance}</b> 🐟"
    return header + "\n\n" + summary + "\n\n" + "\n\n".join(lines)


async def format_shop_item_card(user_id: int, recipe_id: str) -> str:
    recipe = get_recipe(recipe_id)
    if not recipe or recipe["type"] != "consumable":
        return "Такого товара в лавке нет."

    balance, consumables = await get_shop_state(user_id)
    current_amount = get_consumable_amount(consumables, recipe["name"])
    unit_price = get_shop_unit_price(recipe_id)
    daily_remaining = await get_daily_limited_remaining(user_id, recipe_id)
    available = calculate_shop_amount(
        recipe,
        "max",
        balance,
        current_amount,
        daily_remaining=daily_remaining,
        unit_price=unit_price,
        three_for_two_active=recipe_id == get_three_for_two_recipe_id(),
    )
    return "🏪 <b>Карточка товара</b>\n\n" + format_shop_item_line(
        recipe_id,
        current_amount,
        available,
        daily_remaining,
    )


async def build_shop_preview(user_id: int, recipe_id: str, amount: int | str) -> tuple[str, int]:
    recipe = get_recipe(recipe_id)
    if not recipe or recipe["type"] != "consumable":
        return "Такого товара в лавке нет.", 0

    balance, consumables = await get_shop_state(user_id)
    current_amount = get_consumable_amount(consumables, recipe["name"])
    unit_price = get_shop_unit_price(recipe_id)
    three_for_two_active = get_three_for_two_recipe_id() == recipe_id
    daily_remaining = await get_daily_limited_remaining(user_id, recipe_id)
    amount = calculate_shop_amount(
        recipe,
        amount,
        balance,
        current_amount,
        daily_remaining=daily_remaining,
        unit_price=unit_price,
        three_for_two_active=three_for_two_active,
    )

    if amount <= 0:
        if current_amount >= CONSUMABLE_STACK_LIMIT:
            return (
                f"📦 Стек полон: <b>{escape(recipe['name'])}</b>\n"
                f"В запасе: <b>{current_amount}/{CONSUMABLE_STACK_LIMIT}</b> шт.\n"
                f"{escape(random.choice(SHOP_STACK_FULL_TEXTS))}",
                0,
            )
        return (
            f"🐟 <b>{escape(random.choice(SHOP_NOT_ENOUGH_FISH_TEXTS))}</b>\n"
            f"Нужно хотя бы: <b>{recipe.get('fish_cost', 0)}</b> 🐟, есть: <b>{balance}</b> 🐟.",
            0,
        )

    total_cost = calculate_shop_total(unit_price, amount, promo_active=three_for_two_active)
    paid_amount = get_three_for_two_paid_amount(amount) if three_for_two_active else amount
    promo_line = (
        f"Акция: <b>3 по цене 2</b> (оплачивается <b>{paid_amount}</b> шт.)\n"
        if three_for_two_active and amount >= 3
        else ""
    )
    return (
        f"🧾 <b>Подтвердить покупку</b>\n"
        f"Товар: <b>{escape(recipe['name'])}</b>\n"
        f"Количество: <b>{amount}</b> шт.\n"
        f"Цена за штуку: <b>{unit_price}</b> 🐟\n"
        f"{promo_line}"
        f"Итого: <b>{total_cost}</b> 🐟\n"
        f"Баланс сейчас: <b>{balance}</b> 🐟\n"
        f"После покупки: <b>{balance - total_cost}</b> 🐟\n"
        f"В запасе сейчас: <b>{current_amount}/{CONSUMABLE_STACK_LIMIT}</b> шт.\n"
        f"Лимит дня после покупки: <b>{daily_remaining - amount}</b>",
        amount,
    )


async def buy_shop_item_for_user(
    user_id: int,
    recipe_id: str,
    amount: int | str = 1,
    stack_full_text: str | None = None,
    not_enough_fish_text: str | None = None,
) -> tuple[str, bool]:
    recipe = get_recipe(recipe_id)
    if not recipe or recipe["type"] != "consumable":
        return "Такого товара в лавке нет.", False

    unit_price = get_shop_unit_price(recipe_id)
    three_for_two_active = get_three_for_two_recipe_id() == recipe_id
    if amount == "max":
        balance, consumables = await get_shop_state(user_id)
        current_amount = get_consumable_amount(consumables, recipe["name"])
        daily_remaining = await get_daily_limited_remaining(user_id, recipe_id)
        amount = calculate_shop_amount(
            recipe,
            "max",
            balance,
            current_amount,
            daily_remaining=daily_remaining,
            unit_price=unit_price,
            three_for_two_active=three_for_two_active,
        )
        if amount <= 0:
            if current_amount >= CONSUMABLE_STACK_LIMIT:
                stack_full_text = stack_full_text or random.choice(SHOP_STACK_FULL_TEXTS)
                extra = await decorate_failed_shop_attempt(user_id, recipe_id, max(1, int(amount or 1)), "stack_full")
                return (
                    f"📦 Стек полон: <b>{escape(recipe['name'])}</b>\n"
                    f"В запасе: <b>{current_amount}/{CONSUMABLE_STACK_LIMIT}</b> шт.\n"
                    f"{escape(stack_full_text)}{extra}",
                    False,
                )
            not_enough_fish_text = not_enough_fish_text or random.choice(SHOP_NOT_ENOUGH_FISH_TEXTS)
            extra = await decorate_failed_shop_attempt(user_id, recipe_id, max(1, int(amount or 1)), "not_enough_fish")
            return (
                f"🐟 <b>{escape(not_enough_fish_text)}</b>\n"
                f"Нужно хотя бы: <b>{unit_price}</b> 🐟, есть: <b>{balance}</b> 🐟.{extra}",
                False,
            )
    else:
        daily_remaining = await get_daily_limited_remaining(user_id, recipe_id)
        if daily_remaining <= 0:
            extra = await decorate_failed_shop_attempt(user_id, recipe_id, max(1, int(amount or 1)), "daily_limit")
            return (
                f"📦 <b>Партия дня закончилась: {escape(recipe['name'])}</b>\n"
                f"Лавочник спрятал остатки под прилавок и делает вид, что так и было.{extra}",
                False,
            )
        amount = min(max(1, int(amount)), daily_remaining)
    amount = max(1, int(amount))
    result = await db.buy_limited_inventory_item(
        user_id=user_id,
        item_name=recipe["name"],
        item_type="consumable",
        unit_price=unit_price,
        amount=amount,
        total_cost=calculate_shop_total(unit_price, amount, promo_active=three_for_two_active),
        recipe_id=recipe_id,
        shop_date=normalize_shop_date(),
        daily_limit=get_shop_daily_limit(recipe_id),
        discount_recipe_id=get_daily_deal_recipe_id(),
        three_for_two_recipe_id=get_three_for_two_recipe_id(),
    )
    if not result["ok"]:
        if result.get("daily_limit"):
            extra = await decorate_failed_shop_attempt(user_id, recipe_id, amount, "daily_limit")
            return (
                f"📦 <b>Партия дня почти закончилась: {escape(recipe['name'])}</b>\n"
                f"Доступно сейчас: <b>{result['remaining']}</b> шт. Лавочник показывает пустой ящик и делает лицо невиновного инвентаря.{extra}",
                False,
            )
        if result.get("stack_full"):
            stack_full_text = stack_full_text or random.choice(SHOP_STACK_FULL_TEXTS)
            extra = await decorate_failed_shop_attempt(user_id, recipe_id, amount, "stack_full")
            return (
                f"📦 Стек полон: <b>{escape(recipe['name'])}</b>\n"
                f"В запасе: <b>{result['amount']}/{result['max_amount']}</b> шт.\n"
                f"{escape(stack_full_text)}{extra}",
                False,
            )
        not_enough_fish_text = not_enough_fish_text or random.choice(SHOP_NOT_ENOUGH_FISH_TEXTS)
        extra = await decorate_failed_shop_attempt(user_id, recipe_id, amount, "not_enough_fish")
        return (
            f"🐟 <b>{escape(not_enough_fish_text)}</b>\n"
            f"Нужно: <b>{result['needed']}</b> 🐟, есть: <b>{result['available']}</b> 🐟.{extra}",
            False,
        )
    await record_daily_action(user_id, DAILY_ACTION_SHOP)

    promo_line = (
        f"Акция: <b>3 по цене 2</b> (оплачено <b>{get_three_for_two_paid_amount(amount)}</b> шт.)\n"
        if three_for_two_active and amount >= 3
        else ""
    )
    return (
        f"✅ Куплено: <b>{escape(recipe['name'])}</b>\n"
        f"Количество: <b>{amount}</b> шт.\n"
        f"Цена за штуку: <b>{unit_price}</b> 🐟\n"
        f"{promo_line}"
        f"Итого: <b>{result['spent']}</b> 🐟\n"
        f"Баланс до покупки: <b>{result['balance_before']}</b> 🐟\n"
        f"В запасе: <b>{result['amount']}</b> шт.\n"
        f"Баланс: <b>{result['balance']}</b> 🐟",
        True,
    )


async def sell_shop_item_for_user(user_id: int, recipe_id: str, amount: int | str = 1) -> tuple[str, bool]:
    recipe = get_recipe(recipe_id)
    if not recipe or recipe["type"] != "consumable":
        return "Такого товара в лавке нет.", False

    _, consumables = await get_shop_state(user_id)
    current_amount = get_consumable_amount(consumables, recipe["name"])
    sell_amount, refund = calculate_sell_amount(recipe, amount, current_amount)
    if sell_amount <= 0:
        return (
            f"💸 <b>Продавать нечего: {escape(recipe['name'])}</b>\n"
            "Лавочник посмотрел в пустой карман и уважительно закрыл кассу.",
            False,
        )

    result = await db.sell_inventory_item(
        user_id=user_id,
        item_name=recipe["name"],
        item_type="consumable",
        amount=sell_amount,
        refund=refund,
        recipe_id=recipe_id,
        unit_price=max(1, recipe.get("fish_cost", 0) * 60 // 100),
    )
    if not result["ok"]:
        return (
            f"💸 <b>Продажа не прошла: {escape(recipe['name'])}</b>\n"
            f"Хотели продать: <b>{sell_amount}</b> шт., в запасе: <b>{result['available']}</b> шт.",
            False,
        )
    return (
        f"💸 Продано: <b>{escape(recipe['name'])}</b>\n"
        f"Количество: <b>{sell_amount}</b> шт.\n"
        f"Возврат: <b>{result['refund']}</b> 🐟\n"
        f"Осталось: <b>{result['left']}</b> шт.\n"
        f"Баланс: <b>{result['balance']}</b> 🐟",
        True,
    )


async def build_shop_cart_view(user_id: int) -> tuple[str, bool]:
    balance, consumables = await get_shop_state(user_id)
    cart = calculate_shop_cart(await db.get_shop_cart(user_id))
    if not cart["items"]:
        return cart["text"], False

    problems = []
    for recipe_id, amount in cart["items"].items():
        recipe = get_recipe(recipe_id)
        current_amount = get_consumable_amount(consumables, recipe["name"])
        daily_remaining = await get_daily_limited_remaining(user_id, recipe_id)
        if current_amount + amount > CONSUMABLE_STACK_LIMIT:
            problems.append(f"• {escape(recipe['name'])}: стек забьётся выше <b>{CONSUMABLE_STACK_LIMIT}</b> шт.")
        if amount > daily_remaining:
            problems.append(f"• {escape(recipe['name'])}: в партии осталось <b>{daily_remaining}</b> шт.")

    after_balance = balance - cart["total"]
    if after_balance < 0:
        problems.append(f"• не хватает <b>{abs(after_balance)}</b> 🐟")

    text = (
        f"{cart['text']}\n\n"
        f"Баланс: <b>{balance}</b> 🐟\n"
        f"После покупки: <b>{max(after_balance, 0)}</b> 🐟"
    )
    if problems:
        text += "\n\n⚠️ <b>Касса ругается</b>\n" + "\n".join(problems)
    return text, not problems


async def format_shop_history(user_id: int) -> str:
    return format_shop_transaction_summary(await db.get_shop_transaction_summary(user_id))


async def format_shop_wishlist_for_user(user_id: int) -> str:
    text, _ = await get_shop_wishlist_view(user_id)
    return text


async def get_shop_wishlist_view(user_id: int) -> tuple[str, list[dict]]:
    balance, consumables = await get_shop_state(user_id)
    items = await db.get_shop_wishlist(user_id)
    decorated = []
    for item in items:
        recipe = get_recipe(item["recipe_id"])
        current_amount = get_consumable_amount(consumables, recipe["name"])
        daily_remaining = await get_daily_limited_remaining(user_id, item["recipe_id"])
        unit_price = get_shop_unit_price(item["recipe_id"])
        amount = calculate_shop_amount(
            recipe,
            item["amount"],
            balance,
            current_amount,
            daily_remaining=daily_remaining,
            unit_price=unit_price,
            three_for_two_active=get_three_for_two_recipe_id() == item["recipe_id"],
        )
        row = dict(item)
        row["ready"] = amount >= item["amount"]
        if not row["ready"]:
            row["reason"] = item.get("reason") or "пока нельзя"
        decorated.append(row)
    return format_shop_wishlist(decorated), decorated


async def buy_shop_wishlist_item_for_user(user_id: int, recipe_id: str, amount: int) -> tuple[str, bool]:
    text, ok = await buy_shop_item_for_user(user_id, recipe_id, amount=amount)
    if ok:
        await db.remove_shop_wishlist_item(user_id, recipe_id)
    return text, ok


async def buy_shop_cart_for_user(user_id: int) -> tuple[str, bool]:
    cart_view, can_buy = await build_shop_cart_view(user_id)
    cart = calculate_shop_cart(await db.get_shop_cart(user_id))
    if not cart["items"]:
        return "🧺 Корзина пуста. Лавочник уже приготовил пакетик, но туда легла только тишина.", False
    if not can_buy:
        return cart_view, False

    lines = ["✅ <b>Куплена корзина</b>"]
    for recipe_id, amount in cart["items"].items():
        text, ok = await buy_shop_item_for_user(user_id, recipe_id, amount=amount)
        if not ok:
            return text, False
        recipe = get_recipe(recipe_id)
        lines.append(f"{escape(recipe['name'])}: <b>{amount}</b> шт.")
    await db.clear_shop_cart(user_id)
    lines.append(f"\nИтого по корзине: <b>{cart['total']}</b> 🐟")
    return "\n".join(lines), True


@router.message(F.text == "🏪 Магазин")
@router.message(lambda message: is_alias(message.text, SHOP_ALIASES))
@router.message(Command("shop"))
async def cmd_shop(message: types.Message):
    user = await require_current_user(message)
    if not user:
        return

    await message.answer(
        await format_shop_home(message.from_user.id),
        parse_mode="HTML",
        reply_markup=shop_keyboard(get_shop_item_ids_for_category("all"), category="all"),
    )


@router.message(lambda message: is_alias(message.text, WISHLIST_ALIASES))
async def cmd_shop_wishlist(message: types.Message):
    user = await require_current_user(message)
    if not user:
        return

    text, items = await get_shop_wishlist_view(message.from_user.id)
    await message.answer(text, parse_mode="HTML", reply_markup=shop_wishlist_keyboard(items))


@router.callback_query(F.data == "shop_home")
async def cb_shop_home(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    await callback.answer()
    await callback.message.edit_text(
        await format_shop_home(callback.from_user.id),
        parse_mode="HTML",
        reply_markup=shop_keyboard(get_shop_item_ids_for_category("all"), category="all"),
    )


@router.callback_query(F.data.startswith("shop_cat:"))
async def cb_shop_category(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    category = callback.data.split(":", 1)[1]
    await callback.answer()
    await callback.message.edit_text(
        await format_shop_home(callback.from_user.id, category=category),
        parse_mode="HTML",
        reply_markup=shop_keyboard(get_shop_item_ids_for_category(category), category=category),
    )


@router.callback_query(F.data.startswith("shop_item:"))
async def cb_shop_item(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    recipe_id = callback.data.split(":", 1)[1]
    await callback.answer()
    await callback.message.edit_text(
        await format_shop_item_card(callback.from_user.id, recipe_id),
        parse_mode="HTML",
        reply_markup=shop_item_keyboard(recipe_id),
    )


@router.callback_query(F.data.startswith("shop_buy:"))
async def cb_shop_buy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    payload = callback.data.split(":", 1)[1]
    if ":" in payload:
        recipe_id, amount_text = payload.split(":", 1)
        amount = "max" if amount_text == "max" else int(amount_text)
    else:
        recipe_id = payload
        amount = 1
    if needs_shop_confirmation(amount):
        text, confirmed_amount = await build_shop_preview(user_id, recipe_id, amount)
        await callback.answer("Подтверди покупку", show_alert=False)
        return await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=shop_confirmation_keyboard(recipe_id, confirmed_amount) if confirmed_amount > 0 else shop_keyboard(get_shop_item_ids_for_category("all")),
        )

    text, ok = await buy_shop_item_for_user(user_id, recipe_id, amount=amount)
    await callback.answer("Куплено" if ok else "Покупка не прошла", show_alert=not ok)
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=shop_repeat_keyboard(recipe_id, int(amount)) if ok else main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("shop_preview:"))
async def cb_shop_preview(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    _, recipe_id, amount_text = callback.data.split(":", 2)
    amount = "max" if amount_text == "max" else int(amount_text)
    text, confirmed_amount = await build_shop_preview(user_id, recipe_id, amount)
    await callback.answer("Подтверди покупку" if confirmed_amount > 0 else "Покупка не прошла", show_alert=False)
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=shop_confirmation_keyboard(recipe_id, confirmed_amount) if confirmed_amount > 0 else shop_keyboard(get_shop_item_ids_for_category("all")),
    )


@router.callback_query(F.data.startswith("shop_confirm:"))
async def cb_shop_confirm(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await require_callback_user(callback)
    if not user:
        return

    _, recipe_id, amount_text = callback.data.split(":", 2)
    amount = int(amount_text)
    text, ok = await buy_shop_item_for_user(user_id, recipe_id, amount=amount)
    await callback.answer("Куплено" if ok else "Покупка не прошла", show_alert=not ok)
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=shop_repeat_keyboard(recipe_id, amount) if ok else main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("shop_cart_add:"))
async def cb_shop_cart_add(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    _, recipe_id, amount_text = callback.data.split(":", 2)
    await db.add_shop_cart_item(callback.from_user.id, recipe_id, int(amount_text))
    cart_items = await db.get_shop_cart(callback.from_user.id)
    cart = calculate_shop_cart(cart_items)
    await callback.answer("Добавлено в корзину")
    await callback.message.answer(cart["text"], parse_mode="HTML", reply_markup=shop_cart_keyboard(cart_items))


@router.callback_query(F.data == "shop_cart")
async def cb_shop_cart(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    text, _ = await build_shop_cart_view(callback.from_user.id)
    cart_items = await db.get_shop_cart(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML", reply_markup=shop_cart_keyboard(cart_items))


@router.callback_query(F.data.startswith("shop_cart_adjust:"))
async def cb_shop_cart_adjust(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    _, recipe_id, delta_text = callback.data.split(":", 2)
    await db.adjust_shop_cart_item(callback.from_user.id, recipe_id, int(delta_text))
    text, _ = await build_shop_cart_view(callback.from_user.id)
    cart_items = await db.get_shop_cart(callback.from_user.id)
    await callback.answer("Корзина обновлена")
    await callback.message.answer(text, parse_mode="HTML", reply_markup=shop_cart_keyboard(cart_items))


@router.callback_query(F.data.startswith("shop_cart_remove:"))
async def cb_shop_cart_remove(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    recipe_id = callback.data.split(":", 1)[1]
    await db.remove_shop_cart_item(callback.from_user.id, recipe_id)
    text, _ = await build_shop_cart_view(callback.from_user.id)
    cart_items = await db.get_shop_cart(callback.from_user.id)
    await callback.answer("Убрано из корзины")
    await callback.message.answer(text, parse_mode="HTML", reply_markup=shop_cart_keyboard(cart_items))


@router.callback_query(F.data == "shop_cart_clear")
async def cb_shop_cart_clear(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    await db.clear_shop_cart(callback.from_user.id)
    await callback.answer("Корзина очищена")
    await callback.message.answer("🧺 Корзина очищена. Пакетик грустит, но держится.", reply_markup=shop_cart_keyboard(False))


@router.callback_query(F.data == "shop_history")
async def cb_shop_history(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    await callback.answer()
    await callback.message.answer(await format_shop_history(callback.from_user.id), parse_mode="HTML", reply_markup=shop_cart_keyboard(False))


@router.callback_query(F.data == "shop_wishlist")
async def cb_shop_wishlist(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    text, items = await get_shop_wishlist_view(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML", reply_markup=shop_wishlist_keyboard(items))


@router.callback_query(F.data.startswith("shop_wishlist_buy:"))
async def cb_shop_wishlist_buy(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    _, recipe_id, amount_text = callback.data.split(":", 2)
    text, ok = await buy_shop_wishlist_item_for_user(callback.from_user.id, recipe_id, int(amount_text))
    await callback.answer("Куплено" if ok else "Покупка не прошла", show_alert=not ok)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("shop_wishlist_cart:"))
async def cb_shop_wishlist_cart(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    _, recipe_id, amount_text = callback.data.split(":", 2)
    await db.add_shop_cart_item(callback.from_user.id, recipe_id, int(amount_text))
    await db.remove_shop_wishlist_item(callback.from_user.id, recipe_id)
    text, _ = await build_shop_cart_view(callback.from_user.id)
    cart_items = await db.get_shop_cart(callback.from_user.id)
    await callback.answer("Переложено в корзину")
    await callback.message.answer(text, parse_mode="HTML", reply_markup=shop_cart_keyboard(cart_items))


@router.callback_query(F.data.startswith("shop_wishlist_remove:"))
async def cb_shop_wishlist_remove(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    recipe_id = callback.data.split(":", 1)[1]
    await db.remove_shop_wishlist_item(callback.from_user.id, recipe_id)
    text, items = await get_shop_wishlist_view(callback.from_user.id)
    await callback.answer("Убрано из хотелок")
    await callback.message.answer(text, parse_mode="HTML", reply_markup=shop_wishlist_keyboard(items))


@router.callback_query(F.data == "shop_cart_buy")
async def cb_shop_cart_buy(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    text, ok = await buy_shop_cart_for_user(callback.from_user.id)
    await callback.answer("Корзина куплена" if ok else "Покупка не прошла", show_alert=not ok)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("shop_sell:"))
async def cb_shop_sell(callback: types.CallbackQuery):
    user = await require_callback_user(callback)
    if not user:
        return

    _, recipe_id, amount_text = callback.data.split(":", 2)
    amount = "max" if amount_text == "max" else int(amount_text)
    text, ok = await sell_shop_item_for_user(callback.from_user.id, recipe_id, amount)
    await callback.answer("Продано" if ok else "Продажа не прошла", show_alert=not ok)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


@router.message(Command("buy"))
@router.message(lambda message: parse_prefixed_arg(message.text, BUY_PREFIXES) is not None)
async def cmd_buy(message: types.Message):
    user_id = message.from_user.id
    user = await require_current_user(message)
    if not user:
        return

    buy_arg = parse_prefixed_arg(message.text, BUY_PREFIXES)
    args = buy_arg.split() if buy_arg is not None else (message.text or "").split()[1:]
    item_name, amount = parse_shop_amount(args)
    recipe_id = get_recipe_id(item_name) if item_name else None
    if not recipe_id:
        return await message.answer(
            "Напиши: <code>/buy Валерьянка</code> или открой <code>магазин</code>.",
            parse_mode="HTML",
            reply_markup=shop_keyboard(get_shop_item_ids_for_category("all")),
        )

    amount = amount or 1
    if needs_shop_confirmation(amount):
        text, confirmed_amount = await build_shop_preview(user_id, recipe_id, amount)
        return await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=shop_confirmation_keyboard(recipe_id, confirmed_amount) if confirmed_amount > 0 else shop_keyboard(get_shop_item_ids_for_category("all")),
        )

    text, ok = await buy_shop_item_for_user(user_id, recipe_id, amount=amount)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=shop_repeat_keyboard(recipe_id, int(amount)) if ok else main_menu_keyboard(),
    )
