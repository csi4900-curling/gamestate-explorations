#!/usr/bin/env python3
"""Five-second source-frame ice-motion diagnostic for static-left intervals.

The lower right-panel region is an image activity cue, not a stone detector.
The ROI and threshold were selected after inspecting exposed Italy and Latvia
intervals; this audit is development evidence only.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROI_XYXY = [330, 230, 630, 325]
SAMPLE_PERIOD_S = 5
EDGE_EXCLUSION_S = 20
ACTIVE_MAE_THRESHOLD = 3.0


def digest(path):
    hasher = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def audit(video, activity):
    video_hash = digest(video)
    if video_hash != activity["source_sha256"]:
        raise ValueError("Source video does not match activity audit")
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    x0, y0, x1, y1 = ROI_XYXY
    results = []
    try:
        for interval in activity["newly_unsupported_intervals"]:
            start, stop = interval["interval_s"]
            if start != int(start) or stop != int(stop):
                raise ValueError("Expected integer-second source interval")
            times = list(range(int(start), int(stop) + 1, SAMPLE_PERIOD_S))
            prior = None
            pairs = []
            for time_s in times:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Cannot decode 640×360 frame at {time_s} s")
                crop = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
                if prior is not None:
                    mae = float(np.mean(cv2.absdiff(crop, prior)))
                    pairs.append(
                        {
                            "second_frame_time_s": time_s,
                            "lower_ice_mae": round(mae, 5),
                            "within_interior": start + EDGE_EXCLUSION_S
                            <= time_s
                            <= stop - EDGE_EXCLUSION_S,
                        }
                    )
                prior = crop
            interior = [row["lower_ice_mae"] for row in pairs if row["within_interior"]]
            results.append(
                {
                    "interval_s": [start, stop],
                    "source_run_id": interval["source_run_id"],
                    "frame_sample_count": len(times),
                    "pair_count": len(pairs),
                    "interior_pair_count": len(interior),
                    "interior_median_lower_ice_mae": round(float(np.median(interior)), 5)
                    if interior
                    else None,
                    "interior_pair_count_above_threshold": sum(
                        value > ACTIVE_MAE_THRESHOLD for value in interior
                    ),
                    "pairs": pairs,
                }
            )
    finally:
        cap.release()
    return {
        "status": "development_lower_ice_activity_not_throw_events",
        "source_sha256": video_hash,
        "sample_period_s": SAMPLE_PERIOD_S,
        "roi_xyxy": ROI_XYXY,
        "edge_exclusion_s": EDGE_EXCLUSION_S,
        "active_mae_threshold": ACTIVE_MAE_THRESHOLD,
        "intervals": results,
        "limitations": [
            "The ROI and threshold were chosen after inspecting these two recordings.",
            "Lower-ice pixel change may be a stone, player, camera/edit or graphic; stillness may miss small distant stones.",
            "Five-second sampling can miss a complete short transit between frames.",
            "This audit gives no physical throw count, recall or event identity.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "activity", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    activity = json.loads(args.activity.read_text())
    result = audit(args.video, activity)
    result["activity_audit_sha256"] = digest(args.activity)
    result["runner_sha256"] = digest(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            [
                {
                    "interval_s": r["interval_s"],
                    "interior_pair_count": r["interior_pair_count"],
                    "above_threshold": r["interior_pair_count_above_threshold"],
                }
                for r in result["intervals"]
            ]
        )
    )


if __name__ == "__main__":
    main()
