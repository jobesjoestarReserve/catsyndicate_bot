import unittest

from handlers.inventory import format_inventory_text


class InventoryViewTests(unittest.TestCase):
    def test_inventory_text_escapes_item_names(self):
        text = format_inventory_text(
            user={"balance": 10, "mice_count": 2},
            resources=[{"item_name": "<wool>", "amount": 3}],
            consumables=[{"item_name": "<script>", "amount": 1}],
            equipment=[{"item_name": "Шлем из фольги", "amount": 1}],
            equipped=[{"item_name": "<b>bad</b>"}],
        )

        self.assertIn("&lt;wool&gt;", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("&lt;b&gt;bad&lt;/b&gt;", text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("<b>bad</b>", text)


if __name__ == "__main__":
    unittest.main()
