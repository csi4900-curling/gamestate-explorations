"""Extract directional image-motion episodes from sparse stone-box paths.

This does not identify a physical stone or locate its release. In particular,
a track may switch identity at the apparent onset.
"""

from math import hypot


def sustained_motion_episode(points, *, min_axis_step_px=20,
                             min_consecutive_steps=2, min_axis_span_px=75):
    """Find the first sustained vertical movement in one-second observations.

    Return an observation bracket and the path suffix starting at the last
    pre-motion sample. Slow movement before the bracket remains unresolved.
    """
    if min_axis_step_px <= 0 or min_consecutive_steps < 2 or min_axis_span_px <= 0:
        raise ValueError("Invalid motion thresholds")
    if len(points) < min_consecutive_steps + 1:
        return None
    times = [p["time_s"] for p in points]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Image observations must increase in time")
    steps = []
    for before, after in zip(points, points[1:]):
        gap = after["time_s"]-before["time_s"]
        dx = after["center_1080p_px"][0]-before["center_1080p_px"][0]
        dy = after["center_1080p_px"][1]-before["center_1080p_px"][1]
        sign = 1 if gap == 1 and dy >= min_axis_step_px else \
            -1 if gap == 1 and dy <= -min_axis_step_px else 0
        steps.append((sign, dx, dy, hypot(dx, dy)))
    for start in range(len(steps)-min_consecutive_steps+1):
        sign = steps[start][0]
        if sign == 0 or any(steps[j][0] != sign
                            for j in range(start, start+min_consecutive_steps)):
            continue
        end = start+min_consecutive_steps
        while end < len(steps) and steps[end][0] == sign:
            end += 1
        span = sign*(points[end]["center_1080p_px"][1] -
                     points[start]["center_1080p_px"][1])
        if span < min_axis_span_px:
            continue
        return {
            "status": "sustained_image_motion_not_release_or_identity_proof",
            "direction": "positive_y" if sign > 0 else "negative_y",
            "motion_onset_observation_bracket_s": [times[start], times[start+1]],
            "moving_run_interval_s": [times[start], times[end]],
            "moving_run_axis_span_1080p_px": round(span, 2),
            "pre_onset_observation_count": start,
            "pre_onset_observed_interval_s": [times[0], times[start]]
            if start else None,
            "path_suffix_start_index": start,
            "identity_continuity_across_onset_verified": False,
            "physical_release_verified": False,
        }
    return None
