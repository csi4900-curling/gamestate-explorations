"""Separate observed moving prefixes from stationary-looking tracker tails.

These are image-motion intervals, not physical release or settle timestamps.
"""

from math import hypot


def split_moving_prefix(points, *, stable_step_px=4, stable_steps=3):
    """Return a visual-stop bracket only after consecutive one-second stillness.

    A gap or renewed motion resets the streak. The bracket ends at the first
    stable observation; it does not establish that this is the same stone.
    """
    if not points:
        raise ValueError("At least one image observation is required")
    if stable_step_px < 0 or stable_steps < 1:
        raise ValueError("Invalid stillness rule")
    streak = 0
    for index in range(1, len(points)):
        before, after = points[index - 1], points[index]
        gap = after["time_s"] - before["time_s"]
        if gap <= 0:
            raise ValueError("Image observations must increase in time")
        distance = hypot(
            *(after["center_1080p_px"][axis] - before["center_1080p_px"][axis] for axis in (0, 1))
        )
        if gap == 1 and distance <= stable_step_px:
            streak += 1
            if streak == stable_steps:
                first_stable_index = index - stable_steps + 1
                last_moving = points[first_stable_index - 1]["time_s"]
                first_stable = points[first_stable_index]["time_s"]
                return {
                    "status": "visual_stop_candidate_identity_unverified",
                    "observed_moving_prefix_first_s": points[0]["time_s"],
                    "observed_moving_prefix_last_s": last_moving,
                    "visual_stop_bracket_s": [last_moving, first_stable],
                    "stable_confirmation_last_s": points[index]["time_s"],
                    "post_stop_tracker_tail_excluded": len(points) - index - 1,
                }
        else:
            streak = 0
    return {
        "status": "moving_path_right_censored_no_visual_stop",
        "observed_moving_prefix_first_s": points[0]["time_s"],
        "observed_moving_prefix_last_s": points[-1]["time_s"],
        "visual_stop_bracket_s": None,
        "stable_confirmation_last_s": None,
        "post_stop_tracker_tail_excluded": 0,
    }
