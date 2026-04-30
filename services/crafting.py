import random

RESOURCE_LABELS = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}

SLOT_LABELS = {
    "weapon": "оружие",
    "helmet": "шлем",
    "chest": "нагрудник",
    "bracers": "нарукавники",
    "boots": "ботинки",
}

BUFF_LABELS = {
    "grow_focus": "Валерьянка: следующая попытка роста получает +10% к шансу и +10% XP.",
    "meow_luck": "Кошачья мята: следующий мяу-поход получает +12% к шансу и +25% к добыче.",
    "work_boost": "Мышиный энергетик: следующая работа приносит +20% рыбов.",
    "hunt_safety": "Лапомазь: следующая охота получает +10% к шансу и не теряет мышь при провале.",
}

CRAFT_OUTCOME_TEXTS = {
    "critical_success": [
        "Мастер был в ударе: материалы остались целы, а вещь вышла настолько важной, что сама попросила отдельную полку.",
        "Кузнец чихнул в правильной тональности, и металл сам принял форму. Ресурсы не пострадали, кроме чувства собственной значимости.",
        "Молот попал в ритм дворового джаза. Заготовка стала королевской, материалы остались лежать с видом свидетелей чуда.",
        "Печь моргнула, кузнец подмигнул, предмет получился с таким лоском, что его хочется записать в родословную.",
        "Секретная техника сработала: один удар, ноль потерь, максимум самодовольства.",
        "Кузнец случайно открыл режим 'премиум'. Материалы целы, предмет сияет так, будто знает юриста.",
        "Заготовка сама прыгнула на наковальню и попросила сделать её легендой. Кузнец не стал спорить.",
        "Мастер произнёс запрещённое 'мяу' кузнечного цеха. Ресурсы сохранились, качество стало неприлично высоким.",
        "Наковальня выдала стоячую овацию. Материалы остались целы, предмет вышел с королевским нахальством.",
        "Кузнец использовал технику 'а что если идеально'. Невероятно, но сработало.",
        "Искры сложились в герб Синдиката. Предмет получился шикарным, материалы тихо аплодируют из инвентаря.",
        "Печь решила не брать плату за красоту. Вещь выкована, ресурсы на месте, бухгалтерия в растерянности.",
        "Молот ударил ровно туда, где у хаоса кнопка 'улучшить'. Получилось роскошно и почти незаконно.",
        "Кузнец сделал вид, что всё было по плану. Никто не поверил, но предмет получился королевский.",
        "Заготовка вышла из огня с осанкой аристократа. Материалы сохранены, Синдикат доволен.",
    ],
    "success": [
        "Кузнец отработал смену без театра: ресурсы ушли, предмет появился, наковальня не жалуется.",
        "Печь шумела, молот стучал, результат получился достаточно убедительным, чтобы им гордиться.",
        "Материалы честно превратились в вещь. Никаких чудес, только ремесло и подозрительный запах шерсти.",
        "Заготовка сопротивлялась, но капитулировала перед профессиональной наглостью.",
        "Кузнец сказал 'нормально будет', и, что удивительно, действительно нормально.",
        "Искры летели строго по регламенту. Предмет собран, ресурсы списаны, цех выжил.",
        "Наковальня выдержала, кузнец не промахнулся, вещь получила право на существование.",
        "Материалы ушли в дело, а не в легенды о неудачах. Уже победа.",
        "Пара ударов, немного дыма, один новый предмет. Классика Синдиката.",
        "Кузнец сделал работу так спокойно, что это даже подозрительно.",
        "Заготовка стала предметом без лишней драмы. Где-то грустит один пожарный инспектор.",
        "Ресурсы потрачены, вещь готова. Всё честно, почти скучно, зато полезно.",
        "Мастер не спорил с физикой и получил вполне приличный результат.",
        "Печь фыркнула, но выполнила заказ. Предмет можно забирать.",
        "Кузница выдала рабочий результат и ни одного лишнего судебного дела.",
    ],
    "failure": [
        "Заготовка сказала 'нет' и превратилась в учебное пособие по разочарованию. Ресурсы ушли.",
        "Кузнец ударил с душой, но душа промахнулась. Материалы списаны, предмет не родился.",
        "Печь приняла ресурсы и выдала дым философского характера. Пользы мало, выводов много.",
        "Наковальня звякнула так, будто ей стыдно. Ковка сорвалась.",
        "Материалы закончились раньше, чем у кузнеца появилась уверенность. Бывает.",
        "Заготовка развалилась на аргументы против ремесла. Предмет не получился.",
        "Кузнец перепутал вдохновение с самоуверенностью. Ресурсы это не пережили.",
        "Искры были красивые, результат нет. Синдикат делает вид, что ничего не видел.",
        "Печь решила устроить забастовку без уведомления. Материалы сгорели в переговорах.",
        "Молот попал, но не в эпоху. Ковка провалена.",
        "Заготовка стала комком с характером. Пользоваться этим нельзя, помнить неприятно.",
        "Кузнец попытался импровизировать. Импровизация подала на развод.",
        "Материалы ушли в дым, дым ушёл в потолок, потолок теперь главный свидетель.",
        "Наковальня сказала 'дзынь', и это был звук финансовой грусти.",
        "План был хороший, пока не встретился с реальностью. Предмет не создан.",
    ],
    "critical_failure": [
        "Кузнец уронил заготовку в чан с лавой. Чтобы спасти проект, пришлось потратить в два раза больше материалов.",
        "Печь внезапно потребовала двойной тариф за эмоциональный ущерб. Предмет спасли, карман похудел.",
        "Молот отскочил, заготовка улетела в ведро с неизвестностью. Достали, но ресурсов ушло вдвое больше.",
        "Кузнец перепутал щипцы с амбициями. Проект выжил только после двойной порции материалов.",
        "Наковальня закашлялась искрами и попросила добавки. Пришлось платить ресурсами дважды.",
        "Заготовка начала плавиться не по сценарию. Её спасли, но склад материалов теперь молчит осуждающе.",
        "Печь включила режим 'дорого-богато-больно'. Предмет есть, ресурсов стало заметно меньше.",
        "Кузнец сказал 'сейчас исправим' четыре раза. Исправили с двойной ценой.",
        "Материалы провалились в технологическую яму. Чтобы вытащить результат, пришлось докинуть столько же.",
        "Искры сложились в слово 'упс'. Проект спасён, но бухгалтерия рыдает в углу.",
        "Заготовка попыталась стать супом. Кузнец победил, ресурсы проиграли.",
        "Печь решила, что один комплект материалов это только вступительный взнос. Пришлось доплатить.",
        "Мастер применил секретную технику паники. Работает, но стоит в два раза дороже.",
        "Наковальня ушла в драму, кузнец в отрицание, материалы в расход. Предмет чудом спасён.",
        "Кузница устроила спектакль с антрактом. Во втором акте пришлось потратить ещё столько же ресурсов.",
    ],
}

