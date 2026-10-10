import pytest

from prototype.candidate_cross_view_colour import reconcile_visual_only_colours


def candidate(colour="red"):
    return {
        "candidate_id": "T1",
        "shot_id": "S1",
        "counter_id": None,
        "evidence_class": "origin_view_candidate",
        "release_window_s": [1, 2],
        "colour": colour,
    }


def postcut(colour="yellow"):
    return {
        "candidate_id": "T1",
        "shot_id": "S1",
        "release_window_s": [1, 2],
        "original_colour": "red",
        "postcut_colour": colour,
        "postcut_status": "unique_strict_postcut_motion",
    }


def test_conflict_abstains_and_preserves_observations():
    row = reconcile_visual_only_colours([candidate()], [postcut()])[0]
    assert row["relation"] == "colour_conflict"
    assert row["origin_colour"] == "red" and row["receiving_colour"] == "yellow"
    assert row["two_view_colour"] is None
    assert not row["camera_handoff_identity_verified"]


def test_agreement_is_still_not_game_state_identity():
    row = reconcile_visual_only_colours([candidate()], [postcut("red")])[0]
    assert row["two_view_colour"] == "red"
    assert not row["game_state_colour_ready"]


def test_missing_scan_is_rejected():
    with pytest.raises(ValueError, match="IDs differ"):
        reconcile_visual_only_colours([candidate()], [])


def test_mismatched_candidate_is_rejected():
    with pytest.raises(ValueError, match="differs"):
        reconcile_visual_only_colours([candidate("yellow")], [postcut("yellow")])
