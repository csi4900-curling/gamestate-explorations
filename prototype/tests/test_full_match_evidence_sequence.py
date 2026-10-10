from copy import deepcopy

import pytest

from prototype.full_match_evidence_sequence import build_sequence


def fixtures():
    source = "a" * 64
    timeline = {
        "source_sha256": source,
        "supported_runs": [{"id": "R01", "layout": "split_2024", "interval_s": [10, 50]}],
        "coverage_gaps_s": [[0, 10], [50, 60]],
        "observed_events": [
            {"id": "L1", "crossing_time_s": 20, "colour": "red"},
            {"id": "L2", "crossing_time_s": 40, "colour": "yellow"},
        ],
    }
    inventory = {
        "source_sha256": source,
        "supported_runs": [{"id": "R01", "interval_s": [10, 50]}],
        "coverage_gaps_s": [[0, 10], [50, 60]],
        "left_event_count": 2,
        "right_proposal_count": 2,
        "left_events_without_any_right_time_colour_candidate": ["L2"],
        "rows": [
            {"proposal_id": "R01:A1", "raw_track_id": "A1", "colour_claim": "red",
             "passage_time_s": 24, "temporal_status": "one_left_time_colour_candidate",
             "direction_aware_same_colour_left_ids_within_lag": ["L1"]},
            {"proposal_id": "R01:A2", "raw_track_id": "A2", "colour_claim": "yellow",
             "passage_time_s": 30, "temporal_status": "no_left_time_colour_candidate",
             "direction_aware_same_colour_left_ids_within_lag": []},
        ],
    }
    context = {"source_sha256": source, "rows": [
        {"proposal_id": "R01:A1", "context_tier": "clear_context_review"},
        {"proposal_id": "R01:A2", "context_tier": "context_cluttered_review"},
    ]}
    right_reviews = {"R01": {"source_sha256": source, "rows": [
        {"raw_track_id": "A2", "source_prefix_class": "person_or_wheelchair_or_equipment"},
    ]}}
    left_review = {"source_sha256": source, "rows": [
        {"left_event_id": "L2", "source_prefix_class": "moving_stone"},
    ]}
    rescue = {"source_sha256": source, "rows": [
        {"left_event_id": "L2", "candidates": [{"raw_track_id": "A3"}]},
    ]}
    rescue_review = {"source_sha256": source, "rows": [
        {"raw_track_id": "A3", "source_prefix_class": "stone_pixels_identity_uncertain"},
    ]}
    return timeline, inventory, context, right_reviews, left_review, rescue, rescue_review


def test_sequence_keeps_right_only_nonstone_and_left_only_rescue_separate():
    result = build_sequence(*fixtures())
    assert result["sequence_row_count"] == 3
    assert result["coverage_gaps_s"] == [[0, 10], [50, 60]]
    assert [row["candidate_id"] for row in result["rows"]] == [
        "left:L1", "right:R01:A2", "left:L2"]
    assert result["rows"][2]["right_targeted_relaxed_raw_ids"] == ["A3"]
    assert result["rows"][2]["right_targeted_relaxed_source_classes"] == {
        "A3": "stone_pixels_identity_uncertain"}
    assert result["rows"][2]["right_temporal_candidate_ids"] == []
    assert result["right_proposals"][1]["source_pixel_class"] == "person_or_wheelchair_or_equipment"
    assert all(not row["game_state_after"]["simulation_ready"] for row in result["rows"])
    assert not result["complete_throw_sequence_verified"]


def test_sequence_rejects_missing_disagreement_review():
    args = list(fixtures())
    args[3] = {"R01": {"source_sha256": "a" * 64, "rows": []}}
    with pytest.raises(ValueError, match="Unreviewed right-only"):
        build_sequence(*args)


def test_sequence_rejects_inconsistent_inventory_links():
    args = list(fixtures())
    args[1] = deepcopy(args[1])
    args[1]["rows"][0]["direction_aware_same_colour_left_ids_within_lag"] = ["L2"]
    with pytest.raises(ValueError, match="Invalid temporal left reference"):
        build_sequence(*args)


def test_sequence_rejects_changed_coverage():
    args = list(fixtures())
    args[1] = deepcopy(args[1])
    args[1]["coverage_gaps_s"] = []
    with pytest.raises(ValueError, match="Coverage gaps differ"):
        build_sequence(*args)
