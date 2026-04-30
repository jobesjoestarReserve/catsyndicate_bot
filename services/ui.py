from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from services.crafting import WEAPON_CLASS_LABELS, get_item_recipe_id, get_recipe


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🐟 Мяу"), KeyboardButton(text="🐭 Охота")],
            [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛠 Кузница")],
            [KeyboardButton(text="🏪 Магазин"), KeyboardButton(text="🧥 Экипировка")],
            [KeyboardButton(text="📅 Ежедневки"), KeyboardButton(text="📊 Досье")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие Синдиката",
    )


def craft_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🪖 Шлемы", callback_data="craft_cat:helmet"),
                InlineKeyboardButton(text="🧥 Нагрудники", callback_data="craft_cat:chest"),
            ],
            [
                InlineKeyboardButton(text="🧤 Нарукавники", callback_data="craft_cat:bracers"),
                InlineKeyboardButton(text="🥾 Ботинки", callback_data="craft_cat:boots"),
            ],
            [InlineKeyboardButton(text="🗡 Оружие классов", callback_data="craft_cat:weapon")],
            [
                InlineKeyboardButton(text="🏪 Магазин", callback_data="shop_home"),
                InlineKeyboardButton(text="🎒 Инвентарь", callback_data="open:inv"),
            ],
        ]
    )


def recipe_keyboard(recipe_ids: list[str], category: str | None = None) -> InlineKeyboardMarkup:
    if category == "weapon":
        rows = [
            [InlineKeyboardButton(text=label, callback_data=f"craft_weapon_class:{cat_class}")]
            for cat_class, label in WEAPON_CLASS_LABELS.items()
        ]
        rows.append([InlineKeyboardButton(text="⬅️ Назад в кузницу", callback_data="craft_home")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    rows = [
        [InlineKeyboardButton(text=get_recipe(recipe_id)["name"], callback_data=f"craft_recipe:{recipe_id}")]
        for recipe_id in recipe_ids
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад в кузницу", callback_data="craft_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipe_detail_keyboard(recipe_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Собрать", callback_data=f"craft_make:{recipe_id}")],
            [InlineKeyboardButton(text="⬅️ Назад к разделу", callback_data="craft_home")],
        ]
    )


def inventory_keyboard(consumables=None) -> InlineKeyboardMarkup:
    rows = []
    for row in consumables or []:
        recipe_id = get_item_recipe_id(row["item_name"])
        if recipe_id:
            rows.append([
                InlineKeyboardButton(
                    text=f"🧪 Использовать: {row['item_name']}",
                    callback_data=f"use_item:{recipe_id}",
                )
            ])
    rows.append(
        [
            InlineKeyboardButton(text="🛠 Кузница", callback_data="craft_home"),
            InlineKeyboardButton(text="🏪 Магазин", callback_data="shop_home"),
            InlineKeyboardButton(text="🧥 Экипировка", callback_data="open:gear"),
        ]
    )
    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def gear_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎒 Инвентарь", callback_data="open:inv"),
                InlineKeyboardButton(text="🛠 Кузница", callback_data="craft_home"),
            ],
        ]
    )


def class_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"choose_class:{cat_class}")]
            for cat_class, label in WEAPON_CLASS_LABELS.items()
        ]
    )


