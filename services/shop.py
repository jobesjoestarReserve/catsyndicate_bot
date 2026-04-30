import random
from datetime import date
from html import escape

from database.db_manager import CONSUMABLE_STACK_LIMIT
from services.crafting import BUFF_LABELS, get_recipe, get_shop_item_ids


SHOP_EFFECT_ORDER = {
    "grow_focus": 0,
    "hunt_safety": 1,
    "work_boost": 2,
    "meow_luck": 3,
}
SHOP_CONFIRMATION_THRESHOLD = 25
SHOP_DAILY_LIMIT = 120
SHOP_SELL_REFUND_PERCENT = 60
SHOP_CATEGORIES = {
    "all": ("Все", None),
    "grow": ("Рост", "grow_focus"),
    "hunt": ("Охота", "hunt_safety"),
    "work": ("Работа", "work_boost"),
    "fish": ("Рыбовы", "meow_luck"),
}
SHOP_SHELF_EVENTS = [
    {
        "id": "sleepy_clerk",
        "title": "Сонный лавочник",
        "description": "один товар продаётся чуть дешевле, потому что ценник зевнул",
        "price_percent": 95,
        "limit_bonus": 0,
    },
    {
        "id": "fish_tax",
        "title": "Рыбный налог",
        "description": "один товар слегка дороже, зато лавочник очень официально кашляет",
        "price_percent": 105,
        "limit_bonus": 0,
    },
    {
        "id": "inventory_day",
        "title": "Инвентаризация наоборот",
        "description": "по одному товару нашли лишний ящик под прилавком",
        "price_percent": 100,
        "limit_bonus": 30,
    },
]


def normalize_shop_date(today=None) -> date:
    if today is None:
        return date.today()
    if isinstance(today, date):
        return today
    return date.fromisoformat(str(today))


def get_sorted_shop_item_ids() -> list[str]:
    return sorted(
        get_shop_item_ids(),
        key=lambda recipe_id: (
            SHOP_EFFECT_ORDER.get(get_recipe(recipe_id).get("effect"), 99),
            get_recipe(recipe_id)["name"],
        ),
    )


def get_shop_item_ids_for_category(category: str = "all") -> list[str]:
    category = category if category in SHOP_CATEGORIES else "all"
    effect = SHOP_CATEGORIES[category][1]
    item_ids = get_sorted_shop_item_ids()
    if effect is None:
        return item_ids
    return [recipe_id for recipe_id in item_ids if get_recipe(recipe_id).get("effect") == effect]


def get_daily_promo_recipe_id(promo_name: str, today=None) -> str:
    item_ids = get_sorted_shop_item_ids()
    shop_date = normalize_shop_date(today)
    rng = random.Random(f"{promo_name}:{shop_date.isoformat()}")
    return rng.choice(item_ids)


def get_daily_deal_recipe_id(today=None) -> str:
    return get_daily_promo_recipe_id("discount20", today=today)


def get_three_for_two_recipe_id(today=None) -> str:
    return get_daily_promo_recipe_id("three_for_two", today=today)


def get_daily_stock_boost_recipe_id(today=None) -> str:
    return get_daily_promo_recipe_id("stock_boost", today=today)


def get_shop_daily_limit(recipe_id: str, today=None) -> int:
    limit = SHOP_DAILY_LIMIT
    if get_daily_stock_boost_recipe_id(today=today) == recipe_id:
        limit += 80
    shelf_event = get_daily_shelf_event(today=today)
    if shelf_event["recipe_id"] == recipe_id:
        limit += shelf_event.get("limit_bonus", 0)
    return limit


def get_daily_shelf_event(today=None) -> dict:
    item_ids = get_sorted_shop_item_ids()
    shop_date = normalize_shop_date(today)
    rng = random.Random(f"shelf_event:{shop_date.isoformat()}")
    event = dict(rng.choice(SHOP_SHELF_EVENTS))
    event["recipe_id"] = rng.choice(item_ids)
    return event


def get_shop_reputation(summary: dict) -> dict:
    spent = max(0, int(summary.get("spent", 0) or 0))
    if spent >= 5000:
        return {"title": "Почётный шуршатель рыбов", "limit_bonus": 20}
    if spent >= 1500:
        return {"title": "Свой у прилавка", "limit_bonus": 10}
    if spent >= 300:
        return {"title": "Знакомый пакетика", "limit_bonus": 5}
    return {"title": "Нюхатель витрины", "limit_bonus": 0}


