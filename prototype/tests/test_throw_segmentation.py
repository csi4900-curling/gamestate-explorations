import unittest, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from throw_segmentation import review_segments, visible_settling


class SegmentationTests(unittest.TestCase):
    def test_contiguous(self):
        x = review_segments(
            [{"id": "b", "crossing_time_s": 20}, {"id": "a", "crossing_time_s": 10}], 0, 30
        )
        self.assertEqual([(r["start_s"], r["end_s"]) for r in x], [(10, 20), (20, 30)])
        self.assertTrue(all(r["physical_end_s"] is None for r in x))

    def test_invalid(self):
        for times in [[10, 10], [float("nan")], [31]]:
            with self.assertRaises(ValueError):
                review_segments(
                    [{"id": str(i), "crossing_time_s": t} for i, t in enumerate(times)], 0, 30
                )

    def segment(self):
        return {
            "event": {"colour": "yellow"},
            "outcome": {"track_id": 1, "settled": {"time_s": 2}},
            "timeline": {
                "source_start_s": 0,
                "records": [
                    {
                        "time_s": i / 2,
                        "views": {
                            "right": {
                                "H": [[1]],
                                "stones": [
                                    {"colour": "yellow", "track_id": 1, "pixel_center": [10, 10]},
                                    {"colour": "red", "track_id": 2, "pixel_center": [20, 20]},
                                ],
                            }
                        },
                    }
                    for i in range(5)
                ],
            },
        }

    def test_stable(self):
        self.assertEqual(
            visible_settling(self.segment())["status"], "visible_scene_stable_candidate"
        )

    def test_other_stone_moving(self):
        s = self.segment()
        s["timeline"]["records"][-1]["views"]["right"]["stones"][1]["pixel_center"] = [30, 20]
        self.assertEqual(visible_settling(s)["status"], "unavailable")

    def test_missing_stone_not_settled(self):
        s = self.segment()
        s["timeline"]["records"][-1]["views"]["right"]["stones"].pop()
        self.assertEqual(visible_settling(s)["status"], "unavailable")

    def test_geometry_gap(self):
        s = self.segment()
        s["timeline"]["records"][2]["views"]["right"]["H"] = None
        self.assertEqual(visible_settling(s)["status"], "unavailable")
