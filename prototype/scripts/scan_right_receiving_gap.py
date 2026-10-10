"""Scan a candidate-free interval for right-view moving-stone paths without ROI triggers."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from adaptive_view_reference import rebase_view_calibrator  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from motion_path_dedup import shared_timed_observations  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def select_paths(samples, start_s, end_s, window_s=12.0, stride_s=5.0):
    windows = []
    start = start_s
    while start + window_s <= end_s + 1e-6:
        chunk = [row for row in samples if start <= row["source_time_s"] <= start + window_s]
        for colour in ("red", "yellow"):
            selection = select_far_entry_motion_path(
                chunk,
                colour,
                view="right",
                max_gap_s=0.6,
                entry_y_threshold_m=12.0,
                forward_direction=-1,
                min_samples=5,
                max_forward_speed_change_m_s=0.75,
            )
            if selection["status"] == "provisional_unique_far_entry_motion_path":
                windows.append(
                    {
                        "window_start_s": round(start, 3),
                        "window_end_s": round(start + window_s, 3),
                        "colour": colour,
                        "selection": selection,
                    }
                )
        start += stride_s
    groups = []
    for item in windows:
        path = item["selection"]["path"]
        matching = [
            group
            for group in groups
            if group[0]["colour"] == item["colour"]
            and any(
                shared_timed_observations(path, other["selection"]["path"]) >= 4 for other in group
            )
        ]
        if matching:
            matching[0].append(item)
            for duplicate in matching[1:]:
                matching[0].extend(duplicate)
                groups.remove(duplicate)
        else:
            groups.append([item])
    episodes = []
    for index, group in enumerate(
        sorted(groups, key=lambda g: min(x["selection"]["first_observation_s"] for x in g)), start=1
    ):
        representative = max(
            group,
            key=lambda row: (
                row["selection"]["sample_count"],
                row["selection"]["endpoint_displacement_m"],
            ),
        )
        episodes.append(
            {
                "episode_id": f"G{index:02d}",
                "colour": representative["colour"],
                "window_count": len(group),
                "window_starts_s": [row["window_start_s"] for row in group],
                "representative": representative,
                "physical_throw_verified": False,
            }
        )
    return windows, episodes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--source-id", required=True)
    p.add_argument("--start", type=float, required=True)
    p.add_argument("--end", type=float, required=True)
    p.add_argument("--sample-period", type=float, default=0.5)
    p.add_argument("--right-anchor-time", type=float, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.end <= a.start or a.sample_period <= 0:
        p.error("Invalid interval, sample period, or output already exists")
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    view = dict(json.loads(cfg_path.read_text())["views"]["right"])
    view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
    cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
    cal.H = np.array(json.loads(rect_path.read_text())["right"]["refined_H"])
    prior_H = cal.H.copy()
    clean_reference = cal.reference.copy()
    capture = cv2.VideoCapture(str(a.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        p.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    samples = []
    count = round((a.end - a.start) / a.sample_period)
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(a.right_anchor_time * fps))
        ok, anchor_frame = capture.read()
        if not ok:
            raise RuntimeError("Cannot decode right-camera anchor")
        cal, anchor_registration = rebase_view_calibrator(
            cal, anchor_frame, max_corner_displacement_px=160.0
        )
        for index in range(count + 1):
            t = round(a.start + index * a.sample_period, 3)
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {t}")
            H, registration = cal.register(frame, max_corner_displacement_px=160.0)
            found = []
            if H is not None:
                A = np.linalg.inv(H) @ prior_H
                background = cv2.warpPerspective(
                    clean_reference, A, (frame.shape[1], frame.shape[0])
                )
                prior = transported_reference_camera(prior_H, H, cal.view["region"])
                found, _ = detect_and_localize(frame, H, cal.view, background, prior)
            samples.append(
                {
                    "source_time_s": t,
                    "registration_status": registration["status"],
                    "views": {
                        "right": {
                            "proposals": [
                                {
                                    "colour": row["colour"],
                                    "pixel_center": row["pixel_center"],
                                    "ground_position_m": row["ground_position_m"],
                                }
                                for row in found
                            ]
                        }
                    },
                }
            )
            if (index + 1) % 25 == 0:
                print(f"sampled {index + 1}/{count + 1}", flush=True)
    finally:
        capture.release()
    windows, episodes = select_paths(samples, a.start, a.end)
    output = {
        "status": "postscore_candidate_free_right_receiver_sweep_not_throw_truth",
        "source_id": a.source_id,
        "high_resolution_source_sha256": file_sha256(a.video),
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "detector_code_sha256": file_sha256(ROOT / "prototype/body_localization.py"),
        "path_selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "source_interval_s": [a.start, a.end],
        "right_anchor_time_s": a.right_anchor_time,
        "right_anchor_registration": anchor_registration,
        "sample_period_s": a.sample_period,
        "path_window_s": 12.0,
        "path_stride_s": 5.0,
        "registration_counts": dict(Counter(row["registration_status"] for row in samples)),
        "sample_count": len(samples),
        "selected_window_count": len(windows),
        "deduplicated_episode_count": len(episodes),
        "selected_windows": windows,
        "episodes": episodes,
        "samples": samples,
        "limitations": [
            "The interval was chosen after source inspection; this is a development recall probe, not independent detection accuracy.",
            "Only the right receiving camera is scanned and the inherited conditional homography is not metrically validated.",
            "A moving coloured proposal is not a verified delivered stone; path duplication and false positives remain possible.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, indent=2) + "\n")
    print(len(samples), "samples;", len(windows), "selected windows;", len(episodes), "episodes")


if __name__ == "__main__":
    main()
