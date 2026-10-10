import copy

import pytest

from source_diverse_episode_handoff import build_episode_handoff


def fixture():
    episodes = {
        "episode_count": 2,
        "original_left_candidate_count": 2,
        "right_proposal_count": 2,
        "episodes": [
            {"episode_id": "E1", "episode_kind": "one_to_one_time_candidate",
             "member_left_candidate_ids": ["S1"], "right_proposal_ids": ["R1"]},
            {"episode_id": "E2", "episode_kind": "one_to_one_time_candidate",
             "member_left_candidate_ids": ["S2"], "right_proposal_ids": ["R2"]},
        ],
    }
    states = {"episodes": [
        {"episode_id": "E1", "episode_kind": "one_to_one_time_candidate",
         "left_members": [{"interval_candidate_id": "S1"}],
         "right_proposal_ids": ["R1"],
         "post_event_partial_board": {"stones": [{"colour": "red"}]},
         "complete_game_state": False, "simulation_ready": False},
        {"episode_id": "E2", "episode_kind": "one_to_one_time_candidate",
         "left_members": [{"interval_candidate_id": "S2"}],
         "right_proposal_ids": ["R2"], "post_event_partial_board": None,
         "complete_game_state": False, "simulation_ready": False},
    ]}
    scores = {"rows": [
        {"right_proposal_id": "R1", "passage_time_s": 10,
         "positive_patch_count": 3, "any_positive_patch": True,
         "samples": [{"time_s": 9}, {"time_s": 10}, {"time_s": 11}]},
        {"right_proposal_id": "R2", "passage_time_s": 20,
         "positive_patch_count": 0, "any_positive_patch": False,
         "samples": [{"time_s": 19}, {"time_s": 20}, {"time_s": 21}]},
    ]}
    audits = {"review": {"rows": [
        {"right_proposal_id": "R1",
         "sampled_source_pixel_class": "moving_stone_pixels",
         "source_sample_times_s": [9, 10, 11], "page": "page-1.jpg"},
        {"right_proposal_id": "R2",
         "sampled_source_pixel_class": "person_or_equipment_pixels",
         "source_sample_times_s": [19, 20, 21], "page": "page-1.jpg"},
    ]}}
    return episodes, states, scores, audits


def test_preserves_every_candidate_board_and_uncertain_identity():
    rows, priorities = build_episode_handoff(*fixture())
    assert [row["episode_id"] for row in rows] == ["E1", "E2"]
    assert rows[0]["post_event_partial_board"] == {
        "stones": [{"colour": "red"}]}
    assert rows[0]["source_reviewed_stone_prefix_right_ids"] == ["R1"]
    assert rows[1]["right_proposal_evidence"][0][
        "sampled_source_pixel_class"] == "person_or_equipment_pixels"
    assert rows[1]["right_proposal_evidence"][0]["right_proposal_id"] == "R2"
    assert priorities == {
        "review_stone_prefix_cross_view_identity_and_board": 1,
        "review_left_candidate_or_missing_right_stone": 1,
    }
    assert all(not row["simulation_ready"] and not row[
        "cross_view_identity_verified"] for row in rows)


def test_rejects_source_review_that_uses_different_frames():
    inputs = list(fixture())
    inputs[3] = copy.deepcopy(inputs[3])
    inputs[3]["review"]["rows"][0]["source_sample_times_s"] = [8, 10, 11]
    with pytest.raises(ValueError, match="Source review/score mismatch"):
        build_episode_handoff(*inputs)


def test_rejects_dropped_or_duplicate_right_candidate():
    inputs = list(fixture())
    inputs[0] = copy.deepcopy(inputs[0])
    inputs[0]["episodes"][1]["right_proposal_ids"] = ["R1"]
    inputs[1] = copy.deepcopy(inputs[1])
    inputs[1]["episodes"][1]["right_proposal_ids"] = ["R1"]
    with pytest.raises(ValueError, match="Episode candidate conservation failed"):
        build_episode_handoff(*inputs)


def test_attaches_measured_path_overlap_without_promoting_identity():
    overlap = [{"left_candidate_id": "S1", "right_proposal_id": "R1",
                "sampled_time_overlap_count": 3,
                "median_center_distance_px_360": 0.8}]
    rows, _ = build_episode_handoff(*fixture(), overlap)
    assert rows[0]["cross_resolution_candidate_pair_evidence"] == [{
        "left_candidate_id": "S1", "right_proposal_id": "R1",
        "sampled_time_overlap_count": 3,
        "median_center_distance_px_360": 0.8,
        "physical_stone_identity_verified": False,
    }]
    assert rows[1]["cross_resolution_candidate_pair_evidence"] == []
    assert not rows[0]["simulation_ready"]


def test_rejects_orphan_cross_resolution_pair():
    overlap = [{"left_candidate_id": "S1", "right_proposal_id": "R2",
                "sampled_time_overlap_count": 3,
                "median_center_distance_px_360": 0.8}]
    with pytest.raises(ValueError, match="Episode candidate conservation failed"):
        build_episode_handoff(*fixture(), overlap)
