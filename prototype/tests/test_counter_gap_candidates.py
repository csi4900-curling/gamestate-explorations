import pytest

from prototype.counter_gap_candidates import audit_counter_gaps


def slot(name, counter=None, time_s=None):
    return {
        "official_shot_id": name,
        "official_colour": "red",
        "counter_id": counter,
        "video_event_evidence": {
            "candidate_release_window_s": [time_s, time_s + 1] if time_s is not None else None
        },
    }


def candidate(name, time_s):
    return {
        "candidate_id": name,
        "shot_id": name,
        "counter_id": None,
        "evidence_class": "origin_view_candidate",
        "release_window_s": [time_s, time_s + 1],
    }


def colour(name):
    return {
        "candidate_id": name,
        "origin_colour": "red",
        "receiving_colour": None,
        "two_view_colour": None,
        "relation": "origin_only",
    }


def test_single_temporal_proposal_does_not_verify_identity():
    groups = audit_counter_gaps(
        [slot("S1", "B1", 1), slot("S2"), slot("S3", "B2", 3)], [candidate("T2", 2)], [colour("T2")]
    )
    assert len(groups) == 1
    assert groups[0]["status"] == "single_temporal_proposal_not_identity_verified"
    assert not groups[0]["official_slot_association_verified"]


def test_visual_extra_between_adjacent_anchors_is_retained():
    groups = audit_counter_gaps(
        [slot("S1", "B1", 1), slot("S2", "B2", 3)], [candidate("T2", 2)], [colour("T2")]
    )
    assert groups[0]["status"] == "visual_proposals_without_missing_official_slot"


def test_duplicate_colour_handoff_rejected():
    with pytest.raises(ValueError, match="IDs differ"):
        audit_counter_gaps([slot("S1")], [candidate("T1", 1)], [colour("T1"), colour("T1")])