def shop_keyboard(item_ids: list[str], category: str = "all") -> InlineKeyboardMarkup:
    categories = [
        ("Все", "all"),
        ("Рост", "grow"),
        ("Охота", "hunt"),
        ("Работа", "work"),
        ("Рыбовы", "fish"),
    ]
    rows = []
    rows.append([
        InlineKeyboardButton(
            text=f"{'• ' if key == category else ''}{label}",
            callback_data=f"shop_cat:{key}",
        )
        for label, key in categories
    ])
    for recipe_id in item_ids:
        recipe = get_recipe(recipe_id)
        rows.append([InlineKeyboardButton(text=recipe["name"], callback_data=f"shop_item:{recipe_id}")])
    rows.append(
        [
            InlineKeyboardButton(text="🧺 Корзина", callback_data="shop_cart"),
            InlineKeyboardButton(text="🧾 История", callback_data="shop_history"),
            InlineKeyboardButton(text="📝 Хотелки", callback_data="shop_wishlist"),
            InlineKeyboardButton(text="🎒 Инвентарь", callback_data="open:inv"),
            InlineKeyboardButton(text="🛠 Кузница", callback_data="craft_home"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shop_item_keyboard(recipe_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="x1", callback_data=f"shop_buy:{recipe_id}:1"),
                InlineKeyboardButton(text="x5", callback_data=f"shop_buy:{recipe_id}:5"),
                InlineKeyboardButton(text="x10", callback_data=f"shop_buy:{recipe_id}:10"),
            ],
            [
                InlineKeyboardButton(text="x25", callback_data=f"shop_preview:{recipe_id}:25"),
                InlineKeyboardButton(text="x100", callback_data=f"shop_preview:{recipe_id}:100"),
                InlineKeyboardButton(text="max", callback_data=f"shop_preview:{recipe_id}:max"),
            ],
            [
                InlineKeyboardButton(text="🧺 +1", callback_data=f"shop_cart_add:{recipe_id}:1"),
                InlineKeyboardButton(text="🧺 +5", callback_data=f"shop_cart_add:{recipe_id}:5"),
            ],
            [
                InlineKeyboardButton(text="💸 Продать 1", callback_data=f"shop_sell:{recipe_id}:1"),
                InlineKeyboardButton(text="💸 Всё", callback_data=f"shop_sell:{recipe_id}:max"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад в магазин", callback_data="shop_home")],
        ]
    )


def shop_confirmation_keyboard(recipe_id: str, amount: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"shop_confirm:{recipe_id}:{amount}")],
            [InlineKeyboardButton(text="🏪 Назад в магазин", callback_data="shop_home")],
        ]
    )


def shop_repeat_keyboard(recipe_id: str, amount: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🔁 Повторить x{amount}", callback_data=f"shop_buy:{recipe_id}:{amount}")],
            [
                InlineKeyboardButton(text="🏪 Магазин", callback_data="shop_home"),
                InlineKeyboardButton(text="🎒 Инвентарь", callback_data="open:inv"),
            ],
        ]
    )


def shop_cart_keyboard(cart_items) -> InlineKeyboardMarkup:
    if isinstance(cart_items, bool):
        items = {}
        has_items = cart_items
    else:
        items = cart_items or {}
        has_items = bool(items)
    rows = []
    for recipe_id, amount in items.items():
        recipe = get_recipe(recipe_id)
        rows.append([
            InlineKeyboardButton(text=f"− {recipe['name']}", callback_data=f"shop_cart_adjust:{recipe_id}:-1"),
            InlineKeyboardButton(text=f"{amount} шт.", callback_data="shop_cart"),
            InlineKeyboardButton(text="+", callback_data=f"shop_cart_adjust:{recipe_id}:1"),
            InlineKeyboardButton(text="✕", callback_data=f"shop_cart_remove:{recipe_id}"),
        ])
    if has_items:
        rows.append([
            InlineKeyboardButton(text="✅ Купить корзину", callback_data="shop_cart_buy"),
            InlineKeyboardButton(text="🧹 Очистить", callback_data="shop_cart_clear"),
        ])
    rows.append([InlineKeyboardButton(text="🏪 Назад в магазин", callback_data="shop_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shop_wishlist_keyboard(items) -> InlineKeyboardMarkup:
    rows = []
    for item in items or []:
        recipe_id = item["recipe_id"]
        amount = item.get("amount", 1)
        recipe = get_recipe(recipe_id)
        if item.get("ready"):
            rows.append([
                InlineKeyboardButton(text=f"✅ Купить: {recipe['name']} x{amount}", callback_data=f"shop_wishlist_buy:{recipe_id}:{amount}"),
                InlineKeyboardButton(text="🧺 В корзину", callback_data=f"shop_wishlist_cart:{recipe_id}:{amount}"),
            ])
        rows.append([InlineKeyboardButton(text=f"✕ Убрать: {recipe['name']}", callback_data=f"shop_wishlist_remove:{recipe_id}")])
    rows.append([InlineKeyboardButton(text="🏪 Назад в магазин", callback_data="shop_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def daily_keyboard(can_claim: bool) -> InlineKeyboardMarkup:
    rows = []
    if can_claim:
        rows.append([InlineKeyboardButton(text="🎁 Забрать награду", callback_data="daily_claim")])
    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="daily_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
