"""Weak counter windows may overlap but matches remain one-to-one."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from counter_concordance import concordance


def test_overlapping_proxy_windows_cannot_both_claim_one_visual_track():
    refs = [
        {"id": "C1", "colour": "red", "counter_update_s": 20, "delivery_interval_s": [10, 30]},
        {"id": "C2", "colour": "yellow", "counter_update_s": 25, "delivery_interval_s": [15, 35]},
    ]
    candidates = [
        {"id": "Y", "colour": "yellow", "crossing_time_s": 22},
        {"id": "R", "colour": "red", "crossing_time_s": 24},
    ]
    score = concordance(candidates, refs)
    assert score["temporal_match_count"] == 2
    assert score["colour_match_count"] == 2
    assert {row["candidate_id"] for row in score["colour_matches"]} == {"Y", "R"}
    assert concordance(candidates[:1], refs)["temporal_match_count"] == 1
