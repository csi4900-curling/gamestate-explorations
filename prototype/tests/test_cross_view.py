from pathlib import Path
import sys, unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cross_view import (
    rink_position,
    arrival_candidates,
    connect,
    TEE_DISTANCE_M,
    truncate_after_stability,
)


class CrossViewTests(unittest.TestCase):
    def segment(self, duplicate=False):
        rows = []
        for i, y in enumerate([7.2, 6.6, 6.0, 5.3]):
            ss = [
                {
                    "colour": "yellow",
                    "track_id": 2,
                    "pixel_center": [1300, 600 - i * 20],
                    "ground_position_m": [0.2, y],
                }
            ]
            if duplicate:
                ss.append(dict(ss[0], track_id=3))
            rows.append({"source_time_s": 110 + i * 0.5, "views": {"right": {"stones": ss}}})
        return {
            "event": {"id": "T", "colour": "yellow", "crossing_time_s": 100},
            "review_interval_s": [100, 150],
            "timeline": {"records": rows},
        }

    def departure(self):
        return {"records": [{"time_s": 101, "position_local_m": [0.1, -10], "pixel": [480, 180]}]}

    def test_common_coordinates(self):
        self.assertEqual(rink_position([1, -10], "departure"), [1, 10])
        self.assertAlmostEqual(rink_position([1, 6.401], "receiving")[1], TEE_DISTANCE_M - 6.401)

    def test_unique_crossing(self):
        self.assertEqual(connect(self.segment(), self.departure())["status"], "provisional_link")

    def test_ambiguous_abstains(self):
        self.assertEqual(connect(self.segment(True), self.departure())["status"], "unresolved")

    def test_collision_track_no_hog_crossing(self):
        s = self.segment()
        for r in s["timeline"]["records"]:
            r["views"]["right"]["stones"][0]["ground_position_m"][1] -= 5
        self.assertEqual(arrival_candidates(s)[0], [])

    def test_wrong_colour(self):
        s = self.segment()
        s["event"]["colour"] = "red"
        self.assertEqual(arrival_candidates(s)[0], [])

    def test_no_calibration_no_link(self):
        self.assertEqual(connect(self.segment(), {"records": []})["status"], "unresolved")

    def test_reverse_time_rejected(self):
        d = self.departure()
        d["records"][0]["time_s"] = 120
        self.assertEqual(connect(self.segment(), d)["status"], "unresolved")

    def test_no_gap_interpolation(self):
        self.assertFalse(connect(self.segment(), self.departure())["gap"]["interpolated"])

    def test_stop_before_late_reassociation(self):
        points = [{"time_s": i * 0.5, "pixel": [10, 10]} for i in range(5)] + [
            {"time_s": 2.5, "pixel": [90, 90]}
        ]
        displayed, stop = truncate_after_stability(points)
        self.assertEqual(len(displayed), 5)
        self.assertEqual(len(points), 6)
        self.assertFalse(stop["physical_end_verified"])
