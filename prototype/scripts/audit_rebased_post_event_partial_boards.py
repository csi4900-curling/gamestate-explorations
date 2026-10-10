"""Observe partial post-event boards with the selected local camera reference."""

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
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from adaptive_view_reference import rebase_view_calibrator  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from post_event_partial_board import stable_view_local_stones, tail_bounds  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--hold", type=Path, required=True)
    parser.add_argument("--source-motion", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Post-event board audit already exists")
    candidates = json.loads(args.candidates.read_text())
    screen = json.loads(args.screen.read_text())
    motion = json.loads(args.motion.read_text())
    hold = json.loads(args.hold.read_text())
    source_motion = json.loads(args.source_motion.read_text())
    if (screen["candidates_sha256"] != file_sha256(args.candidates) or
            screen["motion_sha256"] != file_sha256(args.motion) or
            motion["hold_sha256"] != file_sha256(args.hold) or
            hold["motion_sha256"] != file_sha256(args.source_motion) or
            file_sha256(args.video) != source_motion["high_resolution_source_sha256"] or
            source_motion.get("detection_background") !=
            "original_clean_reference_transported_to_current_frame" or
            screen["source_id"] != candidates["source_id"] or
            screen["source_sha256"] != candidates["source_sha256"]):
        parser.error("Candidate, screen, motion, or source-video chain differs")
    events = sorted(candidates["events"], key=lambda row: row["crossing_time_s"])
    by_motion = {row["candidate_id"]: row for row in motion["rows"]}
    if len(by_motion) != len(motion["rows"]) or (
            set(by_motion) != {event["id"] for event in events}):
        parser.error("Motion and candidate IDs differ")
    vision_path = ROOT / "prototype/vision/annotations/calibration.json"
    rectification_path = ROOT / "prototype/rectification/calibration.json"
    views = json.loads(vision_path.read_text())["views"]
    refined = json.loads(rectification_path.read_text())
    calibrators = {}
    original_H = {}
    clean_reference = {}
    for name in ("left", "right"):
        view = dict(views[name])
        if name == "right":
            view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
        cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
        cal.H = np.array(refined[name]["refined_H"])
        calibrators[name] = cal
        original_H[name] = cal.H.copy()
        clean_reference[name] = cal.reference.copy()
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        anchor_time = source_motion["right_reference_anchor_time_s"]
        capture.set(cv2.CAP_PROP_POS_FRAMES,
                    round((anchor_time - source_motion["source_offset_s"]) * fps))
        ok, anchor_frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode local anchor {anchor_time}")
        calibrators["right"], anchor_registration = rebase_view_calibrator(
            calibrators["right"], anchor_frame,
            max_corner_displacement_px=source_motion[
                "max_corner_displacement_px"])
        for event in screen["events"]:
            pid = event["id"]
            motion_row = by_motion[pid]
            path = motion_row["selection"].get("path") or []
            if not path:
                raise ValueError(f"Screened event {pid} has no motion path")
            view = motion_row["receiving_view"]
            if view != {"positive_y": "left", "negative_y": "right"}[
                    event["view_motion"]]:
                raise ValueError(f"Receiving view differs for {pid}")
            next_candidate = next((candidate["crossing_time_s"] for candidate in events
                                   if candidate["crossing_time_s"] >
                                   event["crossing_time_s"]), None)
            bounds = tail_bounds(path[-1]["source_time_s"],
                                 event["crossing_time_s"], next_candidate,
                                 candidates["source_interval_s"][1])
            frames = []
            if bounds["eligible"]:
                cal = calibrators[view]
                for t in range(ceil(bounds["start_s"]), floor(bounds["stop_s"]) + 1):
                    capture.set(cv2.CAP_PROP_POS_FRAMES,
                                round((t - source_motion["source_offset_s"]) * fps))
                    ok, image = capture.read()
                    if not ok:
                        raise RuntimeError(f"Cannot decode source time {t}")
                    H, registration = cal.register(
                        image, max_corner_displacement_px=source_motion[
                            "max_corner_displacement_px"])
                    stones = []
                    if H is not None:
                        A = np.linalg.inv(H) @ original_H[view]
                        background = cv2.warpPerspective(
                            clean_reference[view], A,
                            (image.shape[1], image.shape[0]))
                        prior = transported_reference_camera(
                            original_H[view], H, cal.view["region"])
                        found, _ = detect_and_localize(
                            image, H, cal.view, background, prior)
                        stones = [
                            {"colour": p["colour"],
                             "pixel_center": p["pixel_center"],
                             "view_local_ground_position_m": p["ground_position_m"],
                             "localization_status": p["localization"]["status"]}
                            for p in found if p["ground_position_m"] is not None and
                            abs(p["ground_position_m"][0]) <= 2.375 and
                            abs(p["ground_position_m"][1]) <= 4.5]
                    frames.append({"source_time_s": float(t),
                                   "status": registration["status"],
                                   "stones": stones})
            board = (stable_view_local_stones(frames) if bounds["eligible"] else
                     {"status": "no_quiet_tail_before_next_candidate_or_interval_end",
                      "stones": [], "last_registered_s": None})
            rows.append({
                "candidate_id": pid, "colour": event["colour"],
                "crossing_time_s": event["crossing_time_s"],
                "receiving_view": view,
                "receiving_path_last_observed_s": path[-1]["source_time_s"],
                "next_passage_candidate_time_s": next_candidate,
                "tail": bounds,
                "registered_frame_count": sum(frame["status"] == "registered"
                                              for frame in frames),
                "registration_abstention_count": sum(
                    frame["status"] != "registered" for frame in frames),
                "board": board,
                "coordinate_frame": {"name": "receiving_camera_view_local_ice_plane",
                                     "origin": "target_house_button",
                                     "unit": "metres_conditional_projection",
                                     "orientation_shared_across_views": False,
                                     "metric_accuracy_verified": False},
                "completeness": "unknown_from_video",
                "post_throw_settle_verified": False,
                "persistent_stone_ids_verified": False,
                "simulation_ready": False,
                "frames": frames,
            })
            print(pid, board["status"], len(board["stones"]), flush=True)
    finally:
        capture.release()
    result = {
        "status": "postscore_rebased_partial_board_observations_not_game_states",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "high_resolution_source_sha256": source_motion["high_resolution_source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "candidates_sha256": file_sha256(args.candidates),
        "screen_sha256": file_sha256(args.screen),
        "motion_sha256": file_sha256(args.motion),
        "hold_sha256": file_sha256(args.hold),
        "source_motion_sha256": file_sha256(args.source_motion),
        "right_reference_anchor_time_s": anchor_time,
        "right_reference_anchor_registration": anchor_registration,
        "rebase_code_sha256": file_sha256(ROOT / "prototype/adaptive_view_reference.py"),
        "vision_calibration_sha256": file_sha256(vision_path),
        "rectification_sha256": file_sha256(rectification_path),
        "board_code_sha256": file_sha256(
            ROOT / "prototype/post_event_partial_board.py"),
        "runner_sha256": file_sha256(__file__),
        "board_status_counts": dict(Counter(row["board"]["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "All boards are partial view-local observations of stable proposals, never complete game states.",
            "The quiet tail ends before the next passage candidate, even when that candidate may be false.",
            "A stable cap proposal can be a false object; physical stone identity and metric error are unverified.",
            "No exact stone settle time, complete sheet coverage, release time, or simulation-ready input is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["board_status_counts"])


if __name__ == "__main__":
    main()
