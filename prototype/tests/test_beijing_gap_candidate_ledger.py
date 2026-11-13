import copy

import pytest

from prototype.beijing_gap_candidate_ledger import build_gap_candidate_ledger


def fixtures():
    timeline = {
        "source_id": "video",
        "source_sha256": "hash",
        "source_interval_s": [0, 100],
        "coverage_gaps_s": [[40, 60]],
        "supported_runs": [{"interval_s": [0, 40]}, {"interval_s": [60, 100]}],
        "observed_events": [
            {"id": "A", "crossing_time_s": 10, "evidence_interval_s": [8, 10], "colour": "red"}
        ],
    }
    inventory = {
        "source_id": "video",
        "source_sha256": "hash",
        "source_interval_s": [0, 100],
        "coverage_gaps_s": [[40, 60]],
        "interior_gap_candidates": [
            {
                "counter_id": "B",
                "counter_update_s": 50,
                "counter_evidence_interval_s": [48, 50],
                "colour": "yellow",
                "gap_interval_s": [40, 60],
                "remaining_before": [1, 1],
                "remaining_after": [1, 0],
            }
        ],
        "boundary_ambiguous": [
            {
                "counter_id": "C",
                "counter_update_s": 62,
                "counter_evidence_interval_s": [59, 62],
                "colour": "red",
                "gap_interval_s": [40, 60],
                "remaining_before": [1, 0],
                "remaining_after": [0, 0],
            }
        ],
    }
    visual = {
        "source_id": "video",
        "source_sha256": "hash",
        "source_interval_s": [0, 100],
        "motion_candidates": [
            {"id": "V", "crossing_time_s": 53, "evidence_interval_s": [53, 55], "colour": "yellow"}
        ],
    }
    return timeline, inventory, visual


def test_keeps_gap_evidence_without_promoting_to_routed_event():
    rows = build_gap_candidate_ledger(*fixtures())
    assert [row["evidence_id"] for row in rows] == [
        "routed:A",
        "counter-gap:B",
        "visual-gap:V",
        "counter-gap:C",
    ]
    assert rows[2]["nearby_counter_gap_ids"] == ["B"]
    assert rows[2]["counter_visual_physical_identity_verified"] is False
    assert all(not row["distinct_physical_throw_verified"] for row in rows)


def test_rejects_counter_claimed_inside_gap_when_it_crosses_boundary():
    timeline, inventory, visual = fixtures()
    changed = copy.deepcopy(inventory)
    changed["interior_gap_candidates"][0]["counter_evidence_interval_s"] = [39, 50]
    with pytest.raises(ValueError, match="crosses gap boundary"):
        build_gap_candidate_ledger(timeline, changed, visual)
