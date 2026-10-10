import unittest

from throw_event_ledger import build_throw_event_ledger


def counter(identifier, colour):
    return {
        "id": identifier,
        "colour": colour,
        "crossing_time_s": 30,
        "evidence_interval_s": [28, 30],
        "remaining_before": [8, 8],
        "remaining_after": [8, 7],
    }


class ThrowEventLedgerTest(unittest.TestCase):
    def test_orders_origin_and_travel_without_inventing_board_state(self):
        origin = [
            {
                "shot_id": "S2",
                "delivery_window_s": [40, 50],
                "colour": None,
                "colour_status": "conflict",
                "evidence_sources": ["visual_origin_and_adjacent_motion"],
                "counter_id": None,
            }
        ]
        travel = [
            {
                "status": "unlocalized_travel_candidate",
                "travel_shot_id": "S1",
                "release_window_s": [0, 25],
                "observed_travel_window_s": [25, 35],
                "colour": "yellow",
                "counter_id": "B1",
            }
        ]
        result = build_throw_event_ledger(origin, travel, [counter("B1", "yellow")])
        self.assertEqual([row["shot_id"] for row in result["events"]], ["S1", "S2"])
        self.assertEqual(result["events"][0]["broadcast_counter"]["remaining_after"], [8, 7])
        self.assertEqual(result["events"][0]["counter_state_link"]["status"], "initial_observation")
        self.assertIsNone(result["events"][1]["broadcast_counter"])
        self.assertEqual(result["events"][1]["colour_status"], "conflict")

    def test_rejects_duplicate_counter_assignment(self):
        origin = [
            {
                "shot_id": shot,
                "delivery_window_s": [10, 20],
                "colour": "yellow",
                "colour_status": "resolved",
                "evidence_sources": [],
                "counter_id": "B1",
            }
            for shot in ("S1", "S2")
        ]
        with self.assertRaises(ValueError):
            build_throw_event_ledger(origin, [], [counter("B1", "yellow")])

    def test_rejects_counter_update_before_proposed_release(self):
        origin = [
            {
                "shot_id": "S1",
                "delivery_window_s": [40, 50],
                "colour": "yellow",
                "colour_status": "resolved",
                "evidence_sources": [],
                "counter_id": "B1",
            }
        ]
        with self.assertRaisesRegex(ValueError, "updates before candidate"):
            build_throw_event_ledger(origin, [], [counter("B1", "yellow")])

    def test_marks_counter_gap_without_interpolating_state(self):
        first = counter("B1", "yellow")
        second = counter("B2", "red")
        second["crossing_time_s"] = 70
        second["remaining_before"] = [7, 7]
        result = build_throw_event_ledger([], [], [first, second])
        self.assertEqual(result["counter_updates_without_candidate"], ["B1", "B2"])
        self.assertEqual(
            result["counter_state_discontinuities"],
            [
                {
                    "previous_counter_id": "B1",
                    "counter_id": "B2",
                    "previous_remaining_after": [8, 7],
                    "current_remaining_before": [7, 7],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
