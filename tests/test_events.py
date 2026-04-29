import unittest

from tests.support import install_dependency_stubs

install_dependency_stubs()

from services.events import (  # noqa: E402
    EVENT_CONFIGS,
    format_event_status,
    get_event_action,
    get_event_title,
    normalize_event_type,
)


class EventTests(unittest.TestCase):
    def test_event_type_aliases(self):
        self.assertEqual(normalize_event_type("dog"), "boss")
        self.assertEqual(normalize_event_type("fish"), "fish_drop")
        self.assertEqual(normalize_event_type("resources"), "resource_drop")
        self.assertIsNone(normalize_event_type("unknown"))

    def test_event_actions_match_event_kind(self):
        self.assertEqual(get_event_action("boss"), "/bite_boss")
        self.assertEqual(get_event_action("fish_drop"), "/grab")
        self.assertEqual(get_event_action("resource_drop"), "/grab")

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
