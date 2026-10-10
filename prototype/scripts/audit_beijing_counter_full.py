"""Scan the verified Beijing overlay every second across one source interval.

This coverage audit records visible and unreadable frames and stable counter
decrements. It intentionally does not perform visual fallback or claim that
unreadable spans contain no throws.
"""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from broadcast_scoreboard import ScoreboardEvents, read_beijing_counts
from cache_contract import file_sha256


def visibility_runs(samples):
    runs = []
    for row in samples:
        visible = row["counts"] is not None
        if runs and runs[-1]["visible"] == visible and runs[-1]["interval_s"][1] == row["time_s"]:
            runs[-1]["interval_s"][1] = row["time_s"] + 1
            runs[-1]["samples"] += 1
        else:
            runs.append(
                {"visible": visible, "interval_s": [row["time_s"], row["time_s"] + 1], "samples": 1}
            )
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first audit")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    digest = file_sha256(args.video)
    if digest == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if not 0 <= args.start < args.end <= duration:
        cap.release()
        parser.error("Invalid source interval")
    tracker = ScoreboardEvents()
    samples = []
    for second in range(args.start, args.end):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
        ok, frame = cap.read()
        if not ok:
            cap.release()
            raise RuntimeError(f"Frame decode failed at {second} s")
        counts = read_beijing_counts(frame)
        tracker.update(counts, float(second))
        samples.append({"time_s": second, "counts": list(counts) if counts is not None else None})
    cap.release()
    runs = visibility_runs(samples)
    result = {
        "status": "development_continuous_beijing_counter_coverage_audit",
        "source_id": args.source_id,
        "source_sha256": digest,
        "source_interval_s": [args.start, args.end],
        "sample_period_s": 1,
        "counter_model_sha256": file_sha256(ROOT / "prototype/broadcast_scoreboard.py"),
        "runner_sha256": file_sha256(__file__),
        "sample_count": len(samples),
        "visible_sample_count": tracker.visible_samples,
        "visibility_runs": runs,
        "counter_samples": samples,
        "counter_events": tracker.events,
        "unresolved_counter_changes": tracker.unresolved,
        "terminal_counter_state": asdict(tracker.state) if tracker.state else None,
        "limitations": [
            "A readable graphic is broadcast evidence, not proof of continuous live-video coverage.",
            "Unreadable seconds cannot be certified throw-free.",
            "Counter decrements confirm a delivery but do not measure release time or motion.",
            "The reader applies only to the development Beijing 2022 overlay at 640x360.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "samples": len(samples),
                "visible": tracker.visible_samples,
                "events": len(tracker.events),
                "unresolved": len(tracker.unresolved),
                "visibility_runs": len(runs),
            }
        )
    )


if __name__ == "__main__":
    main()
