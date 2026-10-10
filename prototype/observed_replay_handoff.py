"""Conservative two-camera observation replay contract for curling stones."""

from math import hypot, isfinite


def _segment(points, camera, *, position_scope):
    if not points:
        raise ValueError(f"Missing {camera} observations")
    previous_time = None
    emitted = []
    for point in points:
        t = float(point["time_s"])
        x, y = (float(value) for value in point["world_m"])
        if (
            not all(isfinite(value) for value in (t, x, y))
            or previous_time is not None
            and t <= previous_time
        ):
            raise ValueError(f"Invalid {camera} observation chronology")
        emitted.append(
            {
                "source_time_s": t,
                "world_xy_m": [x, y],
                "source_pixel": point["pixel"],
                "point_scope": point.get("scope", position_scope),
            }
        )
        previous_time = t
    return {
        "camera": camera,
        "coordinate_status": "conditional_metric_projection_not_physically_validated",
        "first_observed_s": emitted[0]["source_time_s"],
        "last_observed_s": emitted[-1]["source_time_s"],
        "points": emitted,
    }


def build_observed_replay(throw, segment_source):
    departure = _segment(
        throw["departure"], "departure_left", position_scope="original_departure_projection"
    )
    arrival_input = throw.get("display_arrival") or throw["arrival"]
    arrival = _segment(
        arrival_input, "receiving_right", position_scope="bounded_receiving_projection"
    )
    left_last = departure["points"][-1]
    right_first = arrival["points"][0]
    gap = round(right_first["source_time_s"] - left_last["source_time_s"], 6)
    if gap < -0.000001:
        raise ValueError("Receiving observations start before departure ends")
    if abs(gap) < 0.000001:
        dx = right_first["world_xy_m"][0] - left_last["world_xy_m"][0]
        dy = right_first["world_xy_m"][1] - left_last["world_xy_m"][1]
        seam = {
            "status": "same_time_projections_disagree_unresolved",
            "sampled_time_gap_s": 0.0,
            "same_time_lateral_difference_m": round(dx, 6),
            "same_time_longitudinal_difference_m": round(dy, 6),
            "same_time_distance_m": round(hypot(dx, dy), 6),
            "physical_identity_verified": False,
        }
    else:
        seam = {
            "status": "unobserved_temporal_gap",
            "sampled_time_gap_s": gap,
            "same_time_lateral_difference_m": None,
            "same_time_longitudinal_difference_m": None,
            "same_time_distance_m": None,
            "physical_identity_verified": False,
        }
    source_outcome = segment_source["outcome"]
    settled = source_outcome.get("settled")
    return {
        "candidate_id": throw["id"],
        "colour_claim": throw["colour"],
        "virtual_line_passage_s": throw["gate_time_s"],
        "observed_envelope_s": [departure["first_observed_s"], arrival["last_observed_s"]],
        "piecewise_observed_trajectory": [departure, arrival],
        "seam": seam,
        "interaction_candidates": source_outcome.get("interaction_candidates", []),
        "visually_stable_delivered_stone_candidate": (
            {
                "source_time_s": settled["time_s"],
                "receiving_local_position_m": settled["position_m"],
                "candidate_window_s": settled["window_s"],
                "physical_settle_verified": False,
            }
            if settled
            else None
        ),
        "physical_throw_identity_verified": False,
        "physical_release_time_s": None,
        "physical_settle_time_s": None,
        "complete_post_throw_board": None,
        "stone_spin_revolutions": None,
        "metric_accuracy_validated": False,
        "continuous_physical_trajectory_verified": False,
        "piecewise_observation_replay_available": True,
        "physics_simulation_ready": False,
    }
