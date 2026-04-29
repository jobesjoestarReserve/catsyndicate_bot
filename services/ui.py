from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from services.crafting import get_item_recipe_id


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🐟 Мяу"), KeyboardButton(text="🐭 Охота")],
            [KeyboardButton(text="🎒 Инвентарь"), KeyboardButton(text="🛠 Кузница")],
            [KeyboardButton(text="🧥 Экипировка"), KeyboardButton(text="📊 Досье")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие Синдиката",
    )


def craft_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧪 Расходники", callback_data="craft_cat:consumables")],
            [
                InlineKeyboardButton(text="🪖 Шлемы", callback_data="craft_cat:helmet"),
                InlineKeyboardButton(text="🧥 Нагрудники", callback_data="craft_cat:chest"),
            ],
            [
                InlineKeyboardButton(text="🧤 Нарукавники", callback_data="craft_cat:bracers"),
                InlineKeyboardButton(text="🥾 Ботинки", callback_data="craft_cat:boots"),
            ],
            [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="open:inv")],
        ]
    )


def recipe_keyboard(recipe_ids: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Собрать: {recipe_id}", callback_data=f"craft_make:{recipe_id}")]
        for recipe_id in recipe_ids
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад в кузницу", callback_data="craft_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inventory_keyboard(consumables=None, equipment=None) -> InlineKeyboardMarkup:
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
    for row in equipment or []:
        recipe_id = get_item_recipe_id(row["item_name"])
        if recipe_id:
            rows.append([
                InlineKeyboardButton(
                    text=f"🧷 Надеть: {row['item_name']}",
                    callback_data=f"equip_item:{recipe_id}",
                )
            ])
    rows.append(
        [
            InlineKeyboardButton(text="🛠 Кузница", callback_data="craft_home"),
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
