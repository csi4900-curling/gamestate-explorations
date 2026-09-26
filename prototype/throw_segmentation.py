"""Review segmentation and conservative visible-scene settling evidence.
Physical completion and cross-camera identity remain unverified.
"""

import math


def review_segments(events, source_start, source_end):
    events = sorted(events, key=lambda e: e["crossing_time_s"])
    if (
        not all(math.isfinite(t) for t in [source_start, source_end])
        or not source_start < source_end
    ):
        raise ValueError("Invalid source interval")
    times = [e["crossing_time_s"] for e in events]
    if any(not math.isfinite(t) or not source_start <= t < source_end for t in times):
        raise ValueError("Passage outside source")
    if len(set(times)) != len(times):
        raise ValueError("Duplicate passage time")
    return [
        {
            "id": e["id"],
            "start_s": e["crossing_time_s"],
            "end_s": times[i + 1] if i + 1 < len(times) else source_end,
            "end_reason": "next_passage" if i + 1 < len(times) else "source_end",
            "physical_end_s": None,
        }
        for i, e in enumerate(events)
    ]


def visible_settling(segment):
    outcome = segment["outcome"]
    settled = outcome.get("settled")
    if not settled:
        return {
            "status": "unavailable",
            "reason": "No associated delivered-stone settling candidate.",
        }
    rows = segment["timeline"]["records"]
    start = segment["timeline"]["source_start_s"]
    tid = outcome["track_id"]
    colour = segment["event"]["colour"]
    for i, row in enumerate(rows):
        end = start + row["time_s"]
        if end < settled["time_s"]:
            continue
        win = rows[max(0, i - 4) : i + 1]
        if len(win) != 5 or abs((win[-1]["time_s"] - win[0]["time_s"]) - 2) > 0.01:
            continue
        if any(not 0 < b["time_s"] - a["time_s"] <= 0.51 for a, b in zip(win, win[1:])):
            continue
        views = [r["views"]["right"] for r in win]
        if any(v.get("H") is None for v in views):
            continue
        if any(
            len(s["pixel_center"]) != 2 or not all(math.isfinite(x) for x in s["pixel_center"])
            for v in views
            for s in v["stones"]
        ):
            continue
        maps = [{(s["colour"], s["track_id"]): s for s in v["stones"]} for v in views]
        if any(len(m) != len(v["stones"]) for m, v in zip(maps, views)):
            continue
        keys = set(maps[0])
        if (colour, tid) not in keys or any(set(m) != keys for m in maps[1:]):
            continue
        # Every visible proposal must persist and remain within three image pixels.
        if any(
            max(math.dist(m[k]["pixel_center"], maps[0][k]["pixel_center"]) for m in maps) > 3
            for k in keys
        ):
            continue
        return {
            "status": "visible_scene_stable_candidate",
            "confirmed_at_s": end,
            "window_s": [start + win[0]["time_s"], end],
            "visible_stone_count": len(keys),
            "physical_completion_verified": False,
            "reason": "Same visible track set for 2 seconds, every displacement <=3 px. Hidden or undetected stones remain unknown.",
        }
    return {
        "status": "unavailable",
        "reason": "No uninterrupted stable set of visible tracks after delivered-stone settling.",
    }
