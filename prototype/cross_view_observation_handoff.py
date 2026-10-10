"""Carry observed cross-view stone paths into a simulation-oriented schema."""

from math import dist


def build_observation_handoff(throws, path_rows):
    by_id = {row["throw_id"]: row for row in path_rows}
    if len(by_id) != len(path_rows) or set(by_id) != {row["id"] for row in throws}:
        raise ValueError("Throw and far-path IDs differ or repeat")
    rows = []
    for event in throws:
        far = by_id[event["id"]]
        if far["colour"] != event["colour"]:
            raise ValueError(f"Throw colour mismatch: {event['id']}")
        departure = event["departure"]
        near = event["arrival"]
        if not departure or not near:
            raise ValueError(f"Missing bounded track: {event['id']}")
        unique = far["status"] == "unique_maximum_coverage_path_provisional"
        path = far["path"] if unique else []
        first = path[0] if path else None
        gap = round(first["time_s"] - departure[-1]["time_s"], 3) if first else None
        if gap is not None and gap < 0:
            raise ValueError(f"Negative observed gap: {event['id']}")
        simultaneous_disagreement = (
            round(dist(first["world_m"], departure[-1]["world_m"]), 4)
            if first and gap == 0
            else None
        )
        rows.append(
            {
                "throw_id": event["id"],
                "colour": event["colour"],
                "origin_gate_time_s": event["gate_time_s"],
                "bounded_receiving_track_id": event["receiving_track_id"],
                "far_receiving_path_status": far["status"],
                "departure_observations": departure,
                "far_receiving_observations": path,
                "bounded_receiving_observations": near,
                "old_bounded_processing_gap_s": event["gap"]["duration_s"],
                "last_departure_to_first_far_observation_s": gap,
                "same_time_camera_position_disagreement_m": simultaneous_disagreement,
                "observed_points_only": True,
                "physical_stone_identity_verified": False,
                "far_metric_accuracy_verified": False,
                "exact_physical_release_time_s": None,
                "exact_physical_settle_time_s": None,
                "physics_simulation_ready": False,
            }
        )
    return {
        "throw_count": len(rows),
        "far_path_selected_count": sum(bool(row["far_receiving_observations"]) for row in rows),
        "ambiguous_or_unresolved_count": sum(not row["far_receiving_observations"] for row in rows),
        "physics_simulation_ready_count": 0,
        "rows": rows,
        "limitations": [
            "Tracks are separately observed camera segments, not one validated physical identity.",
            "Same-time camera positions are preserved even if they disagree; no forced alignment or interpolation.",
            "Far-field homography and camera timing offset have not been independently calibrated.",
            "Exact release, settle, collisions and full game state remain unknown.",
        ],
    }
