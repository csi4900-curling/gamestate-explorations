import pytest

from prototype.attach_routed_partial_caps import attach_routed_partial_caps


def inputs():
    sequence = {"source_sha256": "s", "left_candidate_count": 2,
                "rows": [
                    {"candidate_id": "L1", "observation_kind": "left_tracked_passage",
                     "observation_time_s": 10, "colour_claim": "yellow",
                     "post_candidate_partial_cap_observation": {
                         "status": "no_stable_colour_cap_proposals", "sample_times_s": [25, 30, 35],
                         "coordinate_frame": "right_pixels", "stable_cap_proposals": [],
                         "complete_board_verified": False, "physical_settle_verified": False,
                         "simulation_ready": False},
                     "game_state_after": {"complete_board": None, "simulation_ready": False}},
                    {"candidate_id": "L2", "observation_kind": "left_tracked_passage",
                     "observation_time_s": 50, "colour_claim": "red",
                     "post_candidate_partial_cap_observation": {
                         "status": "partial", "sample_times_s": [65, 70, 75],
                         "coordinate_frame": "right_pixels", "stable_cap_proposals": ["red"],
                         "complete_board_verified": False, "physical_settle_verified": False,
                         "simulation_ready": False},
                     "game_state_after": {"complete_board": None, "simulation_ready": False}}],
                "limitations": []}
    routes = {"source_sha256": "s", "conditional_receiving_view_counts":
              {"left": 1, "right": 1},
              "rows": [{"candidate_id": "L1", "observation_time_s": 10,
                        "colour_claim": "yellow", "conditional_receiving_view": "left",
                        "routing_status": "conditional"},
                       {"candidate_id": "L2", "observation_time_s": 50,
                        "colour_claim": "red", "conditional_receiving_view": "right",
                        "routing_status": "conditional"}]}
    caps = {"source_sha256": "s", "rows": [
        {"candidate_id": "L1", "status": "partial_repeated_left_image_caps",
         "sample_times_s": [35, 40, 45], "stable_cap_proposals": ["yellow"],
         "complete_board_verified": False, "physical_settle_verified": False,
         "simulation_ready": False}]}
    return sequence, routes, caps


def test_attaches_view_specific_evidence_without_promoting_board():
    sequence, routes, caps = inputs()
    result = attach_routed_partial_caps(sequence, routes, caps)
    first, second = result["rows"]
    assert first["post_candidate_receiving_view_observation"]["view"] == "left"
    assert first["prior_right_scan_view_relevance"] == "prior_right_scan_not_receiving_view_conditional"
    assert second["post_candidate_receiving_view_observation"]["view"] == "right"
    assert first["game_state_after"]["complete_board"] is None
    assert not first["post_candidate_receiving_view_observation"]["simulation_ready"]
    assert "post_candidate_receiving_view_observation" not in sequence["rows"][0]


def test_rejects_missing_left_scan():
    sequence, routes, caps = inputs()
    caps["rows"] = []
    with pytest.raises(ValueError, match="coverage"):
        attach_routed_partial_caps(sequence, routes, caps)
