"""Source-video-only temporal board scan on Norway end two.

The 16 clean end-two counter events are fixed before reading any PDF diagrams.
This file deliberately does not import the official board reference.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.temporal_board_state import stable_board_stones
from prototype.video_board_observation_v2 import detect_board_stones, detect_overhead_house

BASE = ROOT / "validation/official-shot-sequence"
COUNTERS = (
    ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/counter-replay.json"
)
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = BASE / "norway-end2-source-video-partial-boards-first.json"
OFFSETS_S = tuple(range(4, 31, 2))
NEXT_COUNTER_BUFFER_S = 12


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read_frame(cap, fps, time_s):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
    ok, frame = cap.read()
    return cv2.resize(frame, (640, 360)) if ok else None


def build():
    source = json.loads(COUNTERS.read_text())
    events = source["counter_events"]
    selected = events[15:31]
    if len(selected) != 16 or [e["id"] for e in selected] != [f"B{i:02}" for i in range(16, 32)]:
        raise ValueError("Norway end-two counter selection changed")
    if source["source_sha256"] != digest(VIDEO):
        raise ValueError("Counter source and video hashes differ")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    scans = []
    try:
        for i, event in enumerate(selected):
            next_time = events[15 + i + 1]["crossing_time_s"] if 15 + i + 1 < len(events) else None
            offsets = [
                offset
                for offset in OFFSETS_S
                if next_time is None
                or event["crossing_time_s"] + offset <= next_time - NEXT_COUNTER_BUFFER_S
            ]
            frames = []
            for offset in offsets:
                time_s = event["crossing_time_s"] + offset
                frame = read_frame(cap, fps, time_s)
                if frame is None:
                    continue
                house = detect_overhead_house(frame)
                if house is not None:
                    frames.append(
                        {"time_s": time_s, "offset_s": offset, "house": house, "frame": frame}
                    )
            scans.append((event, next_time, offsets, frames))
    finally:
        cap.release()
    known = [
        item["house"]["delivery_side"]
        for _, _, _, frames in scans
        for item in frames
        if item["house"]["delivery_side"] != "uncertain"
    ]
    inferred_side = known[0] if len(known) >= 3 and len(set(known)) == 1 else None
    rows = []
    for i, (event, next_time, offsets, frames) in enumerate(scans, start=1):
        observations = []
        for item in frames:
            house = dict(item["house"])
            if house["delivery_side"] == "uncertain":
                if inferred_side is None:
                    continue
                house["delivery_side"] = inferred_side
            stones = detect_board_stones(item["frame"], house)
            observations.append(
                {
                    "time_s": item["time_s"],
                    "offset_s": item["offset_s"],
                    "house": house,
                    "stones": stones,
                }
            )
        stable = stable_board_stones(observations)
        rows.append(
            {
                "shot_order_in_end": i,
                "counter_id": event["id"],
                "counter_time_s": event["crossing_time_s"],
                "following_counter_time_s": next_time,
                "sampled_offsets_s": offsets,
                "accepted_frame_count": len(observations),
                "frame_observations": observations,
                "stable_partial_board": stable,
                "state_status": "partial_video_observation" if stable else "no_stable_board",
                "simulation_ready": False,
            }
        )
    return {
        "status": "source_video_norway_end2_board_transfer_before_official_comparison",
        "source_video_sha256": digest(VIDEO),
        "counter_replay_sha256": digest(COUNTERS),
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "stone_detector_sha256": digest(ROOT / "prototype/video_board_observation.py"),
        "temporal_cluster_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "Norway counter events B16–B31, end two; +4..+30 s every 2 s, stopping 12 s before the next counter. Uncertain orientation is filled only when all clear source-video views in this end agree.",
        "inferred_delivery_side": inferred_side,
        "known_delivery_side_counts": dict(Counter(known)),
        "shot_count": len(rows),
        "rows_with_accepted_frames": sum(row["accepted_frame_count"] > 0 for row in rows),
        "rows_with_stable_stones": sum(bool(row["stable_partial_board"]) for row in rows),
        "stable_stone_count": sum(len(row["stable_partial_board"]) for row in rows),
        "rows": rows,
        "limitations": [
            "Counter times lag the actual delivery; a sampled board may belong to a neighbouring physical state.",
            "No official diagram coordinates are read by this scan.",
            "Unknown completeness, metric scale, persistent identities, exact settle time, and simulation readiness.",
        ],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first source-video transfer")
    result = build()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "shot_count",
                "rows_with_accepted_frames",
                "rows_with_stable_stones",
                "stable_stone_count",
            )
        }
    )


if __name__ == "__main__":
    main()
