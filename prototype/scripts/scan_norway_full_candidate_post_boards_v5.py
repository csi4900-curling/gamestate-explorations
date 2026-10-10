"""One-second full-match board sensitivity scan with terminal visibility evidence."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.candidate_post_window_board_gate import post_window_sample_times  # noqa: E402
from prototype.image_relative_board_state import stable_image_boards_by_camera_shot  # noqa: E402
from prototype.video_board_observation_v2 import detect_overhead_house, detect_board_stones  # noqa: E402

BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
EVENTS = BASE / "fused-linked.json"
SHOTS = BASE / "shot-review/manifest.json"
COUNTERS = BASE / "counter-audit.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = (
    ROOT
    / "validation/official-shot-sequence/norway-full-candidate-post-counter-dense-boards-v5.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("V5 dense scan already exists")
    source = json.loads(EVENTS.read_text())
    manifest = json.loads(SHOTS.read_text())
    counters = json.loads(COUNTERS.read_text())
    by_counter = {row["id"]: row for row in counters["counter_events"]}
    if len(by_counter) != len(counters["counter_events"]):
        raise SystemExit("Duplicate counter IDs")
    video_hash = digest(VIDEO)
    if (
        len(
            {
                source["source_sha256"],
                manifest["source_sha256"],
                counters["source_sha256"],
                video_hash,
            }
        )
        != 1
    ):
        raise SystemExit("Source hash conflict")
    events = source["events"]
    starts = [row["delivery_window_s"][0] for row in events]
    if any(a >= b for a, b in zip(starts, starts[1:])):
        raise SystemExit("Candidate starts must increase")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    rows = []
    try:
        for index, event in enumerate(events):
            next_start = starts[index + 1] if index + 1 < len(events) else 9039.0
            times = post_window_sample_times(
                event["delivery_window_s"], next_start, horizon_s=90.0, step_s=1.0
            )
            counter_time = None
            if event["counter_id"] is not None:
                counter_time = by_counter[event["counter_id"]]["crossing_time_s"]
                times = [t for t in times if t >= counter_time + 2.0]
            observations = []
            for time_s in times:
                cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
                ok, frame = cap.read()
                if not ok:
                    continue
                house = detect_overhead_house(frame)
                if house is None:
                    continue
                observations.append(
                    {"time_s": time_s, "house": house, "stones": detect_board_stones(frame, house)}
                )
            groups = stable_image_boards_by_camera_shot(observations, manifest["shots"])
            for group in groups:
                end = group["observation_interval_s"][1]
                group["terminal_stable_image_relative_stones"] = [
                    stone
                    for stone in group["stable_image_relative_stones"]
                    if stone["last_seen_s"] >= end - 2.0
                ]
                group["terminal_evidence_end_s"] = end
            rows.append(
                {
                    "shot_id": event["shot_id"],
                    "counter_id": event["counter_id"],
                    "counter_crossing_time_s": counter_time,
                    "candidate_colour": event["colour"],
                    "delivery_window_s": event["delivery_window_s"],
                    "next_candidate_start_s": next_start,
                    "sampled_times_s": times,
                    "camera_shot_boards": groups,
                    "completeness": "unknown_from_video",
                    "simulation_ready": False,
                }
            )
            if (index + 1) % 20 == 0:
                print(f"scanned {index + 1}/{len(events)}", flush=True)
    finally:
        cap.release()
    result = {
        "status": "source_only_full_match_dense_board_sensitivity_scan",
        "source_video_sha256": video_hash,
        "input_sha256": {
            name: digest(path)
            for name, path in {
                "candidate_ledger": EVENTS,
                "counter_audit": COUNTERS,
                "camera_shot_manifest": SHOTS,
            }.items()
        },
        "code_sha256": {
            name: digest(path)
            for name, path in {
                "sampling_gate": ROOT / "prototype/candidate_post_window_board_gate.py",
                "image_board": ROOT / "prototype/image_relative_board_state.py",
                "house_v1": ROOT / "prototype/video_board_observation.py",
                "house_v2": ROOT / "prototype/video_board_observation_v2.py",
                "stability": ROOT / "prototype/temporal_board_state.py",
                "runner": Path(__file__),
            }.items()
        },
        "sampling_rule": "One-second samples from candidate window end +4 s to earlier of end +90 s or next candidate start -2 s; linked candidates require counter crossing +2 s. No official diagram used for frame or stone selection.",
        "terminal_rule": "A stable stone is terminally observed when its last detection is within 2 s of the last accepted overhead frame in its camera shot. Both the full stable list and terminal subset are retained.",
        "candidate_count": len(rows),
        "candidates_with_stable_image_board": sum(
            any(g["stable_image_relative_stones"] for g in r["camera_shot_boards"]) for r in rows
        ),
        "candidates_with_terminal_image_board": sum(
            any(g["terminal_stable_image_relative_stones"] for g in r["camera_shot_boards"])
            for r in rows
        ),
        "stable_image_stone_count": sum(
            len(g["stable_image_relative_stones"]) for r in rows for g in r["camera_shot_boards"]
        ),
        "terminal_image_stone_count": sum(
            len(g["terminal_stable_image_relative_stones"])
            for r in rows
            for g in r["camera_shot_boards"]
        ),
        "rows": rows,
        "limitations": [
            "Denser sampling can recover brief valid cap detections and also create transient false stable tracks.",
            "Terminal visibility is a diagnostic, not proof that a stone remains after camera cut or occlusion.",
            "Candidate chronology and counter links are provisional; a missed throw can contaminate post-window boards.",
            "Camera-relative positions are not metric rink coordinates or verified stone identities.",
            "No complete video game state or physical simulation readiness is claimed.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "candidate_count",
                    "candidates_with_stable_image_board",
                    "candidates_with_terminal_image_board",
                    "stable_image_stone_count",
                    "terminal_image_stone_count",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
