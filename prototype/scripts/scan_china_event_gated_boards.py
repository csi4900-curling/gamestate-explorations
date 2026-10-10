"""Source-only board scan after each provisional delivery window.

The event windows and broadcast counter times were frozen before the official
board comparison. This gate avoids clustering stones seen only while the
current delivery might still be in progress. It does not prove settling.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.scan_china_full_match_boards import read_frame, infer_local_side
from prototype.temporal_board_state import stable_board_stones
from prototype.video_board_observation_v2 import detect_board_stones, detect_overhead_house

BASE = ROOT / "validation/official-shot-sequence"
REVIEW = BASE / "pwg2022-full-match-event-review-segments-v3-preorigin-travel-development.json"
COUNTERS = ROOT / "validation/throw-event-benchmark/layout-router/full-china22-counter-postscore-replay.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
OUTPUT = BASE / "china-full-match-event-gated-source-video-boards-first.json"
OFFSETS = tuple(range(-24, 31, 2))
EVENT_END_BUFFER_S = 4
COUNTER_NEIGHBOUR_BUFFER_S = 12


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def make_sample_times(counter_time, previous_time, next_time, delivery_end):
    """Choose frames solely from broadcast event/counter timing evidence."""
    lower = max(delivery_end + EVENT_END_BUFFER_S,
                previous_time + COUNTER_NEIGHBOUR_BUFFER_S if previous_time is not None else 0)
    upper = next_time - COUNTER_NEIGHBOUR_BUFFER_S if next_time is not None else float("inf")
    return [counter_time + offset for offset in OFFSETS
            if lower <= counter_time + offset <= upper]


def build():
    review = json.loads(REVIEW.read_text())
    game = next(g for g in review["games"] if g["official_game_code"] == "PREL000102")
    counter_source = json.loads(COUNTERS.read_text())
    events = counter_source["counter_events"]
    windows = {s["counter_id"]: s for s in game["segments"] if s["counter_id"]}
    if (game["source_sha256"] != counter_source["source_sha256"]
            or game["source_sha256"] != digest(VIDEO)
            or len(events) != 116 or len(windows) != 116):
        raise ValueError("Counter, event, or source-video evidence changed")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    scans = []
    try:
        for index, event in enumerate(events):
            counter_id = event["id"]
            t = event["crossing_time_s"]
            previous = events[index - 1]["crossing_time_s"] if index else None
            following = events[index + 1]["crossing_time_s"] if index + 1 < len(events) else None
            window = windows[counter_id]
            delivery_end = window["delivery_window_s"][1]
            times = make_sample_times(t, previous, following, delivery_end)
            frames = []
            for time_s in times:
                frame = read_frame(cap, fps, time_s)
                if frame is None:
                    continue
                house = detect_overhead_house(frame)
                if house is not None:
                    frames.append({"time_s": time_s, "house": house, "frame": frame})
            scans.append({"counter_id": counter_id, "counter_time_s": t,
                          "delivery_window_end_s": delivery_end,
                          "sampled_times_s": times, "frames": frames})
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
            observations.append({"time_s": item["time_s"], "house": house,
                                 "stones": detect_board_stones(item["frame"], house)})
        stable = stable_board_stones(observations)
        rows.append({"counter_id": scan["counter_id"],
                     "counter_time_s": scan["counter_time_s"],
                     "delivery_window_end_s": scan["delivery_window_end_s"],
                     "sampled_times_s": scan["sampled_times_s"],
                     "local_inferred_delivery_side": side,
                     "accepted_frame_count": len(observations),
                     "observation_interval_s": [min(o["time_s"] for o in observations),
                                                max(o["time_s"] for o in observations)] if observations else None,
                     "stable_partial_board": stable,
                     "completeness": "unknown_from_video", "simulation_ready": False})
    return {"status": "source_video_event_gated_partial_board_scan_before_official_comparison",
            "source_video_sha256": digest(VIDEO),
            "counter_replay_sha256": digest(COUNTERS),
            "event_review_sha256": digest(REVIEW),
            "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
            "stone_detector_sha256": digest(ROOT / "prototype/video_board_observation.py"),
            "temporal_cluster_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
            "runner_sha256": digest(Path(__file__)),
            "selection_rule": "Counter -24..+30 s every 2 s, after provisional delivery-window end +4 s, after previous counter +12 s, and before next counter -12 s. No official diagrams used.",
            "counter_interval_count": len(rows),
            "rows_with_accepted_frames": sum(r["accepted_frame_count"] > 0 for r in rows),
            "rows_with_stable_board": sum(bool(r["stable_partial_board"]) for r in rows),
            "stable_stone_count": sum(len(r["stable_partial_board"]) for r in rows),
            "rows": rows,
            "limitations": ["Provisional delivery-window ends are not measured settle times.",
                            "Broadcast counters and review windows are imperfect event proxies.",
                            "All boards are partial and unitless; none is simulation-ready."]}


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first event-gated scan")
    result = build()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in ("counter_interval_count", "rows_with_accepted_frames",
                                         "rows_with_stable_board", "stable_stone_count")})


if __name__ == "__main__":
    main()
