"""Development-only agreement between public-box and colour-cap tracks."""

from statistics import median
from math import dist


def cross_channel_pairs(learned, learned_decisions, caps, cap_decisions):
    """Find same-colour, time-aligned visual tracks with independent boxes."""
    learned_context = {row["id"]: row for row in learned_decisions}
    cap_context_by_id = {row["id"]: row for row in cap_decisions}
    if set(learned_context) != {row["id"] for row in learned}:
        raise ValueError("Learned candidate/context IDs differ")
    if set(cap_context_by_id) != {row["id"] for row in caps}:
        raise ValueError("Cap candidate/context IDs differ")
    pairs = []
    for box in learned:
        box_context = learned_context[box["id"]]
        if (box_context["moving_steps_gt4px"] < 5
                or box_context["live_overlay_sample_fraction"] < 0.6):
            continue
        positions = {round(point["time_s"], 1): point["pixel"]
                     for point in box["visual_track_points"]}
        for cap in caps:
            cap_context = cap_context_by_id[cap["id"]]
            if (cap["colour"] != box["colour"]
                    or cap_context["moving_steps_gt4px"] < 5
                    or cap_context["median_local_ice_fraction"] < 0.7
                    or cap_context["live_overlay_sample_fraction"] < 0.6):
                continue
            offsets = [
                dist(positions[round(point["time_s"], 1)], point["pixel"])
                for point in cap["visual_track_points"]
                if round(point["time_s"], 1) in positions
            ]
            if len(offsets) >= 8 and median(offsets) <= 15:
                pairs.append({
                    "learned_id": box["id"], "cap_id": cap["id"],
                    "colour": box["colour"], "crossing_time_s": cap["crossing_time_s"],
                    "shared_frames": len(offsets),
                    "median_position_difference_px": round(median(offsets), 3),
                })
    return sorted(pairs, key=lambda row: (row["crossing_time_s"],
                                          -row["shared_frames"], row["learned_id"]))
