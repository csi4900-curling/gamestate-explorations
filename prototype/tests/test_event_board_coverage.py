from copy import deepcopy

import pytest

from event_board_coverage import audit_board_event_coverage


def sample():
    board = {
        "source_video_sha256": "a" * 64,
        "board_window_id": "shot-1",
        "counter_anchor_s": 42.0,
        "partial_board_stone_count": 1,
    }
    legacy = {
        "candidate_id": "T1",
        "shot_id": "S1",
        "counter_id": "B1",
        "colour": "red",
        "colour_status": "resolved",
        "release_window_s": [30.0, 40.0],
        "broadcast_counter": {"update_s": 42.0},
    }
    grounded = {
        "shot_id": "S1",
        "counter_id": "B1",
        "colour": "red",
        "colour_provenance": {"basis": "visual_and_counter_agree"},
        "camera_boundary_evidence": {"continuity_status": "no_proposed_internal_edit"},
    }
    return board, legacy, grounded


def test_missing_grounded_event_does_not_erase_partial_board():
    board, legacy, _ = sample()
    row = audit_board_event_coverage([board], [legacy], [])[0]
    assert row["partial_board_stone_count"] == 1
    assert row["legacy_event"]["candidate_id"] == "T1"
    assert row["grounded_event"] is None
    assert row["grounded_event_coverage"] == "absent"
    assert row["physical_transition_verified"] is False
    assert row["simulation_ready"] is False


def test_grounded_event_join_retains_colour_basis_and_camera_risk():
    board, legacy, grounded = sample()
    row = audit_board_event_coverage([board], [legacy], [grounded])[0]
    assert row["grounded_event"]["colour_basis"] == "visual_and_counter_agree"
    assert row["grounded_event"]["camera_continuity_status"] == ("no_proposed_internal_edit")


def test_ambiguous_legacy_anchor_and_changed_colour_are_rejected():
    board, legacy, grounded = sample()
    duplicate = deepcopy(legacy)
    duplicate["candidate_id"] = "T2"
    with pytest.raises(ValueError, match="one legacy counter match"):
        audit_board_event_coverage([board], [legacy, duplicate], [grounded])
    grounded["colour"] = "yellow"
    with pytest.raises(ValueError, match="changed resolved colour"):
        audit_board_event_coverage([board], [legacy], [grounded])
