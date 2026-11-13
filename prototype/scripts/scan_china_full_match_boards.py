"""Scan every readable China 2022 counter interval for source-video boards.

This stage uses no official post-shot diagrams or shot numbers. A later scorer
may compare these frozen video-only observations with the independent PDF.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.temporal_board_state import stable_board_stones
from prototype.video_board_observation_v2 import detect_board_stones, detect_overhead_house

COUNTERS = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-china22-counter-postscore-replay.json"
)
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
OUTPUT = ROOT / "validation/official-shot-sequence/china-full-match-source-video-boards-first.json"
OFFSETS_S = tuple(range(4, 31, 2))
NEXT_COUNTER_BUFFER_S = 12


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read_frame(cap, fps, time_s):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
    ok, frame = cap.read()
    return cv2.resize(frame, (640, 360)) if ok else None


def infer_local_side(index, scans):
    own = [
        item["house"]["delivery_side"]
        for item in scans[index]["frames"]
        if item["house"]["delivery_side"] != "uncertain"
    ]
    if own:
        return own[0] if len(set(own)) == 1 else None
    neighbours = []
    for other in range(max(0, index - 2), min(len(scans), index + 3)):
        if other == index:
            continue
        if abs(scans[other]["counter_time_s"] - scans[index]["counter_time_s"]) > 180:
            continue
        neighbours += [
            item["house"]["delivery_side"]
            for item in scans[other]["frames"]
            if item["house"]["delivery_side"] != "uncertain"
        ]
    return neighbours[0] if len(neighbours) >= 3 and len(set(neighbours)) == 1 else None


def build():
    source = json.loads(COUNTERS.read_text())
    if source["source_sha256"] != digest(VIDEO):
        raise ValueError("Counter source and full-match video differ")
    events = source["counter_events"]
    if len(events) != 116 or len({e["id"] for e in events}) != len(events):
        raise ValueError("Frozen China counter evidence changed")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    scans = []
    try:
        for index, event in enumerate(events):
            next_time = events[index + 1]["crossing_time_s"] if index + 1 < len(events) else None
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
            scans.append(
                {
                    "counter_id": event["id"],
                    "counter_time_s": event["crossing_time_s"],
                    "next_counter_time_s": next_time,
                    "sampled_offsets_s": offsets,
                    "frames": frames,
                }
            )
    finally:
        cap.release()
    rows = []
    for index, scan in enumerate(scans):
        side = infer_local_side(index, scans)
        observations = []
        for item in scan["frames"]:
            house = dict(item["house"])
            if house["delivery_side"] == "uncertain":
                if side is None:
                    continue
                house["delivery_side"] = side
            elif side is not None and house["delivery_side"] != side:
                continue
            observations.append(
                {
                    "time_s": item["time_s"],
                    "offset_s": item["offset_s"],
                    "house": house,
                    "stones": detect_board_stones(item["frame"], house),
                }
            )
        stable = stable_board_stones(observations)
        rows.append(
            {
                "counter_id": scan["counter_id"],
                "counter_time_s": scan["counter_time_s"],
                "following_counter_time_s": scan["next_counter_time_s"],
                "sampled_offsets_s": scan["sampled_offsets_s"],
                "local_inferred_delivery_side": side,
                "accepted_frame_count": len(observations),
                "observation_interval_s": [
                    min(o["time_s"] for o in observations),
                    max(o["time_s"] for o in observations),
                ]
                if observations
                else None,
                "stable_partial_board": stable,
                "state_status": "partial_video_observation" if stable else "no_stable_board",
                "completeness": "unknown_from_video",
                "simulation_ready": False,
            }
        )
    return {
        "status": "full_match_source_video_partial_board_scan_before_official_comparison",
        "source_video_sha256": digest(VIDEO),
        "counter_replay_sha256": digest(COUNTERS),
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "stone_detector_sha256": digest(ROOT / "prototype/video_board_observation.py"),
        "temporal_cluster_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "All 116 readable China counter decrements; +4..+30 s every 2 s, stopping 12 s before next counter. Uncertain overhead orientation is filled only by unanimous local source-video views within 180 s.",
        "counter_interval_count": len(rows),
        "rows_with_accepted_frames": sum(r["accepted_frame_count"] > 0 for r in rows),
        "rows_with_stable_board": sum(bool(r["stable_partial_board"]) for r in rows),
        "stable_stone_count": sum(len(r["stable_partial_board"]) for r in rows),
        "rows": rows,
        "limitations": [
            "Counter decrements are delayed broadcast proxies, not exact throw completion times.",
            "No official PDF diagrams enter this source-only board stage.",
            "No output board is assumed complete or simulation-ready; unreadable counter intervals are outside this scan.",
        ],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first full-match source-only board scan")
    result = build()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "counter_interval_count",
                "rows_with_accepted_frames",
                "rows_with_stable_board",
                "stable_stone_count",
            )
        }
    )


if __name__ == "__main__":
    main()
