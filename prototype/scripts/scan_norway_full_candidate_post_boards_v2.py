"""Match-wide source-only boards in camera-scoped image-house coordinates."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.candidate_post_window_board_gate import post_window_sample_times
from prototype.image_relative_board_state import stable_image_boards_by_camera_shot
from prototype.video_board_observation_v2 import detect_overhead_house, detect_board_stones


BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
EVENTS = BASE / "fused-linked.json"
SHOTS = BASE / "shot-review/manifest.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = (
    ROOT
    / "validation/official-shot-sequence/norway-full-candidate-post-window-image-boards-v2.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("V2 camera-scoped scan already exists")
    source = json.loads(EVENTS.read_text())
    manifest = json.loads(SHOTS.read_text())
    video_hash = digest(VIDEO)
    if len({source["source_sha256"], manifest["source_sha256"], video_hash}) != 1:
        raise SystemExit("Video, candidate, and shot-manifest sources differ")
    events = source["events"]
    camera_shots = manifest["shots"]
    starts = [row["delivery_window_s"][0] for row in events]
    if any(a >= b for a, b in zip(starts, starts[1:])):
        raise SystemExit("Candidate starts must be strictly increasing")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    rows = []
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
                observations.append(
                    {"time_s": time_s, "house": house, "stones": detect_board_stones(frame, house)}
                )
            groups = stable_image_boards_by_camera_shot(observations, camera_shots)
            rows.append(
                {
                    "shot_id": event["shot_id"],
                    "counter_id": event["counter_id"],
                    "candidate_colour": event["colour"],
                    "delivery_window_s": event["delivery_window_s"],
                    "next_candidate_start_s": next_start,
                    "sampled_times_s": times,
                    "camera_shot_boards": groups,
                    "completeness": "unknown_from_video",
                    "simulation_ready": False,
                }
            )
    finally:
        cap.release()
    result = {
        "status": "source_only_full_match_camera_scoped_image_relative_partial_boards",
        "source_video_sha256": video_hash,
        "candidate_ledger_sha256": digest(EVENTS),
        "camera_shot_manifest_sha256": digest(SHOTS),
        "gate_code_sha256": digest(ROOT / "prototype/candidate_post_window_board_gate.py"),
        "image_board_code_sha256": digest(ROOT / "prototype/image_relative_board_state.py"),
        "house_detector_sha256": {
            "v1": digest(ROOT / "prototype/video_board_observation.py"),
            "v2": digest(ROOT / "prototype/video_board_observation_v2.py"),
        },
        "stability_code_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "runner_sha256": digest(Path(__file__)),
        "sampling_rule": "Every 2 s from candidate window end +4 s to earlier of end +32 s or next candidate start -2 s; source camera cuts isolate boards.",
        "candidate_count": len(rows),
        "candidates_with_sample_times": sum(bool(row["sampled_times_s"]) for row in rows),
        "candidates_with_overhead_frames": sum(bool(row["camera_shot_boards"]) for row in rows),
        "candidates_with_stable_image_board": sum(
            any(group["stable_image_relative_stones"] for group in row["camera_shot_boards"])
            for row in rows
        ),
        "stable_image_stone_count": sum(
            len(group["stable_image_relative_stones"])
            for row in rows
            for group in row["camera_shot_boards"]
        ),
        "rows": rows,
        "limitations": [
            "Coordinates are image-house relative, not calibrated physical or canonical rink coordinates.",
            "No delivery direction is inferred from house vertical position alone.",
            "Camera-shot grouping prevents cross-cut merging but does not establish physical stone identity.",
            "Candidate chronology is provisional; missing true throws can contaminate post-window boards.",
            "Stones outside accepted house views remain unobserved; no complete game state is claimed.",
            "Official board diagrams are not used to choose source frames or detections.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "candidate_count",
                "candidates_with_overhead_frames",
                "candidates_with_stable_image_board",
                "stable_image_stone_count",
            )
        }
    )


if __name__ == "__main__":
    main()
