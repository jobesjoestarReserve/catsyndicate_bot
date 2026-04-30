import unittest

from database.db_manager import DBManager


class FakeInventoryConn:
    def __init__(self):
        self.items = {}
        self.next_id = 1

    async def fetchrow(self, query, user_id, item_name, item_type):
        item = self.items.get((user_id, item_name, item_type))
        if not item:
            return None
        return {"id": item["id"], "bonus_value": item["bonus_value"]}

    async def fetchval(self, query, *args):
        if query.lstrip().startswith("UPDATE inventory"):
            amount, item_id = args
            for item in self.items.values():
                if item["id"] == item_id:
                    item["bonus_value"] += amount
                    return item["bonus_value"]
            return None

        user_id, item_name, item_type, amount = args
        self.items[(user_id, item_name, item_type)] = {
            "id": self.next_id,
            "bonus_value": amount,
        }
        self.next_id += 1
        return amount


class DBInventoryHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_inventory_amount_inserts_then_updates_stack(self):
        manager = DBManager()
        conn = FakeInventoryConn()

        first = await manager._add_inventory_amount(conn, 10, "wool", "resource", 3)
        second = await manager._add_inventory_amount(conn, 10, "wool", "resource", 2)

        self.assertEqual(first, 3)
        self.assertEqual(second, 5)
        self.assertEqual(conn.items[(10, "wool", "resource")]["bonus_value"], 5)

    async def test_add_resource_amounts_skips_zero_and_negative_values(self):
        manager = DBManager()
        conn = FakeInventoryConn()

        totals = await manager._add_resource_amounts(
            conn,
            10,
            {"wool": 3, "metal": 0, "trash": -1},
        )

        self.assertEqual(totals, {"wool": 3})
        self.assertEqual(list(conn.items), [(10, "wool", "resource")])

    async def test_add_inventory_amount_rejects_overfull_consumable_stack(self):
        manager = DBManager()
        conn = FakeInventoryConn()

        first = await manager._add_inventory_amount(conn, 10, "Валерьянка", "consumable", 9998, max_amount=9999)
        second = await manager._add_inventory_amount(conn, 10, "Валерьянка", "consumable", 5, max_amount=9999)
        third = await manager._add_inventory_amount(conn, 10, "Валерьянка", "consumable", 1, max_amount=9999)

        self.assertEqual(first, 9998)
        self.assertIsNone(second)
        self.assertEqual(third, 9999)
        self.assertEqual(conn.items[(10, "Валерьянка", "consumable")]["bonus_value"], 9999)

    async def test_add_inventory_amount_rejects_partial_consumable_update(self):
        manager = DBManager()
        conn = FakeInventoryConn()

        first = await manager._add_inventory_amount(conn, 10, "Валерьянка", "consumable", 9998, max_amount=9999)
        second = await manager._add_inventory_amount(conn, 10, "Валерьянка", "consumable", 5, max_amount=9999)

        self.assertEqual(first, 9998)
        self.assertIsNone(second)
        self.assertEqual(conn.items[(10, "Валерьянка", "consumable")]["bonus_value"], 9998)


if __name__ == "__main__":
    unittest.main()
