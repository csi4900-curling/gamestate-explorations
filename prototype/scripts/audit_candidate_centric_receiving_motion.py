"""Scan receiving-view stone motion after every passage candidate, without labels."""

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
from cache_contract import file_sha256  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def sample_times(crossing_s, source_end_s, lookahead_s, period_s=1.0):
    if period_s <= 0:
        raise ValueError("Sample period must be positive")
    end = min(source_end_s, crossing_s + lookahead_s)
    return [round(tick * period_s, 6)
            for tick in range(ceil(crossing_s / period_s),
                              floor(end / period_s) + 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--source-offset", type=float, required=True)
    parser.add_argument("--lookahead-s", type=float, default=12.0)
    parser.add_argument("--sample-period-s", type=float, default=1.0)
    parser.add_argument("--max-corner-displacement-px", type=float, default=160.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Candidate-centric motion artifact already exists")
    if args.lookahead_s <= 0:
        parser.error("Lookahead must be positive")
    if args.sample_period_s <= 0:
        parser.error("Sample period must be positive")
    source_hash = file_sha256(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development audit")
    candidates = json.loads(args.candidates.read_text())
    vision_path = ROOT / "prototype/vision/annotations/calibration.json"
    rectification_path = ROOT / "prototype/rectification/calibration.json"
    views = json.loads(vision_path.read_text())["views"]
    refined = json.loads(rectification_path.read_text())
    calibrators = {}
    for name in ("left", "right"):
        view = dict(views[name])
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
    records = []
    try:
        for candidate in candidates["events"]:
            view_name = {"positive_y": "left", "negative_y": "right"}.get(
                candidate["view_motion"])
            if view_name is None:
                raise ValueError(f"Unknown view direction for {candidate['id']}")
            calibrator = calibrators[view_name]
            samples = []
            for t in sample_times(candidate["crossing_time_s"],
                                  candidates["source_interval_s"][1], args.lookahead_s,
                                  args.sample_period_s):
                capture.set(cv2.CAP_PROP_POS_FRAMES,
                            round((t - args.source_offset) * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode source time {t}")
                H, registration = calibrator.register(
                    frame, max_corner_displacement_px=args.max_corner_displacement_px)
                proposals = []
                if H is not None:
                    A = np.array(registration["reference_to_current"])
                    background = cv2.warpPerspective(
                        calibrator.reference, A, (frame.shape[1], frame.shape[0]))
                    prior = transported_reference_camera(
                        calibrator.H, H, calibrator.view["region"])
                    found, _ = detect_and_localize(
                        frame, H, calibrator.view, background, prior)
                    proposals = [{"colour": p["colour"],
                                  "pixel_center": p["pixel_center"],
                                  "ground_position_m": p["ground_position_m"]}
                                 for p in found]
                samples.append({"source_time_s": t,
                                "registration_status": registration["status"],
                                "views": {view_name: {"proposals": proposals}}})
            kwargs = ({"view": "left", "entry_y_threshold_m": -4.5,
                       "forward_direction": 1, "min_samples": 4,
                       "max_forward_speed_change_m_s": 2.0}
                      if view_name == "left" else {"view": "right"})
            selection = select_far_entry_motion_path(
                samples, candidate["colour"],
                max_gap_s=args.sample_period_s + 0.1, **kwargs)
            records.append({"candidate_id": candidate["id"],
                            "crossing_time_s": candidate["crossing_time_s"],
                            "colour": candidate["colour"],
                            "view_motion": candidate["view_motion"],
                            "receiving_view": view_name,
                            "sample_count": len(samples),
                            "registration_abstentions": sum(
                                s["registration_status"] != "registered"
                                for s in samples),
                            "selection": selection,
                            "samples": samples})
            print(candidate["id"], selection["status"], flush=True)
    finally:
        capture.release()
    result = {
        "status": "development_candidate_centric_receiving_motion_not_independent_validation",
        "candidate_source_id": candidates["source_id"],
        "candidate_source_sha256": candidates["source_sha256"],
        "high_resolution_source_sha256": source_hash,
        "source_offset_s": args.source_offset,
        "lookahead_s": args.lookahead_s,
        "sample_period_s": args.sample_period_s,
        "max_corner_displacement_px": args.max_corner_displacement_px,
        "candidates_sha256": file_sha256(args.candidates),
        "vision_calibration_sha256": file_sha256(vision_path),
        "rectification_sha256": file_sha256(rectification_path),
        "registration_code_sha256": file_sha256(ROOT / "prototype/vision_core.py"),
        "detector_code_sha256": file_sha256(ROOT / "prototype/body_localization.py"),
        "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "runner_sha256": file_sha256(__file__),
        "candidate_count": len(records),
        "selection_status_counts": dict(Counter(
            r["selection"]["status"] for r in records)),
        "rows": records,
        "limitations": [
            "This scan uses candidate time, colour, and view direction only; it does not read reference delivery windows or labels.",
            "Geometry, motion rules, and 12-second lookahead were selected after development on this recording.",
            "A unique moving path does not independently verify physical stone identity or event truth.",
            "The high-resolution interval is a separately aligned copy of the 360p full-match candidate source.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["selection_status_counts"])


if __name__ == "__main__":
    main()
