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
from handlers.shop import SHOP_STACK_FULL_TEXTS, buy_shop_item_for_user


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
            patch("handlers.shop.db.buy_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.shop.record_daily_action", new=AsyncMock()) as record_daily,
        ):
            text, ok = await buy_shop_item_for_user(user_id=7, recipe_id="valerian")

        self.assertFalse(ok)
        self.assertIn("Стек полон", text)
        self.assertIn("9999/9999", text)
        record_daily.assert_not_awaited()

    def test_shop_stack_full_has_15_comic_replies(self):
        self.assertEqual(len(SHOP_STACK_FULL_TEXTS), 15)
        self.assertEqual(len(set(SHOP_STACK_FULL_TEXTS)), 15)

    async def test_buy_shop_item_for_user_can_use_selected_stack_full_reply(self):
        db_result = {
            "ok": False,
            "stack_full": True,
            "amount": 9999,
            "max_amount": 9999,
        }

        with (
            patch("handlers.shop.db.buy_inventory_item", new=AsyncMock(return_value=db_result)),
            patch("handlers.shop.record_daily_action", new=AsyncMock()),
        ):
            text, ok = await buy_shop_item_for_user(
                user_id=7,
                recipe_id="valerian",
                stack_full_text=SHOP_STACK_FULL_TEXTS[3],
            )

        self.assertFalse(ok)
        self.assertIn(SHOP_STACK_FULL_TEXTS[3], text)


if __name__ == "__main__":
    unittest.main()
