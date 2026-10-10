"""Development-only gate ablation on identical decoded frames; no reference labels.

Preserves the frozen detector and archived outputs. Larger image y means earlier
on this outgoing view. Gate times are never treated as release times.
"""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cache_contract import file_sha256
from throw_detection import PassageConfig, PassageDetector, stone_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=float, default=1650)
    parser.add_argument("--end", type=float, default=2760)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must not exist; preserve earlier experiments.")
    source = ROOT / "sources/canada-korea-2024-360p.mp4"
    cap = cv2.VideoCapture(str(source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if not cap.isOpened() or not 0 <= args.start < args.end <= duration:
        parser.error("Invalid video or interval")
    configs = [PassageConfig(gate_y=y) for y in (60, 75, 90)]
    detectors = [PassageDetector(c) for c in configs]
    # Identical ROI and proposals isolate the effect of moving the trigger.
    step = max(1, round(fps / 10))
    first = round(args.start * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    started = time.monotonic()
    samples = 0
    for n in range(first, round(args.end * fps)):
        if not cap.grab():
            raise RuntimeError(f"Decode failed at frame {n}")
        if (n - first) % step:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            raise RuntimeError(f"Retrieval failed at frame {n}")
        candidates = stone_candidates(frame, configs[0])
        for detector in detectors:
            detector.update(candidates, n / fps)
        samples += 1
    cap.release()
    baseline = {e["track_id"]: e for e in detectors[0].events}
    runs = []
    for detector in detectors:
        paths = detector.trajectories()
        rows = []
        for event in detector.events:
            track = paths[event["track_id"]]
            old = baseline.get(event["track_id"])
            rows.append(
                dict(
                    event,
                    trajectory=track,
                    baseline_event_id=old["id"] if old else None,
                    earlier_than_baseline_s=(old["crossing_time_s"] - event["crossing_time_s"])
                    if old
                    else None,
                    first_observed_s=track[0]["time_s"],
                    last_observed_s=track[-1]["time_s"],
                    confirmation_delay_s=event["confirmed_at_s"] - event["crossing_time_s"],
                )
            )
        advances = [r["earlier_than_baseline_s"] for r in rows if r["baseline_event_id"]]
        matched = {r["baseline_event_id"] for r in rows}
        runs.append(
            {
                "config": asdict(detector.config),
                "events": rows,
                "event_count": len(rows),
                "baseline_tracks_not_emitted": [
                    e["id"] for e in baseline.values() if e["id"] not in matched
                ],
                "additional_track_ids": [
                    r["track_id"] for r in rows if r["baseline_event_id"] is None
                ],
                "median_earlier_crossing_s": float(np.median(advances)) if advances else None,
            }
        )
    result = {
        "status": "development_ablation_not_independent_accuracy",
        "source_sha256": file_sha256(source),
        "model_sha256": file_sha256(ROOT / "throw_detection.py"),
        "runner_sha256": file_sha256(__file__),
        "source_interval_s": [args.start, args.end],
        "samples": samples,
        "sample_rate_hz": fps / step,
        "processing_seconds": time.monotonic() - started,
        "runs": runs,
        "interpretation": [
            "Track IDs are comparable only because proposal generation and association are identical.",
            "Additional or missing emissions are disagreements with baseline, not measured false positives or misses.",
            "No new gate-specific reference labels were used. Old y=60 timing labels cannot score other gates.",
            "A changed trigger does not extend a matched track or reduce its cross-camera observation gap.",
            "Full track history is retained before confirmation; release_time_s remains null.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            [
                {
                    k: r[k]
                    for k in (
                        "event_count",
                        "baseline_tracks_not_emitted",
                        "additional_track_ids",
                        "median_earlier_crossing_s",
                    )
                }
                for r in runs
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
