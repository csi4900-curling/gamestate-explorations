"""Conservative same-view cap continuation beyond the early detection ROI."""

import math
import statistics


def next_observation(path, detections, time_s, *, max_distance_px=13,
                     min_second_best_margin_px=5):
    """Return a unique nearby candidate or an explicit reason to stop.

    This is image association, never a physical stone-identity assertion.
    `detections` must already be limited to the seed path's colour.
    """
    if not path or time_s <= path[-1]["time_s"]:
        raise ValueError("Continuation requires a later source time")
    last = path[-1]
    velocities = []
    recent = path[-4:]
    for first, second in zip(recent, recent[1:]):
        dt = second["time_s"] - first["time_s"]
        if dt > 0:
            velocities.append([(second["pixel"][axis] - first["pixel"][axis]) / dt
                               for axis in (0, 1)])
    vx = statistics.median(v[0] for v in velocities) if velocities else 0
    vy = statistics.median(v[1] for v in velocities) if velocities else 0
    dt = time_s - last["time_s"]
    predicted = [last["pixel"][0] + vx * dt,
                 last["pixel"][1] + vy * dt]
    ranked = sorted(((math.dist(candidate["pixel"], predicted), candidate)
                     for candidate in detections), key=lambda pair: pair[0])
    if not ranked or ranked[0][0] > max_distance_px:
        return None, "no_nearby_same_colour_cap"
    if (len(ranked) > 1 and
            ranked[1][0] - ranked[0][0] < min_second_best_margin_px):
        return None, "ambiguous_nearby_caps"
    chosen = ranked[0][1]
    return {**chosen, "time_s": time_s,
            "prediction_distance_px": round(ranked[0][0], 3)}, "continued"
