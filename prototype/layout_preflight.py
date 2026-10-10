"""Conservative source-layout routing for two development broadcast families.

This checks visible production features, not whether every throw is observable.
An unknown or mixed interval must not silently inherit a detector's geometry.
"""

import cv2
import numpy as np

from broadcast_scoreboard import read_beijing_counts


def split_2024_signature(left_pale, left_bright, right_blue):
    """Recognize the fixed split view across normal and darker scoreboards."""
    return bool(
        (left_pale > 0.80 and left_bright > 0.65 and right_blue > 0.50)
        or (left_pale > 0.90 and left_bright > 0.85 and right_blue > 0.40)
    )


def frame_evidence(frame):
    """Return two layout indicators for one BGR source frame."""
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    left = hsv[15:80, 30:280]
    right = hsv[15:80, 350:570]
    left_pale = float(np.mean(left[:, :, 1] < 70))
    left_bright = float(np.mean(left[:, :, 2] > 150))
    right_blue = float(
        np.mean((right[:, :, 0] > 90) & (right[:, :, 0] < 135) & (right[:, :, 1] > 60))
    )
    return {
        "split_2024_signature": split_2024_signature(left_pale, left_bright, right_blue),
        "beijing_2022_counter": read_beijing_counts(frame) is not None,
        "left_pale_fraction": round(left_pale, 4),
        "left_bright_fraction": round(left_bright, 4),
        "right_blue_fraction": round(right_blue, 4),
    }


def classify_chunk(samples):
    """Require repeated layout evidence rather than trusting a single frame."""
    if len(samples) < 6:
        return "unknown"
    split = sum(row["split_2024_signature"] for row in samples) / len(samples)
    beijing = sum(row["beijing_2022_counter"] for row in samples) / len(samples)
    beijing_only = sum(row["beijing_2022_counter"] and
                       not row["split_2024_signature"] for row in samples)
    # The Beijing digit reader occasionally matches a 2024 scoreboard frame.
    # A single dual-positive sample cannot overrule a sustained split signature;
    # a Beijing-only sample or repeated conflict still fails closed.
    if split >= 0.75 and beijing_only == 0 and sum(
            row["beijing_2022_counter"] for row in samples) <= 1:
        return "split_2024"
    if beijing >= 0.25 and split <= 0.10:
        return "beijing_2022"
    return "unknown"


def summarize_evidence(samples, start_s, end_s, *, chunk_s=300):
    """Return a route only when every sampled chunk agrees."""
    if not start_s < end_s or chunk_s <= 0:
        raise ValueError("Invalid interval or chunk size")
    chunks = []
    position = float(start_s)
    while position < end_s:
        boundary = min(position + chunk_s, end_s)
        if 0 < end_s - boundary < 60:
            boundary = float(end_s)
        rows = [row for row in samples if position <= row["time_s"] < boundary]
        kind = classify_chunk(rows)
        chunks.append(
            {
                "interval_s": [position, boundary],
                "samples": len(rows),
                "split_signature_count": sum(row["split_2024_signature"] for row in rows),
                "beijing_counter_count": sum(row["beijing_2022_counter"] for row in rows),
                "layout": kind,
            }
        )
        position = boundary
    kinds = {chunk["layout"] for chunk in chunks}
    route = next(iter(kinds)) if len(kinds) == 1 and "unknown" not in kinds else "unknown"
    runs = []
    for chunk in chunks:
        kind = chunk["layout"]
        start, end = chunk["interval_s"]
        if runs and runs[-1]["layout"] == kind:
            runs[-1]["interval_s"][1] = end
            runs[-1]["samples"] += chunk["samples"]
        else:
            runs.append({"layout": kind, "interval_s": [start, end], "samples": chunk["samples"]})
    return {
        "layout": route,
        "chunks": chunks,
        "runs": runs,
        "coverage_gaps_s": [row["interval_s"] for row in runs if row["layout"] == "unknown"],
    }
