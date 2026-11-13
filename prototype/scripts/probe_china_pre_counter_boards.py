"""Freeze a wider source-only board timing probe around China counter updates.

Offsets are fixed at -24..+30 s by 2 s. The prior counter +12 s and next
counter -12 s bound the window so it cannot freely absorb adjacent deliveries.
No official shot board data are read here.
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
from prototype.scripts.scan_china_full_match_boards import read_frame, infer_local_side

COUNTERS = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-china22-counter-postscore-replay.json"
)
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
BASE_SCAN = (
    ROOT / "validation/official-shot-sequence/china-full-match-source-video-boards-first.json"
)
OUTPUT = (
    ROOT / "validation/official-shot-sequence/china-full-match-pre-counter-board-probe-first.json"
)
OFFSETS = tuple(range(-24, 31, 2))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first wider-window probe")
    source = json.loads(COUNTERS.read_text())
    base = json.loads(BASE_SCAN.read_text())
    events = source["counter_events"]
    if (
        source["source_sha256"] != digest(VIDEO)
        or len(events) != 116
        or base["counter_interval_count"] != 116
    ):
        raise ValueError("Source or first counter scan changed")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    scans = []
    try:
        for index, event in enumerate(events):
            t = event["crossing_time_s"]
            previous = events[index - 1]["crossing_time_s"] if index else None
            following = events[index + 1]["crossing_time_s"] if index + 1 < len(events) else None
            offsets = [
                offset
                for offset in OFFSETS
                if (previous is None or t + offset >= previous + 12)
                and (following is None or t + offset <= following - 12)
            ]
            frames = []
            for offset in offsets:
                time_s = t + offset
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
                    "counter_time_s": t,
                    "previous_counter_time_s": previous,
                    "next_counter_time_s": following,
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
                "previous_counter_time_s": scan["previous_counter_time_s"],
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
                "completeness": "unknown_from_video",
                "simulation_ready": False,
            }
        )
    result = {
        "status": "source_video_pre_counter_timing_probe_before_official_comparison",
        "source_video_sha256": digest(VIDEO),
        "counter_replay_sha256": digest(COUNTERS),
        "original_scan_sha256": digest(BASE_SCAN),
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "stone_detector_sha256": digest(ROOT / "prototype/video_board_observation.py"),
        "temporal_cluster_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "orientation_helper_sha256": digest(
            ROOT / "prototype/scripts/scan_china_full_match_boards.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "All 116 readable counter decrements; -24..+30 seconds by 2 seconds, bounded by previous counter +12 and next counter -12. Same overhead detector and temporal cluster as first scan; no PDF positions used.",
        "counter_interval_count": len(rows),
        "rows_with_accepted_frames": sum(r["accepted_frame_count"] > 0 for r in rows),
        "rows_with_stable_board": sum(bool(r["stable_partial_board"]) for r in rows),
        "stable_stone_count": sum(len(r["stable_partial_board"]) for r in rows),
        "rows": rows,
        "limitations": [
            "The counter update can lag the delivery; a pre-counter stable board may be the previous shot's state.",
            "No official diagram positions were used to select frames or emit stones.",
            "All outputs remain partial, unitless and not simulation-ready.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            k: result[k]
            for k in (
                "counter_interval_count",
                "rows_with_accepted_frames",
                "rows_with_stable_board",
                "stable_stone_count",
            )
        }
    )


if __name__ == "__main__":
    main()
