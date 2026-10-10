"""Apply the frozen China event-time board gate to Norway end two."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.scan_china_event_gated_boards import make_sample_times
from prototype.scripts.scan_norway_end2_boards import read_frame
from prototype.temporal_board_state import stable_board_stones
from prototype.video_board_observation_v2 import detect_board_stones, detect_overhead_house

BASE = ROOT / "validation/official-shot-sequence"
REVIEW = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/fused-linked.json"
COUNTERS = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/counter-replay.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = BASE / "norway-end2-event-gated-source-video-boards-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    review = json.loads(REVIEW.read_text())
    counter_source = json.loads(COUNTERS.read_text())
    events = counter_source["counter_events"]
    selected = events[15:31]
    selected_ids = {e["id"] for e in selected}
    matched = [e for e in review["events"] if e["counter_id"] in selected_ids]
    windows = {e["counter_id"]: e for e in matched}
    if (review["source_sha256"] != counter_source["source_sha256"] or
            review["source_sha256"] != digest(VIDEO)
            or [e["id"] for e in selected] != [f"B{i:02}" for i in range(16, 32)]
            or len(windows) != len(selected) or len(matched) != len(selected)):
        raise ValueError("Norway source, end-two counters, or review windows changed")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    scans = []
    try:
        for i, event in enumerate(selected, start=15):
            t = event["crossing_time_s"]
            previous = events[i - 1]["crossing_time_s"]
            following = events[i + 1]["crossing_time_s"] if i + 1 < len(events) else None
            end = windows[event["id"]]["delivery_window_s"][1]
            times = make_sample_times(t, previous, following, end)
            frames = []
            for time_s in times:
                frame = read_frame(cap, fps, time_s)
                if frame is None:
                    continue
                house = detect_overhead_house(frame)
                if house is not None:
                    frames.append({"time_s": time_s, "house": house, "frame": frame})
            scans.append({"counter_id": event["id"], "counter_time_s": t,
                          "delivery_window_end_s": end, "sampled_times_s": times,
                          "frames": frames})
    finally:
        cap.release()
    known = [item["house"]["delivery_side"] for scan in scans for item in scan["frames"]
             if item["house"]["delivery_side"] != "uncertain"]
    side = known[0] if len(known) >= 3 and len(set(known)) == 1 else None
    rows = []
    for shot_order, scan in enumerate(scans, start=1):
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
        rows.append({"shot_order_in_end": shot_order,
                     "counter_id": scan["counter_id"],
                     "counter_time_s": scan["counter_time_s"],
                     "delivery_window_end_s": scan["delivery_window_end_s"],
                     "sampled_times_s": scan["sampled_times_s"],
                     "accepted_frame_count": len(observations),
                     "observation_interval_s": [min(o["time_s"] for o in observations),
                                                max(o["time_s"] for o in observations)] if observations else None,
                     "stable_partial_board": stable,
                     "completeness": "unknown_from_video", "simulation_ready": False})
    return {"status": "source_video_norway_end2_event_gated_transfer_before_official_comparison",
            "source_video_sha256": digest(VIDEO),
            "counter_replay_sha256": digest(COUNTERS),
            "event_review_sha256": digest(REVIEW),
            "china_gate_runner_sha256": digest(ROOT / "prototype/scripts/scan_china_event_gated_boards.py"),
            "runner_sha256": digest(Path(__file__)),
            "selection_rule": "Same China timing gate: counter -24..+30 s every 2 s, after provisional delivery-window end +4 s, after previous counter +12 s, before next counter -12 s. Norway end two B16–B31 fixed before official comparison.",
            "inferred_delivery_side": side,
            "known_delivery_side_counts": dict(Counter(known)),
            "shot_count": len(rows),
            "rows_with_accepted_frames": sum(r["accepted_frame_count"] > 0 for r in rows),
            "rows_with_stable_board": sum(bool(r["stable_partial_board"]) for r in rows),
            "stable_stone_count": sum(len(r["stable_partial_board"]) for r in rows),
            "rows": rows,
            "limitations": ["Event windows are provisional and may not end at the actual settle time.",
                            "No official diagram positions were used in this scan.",
                            "All emitted boards remain partial and unitless."]}


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first Norway event-gated transfer")
    result = build()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in ("shot_count", "rows_with_accepted_frames",
                                         "rows_with_stable_board", "stable_stone_count")})


if __name__ == "__main__":
    main()
