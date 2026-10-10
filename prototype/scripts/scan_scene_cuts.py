"""Preserve conservative hard-cut evidence from five-hertz video frames."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from scene_cuts import scene_cut_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first scan")
    digest = file_sha256(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if not 0 <= args.start < args.end <= duration:
        parser.error("Invalid source interval")
    step = round(fps / 5)
    if step <= 0:
        parser.error("Unsupported video frame rate")
    first, last = round(args.start * fps), round(args.end * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    previous = None
    cuts = []
    samples = 0
    for index in range(first, last):
        if not cap.grab():
            raise RuntimeError(f"Decode failed at frame {index}")
        if (index - first) % step:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            raise RuntimeError(f"Retrieve failed at frame {index}")
        t = round(index / fps, 3)
        if previous is not None:
            evidence = scene_cut_evidence(previous, frame)
            if evidence["hard_cut"]:
                cuts.append({"time_s": t, **evidence})
        previous = frame
        samples += 1
    cap.release()
    result = {
        "status": "development_conservative_hard_cut_scan",
        "source_id": args.source_id,
        "source_sha256": digest,
        "source_interval_s": [args.start, args.end],
        "sample_count": samples,
        "sample_step_frames": step,
        "sample_rate_hz": fps / step,
        "min_gray_change": 45,
        "min_hist_distance": 0.35,
        "model_sha256": file_sha256(ROOT / "prototype/scene_cuts.py"),
        "runner_sha256": file_sha256(__file__),
        "cuts": cuts,
        "limitations": [
            "Hard-cut detection is conservative; soft cuts and similar-looking edits may remain.",
            "A hard cut ends within-shot identity but does not prove that objects in adjacent shots differ.",
            "A camera cut is not a throw event.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"samples": samples, "hard_cuts": len(cuts), "times_s": [row["time_s"] for row in cuts]}
        )
    )


if __name__ == "__main__":
    main()
