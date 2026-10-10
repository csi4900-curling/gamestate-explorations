"""Check the source layout near every event in a partial throw timeline."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from layout_preflight import frame_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier audits")
    timeline = json.loads(args.timeline.read_text())
    if file_sha256(args.video) != timeline["source_sha256"]:
        parser.error("Video fingerprint differs from timeline")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        parser.error("Cannot open video")
    runs = {row["id"]: row for row in timeline["supported_runs"]}
    rows = []
    for event in timeline["observed_events"]:
        run = runs[event["source_run_id"]]
        samples = []
        for offset in (-1.0, 0.0, 1.0):
            t = event["crossing_time_s"] + offset
            if not run["interval_s"][0] <= t < run["interval_s"][1]:
                continue
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {t:.3f} seconds")
            evidence = frame_evidence(frame)
            samples.append({"time_s": round(t, 3), **evidence})
        key = "split_2024_signature" if run["layout"] == "split_2024" else "beijing_2022_counter"
        matching = sum(row[key] for row in samples)
        rows.append(
            {
                "event_id": event["id"],
                "crossing_time_s": event["crossing_time_s"],
                "source_run_id": event["source_run_id"],
                "expected_layout": run["layout"],
                "matching_samples": matching,
                "sample_count": len(samples),
                "layout_review_required": matching == 0,
                "samples": samples,
            }
        )
    cap.release()
    result = {
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": timeline["source_interval_s"],
        "timeline_sha256": file_sha256(args.timeline),
        "preflight_code_sha256": file_sha256(ROOT / "prototype/layout_preflight.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "event_count": len(rows),
        "layout_review_count": sum(row["layout_review_required"] for row in rows),
        "events": rows,
        "limitations": [
            "Three sampled frames are not continuous coverage.",
            "A failed layout signature does not prove a false throw.",
            "A matching signature does not prove a true throw.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "event_count": result["event_count"],
                "layout_review_count": result["layout_review_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
