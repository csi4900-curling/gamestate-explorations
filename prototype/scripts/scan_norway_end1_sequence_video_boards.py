"""Scan source-video partial boards after the 16 Norway end-one hypotheses."""

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
SEQUENCE = BASE / "norway-end1-16-shot-sequence-hypothesis-first.json"
COUNTERS = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/counter-replay.json"
MANIFEST = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/shot-review/manifest.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = BASE / "norway-end1-source-video-partial-boards-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def sample_plan(sequence, counter_events, shot_manifest):
    rows = sequence["rows"]
    if len(rows) != 16 or [row["counter_id"] for row in rows[:15]] != [
        f"B{i:02}" for i in range(1, 16)
    ]:
        raise ValueError("End-one sequence or counters changed")
    by_counter = {row["id"]: row for row in counter_events}
    plans = []
    final_origin_start = rows[-1]["provisional_delivery_window_s"][0]
    for index, row in enumerate(rows[:15]):
        counter = by_counter[row["counter_id"]]
        previous = by_counter[rows[index - 1]["counter_id"]]["crossing_time_s"] if index else None
        following = (by_counter[rows[index + 1]["counter_id"]]["crossing_time_s"]
                     if index < 14 else final_origin_start)
        times = make_sample_times(counter["crossing_time_s"], previous, following,
                                  row["provisional_delivery_window_s"][1])
        plans.append({"shot_number": index + 1, "video_candidate_shot_id": row["video_candidate_shot_id"],
                      "anchor_kind": "broadcast_counter_decrement", "anchor_s": counter["crossing_time_s"],
                      "sampled_times_s": times})
    final = rows[-1]
    receiving_shot_id = "S87"
    receiving = next(shot for shot in shot_manifest if shot["id"] == receiving_shot_id)
    motion_last_s = final["provisional_delivery_window_s"][1]
    times = [float(t) for t in range(int(motion_last_s + 2), int(receiving["interval_s"][1]) + 1, 2)
             if t < receiving["interval_s"][1]]
    plans.append({"shot_number": 16, "video_candidate_shot_id": final["video_candidate_shot_id"],
                  "anchor_kind": "source_receiving_motion_end_not_counter", "anchor_s": motion_last_s,
                  "receiving_shot_id": receiving_shot_id,
                  "sampled_times_s": times})
    return plans


def build():
    sequence = json.loads(SEQUENCE.read_text())
    counters = json.loads(COUNTERS.read_text())
    manifest = json.loads(MANIFEST.read_text())
    video_hash = digest(VIDEO)
    if counters["source_sha256"] != video_hash or manifest["source_sha256"] != video_hash:
        raise ValueError("Norway video, counter, or camera-shot source changed")
    plans = sample_plan(sequence, counters["counter_events"], manifest["shots"])
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    scans = []
    try:
        for plan in plans:
            frames = []
            for time_s in plan["sampled_times_s"]:
                frame = read_frame(cap, fps, time_s)
                if frame is None:
                    continue
                house = detect_overhead_house(frame)
                if house is not None:
                    frames.append({"time_s": time_s, "house": house, "frame": frame})
            scans.append({"plan": plan, "frames": frames})
    finally:
        cap.release()
    known = [item["house"]["delivery_side"] for scan in scans for item in scan["frames"]
             if item["house"]["delivery_side"] != "uncertain"]
    side = known[0] if len(known) >= 3 and len(set(known)) == 1 else None
    rows = []
    for scan in scans:
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
        rows.append({**scan["plan"],
                     "accepted_frame_count": len(observations),
                     "observation_interval_s": [min(o["time_s"] for o in observations),
                                                max(o["time_s"] for o in observations)] if observations else None,
                     "stable_partial_board": stable,
                     "completeness": "unknown_from_video", "simulation_ready": False})
    return {
        "status": "source_only_norway_end1_partial_boards_before_official_comparison",
        "source_video_sha256": video_hash,
        "sequence_hypothesis_sha256": digest(SEQUENCE),
        "counter_replay_sha256": digest(COUNTERS),
        "camera_shot_manifest_sha256": digest(MANIFEST),
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "stability_code_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "Shots 1–15: frozen China counter gate, with S86 origin as the shot-15 next-event boundary. Shot 16: receiving-shot 1 Hz motion ends at 1215 s, then 2 Hz sample until S87 camera shot end; no official positions used.",
        "inferred_delivery_side": side,
        "known_delivery_side_counts": dict(Counter(known)),
        "shot_count": len(rows),
        "rows_with_accepted_frames": sum(row["accepted_frame_count"] > 0 for row in rows),
        "rows_with_stable_board": sum(bool(row["stable_partial_board"]) for row in rows),
        "stable_stone_count": sum(len(row["stable_partial_board"]) for row in rows),
        "rows": rows,
        "limitations": [
            "The event sequence and delivery windows are provisional; no exact settle time is established.",
            "Shot 16 uses a source-motion endpoint rather than a broadcast counter anchor.",
            "Official PDF board positions are not used in this scan.",
            "All emitted boards are partial and unitless, not simulation-ready game states.",
        ],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-one video-board scan")
    result = build()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in
           ("shot_count", "rows_with_accepted_frames", "rows_with_stable_board", "stable_stone_count")})


if __name__ == "__main__":
    main()
