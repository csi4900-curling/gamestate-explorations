"""Apply the experimental stone proposer to registered Canada–China sample frames."""

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
from cache_contract import file_sha256  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Stone proposal transfer artifact already exists")
    registration = json.loads(args.registration.read_text())
    if file_sha256(args.video) != registration["source_video_sha256"]:
        parser.error("Source video does not match registration audit")
    if registration["sample_count"] != len(registration["rows"]):
        parser.error("Registration audit sample count mismatch")
    vision_path = ROOT / "prototype/vision/annotations/calibration.json"
    rectification_path = ROOT / "prototype/rectification/calibration.json"
    if file_sha256(vision_path) != registration["vision_calibration_sha256"] or (
            file_sha256(rectification_path) != registration["rectification_sha256"]):
        parser.error("Calibration files differ from registration audit")
    cfg = json.loads(vision_path.read_text())["views"]
    refined = json.loads(rectification_path.read_text())
    calibrators = {}
    for name in ("left", "right"):
        view = dict(cfg[name])
        if name == "right":
            view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
        calibrator = ViewCalibrator(view, ROOT / "prototype/vision/frames")
        calibrator.H = np.array(refined[name]["refined_H"])
        calibrators[name] = calibrator
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for sample in registration["rows"]:
            clip_time = sample["source_time_s"] - registration["source_offset_s"]
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(clip_time * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source time {sample['source_time_s']}")
            row = {"reference_event_id": sample["reference_event_id"],
                   "source_time_s": sample["source_time_s"], "views": {}}
            for name, calibrator in calibrators.items():
                audit = sample["views"][name]
                if audit["status"] != "registered":
                    row["views"][name] = {"status": "abstained",
                                          "reason": "Registration rejected",
                                          "proposals": []}
                    continue
                A = np.array(audit["reference_to_current"])
                H = calibrator.H @ np.linalg.inv(A)
                background = cv2.warpPerspective(
                    calibrator.reference, A, (frame.shape[1], frame.shape[0]))
                prior = transported_reference_camera(
                    calibrator.H, H, calibrator.view["region"])
                proposals, diagnostic = detect_and_localize(
                    frame, H, calibrator.view, background, prior)
                row["views"][name] = {
                    "status": diagnostic["status"],
                    "branch": diagnostic.get("branch"),
                    "proposal_count": len(proposals),
                    "proposals": [{"colour": p["colour"],
                                   "pixel_center": p["pixel_center"],
                                   "proposal_kind": p["proposal_kind"],
                                   "ground_position_m": p["ground_position_m"],
                                   "localization_status": p["localization"]["status"],
                                   "height_intrinsics_sensitivity_m": p["localization"].get(
                                       "height_intrinsics_sensitivity_m")}
                                  for p in proposals],
                }
            rows.append(row)
    finally:
        capture.release()
    summary = {}
    for name in calibrators:
        view_rows = [row["views"][name] for row in rows]
        summary[name] = {
            "status_counts": dict(Counter(v["status"] for v in view_rows)),
            "branch_counts": dict(Counter(v.get("branch") for v in view_rows
                                          if v["status"] == "proposals")),
            "frames_with_proposals": sum(bool(v["proposals"]) for v in view_rows),
            "total_proposals": sum(len(v["proposals"]) for v in view_rows),
            "colour_counts": dict(Counter(p["colour"] for v in view_rows
                                          for p in v["proposals"])),
        }
    result = {
        "status": "development_stone_proposal_transfer_not_tracking_or_game_state",
        "source_video_sha256": registration["source_video_sha256"],
        "registration_audit_sha256": file_sha256(args.registration),
        "detector_code_sha256": file_sha256(ROOT / "prototype/body_localization.py"),
        "vision_code_sha256": file_sha256(ROOT / "prototype/vision_core.py"),
        "runner_sha256": file_sha256(__file__),
        "source_offset_s": registration["source_offset_s"],
        "sample_count": len(rows),
        "summary": summary,
        "rows": rows,
        "limitations": [
            "These are sparse still-frame proposals, not stone tracks or event detections.",
            "Colour matches do not identify the newly delivered stone among parked stones.",
            "Ground positions depend on unverified calibration and camera-height assumptions.",
            "A rejected registration produces abstention, not reuse of a prior transform.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(summary)


if __name__ == "__main__":
    main()