CRAFT_OUTCOME_CONFIG = {
    "critical_success": {"weight": 5, "cost_multiplier": 0, "create_amount": 2},
    "success": {"weight": 85, "cost_multiplier": 1, "create_amount": 1},
    "failure": {"weight": 5, "cost_multiplier": 1, "create_amount": 0},
    "critical_failure": {"weight": 5, "cost_multiplier": 2, "create_amount": 1},
}

RECIPES = {
    "valerian": {
        "name": "Валерьянка",
        "type": "consumable",
        "cost": {},
        "fish_cost": 45,
        "effect": "grow_focus",
        "description": "бафф на следующую попытку роста",
    },
    "catnip": {
        "name": "Кошачья мята",
        "type": "consumable",
        "cost": {},
        "fish_cost": 40,
        "effect": "meow_luck",
        "description": "бафф на следующую кражу рыбов",
    },
    "mouse_energy": {
        "name": "Мышиный энергетик",
        "type": "consumable",
        "cost": {},
        "fish_cost": 55,
        "effect": "work_boost",
        "description": "бафф на следующую мышиную работу",
    },
    "paw_ointment": {
        "name": "Лапомазь",
        "type": "consumable",
        "cost": {},
        "fish_cost": 50,
        "effect": "hunt_safety",
        "description": "бафф на следующую охоту",
    },
}

