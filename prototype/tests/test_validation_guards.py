"""Regression tests for audit findings, not detector-performance claims."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cache_contract import context_for, read_cache, write_cache
from cross_view import rink_position, truncate_after_stability, arrival_candidates, connect
import test_cross_view as cross_fixture
import test_throw_segmentation as segment_fixture
from throw_segmentation import visible_settling, review_segments


class AuditGuards(unittest.TestCase):
    def test_cache_requires_matching_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "input.txt"
            source.write_text("before")
            p = root / "cache.json"
            ctx = context_for([source], {"threshold": 3})
            write_cache(p, {"records": []}, ctx)
            self.assertEqual(read_cache(p, ctx)["records"], [])
            source.write_text("after")
            with self.assertRaises(ValueError):
                read_cache(p, context_for([source], {"threshold": 3}))
            self.assertIsNone(read_cache(p, ctx, force=True))

    def test_legacy_cache_not_silently_blessed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cache.json"
            p.write_text(json.dumps({"records": []}))
            with self.assertRaises(ValueError):
                read_cache(p, {"schema": 1})

    def test_same_named_inputs_both_hashed(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a"
            b = Path(d) / "b"
            a.mkdir()
            b.mkdir()
            a = a / "calibration.json"
            b = b / "calibration.json"
            a.write_text("1")
            b.write_text("2")
            self.assertEqual(len(context_for([a, b], {})["inputs"]), 2)

    def test_invalid_coordinates_rejected(self):
        for point in [[float("nan"), 0], [[1], [2]], [1, 2, 3]]:
            with self.assertRaises(ValueError):
                rink_position(point, "departure")
        with self.assertRaises(ValueError):
            rink_position([0, 0], "receiving", float("inf"))

    def test_nan_is_not_stationary(self):
        s = segment_fixture.SegmentationTests().segment()
        s["timeline"]["records"][-1]["views"]["right"]["stones"][0]["pixel_center"] = [
            float("nan"),
            10,
        ]
        self.assertEqual(visible_settling(s)["status"], "unavailable")

    def test_invalid_clock_not_stationary(self):
        with self.assertRaises(ValueError):
            truncate_after_stability([{"time_s": float("nan"), "pixel": [0, 0]}])

    def test_duplicate_times_rejected(self):
        s = cross_fixture.CrossViewTests().segment()
        s["timeline"]["records"][1]["source_time_s"] = s["timeline"]["records"][0]["source_time_s"]
        with self.assertRaises(ValueError):
            arrival_candidates(s)

    def test_crossing_after_segment_boundary_not_used(self):
        s = cross_fixture.CrossViewTests().segment()
        s["review_interval_s"][1] = 110.6
        self.assertEqual(arrival_candidates(s)[0], [])

    def test_wrong_departure_file_rejected(self):
        d = cross_fixture.CrossViewTests().departure()
        d["event_id"] = "OTHER"
        with self.assertRaises(ValueError):
            connect(cross_fixture.CrossViewTests().segment(), d)

    def test_infinite_segment_end_rejected(self):
        with self.assertRaises(ValueError):
            review_segments([], 0, float("inf"))
