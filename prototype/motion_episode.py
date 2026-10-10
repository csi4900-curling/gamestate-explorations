"""Locate a moving passage episode after a stationary track prefix.

An episode start is an observation boundary, not a release time or proof that
the tracker followed one physical object throughout the track.
"""

import numpy as np


def stationary_to_motion_episode(
    points,
    crossing_time_s,
    direction,
    *,
    stationary_window_s=1.5,
    min_stationary_duration_s=0.6,
    max_stationary_range_px=4.0,
    min_moving_span_px=15.0,
    min_moving_speed_px_s=8.0,
):
    """Return evidence for the latest sustained motion onset, or ``None``.

    The pre-onset position must be stable in both x and y. The following
    observations must travel far enough in the event's longitudinal direction.
    The function deliberately makes no stone/person classification.
    """
    if direction not in ("negative_y", "positive_y"):
        raise ValueError("Direction must be negative_y or positive_y")
    if len(points) < 6:
        return None
    times = np.asarray([point["time_s"] for point in points], dtype=float)
    xy = np.asarray([point["pixel"] for point in points], dtype=float)
    if np.any(np.diff(times) <= 0):
        raise ValueError("Track times must increase")
    sign = 1 if direction == "positive_y" else -1
    best = None
    for index, time_s in enumerate(times):
        if not crossing_time_s - 1.5 <= time_s <= crossing_time_s:
            continue
        before = np.flatnonzero((times >= time_s - stationary_window_s) & (times < time_s - 0.05))
        if len(before) < 5 or times[before[-1]] - times[before[0]] < min_stationary_duration_s:
            continue
        stable = xy[before]
        if (
            np.ptp(stable[:, 0]) > max_stationary_range_px
            or np.ptp(stable[:, 1]) > max_stationary_range_px
        ):
            continue
        after = np.flatnonzero((times >= time_s) & (times <= crossing_time_s + 0.5))
        if len(after) < 5:
            continue
        travel = sign * (xy[after[-1], 1] - xy[index, 1])
        duration = times[after[-1]] - time_s
        if (
            travel < min_moving_span_px
            or duration <= 0
            or travel / duration < min_moving_speed_px_s
        ):
            continue
        # The latest valid onset excludes the largest stationary prefix while
        # leaving enough observed moving path to support the transition.
        best = {
            "onset_index": index,
            "onset_time_s": round(float(time_s), 3),
            "stationary_interval_s": [
                round(float(times[before[0]]), 3),
                round(float(times[before[-1]]), 3),
            ],
            "stationary_range_px": [
                round(float(np.ptp(stable[:, 0])), 3),
                round(float(np.ptp(stable[:, 1])), 3),
            ],
            "moving_interval_s": [round(float(time_s), 3), round(float(times[after[-1]]), 3)],
            "moving_longitudinal_span_px": round(float(travel), 3),
            "moving_mean_speed_px_s": round(float(travel / duration), 3),
            "interpretation": "observed_stationary_to_motion_transition_not_release_or_identity_proof",
        }
    return best
