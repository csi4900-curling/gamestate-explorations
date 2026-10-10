"""Protect the timeline from silently inventing complete game states."""

import pytest

from evidence_game_state_handoff import build_evidence_handoff


def fixtures():
    event = {"id": "S01", "colour": "red", "crossing_time_s": 10,
             "time_semantics": "observed_track_midpoint",
             "evidence_kind": "early_roi_motion_span"}
    candidates = {"events": [event], "withheld_events": []}
    screen = {"decisions": [{"candidate_id": "S01", "accepted": True,
                             "status": "provisional_motion_and_patch_support"}]}
    motion = {"rows": [{"candidate_id": "S01", "receiving_view": "right",
                        "selection": {"status": "provisional_path",
                                      "path": [{"source_time_s": 11,
                                                "pixel_center": [5, 6],
                                                "ground_position_m": [1, 2]}]}}]}
    boards = {"rows": [{"candidate_id": "S01", "crossing_time_s": 10,
                        "receiving_view": "right", "registered_frame_count": 5,
                        "registration_abstention_count": 0,
                        "tail": {"eligible": True, "start_s": 12, "stop_s": 20},
                        "board": {"status": "partial_stable_view_local_board",
                                  "stones": []}, "coordinate_frame": {},
                        "completeness": "unknown_from_video",
                        "post_throw_settle_verified": False}]}
    comparisons = {"comparisons": []}
    return candidates, screen, motion, boards, comparisons


def test_provisional_event_keeps_unmeasured_state_unknown():
    row = build_evidence_handoff(*fixtures())[0]
    assert row["event_status"] == "provisional_event"
    assert row["release_time_s"] is None
    assert row["physical_settle_time_s"] is None
    assert row["spin_revolution_count"] is None
    assert row["end_identity"] is None
    assert row["simulation_ready"] is False


def test_view_mismatch_is_rejected():
    args = list(fixtures())
    args[3]["rows"][0]["receiving_view"] = "left"
    with pytest.raises(ValueError, match="Inconsistent accepted event"):
        build_evidence_handoff(*args)


def test_withheld_passage_is_visible_without_invented_post_event_state():
    args = list(fixtures())
    args[0]["withheld_events"] = [{"id": "S02", "colour": "yellow",
                                   "crossing_time_s": 20,
                                   "time_semantics": "observed_track_midpoint",
                                   "evidence_kind": "early_roi_motion_span"}]
    timeline = build_evidence_handoff(*args)
    assert [row["candidate_id"] for row in timeline] == ["S01", "S02"]
    assert timeline[1]["event_status"] == "outside_screen_corridor"
    assert "post_event_partial_board" not in timeline[1]


def test_duplicate_candidate_id_is_rejected():
    args = list(fixtures())
    args[0]["withheld_events"] = [dict(args[0]["events"][0])]
    with pytest.raises(ValueError, match="Duplicate passage candidate"):
        build_evidence_handoff(*args)
