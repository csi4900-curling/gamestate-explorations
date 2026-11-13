"""Shared event -> pixel track -> camera geometry contract.

Every input event survives, including failures. Image evidence is kept separate
from correctness labels; neither successful registration nor a track is a TP.
"""

import math


def bounded_segments(points, *, max_duration_s=30, max_gap_s=1.6, max_speed_px_s=130):
    """Stop stale identity continuation and split gaps/jumps before projection."""
    if not points:
        return [], []
    segments, reasons = [[]], []
    start = points[0]["time_s"]
    for point in points:
        t = point["time_s"]
        if not math.isfinite(t) or not all(math.isfinite(x) for x in point["pixel"]):
            raise ValueError("Nonfinite trajectory observation")
        if t - start > max_duration_s:
            reasons.append("continuation_exceeds_30s_identity_horizon")
            break
        if segments[-1]:
            previous = segments[-1][-1]
            dt = t - previous["time_s"]
            if dt <= 0:
                raise ValueError("Trajectory timestamps must strictly increase")
            if dt > max_gap_s or math.dist(point["pixel"], previous["pixel"]) / dt > max_speed_px_s:
                reasons.append("observation_gap" if dt > max_gap_s else "pixel_identity_jump")
                segments.append([])
        segments[-1].append(point)
    return segments, sorted(set(reasons))


def sample_segment(points, hz=2):
    if hz <= 0:
        raise ValueError("Sampling frequency must be positive")
    selected = []
    for point in points:
        if not selected or point["time_s"] - selected[-1]["time_s"] >= 1 / hz - 1e-6:
            selected.append(point)
    if points and selected[-1] is not points[-1]:
        selected.append(points[-1])
    return selected


def summarize(events):
    """A funnel over all events, never silently conditioning on successful output."""

    def has_points(e):
        return any(len(s["pixel_points"]) >= 2 for s in e["segments"])

    def has_projection(e):
        # Require consecutive accepted samples in ONE camera segment.
        return any(
            any(
                a["top_view_m"] is not None and b["top_view_m"] is not None
                for a, b in zip(s["geometry_samples"], s["geometry_samples"][1:])
            )
            for s in e["segments"]
        )

    count = len(events)
    return {
        "event_candidates": count,
        "events_with_pixel_segment": sum(has_points(e) for e in events),
        "events_with_image_supported_top_view_segment": sum(has_projection(e) for e in events),
        "events_without_image_supported_top_view_segment": sum(
            not has_projection(e) for e in events
        ),
        "events_with_independently_verified_complete_trajectory": 0,
        "denominator": "all accepted event candidates, including event false positives",
        "interpretation": "Output availability, not trajectory precision or physical accuracy",
    }
