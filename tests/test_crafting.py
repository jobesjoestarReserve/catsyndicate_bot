import unittest
from unittest.mock import AsyncMock, patch

from services.crafting import (
    CRAFT_OUTCOME_CONFIG,
    CRAFT_OUTCOME_TEXTS,
    RECIPES,
    format_cost,
    format_durability,
    format_recipe_price,
    format_recipe_line,
    get_category_recipe_ids,
    get_equipment_class,
    get_consumable_effect,
    get_equipment_bonus,
    get_equipment_slot,
    get_forging_cost,
    get_forging_create_amount,
    get_forging_create_amount_for_recipe,
    get_item_recipe_id,
    get_recipe,
    get_recipe_id,
    get_equipment_family_names,
    get_weapon_class_recipe_ids,
    get_shop_item_ids,
    get_slot_item_names,
    get_upgraded_equipment_recipe_id,
    get_upgraded_weapon_recipe_id,
    roll_forging_outcome,
)
from handlers.crafting import (
    can_equip_for_class,
    craft_recipe_for_user,
    equip_item_for_user,
    format_gear_view,
    use_consumable_for_user,
)
from data.texts import SHOP_NOT_ENOUGH_FISH_TEXTS, SHOP_STACK_FULL_TEXTS
from handlers.shop import buy_shop_item_for_user, parse_shop_amount
from handlers.shop import (
    build_shop_preview,
    build_shop_cart_view,
    buy_shop_wishlist_item_for_user,
    format_shop_home,
    format_shop_history,
    get_daily_limited_remaining,
)
from services.shop import (
    SHOP_DAILY_LIMIT,
    calculate_shop_amount,
    calculate_shop_cart,
    calculate_sell_amount,
    calculate_shop_total,
    format_shop_wishlist,
    get_daily_shelf_event,
    get_daily_deal_recipe_id,
    get_daily_stock_boost_recipe_id,
    get_shop_reputation,
    get_shop_daily_limit,
    get_sorted_shop_item_ids,
    get_shop_item_ids_for_category,
    get_shop_unit_price,
    get_three_for_two_paid_amount,
    get_three_for_two_recipe_id,
    needs_shop_confirmation,
)
from services.ui import (
    recipe_detail_keyboard,
    recipe_keyboard,
    shop_cart_keyboard,
    shop_item_keyboard,
    shop_keyboard,
    shop_repeat_keyboard,
    shop_wishlist_keyboard,
)


