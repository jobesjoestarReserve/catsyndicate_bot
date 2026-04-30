import unittest

from handlers.inventory import format_inventory_text
from services.ui import inventory_keyboard


class InventoryViewTests(unittest.TestCase):
    def test_inventory_text_escapes_item_names(self):
        text = format_inventory_text(
            user={"balance": 10, "mice_count": 2},
            resources=[{"item_name": "<wool>", "amount": 3}],
            consumables=[{"item_name": "<script>", "amount": 1}],
            equipment=[{"item_name": "Шлем из фольги", "amount": 1, "durability_current": 18, "durability_max": 30}],
            equipped=[{"item_name": "<b>bad</b>", "durability_current": 1, "durability_max": 2}],
        )

        self.assertIn("&lt;wool&gt;", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("&lt;b&gt;bad&lt;/b&gt;", text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("<b>bad</b>", text)

    def test_inventory_text_omits_free_equipment_items(self):
        text = format_inventory_text(
            user={"balance": 10, "mice_count": 2},
            resources=[],
            consumables=[],
            equipment=[{"item_name": "Шлем из фольги", "amount": 1, "durability_current": 18, "durability_max": 30}],
            equipped=[],
        )

        self.assertNotIn("• Шлем из фольги [18/30]", text)
        self.assertNotIn("Шлем из фольги: <b>1</b>", text)
        self.assertNotIn("Свободная экипировка", text)

    def test_inventory_text_does_not_show_free_equipment_section(self):
        text = format_inventory_text(
            user={"balance": 10, "mice_count": 2},
            resources=[],
            consumables=[],
            equipment=[],
            equipped=[],
        )

        self.assertNotIn("Свободная экипировка", text)
        self.assertNotIn("Нажми кнопку предмета в инвентаре", text)
        self.assertIn("Открой <code>экипировка</code>", text)

    def test_inventory_keyboard_omits_equip_buttons(self):
        keyboard = inventory_keyboard([
            {"item_name": "Мышиный энергетик", "amount": 1},
        ])
        callbacks = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        ]

        self.assertIn("use_item:mouse_energy", callbacks)
        self.assertNotIn("equip_item:foil_helmet", callbacks)


if __name__ == "__main__":
    unittest.main()
