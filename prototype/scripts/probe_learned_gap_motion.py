"""Development probe: public-box detector plus dense video track proposals.

Its tracks are unconfirmed motion candidates, never throw events.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from gap_motion_candidates import candidates_from_observations
from stone_patch_detector import detect_stones, load_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--gap-id", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first result")
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
    observations = {"red": [], "yellow": []}
    for step in range(args.start * 5, args.end * 5):
        t = round(step / 5, 1)
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = capture.read()
        if not ok:
            capture.release()
            raise RuntimeError(f"Frame decode failed at {t} s")
        boxes = detect_stones(frame, model)
        for colour in observations:
            points = []
            for box in boxes:
                if box["colour"] != colour:
                    continue
                x, y, width, height = box["bbox"]
                points.append(
                    {
                        "pixel": [x + width / 2, y + height / 2],
                        "bbox": box["bbox"],
                        "confidence": box["confidence"],
                    }
                )
            observations[colour].append((t, points))
    capture.release()
    candidates = candidates_from_observations(
        observations,
        args.gap_id,
        [args.start, args.end],
        tracker_max_gap_s=1.6,
        tracker_max_step_px=130,
    )
    result = {
        "status": "development_learned_box_gap_motion_probe",
        "source_id": args.source_id,
        "source_sha256": digest,
        "source_interval_s": [args.start, args.end],
        "scanned_gaps": [
            {"id": args.gap_id, "interval_s": [args.start, args.end], "samples": 5 * (args.end - args.start),
             "candidate_count": len(candidates)}
        ],
        "model_sha256": file_sha256(args.model),
        "feature_code_sha256": file_sha256(ROOT / "prototype/stone_patch_detector.py"),
        "tracker_code_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
        "candidate_code_sha256": file_sha256(ROOT / "prototype/gap_motion_candidates.py"),
        "runner_sha256": file_sha256(__file__),
        "sample_period_s": 0.2,
        "tracker_max_gap_s": 1.6,
        "tracker_max_step_px_s": 130,
        "motion_candidates": candidates,
        "candidate_count": len(candidates),
        "limitations": [
            "Publisher-box classifier is not validated across this broadcast camera family.",
            "Greedy nearest-neighbour tracking can swap identity at collisions or camera changes.",
            "No candidate is confirmed as a delivered-stone event by this probe.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"samples": 5 * (args.end - args.start), "motion_candidates": len(candidates)}))


if __name__ == "__main__":
    main()
