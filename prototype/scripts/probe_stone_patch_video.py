"""Inspect a learned stone-box component on a declared video interval."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from stone_patch_detector import detect_stones, load_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier probe")
    if args.start < 0 or args.end <= args.start:
        parser.error("Invalid interval")
    digest = file_sha256(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    model = load_model(args.model)
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if args.end > duration:
        capture.release()
        parser.error("Interval exceeds readable video")
    rows = []
    for t in range(args.start, args.end):
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = capture.read()
        if not ok:
            capture.release()
            raise RuntimeError(f"Frame decode failed at {t} s")
        rows.append({"time_s": float(t), "boxes": detect_stones(frame, model)})
    capture.release()
    result = {
        "status": "development_stone_box_video_probe",
        "source_sha256": digest,
        "source_interval_s": [args.start, args.end],
        "sample_period_s": 1,
        "model_sha256": file_sha256(args.model),
        "feature_code_sha256": file_sha256(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": file_sha256(__file__),
        "frames": rows,
        "limitations": [
            "Image boxes are not confirmed moving stones or throw events.",
            "One-frame-per-second sampling can miss short appearances and fast motion.",
            "The public-box training material may not represent this broadcast camera family.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"frames": len(rows), "boxes": sum(len(row["boxes"]) for row in rows)}))


if __name__ == "__main__":
    main()
