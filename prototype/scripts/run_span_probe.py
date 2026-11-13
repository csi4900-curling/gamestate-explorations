"""Run line-independent early-ROI motion-span candidate detection."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from span_passage_detection import SpanPassageDetector
from throw_detection import stone_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=float, default=1650)
    parser.add_argument("--end", type=float, default=2760)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve prior probes")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    digest = file_sha256(args.video)
    if (
        args.video.resolve() == (ROOT / "validation/unseen-end/source.mp4").resolve()
        or digest == reserved["source_sha256"]
        or any(args.source_id in row["video_url"] for row in reserved["reserved_rows"])
    ):
        parser.error("This event is reserved for independent evaluation")
    cv2.setNumThreads(1)
    detector = SpanPassageDetector()
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if not 0 <= args.start < args.end <= duration:
        raise ValueError("Invalid interval or unreadable video")
    started = time.monotonic()
    step = max(1, round(fps / 10))
    first = round(args.start * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    samples = 0
    for n in range(first, round(args.end * fps)):
        if not cap.grab():
            raise RuntimeError(f"Decode failed at {n / fps}")
        if (n - first) % step:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            raise RuntimeError("Frame retrieval failed")
        detector.update(stone_candidates(frame, detector.config), n / fps)
        samples += 1
    cap.release()
    result = {
        "status": "development_after_canada_estonia_first_score",
        "source_id": args.source_id,
        "source_sha256": digest,
        "source_interval_s": [args.start, args.end],
        "model_sha256": file_sha256(ROOT / "prototype/span_passage_detection.py"),
        "baseline_sha256": file_sha256(ROOT / "prototype/throw_detection.py"),
        "runner_sha256": file_sha256(__file__),
        "config": asdict(detector.config),
        "events": detector.events,
        "samples": samples,
        "processing_seconds": time.monotonic() - started,
        "limitations": [
            "Candidates are motion spans in the 2024 fixed left-panel ROI, not confirmed throws.",
            "Passage timestamps are observed track midpoints, not release times.",
            "Any score on the three exposed 2024 recordings is post-score development fitting.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"events": len(detector.events)}))


if __name__ == "__main__":
    main()
