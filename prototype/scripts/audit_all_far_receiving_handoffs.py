"""Scan all split-view throw gaps in the far receiving camera, without linking identity."""

import argparse
from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from cross_view import rink_position  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def digest(path):
    h = sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sample_times(start_s, end_s):
    if not start_s < end_s:
        raise ValueError("Invalid gap interval")
    times = {round(start_s, 3), round(end_s, 3)}
    times.update(tick / 2 for tick in range(ceil(start_s * 2),
                                            floor(end_s * 2) + 1))
    return sorted(times)


def corridor_candidates(detections, colour, departure_world, arrival_world):
    """Keep candidates in a wide endpoint corridor, retaining multiplicity."""
    x0, y0 = departure_world
    x1, y1 = arrival_world
    rows = []
    for detection in detections:
        if detection["colour"] != colour or detection["ground_position_m"] is None:
            continue
        world = rink_position(detection["ground_position_m"], "receiving")
        x, y = world
        if min(x0, x1) - 1.0 <= x <= max(x0, x1) + 1.0 and (
                y0 - 1.0 <= y <= y1 + 1.0):
            rows.append({"pixel": detection["pixel_center"],
                         "world_m": world,
                         "local_m": detection["ground_position_m"]})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="*", help="Optional throw IDs for a pilot")
    parser.add_argument("--video", type=Path,
                        default=ROOT / "throw-analysis/end3.mp4")
    parser.add_argument("--source-offset", type=float, default=1650.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Far receiving audit already exists")
    video_path = args.video
    results_path = ROOT / "cross-view/results.json"
    vision_path = ROOT / "vision/annotations/calibration.json"
    rectify_path = ROOT / "rectification/calibration.json"
    results = json.loads(results_path.read_text())
    events = results["throws"]
    if args.ids:
        selected = set(args.ids)
        events = [event for event in events if event["id"] in selected]
        if {event["id"] for event in events} != selected:
            parser.error("Unknown throw ID")
    cfg = json.loads(vision_path.read_text())["views"]["right"]
    cfg = dict(cfg, world_bounds=[-2.375, -1.975, 2.375, 22.0])
    calibrator = ViewCalibrator(cfg, ROOT / "vision/frames")
    calibrator.H = np.array(json.loads(rectify_path.read_text())["right"]["refined_H"])
    capture = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open source clip")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for event in events:
            departure = event["departure"][-1]
            arrival = event["arrival"][0]
            start, end = departure["time_s"], arrival["time_s"]
            samples = []
            for source_time in sample_times(start, end):
                clip_time = source_time - args.source_offset
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(clip_time * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode source time {source_time}")
                H, registration = calibrator.register(frame)
                candidates = []
                if H is not None:
                    reference = cv2.warpPerspective(
                        calibrator.reference,
                        np.array(registration["reference_to_current"]),
                        (frame.shape[1], frame.shape[0]))
                    prior = transported_reference_camera(calibrator.H, H, cfg["region"])
                    detections, _ = detect_and_localize(frame, H, cfg, reference, prior)
                    candidates = corridor_candidates(
                        detections, event["colour"], departure["world_m"],
                        arrival["world_m"])
                samples.append({"source_time_s": source_time,
                                "registration_status": registration["status"],
                                "corridor_candidate_count": len(candidates),
                                "corridor_candidates": candidates})
            rows.append({"throw_id": event["id"], "colour": event["colour"],
                         "departure_last": {"time_s": start,
                                            "world_m": departure["world_m"]},
                         "arrival_first": {"time_s": end,
                                           "world_m": arrival["world_m"]},
                         "samples": samples,
                         "unique_sample_count": sum(
                             sample["corridor_candidate_count"] == 1
                             for sample in samples),
                         "ambiguous_sample_count": sum(
                             sample["corridor_candidate_count"] > 1
                             for sample in samples)})
    finally:
        capture.release()
    result = {
        "status": "development_far_receiving_candidate_scan_not_identity_validation",
        "source_clip_sha256": digest(video_path),
        "cross_view_results_sha256": digest(results_path),
        "vision_calibration_sha256": digest(vision_path),
        "rectification_sha256": digest(rectify_path),
        "detector_code_sha256": digest(ROOT / "body_localization.py"),
        "runner_sha256": digest(__file__),
        "source_offset_s": args.source_offset,
        "expanded_right_world_bounds_m": cfg["world_bounds"],
        "throw_count": len(rows),
        "rows": rows,
        "limitations": [
            "Corridor uses endpoints of provisional cross-view links; it is a postscore diagnostic.",
            "Unique same-colour detection in a frame is not persistent physical stone identity.",
            "Far-range receiving homography has no independent metric-accuracy validation.",
            "Unobserved intervals and candidate ambiguity remain explicit; no trajectory is interpolated.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print({"throws": len(rows),
           "unique_samples": sum(row["unique_sample_count"] for row in rows),
           "ambiguous_samples": sum(row["ambiguous_sample_count"] for row in rows)})


if __name__ == "__main__":
    main()
