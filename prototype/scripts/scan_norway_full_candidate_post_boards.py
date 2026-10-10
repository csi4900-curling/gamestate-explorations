"""Source-only post-candidate partial-board scan across the Norway match."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.candidate_post_window_board_gate import post_window_sample_times
from prototype.temporal_board_state import stable_board_stones
from prototype.video_board_observation_v2 import detect_overhead_house, detect_board_stones


BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
EVENTS = BASE / "fused-linked.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = (
    ROOT
    / "validation/official-shot-sequence/norway-full-candidate-post-window-source-boards-first.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("First full-match post-window board scan already exists")
    source = json.loads(EVENTS.read_text())
    if source["source_sha256"] != digest(VIDEO):
        raise SystemExit("Candidate and video source hashes differ")
    events = source["events"]
    starts = [row["delivery_window_s"][0] for row in events]
    if any(a >= b for a, b in zip(starts, starts[1:])):
        raise SystemExit("Candidate starts must be strictly increasing")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    raw_rows = []
    try:
        for index, event in enumerate(events):
            next_start = starts[index + 1] if index + 1 < len(events) else 9039.0
            times = post_window_sample_times(event["delivery_window_s"], next_start)
            observations = []
            for time_s in times:
                cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
                ok, frame = cap.read()
                if not ok:
                    continue
                house = detect_overhead_house(frame)
                if house is None:
                    continue
                stones = detect_board_stones(frame, house)
                observations.append({"time_s": time_s, "house": house, "stones": stones})
            raw_rows.append(
                {
                    "shot_id": event["shot_id"],
                    "counter_id": event["counter_id"],
                    "candidate_colour": event["colour"],
                    "delivery_window_s": event["delivery_window_s"],
                    "next_candidate_start_s": next_start,
                    "sampled_times_s": times,
                    "overhead_observations": observations,
                }
            )
    finally:
        cap.release()
    known = [
        observation["house"]["delivery_side"]
        for row in raw_rows
        for observation in row["overhead_observations"]
        if observation["house"]["delivery_side"] != "uncertain"
    ]
    global_side = known[0] if len(known) >= 3 and len(set(known)) == 1 else None
    rows = []
    for raw in raw_rows:
        observations = []
        for observation in raw["overhead_observations"]:
            house = observation["house"]
            side = house["delivery_side"]
            if side == "uncertain":
                side = global_side
            elif global_side is not None and side != global_side:
                continue
            if side is None or side == "uncertain":
                continue
            cx, cy = house["center_px"]
            radius = house["outer_radius_px"]
            sign = 1 if side == "top" else -1
            stones = [
                {
                    **stone,
                    "canonical_lateral_house_radii": round(
                        sign * (stone["pixel"][0] - cx) / radius, 4
                    ),
                    "longitudinal_house_radii": round(sign * (stone["pixel"][1] - cy) / radius, 4),
                }
                for stone in observation["stones"]
            ]
            observations.append({"time_s": observation["time_s"], "stones": stones})
        stable = stable_board_stones(observations)
        rows.append(
            {key: value for key, value in raw.items() if key != "overhead_observations"}
            | {
                "accepted_overhead_frame_count": len(observations),
                "accepted_overhead_interval_s": [
                    observations[0]["time_s"],
                    observations[-1]["time_s"],
                ]
                if observations
                else None,
                "stable_partial_board": stable,
                "completeness": "unknown_from_video",
                "simulation_ready": False,
            }
        )
    result = {
        "status": "source_only_full_match_candidate_post_window_partial_boards",
        "source_video_sha256": digest(VIDEO),
        "candidate_ledger_sha256": digest(EVENTS),
        "gate_code_sha256": digest(ROOT / "prototype/candidate_post_window_board_gate.py"),
        "house_detector_sha256": {
            "v1": digest(ROOT / "prototype/video_board_observation.py"),
            "v2": digest(ROOT / "prototype/video_board_observation_v2.py"),
        },
        "stability_code_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "runner_sha256": digest(Path(__file__)),
        "sampling_rule": "Every 2 s from candidate window end +4 s to the earlier of end +32 s or next candidate start -2 s; official diagrams are not used.",
        "global_delivery_side_from_known_frames": global_side,
        "known_delivery_side_counts": dict(Counter(known)),
        "candidate_count": len(rows),
        "candidates_with_sample_times": sum(bool(row["sampled_times_s"]) for row in rows),
        "candidates_with_overhead_frames": sum(
            row["accepted_overhead_frame_count"] > 0 for row in rows
        ),
        "candidates_with_stable_partial_board": sum(
            bool(row["stable_partial_board"]) for row in rows
        ),
        "stable_stone_count": sum(len(row["stable_partial_board"]) for row in rows),
        "rows": rows,
        "limitations": [
            "Candidate windows and identities are provisional; the post-window gate does not find physical settle times.",
            "A subsequent true throw missing from the candidate ledger can contaminate an earlier board window.",
            "An empty stable board can mean no stone, no usable view, or insufficient temporal support.",
            "The stone list is partial and excludes unobserved stones; no complete game state or simulation-ready output is inferred.",
            "This source-only scan does not use official board diagrams or score its own correctness.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "candidate_count",
                "candidates_with_sample_times",
                "candidates_with_overhead_frames",
                "candidates_with_stable_partial_board",
                "stable_stone_count",
            )
        }
    )


if __name__ == "__main__":
    main()
