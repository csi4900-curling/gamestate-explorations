import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from passage_corridor import screen_corridor


class PassageCorridorTests(unittest.TestCase):
    def test_preserves_candidate_order_and_marks_outside_edges(self):
        events = [
            {"id": "a", "crossing_time_s": 1.0, "colour": "red", "crossing_x_px": 100.0},
            {"id": "b", "crossing_time_s": 2.0, "colour": "yellow", "crossing_x_px": 220.0},
            {"id": "c", "crossing_time_s": 3.0, "colour": "red", "crossing_x_px": 99.9},
        ]
        result = screen_corridor(events, center_x_px=160.0, half_width_px=60.0)
        self.assertEqual([e["id"] for e in result], ["a", "b", "c"])
        self.assertEqual(
            [e["status"] for e in result],
            ["ice_corridor_candidate", "ice_corridor_candidate", "off_corridor_unconfirmed"],
        )

    def test_refuses_missing_geometry(self):
        with self.assertRaises(ValueError):
            screen_corridor(
                [
                    {
                        "id": "a",
                        "crossing_time_s": 1.0,
                        "colour": "red",
                        "crossing_x_px": float("nan"),
                    }
                ],
                center_x_px=160.0,
                half_width_px=60.0,
            )


if __name__ == "__main__":
    unittest.main()
