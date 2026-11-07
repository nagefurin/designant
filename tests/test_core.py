import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import (
    build_order,
    is_active_normal_new_card,
    parse_frequency,
    reposition_preserving_user_defaults,
)


class FrequencyParsingTests(unittest.TestCase):
    def test_parses_numbers_and_commas(self):
        self.assertEqual(parse_frequency(" 1,234 "), 1234.0)
        self.assertEqual(parse_frequency("2.5"), 2.5)

    def test_missing_or_invalid_values(self):
        self.assertIsNone(parse_frequency(""))
        self.assertIsNone(parse_frequency("not a number"))
        self.assertIsNone(parse_frequency("inf"))


class BuildOrderTests(unittest.TestCase):
    def test_three_part_order_frequency_then_date_then_frequency(self):
        # Creation IDs increase from 1000 (oldest) to 1029 (newest).
        # Frequency values are arranged in the opposite direction.
        rows = [(card_id, str(1030 - card_id)) for card_id in range(1000, 1030)]
        expected = (
            list(range(1029, 1009, -1))
            + list(range(1000, 1005))
            + list(range(1009, 1004, -1))
        )
        self.assertEqual(build_order(rows, frequency_count=20, date_count=5), expected)

    def test_date_group_is_selected_from_after_frequency_prefix(self):
        rows = [
            (10, "1"),
            (90, "2"),
            (30, "3"),
            (20, "4"),
            (40, "5"),
            (50, "6"),
            (60, "7"),
        ]
        self.assertEqual(
            build_order(rows, frequency_count=2, date_count=3),
            [10, 90, 20, 30, 40, 50, 60],
        )

    def test_missing_frequency_can_enter_date_group_but_trails_final_frequency_group(self):
        rows = [(101, "1"), (102, "2"), (103, ""), (104, "3"), (105, "")]
        self.assertEqual(
            build_order(rows, frequency_count=1, date_count=2),
            [101, 102, 103, 104, 105],
        )

    def test_frequency_ties_use_older_card_id(self):
        rows = [(300, "5"), (100, "5"), (200, "5"), (400, "6")]
        self.assertEqual(build_order(rows, frequency_count=2, date_count=1), [100, 200, 300, 400])

    def test_reverse_frequency_does_not_reverse_ties(self):
        rows = [(300, "5"), (100, "5"), (200, "8"), (400, "1")]
        self.assertEqual(
            build_order(rows, frequency_count=2, date_count=1, frequency_reverse=True),
            [200, 100, 300, 400],
        )

    def test_created_reverse_changes_middle_group_order(self):
        rows = [(100, "1"), (200, "2"), (300, "3"), (400, "4"), (500, "5")]
        self.assertEqual(
            build_order(rows, frequency_count=1, date_count=2, created_reverse=True),
            [100, 500, 400, 200, 300],
        )

    def test_zero_frequency_count_starts_with_date_group(self):
        rows = [(300, "3"), (100, "1"), (200, "2"), (400, "4")]
        self.assertEqual(build_order(rows, frequency_count=0, date_count=2), [100, 200, 300, 400])


class CardEligibilityTests(unittest.TestCase):
    class FakeCard:
        def __init__(self, card_type, queue, odid=0):
            self.type = card_type
            self.queue = queue
            self.odid = odid

    def test_only_active_normal_new_cards_are_eligible(self):
        self.assertTrue(is_active_normal_new_card(self.FakeCard(0, 0)))
        self.assertFalse(is_active_normal_new_card(self.FakeCard(1, 1)))  # learning
        self.assertFalse(is_active_normal_new_card(self.FakeCard(2, 2)))  # review
        self.assertFalse(is_active_normal_new_card(self.FakeCard(0, -1)))  # suspended
        self.assertFalse(is_active_normal_new_card(self.FakeCard(0, -2)))  # buried
        self.assertFalse(is_active_normal_new_card(self.FakeCard(0, 0, odid=123)))  # filtered

    def test_missing_scheduler_state_is_not_eligible(self):
        self.assertFalse(is_active_normal_new_card(object()))



class RepositionSafetyTests(unittest.TestCase):
    class FakeScheduler:
        def __init__(self, config):
            self.config = config
            self.received = None

        def reposition_defaults(self):
            return type("Defaults", (), {"random": self.config[23], "shift": self.config[24]})()

        def reposition_new_cards(self, **kwargs):
            self.received = kwargs
            # Simulate Anki persisting the API arguments as user preferences.
            self.config[23] = kwargs["randomize"]
            self.config[24] = kwargs["shift_existing"]
            return type("Changes", (), {"count": len(kwargs["card_ids"])})()

    class FakeCollection:
        def __init__(self):
            self.config = {23: True, 24: True}
            self.sched = RepositionSafetyTests.FakeScheduler(self.config)

        def set_config_bool(self, key, value):
            self.config[key] = value

    def test_reposition_does_not_shift_other_cards_or_change_user_defaults(self):
        col = self.FakeCollection()
        result = reposition_preserving_user_defaults(col, [11, 22, 33], 23, 24)

        self.assertEqual(result.count, 3)
        self.assertEqual(col.sched.received["card_ids"], [11, 22, 33])
        self.assertFalse(col.sched.received["shift_existing"])
        self.assertFalse(col.sched.received["randomize"])
        self.assertEqual(col.sched.received["starting_from"], 0)
        self.assertEqual(col.sched.received["step_size"], 1)
        self.assertEqual(col.config, {23: True, 24: True})


if __name__ == "__main__":
    unittest.main()
