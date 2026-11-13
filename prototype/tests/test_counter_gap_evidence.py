import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from counter_gap_evidence import classify_counter_gap_events


def event(identifier, first, update):
    return {
        "id": identifier,
        "colour": "yellow",
        "evidence_interval_s": [first, update],
        "crossing_time_s": update,
        "remaining_before": [0, 1],
        "remaining_after": [0, 0],
    }


class CounterGapEvidenceTests(unittest.TestCase):
    def test_whole_interval_inside_gap_is_candidate(self):
        rows = classify_counter_gap_events([event("B1", 3661, 3662)], [[3600, 3900]])
        self.assertEqual(rows[0]["classification"], "counter_evidence_inside_gap")

    def test_straddling_interval_is_boundary_ambiguous(self):
        rows = classify_counter_gap_events([event("B1", 3596, 3629)], [[3600, 3900]])
        self.assertEqual(rows[0]["classification"], "boundary_ambiguous_counter_evidence")

    def test_supported_interval_stays_outside(self):
        rows = classify_counter_gap_events([event("B1", 3500, 3501)], [[3600, 3900]])
        self.assertEqual(rows[0]["classification"], "outside_route_gaps")

    def test_invalid_evidence_order_rejected(self):
        with self.assertRaises(ValueError):
            classify_counter_gap_events([event("B1", 3663, 3662)], [[3600, 3900]])
