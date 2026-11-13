"""Grounded handoff contract for partial video-derived curling boards."""

from math import isfinite


def partial_board_observation(row, source_sha256):
    """Export only stable video stones, never official comparison positions.

    A counter-anchored sample is a partial observation, even when a separate
    evaluation later finds it complete against an official diagram. The
    output has no persistent stone identity or validated metric scale.
    """
    stones = row["stable_partial_board"]
    if not stones:
        return None
    if not isinstance(source_sha256, str) or len(source_sha256) != 64:
        raise ValueError("Expected a source SHA-256 fingerprint")
    emitted = []
    for index, stone in enumerate(stones, 1):
        colour = stone["colour"]
        if colour not in ("red", "yellow"):
            raise ValueError("Unsupported stone colour")
        x = float(stone["canonical_lateral_house_radii"])
        y = float(stone["longitudinal_house_radii"])
        first = float(stone["first_seen_s"])
        last = float(stone["last_seen_s"])
        spread = float(stone["max_position_spread_house_radii"])
        count = int(stone["supporting_frame_count"])
        if (
            not all(isfinite(value) for value in (x, y, first, last, spread))
            or first > last
            or spread < 0
            or count < 3
        ):
            raise ValueError("Invalid temporal stone observation")
        emitted.append(
            {
                "local_observation_id": f"V{index:02d}",
                "colour": colour,
                "position_house_radii": [x, y],
                "first_seen_s": first,
                "last_seen_s": last,
                "supporting_frame_count": count,
                "max_position_spread_house_radii": spread,
                "persistent_stone_identity": None,
            }
        )
    return {
        "observation_id": f"{row['official_game_code']}-video-board-{row['official_shot_id']}",
        "source_video_sha256": source_sha256,
        "source_recording_code": row["official_game_code"],
        "counter_anchor_s": row["counter_time_s"],
        "observation_interval_s": [
            min(stone["first_seen_s"] for stone in emitted),
            max(stone["last_seen_s"] for stone in emitted),
        ],
        "coordinate_frame": {
            "name": "canonical_overhead_house",
            "origin": "house_button",
            "unit": "detected_outer_house_radius",
            "metric_scale_status": "unvalidated",
            "orientation_status": "inferred_from_recording_overhead_views",
        },
        "state_status": "partial_video_observation",
        "completeness": "unknown_from_video",
        "simulation_ready": False,
        "stones": emitted,
        "unsupported_fields": {
            "exact_throw_release_time_s": None,
            "physical_settle_time_s": None,
            "persistent_stone_ids": None,
            "trajectory_3d": None,
        },
    }
