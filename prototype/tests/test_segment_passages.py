import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from segment_passages import build_segments


class ScreenedSegmentationTests(unittest.TestCase):
    def test_withheld_candidate_is_retained_and_not_used_as_boundary(self):
        events = [
            {"id": "T01", "colour": "red", "crossing_time_s": 10},
            {"id": "T02", "colour": "yellow", "crossing_time_s": 15},
            {"id": "T03", "colour": "red", "crossing_time_s": 20},
        ]
        screen = {
            "events": [
                {
                    "id": e["id"],
                    "colour": e["colour"],
                    "crossing_time_s": e["crossing_time_s"],
                    "appearance": {
                        "status": "person_or_other_object_suspected"
                        if e["id"] == "T02"
                        else "stone_appearance_candidate"
                    },
                }
                for e in events
            ]
        }
        result = build_segments(events, screen, 0, 30)
        self.assertEqual(
            [(s["start_s"], s["end_s"]) for s in result["segments"]], [(10, 20), (20, 30)]
        )
        self.assertEqual([s["id"] for s in result["withheld_candidates"]], ["T02"])
        self.assertEqual(result["unassigned_prefix_s"], [0, 10])
        self.assertTrue(all(s["physical_end_s"] is None for s in result["segments"]))

    def test_stale_screen_rejected(self):
        events = [{"id": "T01", "colour": "red", "crossing_time_s": 10}]
        screen = {
            "events": [
                {
                    "id": "T01",
                    "colour": "red",
                    "crossing_time_s": 11,
                    "appearance": {"status": "stone_appearance_candidate"},
                }
            ]
        }
        with self.assertRaises(ValueError):
            build_segments(events, screen, 0, 30)


if __name__ == "__main__":
    unittest.main()
