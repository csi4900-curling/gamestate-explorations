import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from event_review_windows import build_review_windows


class EventReviewWindowTests(unittest.TestCase):
    def test_counter_bracket_is_included_with_context_and_unknown_physical_bounds(self):
        events = [
            {
                "id": "B01",
                "colour": "red",
                "crossing_time_s": 103,
                "evidence_interval_s": [90, 103],
                "evidence_kind": "counter",
            }
        ]
        window = build_review_windows(events, [80, 200], before_s=20, after_s=45)["review_windows"][
            0
        ]
        self.assertEqual((window["review_start_s"], window["review_end_s"]), (80, 148))
        self.assertEqual(window["core_evidence_interval_s"], [90, 103])
        self.assertIsNone(window["physical_start_s"])
        self.assertIsNone(window["physical_end_s"])

    def test_overlapping_context_windows_do_not_merge_distinct_events(self):
        events = [
            {"id": "V02", "colour": "yellow", "evidence_interval_s": [110, 115]},
            {"id": "V01", "colour": "red", "evidence_interval_s": [100, 105]},
        ]
        windows = build_review_windows(events, [0, 200])["review_windows"]
        self.assertEqual([w["event_id"] for w in windows], ["V01", "V02"])
        self.assertGreater(windows[0]["review_end_s"], windows[1]["review_start_s"])

    def test_evidence_outside_source_is_rejected(self):
        with self.assertRaises(ValueError):
            build_review_windows(
                [{"id": "B01", "colour": "red", "evidence_interval_s": [95, 101]}],
                [0, 100],
            )


if __name__ == "__main__":
    unittest.main()
