"""Development-only context screen for dense Beijing stone-box tracks."""

import cv2
import numpy as np


def compact_overlay_patch(frame):
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    # Only the opaque team/flag/end panel. The wider crop includes rink and
    # player background and failed when a live camera switched to overhead ice.
    return image[20:70, 65:120].astype(np.float32)


def compact_overlay_visible(frame):
    """Require the opaque blue end label and pale team panel together."""
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    end_label = hsv[55:70, 65:120]
    teams = hsv[20:54, 65:120]
    blue = (
        (end_label[:, :, 0] > 90)
        & (end_label[:, :, 0] < 135)
        & (end_label[:, :, 1] > 60)
        & (end_label[:, :, 2] < 180)
    )
    pale = (teams[:, :, 1] < 80) & (teams[:, :, 2] > 160)
    return bool(blue.mean() >= 0.7 and pale.mean() >= 0.35)


def overlay_distance(frame, template):
    patch = compact_overlay_patch(frame)
    if patch.shape != template.shape:
        raise ValueError("Score-overlay template shape mismatch")
    return float(np.abs(patch - template).mean() / 255)


def local_ice_fraction(frame, bbox):
    """Bright low-saturation ice immediately outside one proposed stone box."""
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    x, y, width, height = bbox
    center_x, center_y = x + width / 2, y + height / 2
    radius = 1.5 * max(width, height)
    left, right = max(0, int(center_x - radius)), min(640, int(center_x + radius))
    top, bottom = max(0, int(center_y - radius)), min(360, int(center_y + radius))
    if left >= right or top >= bottom:
        return 0.0
    hsv = cv2.cvtColor(image[top:bottom, left:right], cv2.COLOR_BGR2HSV)
    yy, xx = np.mgrid[top:bottom, left:right]
    outside = (np.abs(xx - center_x) > width * 0.6) | (np.abs(yy - center_y) > height * 0.6)
    ice = (hsv[:, :, 1] < 95) & (hsv[:, :, 2] > 150)
    return float(ice[outside].mean()) if outside.any() else 0.0


def longest_smooth_motion_run(points, *, max_step_px=25, max_gap_s=0.4):
    """Count moving observations in the longest continuous image-space run."""
    best = (0.0, 0)
    run_start = points[0]["time_s"]
    moving = 0
    for before, after in zip(points, points[1:]):
        step = float(np.linalg.norm(np.subtract(after["pixel"], before["pixel"])))
        if step > max_step_px or after["time_s"] - before["time_s"] > max_gap_s:
            best = max(best, (before["time_s"] - run_start, moving))
            run_start = after["time_s"]
            moving = 0
        elif step > 4:
            moving += 1
    best = max(best, (points[-1]["time_s"] - run_start, moving))
    return {"smooth_run_duration_s": round(best[0], 3), "smooth_run_moving_steps": best[1]}


def confirm_dense_gap_candidates(
    candidates,
    context_rows,
    *,
    max_overlay_distance=0.22,
    min_local_ice=0.5,
    min_moving_steps=5,
    min_live_overlay_fraction=0.6,
    join_gap_s=8,
    min_smooth_run_s=0,
    min_smooth_run_moving_steps=0,
):
    """Return provisional track decisions, retaining all withheld evidence."""
    context = {row["id"]: row for row in context_rows}
    ids = [item["id"] for item in candidates]
    if len(ids) != len(set(ids)) or set(ids) != set(context):
        raise ValueError("Candidate/context IDs differ")
    decisions = {}
    eligible = []
    for item in candidates:
        row = context[item["id"]]
        if row["live_overlay_sample_fraction"] < min_live_overlay_fraction:
            reason = "compact_live_overlay_absent"
        elif row["median_overlay_distance"] > max_overlay_distance:
            reason = "live_overlay_not_supported"
        elif row["median_local_ice_fraction"] < min_local_ice:
            reason = "stone_not_locally_surrounded_by_ice"
        elif row["moving_steps_gt4px"] < min_moving_steps:
            reason = "insufficient_sustained_motion"
        elif (
            row["smooth_run_duration_s"] < min_smooth_run_s
            or row["smooth_run_moving_steps"] < min_smooth_run_moving_steps
        ):
            reason = "insufficient_smooth_motion"
        else:
            eligible.append(item)
            continue
        decisions[item["id"]] = {"id": item["id"], "status": "withheld", "reason": reason}
    eligible.sort(key=lambda item: (item["evidence_interval_s"][0], item["id"]))
    groups = []
    for item in eligible:
        start, end = item["evidence_interval_s"]
        if groups and start <= groups[-1]["end"] + join_gap_s:
            groups[-1]["items"].append(item)
            groups[-1]["end"] = max(groups[-1]["end"], end)
        else:
            groups.append({"items": [item], "end": end})
    for group in groups:
        chosen = min(
            group["items"],
            key=lambda item: (
                item["evidence_interval_s"][0],
                -context[item["id"]]["net_displacement_px"],
                item["id"],
            ),
        )
        for item in group["items"]:
            decisions[item["id"]] = {
                "id": item["id"],
                "status": "corroborated_gap_candidate"
                if item["id"] == chosen["id"]
                else "withheld",
                "reason": "earliest_local_ice_motion_in_episode"
                if item["id"] == chosen["id"]
                else "same_motion_episode",
                "episode_anchor_id": chosen["id"],
            }
    return [dict(decisions[item["id"]], **context[item["id"]]) for item in candidates]
