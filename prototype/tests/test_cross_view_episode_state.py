import copy

import pytest

from prototype.cross_view_episode_state import attach_episode_partial_states


def inputs():
    episodes = {
        "source_sha256": "source", "episodes": [
            {"episode_id": "E1", "episode_kind": "shared_one_right_candidate",
             "observation_time_s": 10, "observation_time_semantics":
             "first_left_candidate_passage", "colour_claim": "red",
             "member_left_candidate_ids": ["A", "B"], "right_proposal_ids": ["R1"]},
            {"episode_id": "E2", "episode_kind": "right_only_candidate",
             "observation_time_s": 30, "observation_time_semantics":
             "right_observed_motion_passage", "colour_claim": "yellow",
             "member_left_candidate_ids": [], "right_proposal_ids": ["R2"]},
        ]}
    corridor = {"source_sha256": "source", "events": [
        {"id": "A", "colour": "red", "crossing_time_s": 10},
        {"id": "B", "colour": "red", "crossing_time_s": 12}]}
    reconciliation = {"rows": [
        {"interval_id": "A", "full_id": "F1", "full_accepted": True,
         "interval_accepted": True, "full_status": "accepted"},
        {"interval_id": "B", "full_id": "F2", "full_accepted": False,
         "interval_accepted": False, "full_status": "duplicate"},
    ]}
    states = {"source_sha256": "source", "events": [
        {"candidate_id": "F1", "candidate_colour": "red", "passage_time_s": 10,
         "post_event_observation": {"stones": [{"colour": "yellow"}]}}]}
    return episodes, corridor, reconciliation, states


def test_attaches_one_partial_board_without_promoting_episode():
    rows = attach_episode_partial_states(*inputs())
    assert rows[0]["source_board_candidate_id"] == "F1"
    assert rows[0]["state_status"] == "partial_board_observed"
    assert rows[0]["post_event_partial_board"]["stones"] == [{"colour": "yellow"}]
    assert rows[1]["state_status"] == "no_accepted_event_member"
    assert rows[1]["post_event_partial_board"] is None
    assert all(not row["simulation_ready"] and
               not row["transition_from_previous_episode_verified"] for row in rows)


def test_rejects_mismatched_full_event_colour():
    args = inputs()
    changed = copy.deepcopy(args)
    changed[3]["events"][0]["candidate_colour"] = "yellow"
    with pytest.raises(ValueError, match="Interval and full-state"):
        attach_episode_partial_states(*changed)
