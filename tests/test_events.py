import unittest

from tests.support import install_dependency_stubs

install_dependency_stubs()

from services.events import (  # noqa: E402
    BOSS_EVENT_TYPES,
    EVENT_CONFIGS,
    format_event_status,
    get_event_action,
    get_event_title,
    normalize_event_type,
)
from data.texts import (  # noqa: E402
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
            ("grab", EVENT_GRAB_TEXTS),
            ("empty", EVENT_EMPTY_TEXTS),
            ("busy", EVENT_BUSY_TEXTS),
            ("mine_critical_success", MINE_CRITICAL_SUCCESS_TEXTS),
        ):
            with self.subTest(pool=pool_name):
                self.assertGreaterEqual(len(texts), 15)

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


if __name__ == "__main__":
    unittest.main()
