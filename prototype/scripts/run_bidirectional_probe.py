"""Run both left-view motion directions as a diagnostic, without phase selection."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from bidirectional_detection import IncomingPassageDetector, crossing_x
from cache_contract import file_sha256
from throw_detection import PassageConfig, PassageDetector, stone_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=float, default=1650)
    parser.add_argument("--end", type=float, default=2760)
    parser.add_argument("--gate-y", type=float, action="append")
    args = parser.parse_args()
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    digest = file_sha256(args.video)
    if (
        args.video.resolve() == (ROOT / "validation/unseen-end/source.mp4").resolve()
        or digest == reserved["source_sha256"]
        or any(args.source_id in row["video_url"] for row in reserved["reserved_rows"])
    ):
        parser.error("This event is reserved for independent evaluation")
    if args.output.exists():
        parser.error("Output exists; preserve previous probes")
    cv2.setNumThreads(1)
    gate_ys = args.gate_y or [60]
    if any(not 25 <= gate_y <= 95 for gate_y in gate_ys):
        parser.error("Gate y must be inside the departure ROI with room for observations")
    detectors = [
        (
            PassageDetector(PassageConfig(gate_y=gate_y)),
            IncomingPassageDetector(PassageConfig(gate_y=gate_y)),
        )
        for gate_y in gate_ys
    ]
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
        candidates = stone_candidates(frame, detectors[0][0].config)
        for outgoing, incoming in detectors:
            outgoing.update(candidates, n / fps)
            incoming.update(candidates, n / fps)
        samples += 1
    cap.release()
    events = []
    for outgoing, incoming in detectors:
        outgoing_paths = outgoing.trajectories()
        events.extend(
            dict(
                e,
                view_motion="negative_y",
                crossing_x_px=crossing_x(e, outgoing_paths[e["track_id"]]),
            )
            for e in outgoing.events
        )
        events.extend(incoming.events)
    events.sort(key=lambda e: (abs(e["gate_y_px"] - 60), e["crossing_time_s"]))
    merged = []
    for event in events:
        same_stone = next(
            (
                prior
                for prior in merged
                if prior["colour"] == event["colour"]
                and prior["view_motion"] == event["view_motion"]
                and abs(prior["crossing_time_s"] - event["crossing_time_s"]) <= 4
                and abs(prior["crossing_x_px"] - event["crossing_x_px"]) <= 20
            ),
            None,
        )
        if same_stone is None:
            merged.append(event)
        else:
            same_stone.setdefault("corroborating_gate_y_px", []).append(event["gate_y_px"])
    events = sorted(merged, key=lambda e: e["crossing_time_s"])
    for i, event in enumerate(events, 1):
        event["id"] = f"D{i:02}"
    result = {
        "status": "development_diagnostic_after_canada_italy_first_score",
        "source_id": args.source_id,
        "source_sha256": digest,
        "source_interval_s": [args.start, args.end],
        "model_sha256": file_sha256(ROOT / "prototype/bidirectional_detection.py"),
        "baseline_sha256": file_sha256(ROOT / "prototype/throw_detection.py"),
        "runner_sha256": file_sha256(__file__),
        "config": [asdict(outgoing.config) for outgoing, _ in detectors],
        "events": events,
        "samples": samples,
        "processing_seconds": time.monotonic() - started,
        "limitations": [
            "Both motion directions are pooled without camera-role or end-phase selection.",
            "This source revealed the direction failure and is development data, not held-out validation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "events": len(events),
                "outgoing": sum(len(outgoing.events) for outgoing, _ in detectors),
                "incoming": sum(len(incoming.events) for _, incoming in detectors),
            }
        )
    )


if __name__ == "__main__":
    main()
