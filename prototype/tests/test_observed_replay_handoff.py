import pytest

from prototype.observed_replay_handoff import build_observed_replay


def point(time, x, y):
    return {"time_s": time, "world_m": [x, y], "pixel": [100, 200]}


def candidate(arrival_start):
    return {
        "id": "T01",
        "colour": "red",
        "gate_time_s": 10.5,
        "departure": [point(10, 0, 5), point(11, 0.1, 7)],
        "arrival": [point(arrival_start, 0.3, 12), point(arrival_start + 1, 0.4, 14)],
    }


def test_gap_stays_unobserved_and_no_physical_end_is_invented():
    row = build_observed_replay(candidate(14), {"outcome": {"settled": None}})
    assert row["seam"]["status"] == "unobserved_temporal_gap"
    assert row["seam"]["sampled_time_gap_s"] == 3
    assert [len(s["points"]) for s in row["piecewise_observed_trajectory"]] == [2, 2]
    assert row["physical_release_time_s"] is None
    assert row["physical_settle_time_s"] is None
    assert row["physics_simulation_ready"] is False


def test_same_time_seam_keeps_spatial_disagreement():
    row = build_observed_replay(candidate(11), {"outcome": {"settled": None}})
    assert row["seam"]["status"] == "same_time_projections_disagree_unresolved"
    assert row["seam"]["sampled_time_gap_s"] == 0
    assert row["seam"]["same_time_longitudinal_difference_m"] == 5
    assert row["seam"]["same_time_lateral_difference_m"] == 0.2


def test_receiving_observation_cannot_precede_last_departure():
    with pytest.raises(ValueError, match="Receiving observations"):
        build_observed_replay(candidate(10.9), {"outcome": {"settled": None}})
