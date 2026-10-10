"""Unsupported live gaps retain visual candidates without confirming throws."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gap_motion_candidates import candidates_from_observations, interior_beijing_gaps


def test_only_interior_beijing_gap_is_scanned():
    runs = [
        {"layout": "unknown", "interval_s": [0, 100]},
        {"layout": "beijing_2022", "interval_s": [100, 300]},
        {"layout": "unknown", "interval_s": [300, 400]},
        {"layout": "beijing_2022", "interval_s": [400, 600]},
        {"layout": "unknown", "interval_s": [600, 700]},
    ]
    assert interior_beijing_gaps(runs) == [[300, 400]]


def test_visual_track_stays_unconfirmed_and_out_of_event_schema():
    observations = {
        "red": [(float(t), []) for t in range(300, 304)],
        "yellow": [(float(t), [{"pixel": [100 + 12 * (t - 300), 150]}]) for t in range(300, 304)],
    }
    candidates = candidates_from_observations(observations, "G01", [300, 400])
    assert len(candidates) == 1
    assert candidates[0]["colour"] == "yellow"
    assert candidates[0]["evidence_interval_s"] == [300.0, 303.0]
    assert candidates[0]["status"] == "unconfirmed_gap_motion_candidate"
