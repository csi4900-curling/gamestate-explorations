"""Test panel-local motion registration on low-drift quiet-board proposals."""

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from split_panel_camera_registration import (  # noqa: E402
    camera_relative_pair,
    panel_for_pixel,
    panel_pixel,
    resize_panel,
)

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
SOURCE = BASE / "source-1080p-full-format270.mp4"
BOARDS = BASE / "full-match-partial-boards-postscore.json"
OUTPUT = BASE / "split-panel-registration-board-controls-edge-guard-v2-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def distance(first, second):
    return math.dist(first, second)


def candidate_pairs(boards):
    """Select mutually unique same-colour low-drift board observations."""
    result = []
    for board in boards["rows"]:
        frames = board.get("frames", [])
        for before, after in zip(frames, frames[1:]):
            if (
                before["status"] != "registered"
                or after["status"] != "registered"
                or not 0.9 <= after["source_time_s"] - before["source_time_s"] <= 1.1
            ):
                continue
            for first in before["stones"]:
                same_after = [
                    stone for stone in after["stones"] if stone["colour"] == first["colour"]
                ]
                same_before = [
                    stone for stone in before["stones"] if stone["colour"] == first["colour"]
                ]
                ranked = sorted(
                    same_after,
                    key=lambda stone: distance(
                        first["view_local_ground_position_m"], stone["view_local_ground_position_m"]
                    ),
                )
                if not ranked:
                    continue
                second = ranked[0]
                ground_drift = distance(
                    first["view_local_ground_position_m"], second["view_local_ground_position_m"]
                )
                if ground_drift >= 0.05:
                    continue
                if (
                    len(ranked) > 1
                    and distance(
                        first["view_local_ground_position_m"],
                        ranked[1]["view_local_ground_position_m"],
                    )
                    < 0.15
                ):
                    continue
                reverse = min(
                    same_before,
                    key=lambda stone: distance(
                        second["view_local_ground_position_m"],
                        stone["view_local_ground_position_m"],
                    ),
                )
                if reverse is not first:
                    continue
                first_pixel, second_pixel = (first["pixel_center"], second["pixel_center"])
                if panel_for_pixel(first_pixel) != panel_for_pixel(second_pixel):
                    continue
                result.append(
                    {
                        "candidate_id": board["candidate_id"],
                        "receiving_view": board["receiving_view"],
                        "colour": first["colour"],
                        "interval_s": [before["source_time_s"], after["source_time_s"]],
                        "first_pixel_1080": first_pixel,
                        "second_pixel_1080": second_pixel,
                        "conditional_ground_drift_m": round(ground_drift, 4),
                        "raw_displacement_1080_px": round(distance(first_pixel, second_pixel), 3),
                    }
                )
    return result


def selected_controls(candidates, *, high_count=30, low_count=30):
    key = lambda row: (
        row["candidate_id"],
        row["interval_s"],
        row["colour"],
        row["first_pixel_1080"],
    )
    high = sorted(
        (row for row in candidates if row["raw_displacement_1080_px"] >= 5),
        key=lambda row: (-row["raw_displacement_1080_px"], key(row)),
    )[:high_count]
    low = sorted((row for row in candidates if row["raw_displacement_1080_px"] < 1), key=key)
    indices = (
        np.linspace(0, len(low) - 1, min(low_count, len(low))).round().astype(int) if low else []
    )
    return [("high_raw_displacement", row) for row in high] + [
        ("low_raw_displacement", low[index]) for index in indices
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Board-control audit already exists")
    boards = json.loads(BOARDS.read_text())
    source_hash = digest(SOURCE)
    if source_hash != boards["high_resolution_source_sha256"]:
        raise ValueError("Board artifact and full-resolution source differ")
    candidates = candidate_pairs(boards)
    selected = selected_controls(candidates)
    cap = cv2.VideoCapture(str(SOURCE), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for group, candidate in selected:
            t0, t1 = candidate["interval_s"]
            pixel0 = candidate["first_pixel_1080"]
            pixel1 = candidate["second_pixel_1080"]
            panel = panel_for_pixel(pixel0)
            cache = {}

            def frame_at(time_s):
                index = round(time_s * fps)
                if index not in cache:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = cap.read()
                    if not ok:
                        raise ValueError(f"Frame {index} unreadable")
                    cache[index] = resize_panel(frame, panel)
                return cache[index]

            p0 = panel_pixel(pixel0, panel)
            p1 = panel_pixel(pixel1, panel)
            result = camera_relative_pair(p0, p1, t0, t1, frame_at)
            rows.append(
                {
                    **candidate,
                    "control_group": group,
                    "panel": "left" if panel == 0 else "right",
                    "raw_displacement_analysis_px": round(distance(p0, p1), 3),
                    **result,
                }
            )
            print(
                len(rows),
                group,
                candidate["candidate_id"],
                result["status"],
                result["camera_residual_px"],
                flush=True,
            )
    finally:
        cap.release()
    payload = {
        "status": "development_low_ground_drift_controls_not_stationary_truth",
        "source_sha256": source_hash,
        "boards_sha256": digest(BOARDS),
        "registration_code_sha256": digest(ROOT / "prototype/split_panel_camera_registration.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection": "Mutual nearest same-colour board observations at adjacent 1 s registered quiet-tail frames, conditional ground drift <0.05 m, next competitor >=0.15 m; top 30 raw >=5 px plus 30 deterministic raw <1 px controls.",
        "candidate_pair_count": len(candidates),
        "selected_count": len(rows),
        "group_counts": dict(Counter(r["control_group"] for r in rows)),
        "registered_count": sum(r["camera_residual_px"] is not None for r in rows),
        "rows": rows,
        "limitations": [
            "Low conditional board-position drift does not independently prove a stone remained physically stationary.",
            "Board observations and matching are development data; high raw movement can be localization jitter rather than camera motion.",
            "Sampled controls cannot establish physical throw precision, recall or F1.",
        ],
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidates": len(candidates),
                "selected": len(rows),
                "registered": payload["registered_count"],
                "groups": payload["group_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
