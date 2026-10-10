"""Tracklet boundaries must follow the comparison evidence exactly."""

import pytest

from scripts.build_partial_board_tracklets import build


def board(candidate_id, time_s, view="left"):
    return {
        "candidate_id": candidate_id,
        "crossing_time_s": time_s,
        "receiving_view": view,
        "board": {"status": "partial_stable_view_local_board", "stones": [{
            "local_observation_id": "V01", "colour": "red",
            "view_local_ground_position_m": [0.0, 0.0],
            "first_seen_s": time_s + 1, "last_seen_s": time_s + 2,
            "supporting_frame_count": 2,
        }]},
    }


def state(candidate_id, view="left"):
    return {
        "candidate_id": candidate_id,
        "event_status": "provisional_unreviewed_candidate",
        "screen_decision": "provisional_motion_and_patch_support",
        "receiving_view": view,
        "post_event_board": {"status": "partial_stable_view_local_board"},
    }


def comparison(before, after, status, matched=False):
    row = {"before_candidate_id": before, "after_candidate_id": after,
           "status": status, "intervening_passage_candidate_ids": []}
    if matched:
        row["matched_observations"] = [{
            "before_local_observation_id": "V01",
            "after_local_observation_id": "V01",
            "colour": "red", "distance_m_conditional": 0.0,
        }]
    return row


def test_abstention_ends_observation_tracklet():
    boards = {"rows": [board("S01", 1), board("S02", 2), board("S03", 3)]}
    comparisons = {
        "comparisons": [comparison("S01", "S02", "view_local_partial_comparison", True),
                        comparison("S02", "S03", "abstain_intervening_passage_candidate")],
        "associated_observation_pair_count": 1,
        "max_association_distance_m_conditional": 0.25,
    }
    timeline = {"timeline": [state("S01"), state("S02"), state("S03")]}
    result = build(boards, comparisons, timeline)
    assert result["tracklet_count"] == 2
    assert sorted(t["observation_count"] for t in result["tracklets"]) == [1, 2]
    assert all(not row["simulation_ready"] for row in result["candidate_states"])


def test_comparison_cannot_link_different_cameras():
    boards = {"rows": [board("S01", 1), board("S02", 2, view="right")]}
    comparisons = {
        "comparisons": [comparison("S01", "S02", "view_local_partial_comparison", True)],
        "associated_observation_pair_count": 1,
        "max_association_distance_m_conditional": 0.25,
    }
    timeline = {"timeline": [state("S01"), state("S02", view="right")]}
    with pytest.raises(ValueError, match="Invalid comparable board pair"):
        build(boards, comparisons, timeline)
