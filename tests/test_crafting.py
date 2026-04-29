import unittest

from services.crafting import (
    RECIPES,
    format_cost,
    get_consumable_effect,
    get_equipment_bonus,
    get_equipment_slot,
    get_item_recipe_id,
    get_recipe,
    get_slot_item_names,
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

    def test_item_names_map_back_to_recipe_ids(self):
        self.assertEqual(get_item_recipe_id("Валерьянка"), "valerian")
        self.assertEqual(get_item_recipe_id("Шлем из фольги"), "poor_helmet")

    def test_each_equipment_slot_has_three_tiers(self):
        for slot in ("helmet", "chest", "bracers", "boots"):
            with self.subTest(slot=slot):
                self.assertEqual(len(get_slot_item_names(slot)), 3)

    def test_equipment_bonus_sums_known_items(self):
        equipped = [
            {"item_name": "Металлические нарукавники"},
            {"item_name": "Сапоги бесшумного тыгыдыка"},
        ]

        self.assertEqual(get_equipment_bonus(equipped, "loot_bonus"), 2)
        self.assertEqual(get_equipment_bonus(equipped, "hunt_chance"), 3)

    def test_recipe_costs_are_non_empty(self):
        for recipe_id, recipe in RECIPES.items():
            with self.subTest(recipe_id=recipe_id):
                self.assertTrue(recipe["cost"])
                self.assertTrue(format_cost(recipe["cost"]))
                self.assertIs(get_recipe(recipe_id), recipe)


if __name__ == "__main__":
    unittest.main()
