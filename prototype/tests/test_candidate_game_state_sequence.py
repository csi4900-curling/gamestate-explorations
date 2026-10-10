"""The ordered ledger must preserve renamed baseline events and uncertainty."""

from copy import deepcopy

import pytest

from candidate_game_state_sequence import build_candidate_sequence


def fixtures():
    old = {"id": "R02-S01", "crossing_time_s": 100.0, "colour": "red"}
    preserved = {**old, "id": "R01-S05"}
    added = {"id": "R01-S06", "crossing_time_s": 140.0, "colour": "yellow"}
    baseline = {"source_sha256": "source", "observed_events": [old]}
    bridged = {"source_sha256": "source", "observed_events": [preserved, added]}
    triage = {"source_sha256": "source", "original_candidates_preserved": [
        {"original_id": "R02-S01", "bridged_id": "R01-S05", "time_s": 100.0,
         "colour": "red"}], "new_review_candidates": [{"id": "R01-S06"}]}
    fusion = {"source_sha256": "source", "right_entries": [
        {"right_raw_track_id": "R11", "conditional_left_candidate_id": "R01-S06",
         "fusion_status": "cross_view_time_colour_corrob", "right_colour_claim": "yellow",
         "right_entry_time_s": 150.0, "right_minus_left_lag_s": 10.0},
        {"right_raw_track_id": "R12", "conditional_left_candidate_id": None,
         "fusion_status": "unmatched_supported_left_review", "right_colour_claim": "red",
         "right_entry_time_s": 180.0, "right_minus_left_lag_s": None}]}
    crossing = {"source_sha256": "source", "rows": [
        {"candidate_id": "R01-S06", "crossing_source_class":
         "stone_at_tracked_crossing"}]}
    right_review = {"source_sha256": "source", "review": [
        {"right_raw_track_id": "R12", "sampled_prefix_class":
         "moving_person_wheelchair"}]}
    return baseline, bridged, triage, fusion, crossing, right_review


def test_preserves_renamed_baseline_and_explicit_unknown_state():
    output = build_candidate_sequence(*fixtures())
    assert output["candidate_sequence_count"] == 3
    assert output["baseline_left_count"] == 1
    assert output["bridged_addition_count"] == 1
    assert output["conditional_two_view_link_count"] == 1
    rows = output["rows"]
    assert [row["candidate_id"] for row in rows] == ["R01-S05", "R01-S06", "R12"]
    assert rows[0]["baseline_candidate_id"] == "R02-S01"
    assert rows[1]["proposal_origin"] == "bridged_gap_review"
    assert rows[1]["evidence_tier"] == "source_reviewed_stone_with_right"
    assert rows[2]["evidence_tier"] == "source_reviewed_nonstone"
    assert all(row["game_state_after"]["complete_board"] is None and
               not row["game_state_after"]["simulation_ready"] for row in rows)


def test_rejects_wrong_renamed_lineage():
    data = list(deepcopy(fixtures()))
    data[2]["original_candidates_preserved"][0]["time_s"] = 101.0
    with pytest.raises(ValueError, match="Baseline candidate changed"):
        build_candidate_sequence(*data)


def test_rejects_colour_inconsistent_right_link():
    data = list(deepcopy(fixtures()))
    data[3]["right_entries"][0]["right_colour_claim"] = "red"
    with pytest.raises(ValueError, match="colour or chronology"):
        build_candidate_sequence(*data)
