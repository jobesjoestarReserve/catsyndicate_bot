RESOURCE_LABELS = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}

SLOT_LABELS = {
    "helmet": "шлем",
    "chest": "нагрудник",
    "bracers": "нарукавники",
    "boots": "ботинки",
}

BUFF_LABELS = {
    "grow_focus": "Валерьянка: следующая попытка /grow получает +10% к шансу и +10% XP.",
    "meow_luck": "Кошачья мята: следующий /meow получает +12% к шансу и +25% к добыче.",
    "work_boost": "Мышиный энергетик: следующая /work приносит +20% рыбов.",
    "hunt_safety": "Лапомазь: следующая /hunt получает +10% к шансу и не теряет мышь при провале.",
}

RECIPES = {
    "valerian": {
        "name": "Валерьянка",
        "type": "consumable",
        "cost": {"wool": 2, "trash": 1},
        "effect": "grow_focus",
        "description": "бафф на следующую попытку роста",
    },
    "catnip": {
        "name": "Кошачья мята",
        "type": "consumable",
        "cost": {"wool": 3, "trash": 2},
        "effect": "meow_luck",
        "description": "бафф на следующую кражу рыбов",
    },
    "mouse_energy": {
        "name": "Мышиный энергетик",
        "type": "consumable",
        "cost": {"metal": 1, "trash": 4},
        "effect": "work_boost",
        "description": "бафф на следующую мышиную работу",
    },
    "paw_ointment": {
        "name": "Лапомазь",
        "type": "consumable",
        "cost": {"wool": 2, "metal": 1},
        "effect": "hunt_safety",
        "description": "бафф на следующую охоту",
    },
}

EQUIPMENT_BLUEPRINTS = {
    "helmet": {
        "poor": ("Шлем из фольги", {"trash": 8, "wool": 2}, {"grow_chance": 1}),
        "common": ("Картонный шлем бригадира", {"trash": 5, "wool": 8, "metal": 4}, {"grow_chance": 2}),
        "rare": ("Шлем тихого авторитета", {"trash": 8, "wool": 16, "metal": 12}, {"grow_chance": 3}),
    },
    "chest": {
        "poor": ("Нагрудник из пакета", {"trash": 10, "wool": 2}, {"damage_guard": 1}),
        "common": ("Жилет из плотной шерсти", {"trash": 6, "wool": 10, "metal": 4}, {"damage_guard": 2}),
        "rare": ("Панцирь диванного дона", {"trash": 8, "wool": 18, "metal": 14}, {"damage_guard": 3}),
    },
    "bracers": {
        "poor": ("Нарукавники из скотча", {"trash": 7, "metal": 2}, {"loot_bonus": 1}),
        "common": ("Металлические нарукавники", {"trash": 5, "wool": 6, "metal": 8}, {"loot_bonus": 2}),
        "rare": ("Нарукавники ночной смены", {"trash": 8, "wool": 12, "metal": 16}, {"loot_bonus": 3}),
    },
    "boots": {
        "poor": ("Ботинки из коробки", {"trash": 8, "wool": 3}, {"hunt_chance": 1}),
        "common": ("Тихие подкрадуны", {"trash": 5, "wool": 8, "metal": 5}, {"hunt_chance": 2}),
        "rare": ("Сапоги бесшумного тыгыдыка", {"trash": 8, "wool": 14, "metal": 12}, {"hunt_chance": 3}),
    },
}

TIER_LABELS = {
    "poor": "доступное",
    "common": "среднее",
    "rare": "редкое",
}

for slot, tiers in EQUIPMENT_BLUEPRINTS.items():
    for tier, (name, cost, effects) in tiers.items():
        RECIPES[f"{tier}_{slot}"] = {
            "name": name,
            "type": "equipment",
            "slot": slot,
            "tier": tier,
            "cost": cost,
            "effects": effects,
            "description": f"{TIER_LABELS[tier]} снаряжение: {SLOT_LABELS[slot]}",
        }

ITEMS_BY_NAME = {recipe["name"]: recipe for recipe in RECIPES.values()}
ITEM_IDS_BY_NAME = {recipe["name"]: recipe_id for recipe_id, recipe in RECIPES.items()}

CRAFT_CATEGORIES = {
    "consumables": [
        recipe_id for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "consumable"
    ],
    "helmet": [
        recipe_id for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "equipment" and recipe.get("slot") == "helmet"
    ],
    "chest": [
        recipe_id for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "equipment" and recipe.get("slot") == "chest"
    ],
    "bracers": [
        recipe_id for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "equipment" and recipe.get("slot") == "bracers"
    ],
    "boots": [
        recipe_id for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "equipment" and recipe.get("slot") == "boots"
    ],
}

CATEGORY_TITLES = {
    "consumables": "🧪 Расходники",
    "helmet": "🪖 Шлемы",
    "chest": "🧥 Нагрудники",
    "bracers": "🧤 Нарукавники",
    "boots": "🥾 Ботинки",
}


def get_recipe(recipe_id: str | None):
    if not recipe_id:
        return None
    return RECIPES.get(recipe_id.lower())


def get_item(item_name: str | None):
    return ITEMS_BY_NAME.get(item_name or "")


def get_item_recipe_id(item_name: str | None) -> str | None:
    return ITEM_IDS_BY_NAME.get(item_name or "")


def get_category_recipe_ids(category: str) -> list[str]:
    return CRAFT_CATEGORIES.get(category, [])


def get_equipment_slot(item_name: str) -> str | None:
    item = get_item(item_name)
    if item and item["type"] == "equipment":
        return item["slot"]
    return None


def get_slot_item_names(slot: str) -> list[str]:
    return [
        recipe["name"]
        for recipe in RECIPES.values()
        if recipe["type"] == "equipment" and recipe.get("slot") == slot
    ]


def get_consumable_effect(item_name: str) -> str | None:
    item = get_item(item_name)
    if item and item["type"] == "consumable":
        return item["effect"]
    return None


def get_equipment_bonus(equipped_items, bonus_name: str) -> int:
    total = 0
    for row in equipped_items or []:
        item = get_item(row["item_name"])
        if not item:
            continue
        total += item.get("effects", {}).get(bonus_name, 0)
    return total


def format_cost(cost: dict[str, int]) -> str:
    return ", ".join(
        f"{RESOURCE_LABELS.get(name, name)} {amount}"
        for name, amount in cost.items()
    )


def format_recipe_line(recipe_id: str, recipe: dict) -> str:
    return (
        f"<code>{recipe_id}</code> — <b>{recipe['name']}</b>\n"
        f"  {recipe['description']}; цена: {format_cost(recipe['cost'])}"
    )


def format_recipe_list() -> str:
    consumables = [
        format_recipe_line(recipe_id, recipe)
        for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "consumable"
    ]
    equipment = [
        format_recipe_line(recipe_id, recipe)
        for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "equipment"
    ]
    return (
        "🧪 <b>Расходники</b>\n"
        + "\n".join(consumables)
        + "\n\n🛠 <b>Экипировка</b>\n"
        + "\n".join(equipment)
    )


def format_recipe_category(category: str) -> str:
    recipe_ids = get_category_recipe_ids(category)
    title = CATEGORY_TITLES.get(category, "Кузница")
    if not recipe_ids:
        return f"{title}\n\nРецептов пока нет."
    return title + "\n\n" + "\n\n".join(
        format_recipe_line(recipe_id, RECIPES[recipe_id])
        for recipe_id in recipe_ids
    )
