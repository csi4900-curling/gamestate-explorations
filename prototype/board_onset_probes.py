"""Describe a local board observation at its first source frame."""

from math import dist


def onset_frame_detection(local_stone, frame_stones):
    """Find the same-colour frame proposal nearest a board-local position.

    This is an internal grouping diagnostic, not delivered-stone identity.
    """
    candidates = [stone for stone in frame_stones if stone["colour"] == local_stone["colour"]]
    if not candidates:
        return None
    ranked = sorted(
        (
            (
                dist(
                    local_stone["view_local_ground_position_m"],
                    stone["view_local_ground_position_m"],
                ),
                stone,
            )
            for stone in candidates
        ),
        key=lambda pair: pair[0],
    )
    best_distance, best = ranked[0]
    return {
        "pixel_center_px_1080": best["pixel_center"],
        "conditional_ground_distance_m": round(best_distance, 3),
        "same_colour_frame_detection_count": len(candidates),
        "grouping_status": "nearest_internal_conditional_board_detection",
    }
