import unittest

from tests.support import install_dependency_stubs

install_dependency_stubs()

from database.db_manager import DBManager  # noqa: E402
from handlers.combat import should_route_bite_to_boss  # noqa: E402
from services.events import (  # noqa: E402
    BOSS_EVENT_TYPES,
    EVENT_CONFIGS,
    format_boss_cooldown,
    format_event_status,
    get_event_action,
    get_event_title,
    normalize_event_type,
)
from data.texts import (  # noqa: E402
    EVENT_BOSS_COOLDOWN_TEXTS,
    EVENT_BOSS_DEFEATED_TEXTS,
    EVENT_BOSS_EXPIRED_TEXTS,
    EVENT_BOSS_HIT_TEXTS,
    EVENT_BUSY_TEXTS,
    EVENT_EMPTY_TEXTS,
    EVENT_GRAB_TEXTS,
    EVENT_SPAWN_TEXTS,
    MINE_CRITICAL_SUCCESS_TEXTS,
)


class EventTests(unittest.TestCase):
    def test_event_type_aliases(self):
        self.assertEqual(normalize_event_type("boss"), "boss")
        self.assertEqual(normalize_event_type("dog"), "boss_dog")
        self.assertEqual(normalize_event_type("vacuum"), "boss_vacuum")
        self.assertEqual(normalize_event_type("slipper"), "boss_slipper")
        self.assertEqual(normalize_event_type("fish"), "fish_drop")
        self.assertEqual(normalize_event_type("resources"), "resource_drop")
        self.assertIsNone(normalize_event_type("unknown"))

    def test_event_actions_match_event_kind(self):
        self.assertEqual(get_event_action("boss"), "босс")
        for event_type in BOSS_EVENT_TYPES:
            with self.subTest(event_type=event_type):
                self.assertEqual(get_event_action(event_type), "босс")
        self.assertEqual(get_event_action("fish_drop"), "контейнер")
        self.assertEqual(get_event_action("resource_drop"), "контейнер")

    def test_event_text_pools_have_fifteen_variants(self):
        for event_type, texts in EVENT_SPAWN_TEXTS.items():
            with self.subTest(pool="spawn", event_type=event_type):
                self.assertGreaterEqual(len(texts), 15)

        for pool_name, pool in (
            ("hit", EVENT_BOSS_HIT_TEXTS),
            ("defeated", EVENT_BOSS_DEFEATED_TEXTS),
            ("expired", EVENT_BOSS_EXPIRED_TEXTS),
        ):
            for event_type in ("boss", *BOSS_EVENT_TYPES):
                with self.subTest(pool=pool_name, event_type=event_type):
                    self.assertGreaterEqual(len(pool[event_type]), 15)

        for pool_name, texts in (
            ("boss_cooldown", EVENT_BOSS_COOLDOWN_TEXTS),
            ("grab", EVENT_GRAB_TEXTS),
            ("empty", EVENT_EMPTY_TEXTS),
            ("busy", EVENT_BUSY_TEXTS),
            ("mine_critical_success", MINE_CRITICAL_SUCCESS_TEXTS),
        ):
            with self.subTest(pool=pool_name):
                self.assertGreaterEqual(len(texts), 15)

    def test_format_boss_cooldown_uses_comic_pool_and_time(self):
        text = format_boss_cooldown("23 сек.", choice=lambda variants: variants[0])

        self.assertIn("23 сек.", text)
        self.assertIn("Зубы", text)

    def test_event_configs_are_spawnable(self):
        for event_type, config in EVENT_CONFIGS.items():
            with self.subTest(event_type=event_type):
                self.assertGreater(config["duration_seconds"], 0)
                self.assertGreater(config["weight"], 0)
                self.assertGreaterEqual(config["hp_max"], config["hp_min"])

    def test_format_event_status_mentions_relevant_pool(self):
        boss = {
            "event_type": "boss",
            "hp_current": 10,
            "hp_max": 20,
        }
        fish_drop = {
            "event_type": "fish_drop",
            "reward_pool": 42,
        }
        resource_drop = {
            "event_type": "resource_drop",
            "wool_pool": 3,
            "metal_pool": 0,
            "trash_pool": 7,
        }

        self.assertIn("10/20", format_event_status(boss))
        self.assertIn("42", format_event_status(fish_drop))
        self.assertIn("шерсть", format_event_status(resource_drop))
        self.assertIn("мусор", format_event_status(resource_drop))
        self.assertEqual(get_event_title("unknown"), "unknown")

    def test_plain_bite_routes_to_active_boss_when_it_has_no_pvp_target(self):
        self.assertTrue(should_route_bite_to_boss("кусь", has_reply=False, reply_from_bot=False, active_event_type="boss_vacuum"))
        self.assertTrue(should_route_bite_to_boss("кус", has_reply=True, reply_from_bot=True, active_event_type="boss_dog"))
        self.assertFalse(should_route_bite_to_boss("кус", has_reply=True, reply_from_bot=False, active_event_type="boss_dog"))
        self.assertFalse(should_route_bite_to_boss("кус", has_reply=False, reply_from_bot=False, active_event_type=None))


class _FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return _FakeAcquire(self.conn)


class _BossDamageConn:
    def __init__(self):
        self.update_query = None

    def transaction(self):
        return _FakeTransaction()

    async def fetchrow(self, query, *args):
        if "UPDATE chat_events" in query:
            self.update_query = query
            if "event_type = 'boss'" in query:
                return None
            return {"id": args[1], "event_type": "boss_vacuum", "hp_current": 70, "hp_max": 77}
        return {"event_id": args[0], "user_id": args[1], "damage": args[2]}


class EventDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_boss_damage_accepts_typed_boss_events(self):
        conn = _BossDamageConn()
        manager = DBManager()
        manager.pool = _FakePool(conn)

        result = await manager.add_boss_damage(event_id=11, user_id=7, damage=5)

        self.assertIsNotNone(result)
        self.assertIn("boss_vacuum", conn.update_query)


if __name__ == "__main__":
    unittest.main()
