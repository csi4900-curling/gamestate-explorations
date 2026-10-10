"""Preserve uncertainty and reject broken event/board joins."""

from copy import deepcopy

import pytest

from partial_state_sequence import build_partial_state_sequence


def inputs():
    common = {"source_sha256": "a" * 64, "source_id": "match",
              "source_interval_s": [0, 100]}
    screen = {**common,
              "events": [{"id": "S1", "colour": "red", "crossing_time_s": 10,
                          "time_semantics": "observed_passage"},
                         {"id": "S2", "colour": "yellow", "crossing_time_s": 50,
                          "time_semantics": "observed_passage"}],
              "decisions": [{"candidate_id": "S1", "accepted": True},
                            {"candidate_id": "S2", "accepted": True},
                            {"candidate_id": "Sx", "accepted": False}]}
    stone = {"local_observation_id": "V01", "colour": "red",
             "view_local_ground_position_m": [1, 2], "first_seen_s": 14,
             "last_seen_s": 18, "supporting_frame_count": 5,
             "max_position_spread_m": .02}
    base_board = {"candidate_id": "S1", "colour": "red", "crossing_time_s": 10,
                  "receiving_view": "right", "tail": {"eligible": True,
                  "start_s": 12, "stop_s": 20},
                  "board": {"status": "partial_stable_view_local_board", "stones": [stone]},
                  "coordinate_frame": {"unit": "metres_conditional_projection"},
                  "completeness": "unknown_from_video",
                  "post_throw_settle_verified": False}
    second = deepcopy(base_board)
    second.update(candidate_id="S2", colour="yellow", crossing_time_s=50)
    boards = {**common, "rows": [base_board, second]}
    comparisons = {**common, "comparisons": [{
        "before_candidate_id": "S1", "after_candidate_id": "S2",
        "status": "view_local_partial_comparison", "same_end_verified": False,
        "matched_observations": [{"before_local_observation_id": "V01",
                                  "after_local_observation_id": "V01",
                                  "colour": "red", "physical_identity_verified": False}],
        "before_only_observations": [], "after_only_observations": [],
        "intervening_passage_candidate_ids": []}]}
    return screen, boards, comparisons


def test_sequence_preserves_conditional_positions_and_nonphysical_pairs():
    result = build_partial_state_sequence(*inputs())
    assert result["event_count"] == 2
    assert result["withheld_screen_candidate_ids"] == ["Sx"]
    assert result["comparable_transition_count"] == 1
    assert result["simulation_ready_count"] == 0
    assert result["events"][1]["post_event_observation"]["stones"][0][
        "position_m_conditional"] == [1, 2]
    transition = result["events"][1]["transition_from_previous_candidate"]
    assert transition["matched_local_observations"][0]["physical_identity_verified"] is False
    assert transition["physical_additions_removals_or_collisions_inferred"] is False


def test_nonadjacent_comparison_rejected():
    data = list(inputs())
    data[2]["comparisons"][0]["before_candidate_id"] = "Sx"
    with pytest.raises(ValueError, match="Nonadjacent comparison"):
        build_partial_state_sequence(*data)


def test_comparison_unknown_stone_rejected():
    data = list(inputs())
    data[2]["comparisons"][0]["matched_observations"][0][
        "after_local_observation_id"] = "V99"
    with pytest.raises(ValueError, match="unknown observation"):
        build_partial_state_sequence(*data)


def test_mismatched_source_rejected():
    data = list(inputs())
    data[1]["source_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="fingerprints differ"):
        build_partial_state_sequence(*data)


def test_source_review_flags_false_path_without_rewriting_event():
    review = {"candidate_id": "S2", "source_sha256": "a" * 64,
              "status": "agent_source_review_not_independent_validation",
              "review_conclusion": "false_positive_wheelchair_movement",
              "basis": "Reviewed source frames show a wheelchair."}
    result = build_partial_state_sequence(*inputs(), [review])
    assert result["event_count"] == 2
    assert result["agent_source_reviewed_false_path_ids"] == ["S2"]
    row = result["events"][1]
    assert row["agent_source_review"]["independent_validation"] is False
    assert "source_reviewed_false_path" in row["simulation_blockers"]


def test_source_review_from_another_video_rejected():
    review = {"candidate_id": "S2", "source_sha256": "b" * 64,
              "status": "agent_source_review_not_independent_validation",
              "review_conclusion": "false_positive_wheelchair_movement",
              "basis": "Another match."}
    with pytest.raises(ValueError, match="Invalid or duplicate source review"):
        build_partial_state_sequence(*inputs(), [review])