class CraftingTests(unittest.TestCase):
    def test_core_consumables_have_effects(self):
        self.assertEqual(get_consumable_effect("Валерьянка"), "grow_focus")
        self.assertEqual(get_consumable_effect("Кошачья мята"), "meow_luck")
        self.assertEqual(get_consumable_effect("Мышиный энергетик"), "work_boost")
        self.assertEqual(get_consumable_effect("Лапомазь"), "hunt_safety")

    def test_equipment_slots_are_known(self):
        self.assertEqual(get_equipment_slot("Шлем из фольги"), "helmet")
        self.assertEqual(get_equipment_slot("Жилет из плотной шерсти"), "chest")
        self.assertEqual(get_equipment_slot("Металлические нарукавники"), "bracers")
        self.assertEqual(get_equipment_slot("Сапоги бесшумного тыгыдыка"), "boots")
        self.assertEqual(get_equipment_slot("Тихий коготь ночной смены"), "weapon")

    def test_item_names_map_back_to_recipe_ids(self):
        self.assertEqual(get_item_recipe_id("Валерьянка"), "valerian")
        self.assertEqual(get_item_recipe_id("Шлем из фольги"), "poor_helmet")
        self.assertEqual(get_item_recipe_id("Отмычка рыбного налога"), "common_weapon_thief")

    def test_recipe_lookup_accepts_case_and_extra_spaces(self):
        self.assertEqual(get_recipe_id("  шлем из фольги  "), "poor_helmet")
        self.assertEqual(get_recipe_id("VALERIAN"), "valerian")

    def test_each_equipment_slot_has_three_tiers(self):
        for slot in ("helmet", "chest", "bracers", "boots"):
            with self.subTest(slot=slot):
                self.assertEqual(len(get_slot_item_names(slot)), 3)

    def test_weapon_slot_has_three_tiers_per_class(self):
        weapon_names = get_slot_item_names("weapon")

        self.assertEqual(len(weapon_names), 12)
        self.assertEqual(
            get_weapon_class_recipe_ids("thief"),
            ["poor_weapon_thief", "common_weapon_thief", "rare_weapon_thief"],
        )
        self.assertEqual(get_weapon_class_recipe_ids("unknown"), [])
        self.assertEqual(get_equipment_class("Сковородный щитолом"), "warrior")
        self.assertEqual(get_equipment_class("Отмычка рыбного налога"), "thief")
        self.assertEqual(get_equipment_class("Лазерная указка наставника"), "support")
        self.assertEqual(get_equipment_class("Тихий коготь ночной смены"), "assassin")
        self.assertIn("Коготь абсолютной тишины", weapon_names)

    def test_equipment_bonus_sums_known_items(self):
        equipped = [
            {"item_name": "Металлические нарукавники"},
            {"item_name": "Сапоги бесшумного тыгыдыка"},
        ]

        self.assertEqual(get_equipment_bonus(equipped, "loot_bonus"), 2)
        self.assertEqual(get_equipment_bonus(equipped, "hunt_chance"), 3)

    def test_class_weapon_effects_are_active(self):
        equipped = [
            {"item_name": "Тихий коготь ночной смены"},
            {"item_name": "Сковородный щитолом"},
        ]

        self.assertEqual(get_equipment_bonus(equipped, "bite_power"), 2)
        self.assertEqual(get_equipment_bonus(equipped, "boss_damage"), 3)
        self.assertEqual(get_equipment_bonus(equipped, "damage_guard"), 2)

    def test_equipment_upgrade_recipe_ids_follow_quality_ladder(self):
        self.assertEqual(get_upgraded_equipment_recipe_id("poor_helmet"), "common_helmet")
        self.assertEqual(get_upgraded_equipment_recipe_id("common_boots"), "rare_boots")
        self.assertIsNone(get_upgraded_equipment_recipe_id("rare_chest"))
        self.assertIsNone(get_upgraded_equipment_recipe_id("valerian"))

        self.assertEqual(get_upgraded_weapon_recipe_id("poor_weapon_thief"), "common_weapon_thief")
        self.assertEqual(get_upgraded_weapon_recipe_id("common_weapon_thief"), "rare_weapon_thief")
        self.assertIsNone(get_upgraded_weapon_recipe_id("rare_weapon_thief"))
        self.assertIsNone(get_upgraded_weapon_recipe_id("poor_helmet"))

    def test_format_durability_for_equipment_rows(self):
        self.assertEqual(format_durability({"durability_current": 18, "durability_max": 30}), " [18/30]")
        self.assertEqual(format_durability({"durability_current": None, "durability_max": None}), "")

    def test_equipment_family_names_follow_slot_or_weapon_class(self):
        self.assertEqual(
            get_equipment_family_names("poor_helmet"),
            ["Шлем из фольги", "Картонный шлем бригадира", "Шлем тихого авторитета"],
        )
        self.assertEqual(
            get_equipment_family_names("poor_weapon_thief"),
            ["Ржавая отмычка хвоста", "Отмычка рыбного налога", "Крючок бесследного налогообложения"],
        )
        self.assertEqual(get_equipment_family_names("valerian"), [])

    def test_class_weapon_equip_guard_matches_user_class(self):
        self.assertTrue(can_equip_for_class({"cat_class": "thief"}, "Отмычка рыбного налога"))
        self.assertFalse(can_equip_for_class({"cat_class": "support"}, "Отмычка рыбного налога"))
        self.assertTrue(can_equip_for_class({"cat_class": "support"}, "Шлем из фольги"))

    def test_equipment_recipe_prices_include_resources_and_fish(self):
        for recipe_id, recipe in RECIPES.items():
            with self.subTest(recipe_id=recipe_id):
                self.assertIs(get_recipe(recipe_id), recipe)
                if recipe["type"] == "equipment":
                    self.assertTrue(recipe["cost"])
                    self.assertGreater(recipe["fish_cost"], 0)
                    self.assertTrue(format_cost(recipe["cost"]))
                    self.assertIn("🐟", format_recipe_price(recipe))

    def test_consumables_are_shop_items_not_craft_categories(self):
        shop_ids = get_shop_item_ids()

        self.assertEqual(set(shop_ids), {"valerian", "catnip", "mouse_energy", "paw_ointment"})
        self.assertEqual(get_category_recipe_ids("consumables"), [])
        for recipe_id in shop_ids:
            with self.subTest(recipe_id=recipe_id):
                recipe = RECIPES[recipe_id]
                self.assertEqual(recipe["type"], "consumable")
                self.assertEqual(recipe["cost"], {})
                self.assertGreater(recipe["fish_cost"], 0)

    def test_shop_items_are_sorted_by_effect_role(self):
        self.assertEqual(get_sorted_shop_item_ids(), ["valerian", "paw_ointment", "mouse_energy", "catnip"])

    def test_shop_category_filters_items_by_effect_role(self):
        self.assertEqual(get_shop_item_ids_for_category("all"), ["valerian", "paw_ointment", "mouse_energy", "catnip"])
        self.assertEqual(get_shop_item_ids_for_category("grow"), ["valerian"])
        self.assertEqual(get_shop_item_ids_for_category("hunt"), ["paw_ointment"])
        self.assertEqual(get_shop_item_ids_for_category("work"), ["mouse_energy"])
        self.assertEqual(get_shop_item_ids_for_category("fish"), ["catnip"])

    def test_daily_deal_is_stable_for_same_date_and_discounts_price(self):
        deal = get_daily_deal_recipe_id(today="2026-04-30")
        self.assertEqual(deal, get_daily_deal_recipe_id(today="2026-04-30"))
        self.assertIn(deal, get_shop_item_ids())

        recipe = get_recipe(deal)
        self.assertEqual(get_shop_unit_price(deal, today="2026-04-30"), max(1, recipe["fish_cost"] * 80 // 100))

    def test_daily_promos_use_separate_stable_random_item_choices(self):
        discount_items = {get_daily_deal_recipe_id(today=f"2026-05-0{day}") for day in range(1, 5)}
        three_for_two_items = {get_three_for_two_recipe_id(today=f"2026-05-0{day}") for day in range(1, 5)}
        stock_boost_items = {get_daily_stock_boost_recipe_id(today=f"2026-05-0{day}") for day in range(1, 5)}

        self.assertGreater(len(discount_items), 1)
        self.assertGreater(len(three_for_two_items), 1)
        self.assertGreater(len(stock_boost_items), 1)
        self.assertEqual(get_three_for_two_recipe_id(today="2026-04-30"), get_three_for_two_recipe_id(today="2026-04-30"))
        self.assertIn(get_three_for_two_recipe_id(today="2026-04-30"), get_shop_item_ids())
        self.assertEqual(get_daily_stock_boost_recipe_id(today="2026-04-30"), get_daily_stock_boost_recipe_id(today="2026-04-30"))
        self.assertEqual(get_shop_daily_limit(get_daily_stock_boost_recipe_id(today="2026-04-30"), today="2026-04-30"), SHOP_DAILY_LIMIT + 80)
        shelf = get_daily_shelf_event(today="2026-04-30")
        self.assertIn(shelf["recipe_id"], get_shop_item_ids())
        self.assertIn("title", shelf)

    def test_shop_reputation_adds_soft_limit_bonus(self):
        rookie = get_shop_reputation({"spent": 0, "refunded": 0})
        regular = get_shop_reputation({"spent": 1500, "refunded": 0})

        self.assertEqual(rookie["limit_bonus"], 0)
        self.assertGreater(regular["limit_bonus"], 0)
        self.assertIn("title", regular)

    def test_shop_wishlist_formats_ready_and_blocked_items(self):
        text = format_shop_wishlist([
            {"recipe_id": "valerian", "amount": 3, "ready": True, "reason": ""},
            {"recipe_id": "catnip", "amount": 2, "ready": False, "reason": "не хватает рыбов"},
        ])

        self.assertIn("Хотелки", text)
        self.assertIn("Валерьянка", text)
        self.assertIn("готово", text.lower())
        self.assertIn("не хватает рыбов", text)

    def test_shop_wishlist_keyboard_can_buy_cart_and_remove_ready_item(self):
        keyboard = shop_wishlist_keyboard([
            {"recipe_id": "valerian", "amount": 3, "ready": True, "reason": ""},
            {"recipe_id": "catnip", "amount": 2, "ready": False, "reason": "не хватает рыбов"},
        ])
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("shop_wishlist_buy:valerian:3", callback_data)
        self.assertIn("shop_wishlist_cart:valerian:3", callback_data)
        self.assertIn("shop_wishlist_remove:valerian", callback_data)
        self.assertNotIn("shop_wishlist_buy:catnip:2", callback_data)

    def test_three_for_two_promo_makes_every_third_item_free(self):
        self.assertEqual(get_three_for_two_paid_amount(1), 1)
        self.assertEqual(get_three_for_two_paid_amount(2), 2)
        self.assertEqual(get_three_for_two_paid_amount(3), 2)
        self.assertEqual(get_three_for_two_paid_amount(6), 4)
        self.assertEqual(calculate_shop_total(unit_price=45, amount=6, promo_active=True), 180)
        self.assertEqual(calculate_shop_total(unit_price=45, amount=6, promo_active=False), 270)

    def test_recipe_lines_show_localized_names_not_internal_ids(self):
        line = format_recipe_line("valerian", RECIPES["valerian"])

        self.assertIn("Валерьянка", line)
        self.assertNotIn("valerian", line)

    def test_forging_outcome_distribution_keeps_90_10_base_split(self):
        self.assertEqual(sum(config["weight"] for config in CRAFT_OUTCOME_CONFIG.values()), 100)
        self.assertEqual(roll_forging_outcome(1), "critical_success")
        self.assertEqual(roll_forging_outcome(6), "success")
        self.assertEqual(roll_forging_outcome(91), "failure")
        self.assertEqual(roll_forging_outcome(96), "critical_failure")

    def test_forging_outcome_costs_and_amounts(self):
        recipe = RECIPES["poor_helmet"]

        self.assertEqual(get_forging_cost(recipe, "critical_success"), {"trash": 0, "wool": 0})
        self.assertEqual(get_forging_create_amount("critical_success"), 2)
        self.assertEqual(get_forging_create_amount_for_recipe(recipe, "critical_success"), 1)
        self.assertEqual(get_forging_create_amount_for_recipe(RECIPES["valerian"], "critical_success"), 2)
        self.assertEqual(get_forging_cost(recipe, "success"), recipe["cost"])
        self.assertEqual(get_forging_create_amount("failure"), 0)
        self.assertEqual(get_forging_cost(recipe, "critical_failure"), {"trash": 16, "wool": 4})

    def test_forging_outcomes_have_15_thematic_lines_each(self):
        for outcome, lines in CRAFT_OUTCOME_TEXTS.items():
            with self.subTest(outcome=outcome):
                self.assertEqual(len(lines), 15)

    def test_gear_view_escapes_item_names_and_lists_empty_slots(self):
        text = format_gear_view([
            {"item_name": "Шлем из фольги"},
            {"item_name": "<script>"},
        ])

        self.assertIn("🧥 <b>Экипировка</b>", text)
        self.assertIn("шлем: <b>Шлем из фольги</b>", text)
        self.assertIn("нагрудник: пусто", text)
        self.assertNotIn("<script>", text)


class CraftingHandlerHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_equip_item_for_user_equips_known_class_item(self):
        user = {"cat_class": "thief"}

        with patch("handlers.crafting.db.equip_item", new=AsyncMock(return_value=True)) as equip_item:
            text, ok, alert = await equip_item_for_user(user_id=7, user=user, item_name="Отмычка рыбного налога")

        self.assertTrue(ok)
        self.assertEqual(alert, "Надето")
        self.assertIn("Надето: <b>Отмычка рыбного налога</b>", text)
        self.assertIn("Слот: <b>оружие</b>", text)
        equip_item.assert_awaited_once()

    async def test_use_consumable_for_user_adds_buff_and_includes_description_when_requested(self):
        with (
            patch("handlers.crafting.db.consume_inventory_item", new=AsyncMock(return_value=2)) as consume_item,
            patch("handlers.crafting.db.add_buff", new=AsyncMock()) as add_buff,
        ):
            text, ok, alert = await use_consumable_for_user(
                user_id=7,
                item_name="Валерьянка",
                include_description=True,
            )

        self.assertTrue(ok)
        self.assertEqual(alert, "Использовано")
        self.assertIn("Использовано: <b>Валерьянка</b>", text)
        self.assertIn("Осталось расходников: <b>2</b>", text)
        self.assertIn("рост", text.lower())
        consume_item.assert_awaited_once_with(7, "Валерьянка", "consumable")
        add_buff.assert_awaited_once_with(7, "grow_focus", uses=1)

    async def test_craft_recipe_for_user_reports_equipment_repair_for_same_recipe(self):
        db_result = {
            "ok": True,
            "repaired": True,
            "item_name": "Шлем из фольги",
            "durability_current": 30,
            "durability_max": 30,
        }

        with (
            patch("handlers.crafting.roll_forging_outcome", return_value="success"),
            patch("handlers.crafting.db.craft_inventory_item", new=AsyncMock(return_value=db_result)) as craft_item,
            patch("handlers.crafting.record_daily_action", new=AsyncMock()),
        ):
            text, ok = await craft_recipe_for_user(user_id=7, recipe_id="poor_helmet")

        self.assertTrue(ok)
        self.assertIn("Починено", text)
        self.assertIn("Шлем из фольги", text)
        self.assertIn("[30/30]", text)
        self.assertIn("Шлем из фольги", craft_item.await_args.kwargs["equipment_family_names"])
        self.assertEqual(craft_item.await_args.kwargs["target_item_name"], "Шлем из фольги")
        self.assertEqual(craft_item.await_args.kwargs["target_durability_max"], 30)

    async def test_craft_recipe_for_user_reports_explicit_next_tier_upgrade(self):
        db_result = {
            "ok": True,
            "upgraded": True,
            "item_name": "Картонный шлем бригадира",
            "durability_current": 40,
            "durability_max": 40,
        }

        with (
            patch("handlers.crafting.roll_forging_outcome", return_value="success"),
            patch("handlers.crafting.db.craft_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.crafting.record_daily_action", new=AsyncMock()),
        ):
            text, ok = await craft_recipe_for_user(user_id=7, recipe_id="common_helmet")

        self.assertTrue(ok)
        self.assertIn("Улучшено", text)
        self.assertIn("Картонный шлем бригадира", text)
        self.assertIn("[40/40]", text)

    async def test_craft_weapon_requires_matching_user_class_before_spending(self):
        with (
            patch("handlers.crafting.roll_forging_outcome", return_value="success") as roll_outcome,
            patch("handlers.crafting.db.craft_inventory_item", new=AsyncMock()) as craft_item,
        ):
            text, ok = await craft_recipe_for_user(
                user_id=7,
                recipe_id="poor_weapon_warrior",
                user={"cat_class": "support"},
            )

        self.assertFalse(ok)
        self.assertIn("оружие другого класса", text)
        roll_outcome.assert_not_called()
        craft_item.assert_not_awaited()

    async def test_craft_weapon_requires_selected_class_before_spending(self):
        with (
            patch("handlers.crafting.roll_forging_outcome", return_value="success") as roll_outcome,
            patch("handlers.crafting.db.craft_inventory_item", new=AsyncMock()) as craft_item,
        ):
            text, ok = await craft_recipe_for_user(
                user_id=7,
                recipe_id="poor_weapon_support",
                user={"cat_class": None},
            )

        self.assertFalse(ok)
        self.assertIn("сначала выбери класс", text.lower())
        roll_outcome.assert_not_called()
        craft_item.assert_not_awaited()

    async def test_craft_recipe_for_user_blocks_already_better_equipment_without_spending(self):
        db_result = {
            "ok": False,
            "already_owned": True,
            "item_name": "Шлем тихого авторитета",
        }

        with (
            patch("handlers.crafting.roll_forging_outcome", return_value="success"),
            patch("handlers.crafting.db.craft_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.crafting.record_daily_action", new=AsyncMock()) as record_daily,
        ):
            text, ok = await craft_recipe_for_user(user_id=7, recipe_id="rare_helmet")

        self.assertFalse(ok)
        self.assertIn("уже есть", text)
        record_daily.assert_not_awaited()

    async def test_buy_shop_item_for_user_reports_full_consumable_stack_without_daily(self):
        db_result = {
            "ok": False,
            "stack_full": True,
            "amount": 9999,
            "max_amount": 9999,
        }

        with (
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.buy_limited_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.shop.record_daily_action", new=AsyncMock()) as record_daily,
        ):
            text, ok = await buy_shop_item_for_user(user_id=7, recipe_id="valerian")

        self.assertFalse(ok)
        self.assertIn("Стек полон", text)
        self.assertIn("9999/9999", text)
        record_daily.assert_not_awaited()

    def test_parse_shop_amount_accepts_number_and_max(self):
        self.assertEqual(parse_shop_amount(["Валерьянка", "10"]), ("Валерьянка", 10))
        self.assertEqual(parse_shop_amount(["Кошачья", "мята", "max"]), ("Кошачья мята", "max"))
        self.assertEqual(parse_shop_amount(["Валерьянка"]), ("Валерьянка", 1))

    def test_calculate_shop_amount_limits_by_balance_stack_and_daily_stock(self):
        recipe = get_recipe("valerian")

        self.assertEqual(calculate_shop_amount(recipe, amount=100, balance=1000, current_amount=9990), 9)
        self.assertEqual(calculate_shop_amount(recipe, amount="max", balance=200, current_amount=9990), 4)
        self.assertEqual(calculate_shop_amount(
            recipe,
            amount="max",
            balance=200,
            current_amount=9990,
            three_for_two_active=True,
        ), 6)
        self.assertEqual(calculate_shop_amount(recipe, amount="max", balance=10, current_amount=0), 0)
        self.assertEqual(calculate_shop_amount(recipe, amount="max", balance=1000, current_amount=9999), 0)
        self.assertEqual(calculate_shop_amount(recipe, amount="max", balance=1000, current_amount=0, daily_remaining=3), 3)

    async def test_daily_limited_stock_reads_persisted_usage(self):
        with patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT - 5)) as get_remaining:
            remaining = await get_daily_limited_remaining(7, "valerian", today="2026-04-30")

        self.assertEqual(remaining, SHOP_DAILY_LIMIT - 5)
        get_remaining.assert_awaited_once()

    def test_cart_calculates_discounted_total_from_persisted_items(self):
        cart = calculate_shop_cart({"valerian": 3, "catnip": 3}, today="2026-04-30")

        self.assertEqual(cart["items"]["valerian"], 3)
        self.assertEqual(cart["items"]["catnip"], 3)
        self.assertEqual(cart["total"], calculate_shop_total(
            get_shop_unit_price("valerian", today="2026-04-30"),
            3,
            promo_active=get_three_for_two_recipe_id(today="2026-04-30") == "valerian",
        ) + calculate_shop_total(
            get_shop_unit_price("catnip", today="2026-04-30"),
            3,
            promo_active=get_three_for_two_recipe_id(today="2026-04-30") == "catnip",
        ))
        self.assertIn("Валерьянка", cart["text"])
        self.assertIn("Кошачья мята", cart["text"])
        promo_item = get_recipe(get_three_for_two_recipe_id(today="2026-04-30"))["name"]
        self.assertIn(promo_item, cart["text"])

    async def test_build_shop_cart_view_shows_balance_after_purchase_and_problems(self):
        with (
            patch("handlers.shop.db.get_user", new=AsyncMock(return_value={"balance": 100})),
            patch("handlers.shop.db.get_inventory_items", new=AsyncMock(return_value=[])),
            patch("handlers.shop.db.get_shop_cart", new=AsyncMock(return_value={"valerian": 3, "catnip": 3})),
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
        ):
            text, can_buy = await build_shop_cart_view(user_id=7)

        self.assertFalse(can_buy)
        self.assertIn("Баланс: <b>100</b> 🐟", text)
        self.assertIn("После покупки", text)
        self.assertIn("не хватает", text.lower())

    def test_shop_cart_keyboard_can_adjust_and_remove_items(self):
        keyboard = shop_cart_keyboard({"valerian": 3})
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("shop_cart_adjust:valerian:-1", callback_data)
        self.assertIn("shop_cart_adjust:valerian:1", callback_data)
        self.assertIn("shop_cart_remove:valerian", callback_data)

    def test_calculate_sell_amount_caps_by_inventory_and_refunds_sixty_percent(self):
        recipe = get_recipe("valerian")
        amount, refund = calculate_sell_amount(recipe, requested_amount=10, current_amount=4)

        self.assertEqual(amount, 4)
        self.assertEqual(refund, max(1, recipe["fish_cost"] * 60 // 100) * 4)

    def test_large_shop_amounts_need_confirmation(self):
        self.assertFalse(needs_shop_confirmation(10))
        self.assertTrue(needs_shop_confirmation(25))
        self.assertTrue(needs_shop_confirmation("max"))

    def test_shop_keyboard_has_large_and_preview_buttons(self):
        keyboard = shop_item_keyboard("valerian")
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("shop_buy:valerian:1", callback_data)
        self.assertIn("shop_buy:valerian:10", callback_data)
        self.assertIn("shop_preview:valerian:25", callback_data)
        self.assertIn("shop_preview:valerian:100", callback_data)
        self.assertIn("shop_preview:valerian:max", callback_data)

    def test_shop_catalog_keyboard_opens_item_cards_without_action_wall(self):
        keyboard = shop_keyboard(["valerian", "catnip"])
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("shop_item:valerian", callback_data)
        self.assertIn("shop_item:catnip", callback_data)
        self.assertNotIn("shop_buy:valerian:1", callback_data)
        self.assertNotIn("shop_cart_add:valerian:1", callback_data)
        self.assertLessEqual(len(keyboard.inline_keyboard), 5)

    def test_shop_item_keyboard_contains_purchase_cart_and_sell_actions(self):
        keyboard = shop_item_keyboard("valerian")
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("shop_buy:valerian:1", callback_data)
        self.assertIn("shop_buy:valerian:10", callback_data)
        self.assertIn("shop_preview:valerian:max", callback_data)
        self.assertIn("shop_cart_add:valerian:5", callback_data)
        self.assertIn("shop_sell:valerian:max", callback_data)

    def test_recipe_catalog_opens_recipe_cards_before_crafting(self):
        keyboard = recipe_keyboard(["poor_helmet", "common_helmet"])
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("craft_recipe:poor_helmet", callback_data)
        self.assertIn("craft_recipe:common_helmet", callback_data)
        self.assertNotIn("craft_make:poor_helmet", callback_data)

    def test_weapon_category_keyboard_opens_class_filters(self):
        keyboard = recipe_keyboard(get_category_recipe_ids("weapon"), category="weapon")
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("craft_weapon_class:warrior", callback_data)
        self.assertIn("craft_weapon_class:thief", callback_data)
        self.assertIn("craft_weapon_class:support", callback_data)
        self.assertIn("craft_weapon_class:assassin", callback_data)
        self.assertNotIn("craft_recipe:poor_weapon_warrior", callback_data)

    def test_recipe_detail_keyboard_contains_single_craft_action(self):
        keyboard = recipe_detail_keyboard("poor_helmet")
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("craft_make:poor_helmet", callback_data)
        self.assertIn("craft_home", callback_data)

    def test_shop_repeat_keyboard_repeats_same_purchase(self):
        keyboard = shop_repeat_keyboard("valerian", 10)
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertIn("shop_buy:valerian:10", callback_data)

    async def test_format_shop_home_shows_balance_stock_and_available_max(self):
        with (
            patch("handlers.shop.db.get_user", new=AsyncMock(return_value={"balance": 200})),
            patch(
                "handlers.shop.db.get_inventory_items",
                new=AsyncMock(return_value=[{"item_name": "Валерьянка", "amount": 9997}]),
            ),
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.get_shop_cart", new=AsyncMock(return_value={"valerian": 2})),
        ):
            text = await format_shop_home(user_id=7)

        self.assertIn("Баланс: <b>200</b> 🐟", text)
        self.assertIn("Валерьянка", text)
        self.assertIn("есть: <b>9997/9999</b>", text)
        self.assertIn("можно: <b>2</b> шт.", text)

    async def test_build_shop_preview_reports_total_and_confirm_payload(self):
        with (
            patch("handlers.shop.db.get_user", new=AsyncMock(return_value={"balance": 2000})),
            patch("handlers.shop.db.get_inventory_items", new=AsyncMock(return_value=[])),
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
        ):
            recipe_id = get_three_for_two_recipe_id()
            text, amount = await build_shop_preview(user_id=7, recipe_id=recipe_id, amount=25)

        self.assertEqual(amount, 25)
        self.assertIn("Подтвердить покупку", text)
        self.assertIn("Количество: <b>25</b> шт.", text)
        self.assertIn("Акция: <b>3 по цене 2</b>", text)

    async def test_buy_shop_item_for_user_buys_batch_and_reports_balance_totals(self):
        db_result = {
            "ok": True,
            "amount": 12,
            "balance": 550,
            "spent": 450,
            "balance_before": 1000,
        }

        with (
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.buy_limited_inventory_item", new=AsyncMock(return_value=db_result)) as buy_item,
            patch("handlers.shop.record_daily_action", new=AsyncMock()),
        ):
            text, ok = await buy_shop_item_for_user(user_id=7, recipe_id="valerian", amount=10)

        self.assertTrue(ok)
        self.assertIn("Количество: <b>10</b> шт.", text)
        self.assertIn("Итого: <b>450</b> 🐟", text)
        self.assertIn("Баланс до покупки: <b>1000</b> 🐟", text)
        self.assertIn("Баланс: <b>550</b> 🐟", text)
        self.assertEqual(buy_item.await_args.kwargs["amount"], 10)

    async def test_buy_shop_item_for_user_max_uses_balance_and_free_stack_space(self):
        db_result = {
            "ok": True,
            "amount": 9999,
            "balance": 775,
            "spent": 225,
            "balance_before": 1000,
        }

        with (
            patch("handlers.shop.db.get_user", new=AsyncMock(return_value={"balance": 1000})),
            patch(
                "handlers.shop.db.get_inventory_items",
                new=AsyncMock(return_value=[{"item_name": "Валерьянка", "amount": 9994}]),
            ),
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.buy_limited_inventory_item", new=AsyncMock(return_value=db_result)) as buy_item,
            patch("handlers.shop.record_daily_action", new=AsyncMock()),
        ):
            text, ok = await buy_shop_item_for_user(user_id=7, recipe_id="valerian", amount="max")

        self.assertTrue(ok)
        self.assertIn("Количество: <b>5</b> шт.", text)
        self.assertEqual(buy_item.await_args.kwargs["amount"], 5)

    async def test_buy_shop_item_for_user_rejects_not_enough_fish_with_comic_text(self):
        db_result = {
            "ok": False,
            "needed": 450,
            "available": 100,
            "amount": 10,
        }

        with (
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.buy_limited_inventory_item", new=AsyncMock(return_value=db_result)),
        ):
            text, ok = await buy_shop_item_for_user(
                user_id=7,
                recipe_id="valerian",
                amount=10,
                not_enough_fish_text="Губу раскотал! Рыбов вперёд!",
            )

        self.assertFalse(ok)
        self.assertIn("Губу раскотал! Рыбов вперёд!", text)
        self.assertIn("Нужно: <b>450</b> 🐟", text)
        self.assertIn("есть: <b>100</b> 🐟", text)

    async def test_buy_shop_item_for_user_reports_persisted_daily_limit_race(self):
        db_result = {
            "ok": False,
            "daily_limit": True,
            "remaining": 2,
            "amount": 10,
        }

        with (
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.buy_limited_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.shop.record_daily_action", new=AsyncMock()) as record_daily,
        ):
            text, ok = await buy_shop_item_for_user(user_id=7, recipe_id="valerian", amount=10)

        self.assertFalse(ok)
        self.assertIn("Партия дня", text)
        self.assertIn("<b>2</b>", text)
        record_daily.assert_not_awaited()

    def test_shop_stack_full_has_15_comic_replies(self):
        self.assertEqual(len(SHOP_STACK_FULL_TEXTS), 15)
        self.assertEqual(len(set(SHOP_STACK_FULL_TEXTS)), 15)

    def test_shop_not_enough_fish_has_15_comic_replies(self):
        self.assertEqual(len(SHOP_NOT_ENOUGH_FISH_TEXTS), 15)
        self.assertEqual(len(set(SHOP_NOT_ENOUGH_FISH_TEXTS)), 15)

    async def test_buy_shop_item_for_user_can_use_selected_stack_full_reply(self):
        db_result = {
            "ok": False,
            "stack_full": True,
            "amount": 9999,
            "max_amount": 9999,
        }

        with (
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.buy_limited_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.shop.record_daily_action", new=AsyncMock()),
        ):
            text, ok = await buy_shop_item_for_user(
                user_id=7,
                recipe_id="valerian",
                stack_full_text=SHOP_STACK_FULL_TEXTS[3],
            )

        self.assertFalse(ok)
        self.assertIn(SHOP_STACK_FULL_TEXTS[3], text)

    async def test_format_shop_history_uses_transaction_summary(self):
        summary = {
            "spent": 450,
            "refunded": 60,
            "favorite_recipe_id": "valerian",
            "favorite_amount": 10,
            "latest": [
                {"action": "buy", "recipe_id": "valerian", "amount": 10, "total_cost": 450},
                {"action": "sell", "recipe_id": "catnip", "amount": 1, "total_cost": -60},
            ],
        }

        with patch("handlers.shop.db.get_shop_transaction_summary", new=AsyncMock(return_value=summary)):
            text = await format_shop_history(user_id=7)

        self.assertIn("История магазина", text)
        self.assertIn("Потрачено: <b>450</b> 🐟", text)
        self.assertIn("Вернулось: <b>60</b> 🐟", text)
        self.assertIn("Любимый товар", text)

    async def test_failed_shop_buy_records_suspicious_attempt_and_wishlist_hint(self):
        db_result = {
            "ok": False,
            "needed": 450,
            "available": 100,
            "amount": 10,
        }

        with (
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.buy_limited_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.shop.db.record_shop_suspicious_attempt", new=AsyncMock(return_value=3)) as suspicious,
            patch("handlers.shop.db.add_shop_wishlist_item", new=AsyncMock()) as wishlist,
        ):
            text, ok = await buy_shop_item_for_user(user_id=7, recipe_id="valerian", amount=10)

        self.assertFalse(ok)
        suspicious.assert_awaited_once()
        wishlist.assert_awaited_once_with(7, "valerian", 10, "not_enough_fish")
        self.assertIn("подозр", text.lower())
        self.assertIn("хотел", text.lower())

    async def test_buy_shop_wishlist_item_removes_item_after_success(self):
        db_result = {
            "ok": True,
            "amount": 5,
            "balance": 865,
            "spent": 135,
            "balance_before": 1000,
        }

        with (
            patch("handlers.shop.db.get_shop_daily_limited_remaining", new=AsyncMock(return_value=SHOP_DAILY_LIMIT)),
            patch("handlers.shop.db.buy_limited_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.shop.db.remove_shop_wishlist_item", new=AsyncMock()) as remove_item,
            patch("handlers.shop.record_daily_action", new=AsyncMock()),
        ):
            text, ok = await buy_shop_wishlist_item_for_user(7, "valerian", 3)

        self.assertTrue(ok)
        self.assertIn("Куплено", text)
        remove_item.assert_awaited_once_with(7, "valerian")


if __name__ == "__main__":
    unittest.main()