WEAPON_BLUEPRINTS = {
    "warrior": {
        "poor": ("Половник обороны", {"metal": 5, "trash": 8, "wool": 2}, {"damage_guard": 1}, "доступное оружие танка"),
        "common": ("Сковородный щитолом", {"metal": 12, "trash": 10, "wool": 4}, {"damage_guard": 2, "boss_damage": 1}, "среднее оружие танка"),
        "rare": ("Крышка непробиваемого авторитета", {"metal": 22, "trash": 14, "wool": 8}, {"damage_guard": 3, "boss_damage": 2}, "редкое оружие танка"),
    },
    "thief": {
        "poor": ("Ржавая отмычка хвоста", {"metal": 4, "trash": 9, "wool": 2}, {"loot_bonus": 1}, "доступное оружие вора"),
        "common": ("Отмычка рыбного налога", {"metal": 8, "trash": 14, "wool": 4}, {"loot_bonus": 2}, "среднее оружие вора"),
        "rare": ("Крючок бесследного налогообложения", {"metal": 14, "trash": 22, "wool": 7}, {"loot_bonus": 3, "bite_power": 1}, "редкое оружие вора"),
    },
    "support": {
        "poor": ("Фонарик моральной поддержки", {"metal": 3, "trash": 6, "wool": 8}, {"hunt_chance": 1}, "доступное оружие саппорта"),
        "common": ("Лазерная указка наставника", {"metal": 6, "trash": 8, "wool": 12}, {"grow_chance": 2, "hunt_chance": 1}, "среднее оружие саппорта"),
        "rare": ("Проектор великого плана", {"metal": 12, "trash": 12, "wool": 22}, {"grow_chance": 3, "hunt_chance": 2}, "редкое оружие саппорта"),
    },
    "assassin": {
        "poor": ("Булавка тихого кусь", {"metal": 7, "trash": 5, "wool": 1}, {"bite_power": 1}, "доступное оружие убийцы"),
        "common": ("Тихий коготь ночной смены", {"metal": 14, "trash": 8, "wool": 3}, {"bite_power": 2, "boss_damage": 2}, "среднее оружие убийцы"),
        "rare": ("Коготь абсолютной тишины", {"metal": 24, "trash": 12, "wool": 6}, {"bite_power": 3, "boss_damage": 3}, "редкое оружие убийцы"),
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

EQUIPMENT_DURABILITY_BY_TIER = {
    "poor": 30,
    "common": 40,
    "rare": 50,
}

ARMOR_FISH_COST_BY_TIER = {
    "poor": 15,
    "common": 40,
    "rare": 85,
}

WEAPON_FISH_COST_BY_TIER = {
    "poor": 25,
    "common": 60,
    "rare": 110,
}

for slot, tiers in EQUIPMENT_BLUEPRINTS.items():
    for tier, (name, cost, effects) in tiers.items():
        RECIPES[f"{tier}_{slot}"] = {
            "name": name,
            "type": "equipment",
            "slot": slot,
            "tier": tier,
            "cost": cost,
            "fish_cost": ARMOR_FISH_COST_BY_TIER[tier],
            "effects": effects,
            "description": f"{TIER_LABELS[tier]} снаряжение: {SLOT_LABELS[slot]}",
        }

for cat_class, tiers in WEAPON_BLUEPRINTS.items():
    for tier, (name, cost, effects, description) in tiers.items():
        RECIPES[f"{tier}_weapon_{cat_class}"] = {
            "name": name,
            "type": "equipment",
            "slot": "weapon",
            "class": cat_class,
            "tier": tier,
            "cost": cost,
            "fish_cost": WEAPON_FISH_COST_BY_TIER[tier],
            "effects": effects,
            "description": description,
        }

ITEMS_BY_NAME = {recipe["name"]: recipe for recipe in RECIPES.values()}
ITEM_IDS_BY_NAME = {recipe["name"]: recipe_id for recipe_id, recipe in RECIPES.items()}
ITEM_IDS_BY_NORMALIZED_NAME = {recipe["name"].lower(): recipe_id for recipe_id, recipe in RECIPES.items()}

CRAFT_CATEGORIES = {
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
    "weapon": [
        recipe_id for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "equipment" and recipe.get("slot") == "weapon"
    ],
}

CATEGORY_TITLES = {
    "helmet": "🪖 Шлемы",
    "chest": "🧥 Нагрудники",
    "bracers": "🧤 Нарукавники",
    "boots": "🥾 Ботинки",
    "weapon": "🗡 Оружие классов",
}

WEAPON_CLASS_LABELS = {
    "warrior": "Танк",
    "thief": "Вор",
    "support": "Саппорт",
    "assassin": "Убийца",
}

SHOP_ITEM_IDS = [
    recipe_id for recipe_id, recipe in RECIPES.items()
    if recipe["type"] == "consumable"
]


def roll_forging_outcome(roll: int | None = None) -> str:
    value = roll if roll is not None else random.randint(1, 100)
    threshold = 0
    for outcome, config in CRAFT_OUTCOME_CONFIG.items():
        threshold += config["weight"]
        if value <= threshold:
            return outcome
    return "critical_failure"


def get_forging_cost(recipe: dict, outcome: str) -> dict[str, int]:
    multiplier = CRAFT_OUTCOME_CONFIG[outcome]["cost_multiplier"]
    return {name: amount * multiplier for name, amount in recipe["cost"].items()}


def get_forging_create_amount(outcome: str) -> int:
    return CRAFT_OUTCOME_CONFIG[outcome]["create_amount"]


def get_forging_create_amount_for_recipe(recipe: dict, outcome: str) -> int:
    amount = get_forging_create_amount(outcome)
    if recipe["type"] == "equipment" and amount > 0:
        return 1
    return amount


def get_upgraded_equipment_recipe_id(recipe_id: str | None) -> str | None:
    recipe = get_recipe(recipe_id)
    if not recipe or recipe.get("type") != "equipment":
        return None

    tiers = ("poor", "common", "rare")
    tier = recipe.get("tier")
    if tier not in tiers:
        return None

    next_index = tiers.index(tier) + 1
    if next_index >= len(tiers):
        return None

    if recipe.get("slot") == "weapon":
        return f"{tiers[next_index]}_weapon_{recipe['class']}"
    return f"{tiers[next_index]}_{recipe['slot']}"


def get_upgraded_weapon_recipe_id(recipe_id: str | None) -> str | None:
    upgraded_recipe_id = get_upgraded_equipment_recipe_id(recipe_id)
    recipe = get_recipe(upgraded_recipe_id)
    if recipe and recipe.get("slot") == "weapon":
        return upgraded_recipe_id
    return None


def get_equipment_durability_max(recipe_id: str | None) -> int | None:
    recipe = get_recipe(recipe_id)
    if not recipe or recipe.get("type") != "equipment":
        return None
    return EQUIPMENT_DURABILITY_BY_TIER.get(recipe.get("tier"))


def get_equipment_family_names(recipe_id: str | None) -> list[str]:
    recipe = get_recipe(recipe_id)
    if not recipe or recipe.get("type") != "equipment":
        return []

    if recipe.get("slot") == "weapon":
        family_recipe_ids = [
            f"{tier}_weapon_{recipe['class']}"
            for tier in ("poor", "common", "rare")
        ]
    else:
        family_recipe_ids = [
            f"{tier}_{recipe['slot']}"
            for tier in ("poor", "common", "rare")
        ]
    return [RECIPES[family_recipe_id]["name"] for family_recipe_id in family_recipe_ids]


def format_durability(row) -> str:
    current = row.get("durability_current") if row else None
    maximum = row.get("durability_max") if row else None
    if current is None or maximum is None:
        return ""
    return f" [{current}/{maximum}]"


def get_recipe(recipe_id: str | None):
    if not recipe_id:
        return None
    lookup = recipe_id.strip().lower()
    return RECIPES.get(lookup) or ITEMS_BY_NAME.get(recipe_id.strip())


def get_recipe_id(recipe_name_or_id: str | None) -> str | None:
    if not recipe_name_or_id:
        return None
    lookup = recipe_name_or_id.strip().lower()
    if lookup in RECIPES:
        return lookup
    return ITEM_IDS_BY_NORMALIZED_NAME.get(lookup)


def get_item(item_name: str | None):
    if not item_name:
        return None
    return ITEMS_BY_NAME.get(item_name) or ITEMS_BY_NAME.get(item_name.strip()) or RECIPES.get(
        ITEM_IDS_BY_NORMALIZED_NAME.get(item_name.strip().lower(), "")
    )


def get_item_recipe_id(item_name: str | None) -> str | None:
    return ITEM_IDS_BY_NAME.get(item_name or "")


def get_category_recipe_ids(category: str) -> list[str]:
    return CRAFT_CATEGORIES.get(category, [])


def get_weapon_class_recipe_ids(cat_class: str) -> list[str]:
    if cat_class not in WEAPON_BLUEPRINTS:
        return []
    return [
        f"{tier}_weapon_{cat_class}"
        for tier in ("poor", "common", "rare")
    ]


def get_equipment_slot(item_name: str) -> str | None:
    item = get_item(item_name)
    if item and item["type"] == "equipment":
        return item["slot"]
    return None


def get_equipment_class(item_name: str) -> str | None:
    item = get_item(item_name)
    if item and item["type"] == "equipment":
        return item.get("class")
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
    if not cost:
        return "без ресурсов"
    return ", ".join(
        f"{RESOURCE_LABELS.get(name, name)} {amount}"
        for name, amount in cost.items()
    )


def format_recipe_price(recipe: dict) -> str:
    parts = []
    if recipe.get("cost"):
        parts.append(format_cost(recipe["cost"]))
    fish_cost = recipe.get("fish_cost", 0)
    if fish_cost:
        parts.append(f"{fish_cost} 🐟")
    return ", ".join(parts) if parts else "бесплатно"


def get_shop_item_ids() -> list[str]:
    return SHOP_ITEM_IDS[:]


def format_recipe_line(recipe_id: str, recipe: dict) -> str:
    return (
        f"<b>{recipe['name']}</b>\n"
        f"  {recipe['description']}; цена: {format_recipe_price(recipe)}"
    )


def format_recipe_list() -> str:
    equipment = [
        format_recipe_line(recipe_id, recipe)
        for recipe_id, recipe in RECIPES.items()
        if recipe["type"] == "equipment"
    ]
    return (
        "🛠 <b>Экипировка</b>\n"
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