def get_shop_unit_price(recipe_id: str, today=None) -> int:
    recipe = get_recipe(recipe_id)
    if not recipe:
        return 0
    price = recipe.get("fish_cost", 0)
    if get_daily_deal_recipe_id(today) == recipe_id:
        price = max(1, price * 80 // 100)
    shelf_event = get_daily_shelf_event(today=today)
    if shelf_event["recipe_id"] == recipe_id:
        price = max(1, price * shelf_event.get("price_percent", 100) // 100)
    return price


def get_three_for_two_paid_amount(amount: int) -> int:
    amount = max(0, int(amount))
    return amount - amount // 3


def calculate_shop_total(unit_price: int, amount: int, promo_active: bool = False) -> int:
    paid_amount = get_three_for_two_paid_amount(amount) if promo_active else max(0, int(amount))
    return unit_price * paid_amount


def get_consumable_amount(consumables: list[dict], item_name: str) -> int:
    for row in consumables:
        if row["item_name"] == item_name:
            return row["amount"] or 0
    return 0


def calculate_shop_amount(
    recipe: dict,
    amount: int | str,
    balance: int,
    current_amount: int,
    daily_remaining: int | None = None,
    unit_price: int | None = None,
    three_for_two_active: bool = False,
) -> int:
    fish_cost = unit_price if unit_price is not None else recipe.get("fish_cost", 0)
    free_space = max(0, CONSUMABLE_STACK_LIMIT - current_amount)
    if daily_remaining is not None:
        free_space = min(free_space, max(0, daily_remaining))
    if fish_cost:
        by_balance = 0
        for candidate in range(free_space, 0, -1):
            if calculate_shop_total(fish_cost, candidate, promo_active=three_for_two_active) <= balance:
                by_balance = candidate
                break
    else:
        by_balance = free_space
    if amount == "max":
        return max(0, min(by_balance, free_space))
    requested = max(1, int(amount))
    return max(0, min(requested, by_balance, free_space))


def needs_shop_confirmation(amount: int | str) -> bool:
    return amount == "max" or int(amount) >= SHOP_CONFIRMATION_THRESHOLD


def calculate_shop_cart(items: dict[str, int], today=None) -> dict:
    items = {recipe_id: max(0, int(amount)) for recipe_id, amount in (items or {}).items()}
    lines = []
    total = 0
    three_for_two_recipe_id = get_three_for_two_recipe_id(today=today)
    for recipe_id in get_sorted_shop_item_ids():
        amount = items.get(recipe_id, 0)
        if amount <= 0:
            continue
        recipe = get_recipe(recipe_id)
        unit_price = get_shop_unit_price(recipe_id, today=today)
        three_for_two_active = three_for_two_recipe_id == recipe_id
        line_total = calculate_shop_total(unit_price, amount, promo_active=three_for_two_active)
        total += line_total
        promo = " · 3 по цене 2" if three_for_two_active and amount >= 3 else ""
        lines.append(f"{escape(recipe['name'])}: <b>{amount}</b> шт. = <b>{line_total}</b> 🐟{promo}")
    text = "🧺 <b>Корзина лавки</b>\n" + ("\n".join(lines) if lines else "Пока пусто.")
    promo_recipe = get_recipe(three_for_two_recipe_id)
    text += f"\n\n🎁 3 по цене 2 сегодня: <b>{escape(promo_recipe['name'])}</b>"
    if lines:
        text += f"\n\nИтого: <b>{total}</b> 🐟"
    return {"items": items, "total": total, "text": text}


def calculate_sell_amount(recipe: dict, requested_amount: int | str, current_amount: int) -> tuple[int, int]:
    if requested_amount == "max":
        amount = max(0, current_amount)
    else:
        amount = min(max(1, int(requested_amount)), max(0, current_amount))
    refund_per_item = max(1, recipe.get("fish_cost", 0) * SHOP_SELL_REFUND_PERCENT // 100)
    return amount, refund_per_item * amount


def format_shop_today_summary(cart_items: dict[str, int] | None = None, today=None) -> str:
    deal_recipe = get_recipe(get_daily_deal_recipe_id(today=today))
    three_for_two_recipe = get_recipe(get_three_for_two_recipe_id(today=today))
    stock_boost_recipe = get_recipe(get_daily_stock_boost_recipe_id(today=today))
    shelf_event = get_daily_shelf_event(today=today)
    shelf_recipe = get_recipe(shelf_event["recipe_id"])
    cart = calculate_shop_cart(cart_items or {}, today=today)
    item_count = sum(cart["items"].values())
    return (
        "🗓 <b>Магазин сегодня</b>\n"
        f"🔻 -20%: <b>{escape(deal_recipe['name'])}</b>\n"
        f"🎁 3 по цене 2: <b>{escape(three_for_two_recipe['name'])}</b>\n"
        f"📦 Большая партия: <b>{escape(stock_boost_recipe['name'])}</b> (+80 шт.)\n"
        f"🪧 Полка дня: <b>{escape(shelf_event['title'])}</b> — {escape(shelf_recipe['name'])}\n"
        f"🧺 Корзина: <b>{item_count}</b> шт. на <b>{cart['total']}</b> 🐟"
    )


def format_shop_item_line(recipe_id: str, current_amount: int, available: int, daily_remaining: int, today=None) -> str:
    recipe = get_recipe(recipe_id)
    effect = recipe.get("effect")
    unit_price = get_shop_unit_price(recipe_id, today=today)
    deal_label = " 🔻 товар дня" if recipe_id == get_daily_deal_recipe_id(today=today) else ""
    three_for_two_label = " 🎁 3 по цене 2" if recipe_id == get_three_for_two_recipe_id(today=today) else ""
    stock_boost_label = " 📦 большая партия" if recipe_id == get_daily_stock_boost_recipe_id(today=today) else ""
    shelf_event = get_daily_shelf_event(today=today)
    shelf_label = f" 🪧 {shelf_event['title'].lower()}" if recipe_id == shelf_event["recipe_id"] else ""
    return (
        f"<b>{escape(recipe['name'])}</b>\n"
        f"  {escape(recipe['description'])}; цена: <b>{unit_price}</b> 🐟{deal_label}{three_for_two_label}{stock_boost_label}{shelf_label}\n"
        f"  есть: <b>{current_amount}/{CONSUMABLE_STACK_LIMIT}</b>; можно: <b>{available}</b> шт.; лимит дня: <b>{daily_remaining}</b>\n"
        f"  {BUFF_LABELS[effect]}"
      )


def format_shop_catalog_line(recipe_id: str, current_amount: int, available: int, daily_remaining: int, today=None) -> str:
    recipe = get_recipe(recipe_id)
    unit_price = get_shop_unit_price(recipe_id, today=today)
    labels = []
    if recipe_id == get_daily_deal_recipe_id(today=today):
        labels.append("🔻")
    if recipe_id == get_three_for_two_recipe_id(today=today):
        labels.append("🎁")
    if recipe_id == get_daily_stock_boost_recipe_id(today=today):
        labels.append("📦")
    shelf_event = get_daily_shelf_event(today=today)
    if recipe_id == shelf_event["recipe_id"]:
        labels.append("🪧")
    badge_text = f" {' '.join(labels)}" if labels else ""
    return (
        f"• <b>{escape(recipe['name'])}</b>{badge_text} — <b>{unit_price}</b> 🐟\n"
        f"  есть: <b>{current_amount}/{CONSUMABLE_STACK_LIMIT}</b>; "
        f"можно: <b>{available}</b> шт.; лимит дня: <b>{daily_remaining}</b>"
    )


def format_shop_transaction_summary(summary: dict) -> str:
    latest = summary.get("latest") or []
    reputation = get_shop_reputation(summary)
    lines = [
        "🧾 <b>История магазина</b>",
        f"Доверие лавки: <b>{escape(reputation['title'])}</b> (+{reputation['limit_bonus']} к дневным лимитам)",
        f"Потрачено: <b>{summary.get('spent', 0)}</b> 🐟",
        f"Вернулось: <b>{summary.get('refunded', 0)}</b> 🐟",
    ]
    favorite_recipe_id = summary.get("favorite_recipe_id")
    if favorite_recipe_id:
        recipe = get_recipe(favorite_recipe_id)
        lines.append(f"Любимый товар: <b>{escape(recipe['name'])}</b> ({summary.get('favorite_amount', 0)} шт.)")
    if latest:
        lines.append("\nПоследние операции:")
        for row in latest:
            recipe = get_recipe(row.get("recipe_id"))
            name = escape(recipe["name"]) if recipe else "товар"
            action = "покупка" if row.get("action") == "buy" else "продажа"
            cost = abs(row.get("total_cost", 0) or 0)
            lines.append(f"• {action}: <b>{name}</b> x{row.get('amount', 0)} = <b>{cost}</b> 🐟")
    else:
        lines.append("\nПока нет операций. Лавочник скучает по шуршанию рыбов.")
    return "\n".join(lines)


def format_shop_wishlist(items: list[dict]) -> str:
    lines = ["📝 <b>Хотелки магазина</b>"]
    if not items:
        lines.append("Пусто. Лавочник записал тишину красивым почерком.")
        return "\n".join(lines)
    for item in items:
        recipe = get_recipe(item["recipe_id"])
        status = "готово" if item.get("ready") else item.get("reason", "пока нельзя")
        lines.append(f"• <b>{escape(recipe['name'])}</b> x{item.get('amount', 1)} — {escape(status)}")
    return "\n".join(lines)
