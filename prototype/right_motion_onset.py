"""Bound an observed right-view transition from quiet cap to directed motion.

This is image-motion timing, not a stone classifier or physical release time.
"""


def observed_quiet_to_motion(
    points,
    direction,
    *,
    quiet_rate_px_s=3,
    strong_rate_px_s=12,
    quiet_steps=3,
    strong_steps=2,
    max_sample_gap_s=1.5,
    max_quiet_to_strong_s=5,
):
    if direction not in ("positive_y", "negative_y"):
        raise ValueError("Unknown image-motion direction")
    if len(points) < quiet_steps + strong_steps + 1:
        return {"status": "insufficient_observations"}
    sign = 1 if direction == "positive_y" else -1
    steps = []
    for prev, current in zip(points, points[1:]):
        dt = current["time_s"] - prev["time_s"]
        if dt <= 0:
            raise ValueError("Track times must increase")
        steps.append(
            {
                "end_time_s": current["time_s"],
                "rate_px_s": sign * (current["pixel"][1] - prev["pixel"][1]) / dt,
                "sample_gap_s": dt,
            }
        )
    for strong_start in range(quiet_steps, len(steps) - strong_steps + 1):
        moving = steps[strong_start : strong_start + strong_steps]
        if not all(
            step["sample_gap_s"] <= max_sample_gap_s and step["rate_px_s"] >= strong_rate_px_s
            for step in moving
        ):
            continue
        quiet_end = None
        for end in range(quiet_steps - 1, strong_start):
            preceding = steps[end - quiet_steps + 1 : end + 1]
            if all(
                step["sample_gap_s"] <= max_sample_gap_s
                and abs(step["rate_px_s"]) <= quiet_rate_px_s
                for step in preceding
            ):
                quiet_end = end
        if quiet_end is None:
            continue
        quiet_time = points[quiet_end + 1]["time_s"]
        strong_time = points[strong_start + 1]["time_s"]
        if strong_time - quiet_time > max_quiet_to_strong_s:
            continue
        return {
            "status": "observed_quiet_to_sustained_directional_motion",
            "onset_bracket_s": [quiet_time, strong_time],
            "first_strong_motion_time_s": strong_time,
            "last_observed_track_time_s": points[-1]["time_s"],
            "observed_moving_points": points[strong_start:],
            "supporting_step_rates_px_s": [round(step["rate_px_s"], 3) for step in moving],
            "quiet_end_time_s": quiet_time,
            "physical_release_time_s": None,
            "physical_stone_identity_verified": False,
            "physical_settle_time_s": None,
        }
    return {"status": "no_supported_quiet_to_motion_transition"}
