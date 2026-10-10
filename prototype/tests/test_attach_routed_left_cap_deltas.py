from prototype.attach_routed_left_cap_deltas import attach_routed_left_cap_deltas


def test_keeps_image_delta_separate_from_physical_board():
    sequence = {"source_sha256": "s", "rows": [{
        "candidate_id": "L1",
        "post_candidate_receiving_view_observation": {"view": "left", "status": "partial"},
        "game_state_after": {"complete_board": None, "simulation_ready": False},
    }]}
    pre = {"source_sha256": "s", "rows": [{
        "candidate_id": "L1", "status": "partial", "sample_times_s": [1, 2, 3],
        "stable_cap_proposals": [{"colour": "red", "pixel_center": [10, 10]}],
        "complete_board_verified": False, "simulation_ready": False,
    }]}
    delta = {"source_sha256": "s", "rows": [{
        "candidate_id": "L1", "pre_observation_status": "partial",
        "post_observation_status": "partial",
        "comparison_status": "partial_cap_image_comparison",
        "image_cap_delta": {"locally_retained": [{"colour": "red"}],
                            "newly_observed": ["C02"]},
        "physical_transition_verified": False,
        "complete_board_verified": False, "simulation_ready": False,
    }]}
    result = attach_routed_left_cap_deltas(sequence, pre, delta)
    row = result["rows"][0]
    assert row["receiving_view_partial_cap_transition"]["image_cap_delta"][
        "newly_observed"] == ["C02"]
    assert row["game_state_after"]["complete_board"] is None
    assert row["game_state_after"]["simulation_ready"] is False
    assert "receiving_view_partial_cap_transition" not in sequence["rows"][0]
