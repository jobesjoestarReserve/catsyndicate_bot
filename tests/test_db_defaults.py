import unittest

from tests.support import install_dependency_stubs

install_dependency_stubs()

from database.db_manager import STARTING_MICE_COUNT  # noqa: E402


class DBDefaultTests(unittest.TestCase):
    def test_new_players_start_with_a_small_mouse_team(self):
        self.assertEqual(STARTING_MICE_COUNT, 3)


if __name__ == "__main__":
    unittest.main()
