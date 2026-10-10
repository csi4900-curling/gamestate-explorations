"""Check whether a calibrated split-view camera registers on another recording."""

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
from cache_contract import file_sha256  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--source-offset", type=float, required=True)
    parser.add_argument("--max-corner-displacement-px", type=float, default=120)
    parser.add_argument("--ids", nargs="*", help="Optional reference event IDs")
    parser.add_argument("--sample-period-s", type=float,
                        help="Sample each selected interval at this period instead of three frames")
    parser.add_argument("--extend-end-s", type=float,
                        help="Extend a single selected window to this source time")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Registration transfer artifact already exists")
    reference = json.loads(args.reference.read_text())
    if args.sample_period_s is not None and args.sample_period_s <= 0:
        parser.error("Sample period must be positive")
    events = reference["events"]
    if args.ids:
        selected = set(args.ids)
        events = [event for event in events if event["id"] in selected]
        if {event["id"] for event in events} != selected:
            parser.error("Unknown reference event ID")
    if args.extend_end_s is not None and len(events) != 1:
        parser.error("End extension requires exactly one selected event")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    source_hash = file_sha256(args.video)
    if source_hash == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development transfer")
    vision_path = ROOT / "prototype/vision/annotations/calibration.json"
    rectification_path = ROOT / "prototype/rectification/calibration.json"
    views = json.loads(vision_path.read_text())["views"]
    refined = json.loads(rectification_path.read_text())
    calibrators = {}
    for name in ("left", "right"):
        calibrator = ViewCalibrator(views[name], ROOT / "prototype/vision/frames")
        calibrator.H = np.array(refined[name]["refined_H"])
        calibrators[name] = calibrator
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for event in events:
            start, end = event["delivery_interval_s"]
            if args.extend_end_s is not None:
                if args.extend_end_s <= end:
                    parser.error("Extended end must follow the reference window")
                end = args.extend_end_s
            if args.sample_period_s is None:
                times = (start, (start + end) / 2, end)
            else:
                period = args.sample_period_s
                times = sorted({start, end} | {
                    round(tick * period, 6)
                    for tick in range(ceil(start / period), floor(end / period) + 1)})
            for source_time in times:
                clip_time = source_time - args.source_offset
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(clip_time * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode source time {source_time}")
                row = {"reference_event_id": event["id"],
                       "source_time_s": source_time, "views": {}}
                for name, calibrator in calibrators.items():
                    _, registration = calibrator.register(
                        frame, max_corner_displacement_px=args.max_corner_displacement_px)
                    row["views"][name] = registration
                rows.append(row)
    finally:
        capture.release()
    counts = {name: dict(Counter(row["views"][name]["status"]
                                 for row in rows)) for name in calibrators}
    result = {
        "status": "development_calibration_registration_transfer_not_metric_validation",
        "source_video_sha256": source_hash,
        "source_offset_s": args.source_offset,
        "max_corner_displacement_px": args.max_corner_displacement_px,
        "sample_period_s": args.sample_period_s,
        "extended_end_s": args.extend_end_s,
        "selected_reference_event_ids": [event["id"] for event in events],
        "reference_sha256": file_sha256(args.reference),
        "vision_calibration_sha256": file_sha256(vision_path),
        "rectification_sha256": file_sha256(rectification_path),
        "registration_code_sha256": file_sha256(ROOT / "prototype/vision_core.py"),
        "runner_sha256": file_sha256(__file__),
        "sample_count": len(rows),
        "registration_status_counts": counts,
        "rows": rows,
        "limitations": [
            "Reference delivery windows are coarse agent-authored source review, not independent truth.",
            "Feature registration does not establish physical metric accuracy or stone identity.",
            "A rejected view cannot inherit the prior match's homography.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(counts)


if __name__ == "__main__":
    main()
