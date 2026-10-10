"""Observe partial house boards after shared-prefix review episodes."""

import argparse
from collections import Counter
import json
from math import ceil, floor
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from adaptive_view_reference import rebase_view_calibrator  # noqa: E402
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from post_event_partial_board import stable_view_local_stones, tail_bounds  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("video", "candidates", "source-motion", "partial-episodes", "output"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    candidates = json.loads(args.candidates.read_text())
    source_motion = json.loads(args.source_motion.read_text())
    union = json.loads(args.partial_episodes.read_text())
    if (
        source_motion["candidates_sha256"] != file_sha256(args.candidates)
        or source_motion["high_resolution_source_sha256"] != file_sha256(args.video)
        or union["source_sha256"] != candidates["source_sha256"]
        or union["source_id"] != candidates["source_id"]
        or union["frozen_candidate_count"]
        != len(candidates["events"]) + len(candidates["withheld_events"])
    ):
        parser.error("Episode, candidate, motion and source evidence differ")
    vision_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    views = json.loads(vision_path.read_text())["views"]
    refined = json.loads(rect_path.read_text())
    calibrators, original_H, clean_reference = {}, {}, {}
    for name in ("left", "right"):
        view = dict(views[name])
        if name == "right":
            view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
        cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
        cal.H = np.asarray(refined[name]["refined_H"])
        calibrators[name] = cal
        original_H[name] = cal.H.copy()
        clean_reference[name] = cal.reference.copy()
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)

    def read_time(t):
        capture.set(cv2.CAP_PROP_POS_FRAMES, round((t - source_motion["source_offset_s"]) * fps))
        ok, image = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode source time {t}")
        return image

    all_candidates = candidates["events"] + candidates["withheld_events"]
    by_id = {row["id"]: row for row in all_candidates}
    if len(by_id) != len(all_candidates):
        raise ValueError("Duplicate candidate ID")
    rows = []
    try:
        anchor_t = source_motion["right_reference_anchor_time_s"]
        calibrators["right"], anchor_registration = rebase_view_calibrator(
            calibrators["right"],
            read_time(anchor_t),
            max_corner_displacement_px=source_motion["max_corner_displacement_px"],
        )
        for episode in union["episodes"]:
            ids = episode["candidate_ids"]
            if any(pid not in by_id for pid in ids):
                raise ValueError("Episode candidate missing from source ledger")
            prefix = episode["observed_receiving_motion"]["samples"]
            if not prefix:
                raise ValueError("Partial episode has no observed path")
            first_cue = min(by_id[pid]["crossing_time_s"] for pid in ids)
            last_path = prefix[-1]["source_time_s"]
            later = [
                row["crossing_time_s"]
                for row in all_candidates
                if row["id"] not in ids and row["crossing_time_s"] > last_path
            ]
            next_candidate = min(later) if later else None
            bounds = tail_bounds(
                last_path, first_cue, next_candidate, candidates["source_interval_s"][1]
            )
            view = episode["receiving_view"]
            frames = []
            if bounds["eligible"]:
                cal = calibrators[view]
                for t in range(ceil(bounds["start_s"]), floor(bounds["stop_s"]) + 1):
                    image = read_time(t)
                    H, registration = cal.register(
                        image,
                        max_corner_displacement_px=source_motion["max_corner_displacement_px"],
                    )
                    stones = []
                    if H is not None:
                        A = np.linalg.inv(H) @ original_H[view]
                        background = cv2.warpPerspective(
                            clean_reference[view], A, (image.shape[1], image.shape[0])
                        )
                        prior = transported_reference_camera(
                            original_H[view], H, cal.view["region"]
                        )
                        found, _ = detect_and_localize(image, H, cal.view, background, prior)
                        stones = [
                            {
                                "colour": p["colour"],
                                "pixel_center": p["pixel_center"],
                                "view_local_ground_position_m": p["ground_position_m"],
                                "localization_status": p["localization"]["status"],
                            }
                            for p in found
                            if p["ground_position_m"] is not None
                            and abs(p["ground_position_m"][0]) <= 2.375
                            and abs(p["ground_position_m"][1]) <= 4.5
                        ]
                    frames.append(
                        {
                            "source_time_s": float(t),
                            "status": registration["status"],
                            "stones": stones,
                        }
                    )
            board = (
                stable_view_local_stones(frames)
                if bounds["eligible"]
                else {
                    "status": "no_quiet_tail_before_next_candidate_or_interval_end",
                    "stones": [],
                    "last_registered_s": None,
                }
            )
            rows.append(
                {
                    "episode_id": episode["episode_id"],
                    "candidate_ids": ids,
                    "receiving_view": view,
                    "path_last_observed_s": last_path,
                    "next_unassociated_passage_candidate_s": next_candidate,
                    "tail": bounds,
                    "registered_frame_count": sum(f["status"] == "registered" for f in frames),
                    "registration_abstention_count": sum(
                        f["status"] != "registered" for f in frames
                    ),
                    "board": board,
                    "coordinate_frame": {
                        "name": "receiving_camera_view_local_ice_plane",
                        "origin": "target_house_button",
                        "unit": "metres_conditional_projection",
                        "orientation_shared_across_views": False,
                        "metric_accuracy_verified": False,
                    },
                    "completeness": "unknown_from_video",
                    "post_throw_settle_verified": False,
                    "persistent_stone_ids_verified": False,
                    "simulation_ready": False,
                    "frames": frames,
                }
            )
            print(episode["episode_id"], board["status"], len(board["stones"]), flush=True)
    finally:
        capture.release()
    result = {
        "status": "postscore_partial_episode_board_diagnostic_not_complete_game_state",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "high_resolution_source_sha256": source_motion["high_resolution_source_sha256"],
        "partial_episodes_sha256": file_sha256(args.partial_episodes),
        "candidates_sha256": file_sha256(args.candidates),
        "source_motion_sha256": file_sha256(args.source_motion),
        "vision_calibration_sha256": file_sha256(vision_path),
        "rectification_sha256": file_sha256(rect_path),
        "rebase_code_sha256": file_sha256(ROOT / "prototype/adaptive_view_reference.py"),
        "body_localization_code_sha256": file_sha256(ROOT / "prototype/body_localization.py"),
        "board_code_sha256": file_sha256(ROOT / "prototype/post_event_partial_board.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "anchor_time_s": anchor_t,
        "anchor_registration": anchor_registration,
        "board_status_counts": dict(Counter(row["board"]["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Board observations follow development review episodes, not independently verified deliveries.",
            "Stable view-local cap proposals do not prove complete board, persistent identity or physical settle time.",
            "An intervening passage candidate prevents causal board attribution without further review.",
            "Metric accuracy and simulation readiness remain unverified.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["board_status_counts"])


if __name__ == "__main__":
    main()
