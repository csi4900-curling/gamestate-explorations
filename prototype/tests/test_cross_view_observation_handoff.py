from prototype.cross_view_observation_handoff import build_observation_handoff


def test_handoff_preserves_same_time_disagreement_and_no_simulation_claim():
    event = {
        "id": "T1",
        "colour": "red",
        "gate_time_s": 0,
        "receiving_track_id": "R1",
        "gap": {"duration_s": 5},
        "departure": [{"time_s": 1, "world_m": [0, 2]}],
        "arrival": [{"time_s": 6, "world_m": [0, 7]}],
    }
    far = {
        "throw_id": "T1",
        "colour": "red",
        "status": "unique_maximum_coverage_path_provisional",
        "path": [{"time_s": 1, "world_m": [0, 2.5]}],
    }
    out = build_observation_handoff([event], [far])
    row = out["rows"][0]
    assert row["last_departure_to_first_far_observation_s"] == 0
    assert row["same_time_camera_position_disagreement_m"] == 0.5
    assert not row["physics_simulation_ready"]


def test_ambiguous_path_kept_empty():
    event = {
        "id": "T1",
        "colour": "red",
        "gate_time_s": 0,
        "receiving_track_id": "R1",
        "gap": {"duration_s": 5},
        "departure": [{"time_s": 1, "world_m": [0, 2]}],
        "arrival": [{"time_s": 6, "world_m": [0, 7]}],
    }
    far = {
        "throw_id": "T1",
        "colour": "red",
        "status": "multiple_maximum_coverage_paths",
        "path": [],
    }
    out = build_observation_handoff([event], [far])
    assert out["ambiguous_or_unresolved_count"] == 1
    assert out["rows"][0]["far_receiving_observations"] == []
