"""Development screen for visual candidates across unsupported Beijing views."""

import cv2
import numpy as np


def ice_scene_fraction(frame):
    """Fraction of the non-overlay frame resembling bright low-saturation ice."""
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    area = hsv[70:360]
    return float(np.mean((area[:, :, 1] < 95) & (area[:, :, 2] > 150)))


def confirm_gap_episodes(candidates, context_rows, *, min_ice_fraction=0.25, join_gap_s=8):
    """Return one provisional passage per plausible motion episode.

    This is a development rule, not a validated throw detector. Rejected
    tracks remain in the returned decisions with their reasons.
    """
    context = {row["id"]: row for row in context_rows}
    ids = [item["id"] for item in candidates]
    if len(ids) != len(set(ids)) or set(ids) != set(context):
        raise ValueError("Candidate/context ID mismatch")
    ordered = sorted(candidates, key=lambda item: (item["crossing_time_s"], item["id"]))
    decisions = {}
    eligible = []
    for item in ordered:
        fraction = context[item["id"]]["median_ice_scene_fraction"]
        if fraction < min_ice_fraction:
            decisions[item["id"]] = {
                "id": item["id"],
                "status": "withheld",
                "reason": "non_ice_scene",
                "median_ice_scene_fraction": fraction,
            }
        else:
            eligible.append(item)
    groups = []
    for item in eligible:
        start, end = item["evidence_interval_s"]
        if groups and start <= groups[-1]["latest_end_s"] + join_gap_s:
            groups[-1]["items"].append(item)
            groups[-1]["latest_end_s"] = max(groups[-1]["latest_end_s"], end)
        else:
            groups.append({"items": [item], "latest_end_s": end})
    for group in groups:
        items = group["items"]
        first_time = items[0]["crossing_time_s"]
        near_first = [item for item in items if item["crossing_time_s"] - first_time <= 2]
        if len({item["colour"] for item in near_first}) > 1:
            for item in items:
                decisions[item["id"]] = {
                    "id": item["id"],
                    "status": "withheld",
                    "reason": "ambiguous_simultaneous_colours",
                    "median_ice_scene_fraction": context[item["id"]]["median_ice_scene_fraction"],
                }
            continue
        chosen = sorted(
            near_first,
            key=lambda item: (
                -(item["evidence_interval_s"][1] - item["evidence_interval_s"][0]),
                item["id"],
            ),
        )[0]
        for item in items:
            decisions[item["id"]] = {
                "id": item["id"],
                "status": "corroborated_gap_candidate"
                if item["id"] == chosen["id"]
                else "withheld",
                "reason": "earliest_ice_motion_in_episode"
                if item["id"] == chosen["id"]
                else "same_motion_episode",
                "episode_anchor_id": chosen["id"],
                "median_ice_scene_fraction": context[item["id"]]["median_ice_scene_fraction"],
            }
    return [decisions[item["id"]] for item in candidates]
