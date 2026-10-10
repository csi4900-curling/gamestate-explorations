"""Check later same-colour board onsets against board-blind cap continuation."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from board_onset_probes import onset_frame_detection  # noqa: E402
from causal_cap_continuation import choose_next_cap  # noqa: E402
from local_colour_cap_probe import local_cap_components  # noqa: E402
from scripts.extend_czech_reviewed_stone_caps import search_roi  # noqa: E402
from scripts.probe_czech_reviewed_settle_gaps import sample_indices  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
GAPS = BASE / "full-reviewed-stone-replay-gaps-development.json"
BOARDS = BASE / "full-match-partial-boards-postscore.json"
CAPS = BASE / "full-reviewed-stone-cap-continuations-development.json"
OUT = BASE / "full-reviewed-later-board-onset-probes-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def selected_center(step):
    selected = step["decision"]["selected"]
    return selected["centroid_px_1080"] if selected else None


def main():
    if OUT.exists():
        raise ValueError("Later board onset probe already exists")
    gaps, boards, caps = (json.loads(p.read_text()) for p in (GAPS, BOARDS, CAPS))
    source_hash = digest(VIDEO)
    if (
        source_hash != boards["high_resolution_source_sha256"]
        or source_hash != caps["source_video_sha256"]
        or caps["input_sha256"]["replay_gaps"] != digest(GAPS)
    ):
        raise ValueError("Board, cap and source lineage differ")
    board_by_id = {r["candidate_id"]: r for r in boards["rows"]}
    gap_by_id = {r["episode_id"]: r for r in gaps["rows"]}
    video = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = video.get(cv2.CAP_PROP_FPS)
    if not video.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("Source unreadable or FPS changed")
    rows = []
    try:
        for first in caps["rows"]:
            _ = gap_by_id[first["episode_id"]]
            board = board_by_id[first["left_motion_candidate_id"]]
            first_time = first["evaluation_horizon_first_board_time_s"]
            later = sorted(
                (
                    s
                    for s in board["board"]["stones"]
                    if s["colour"] == first["colour_claim"] and s["first_seen_s"] > first_time
                ),
                key=lambda s: (s["first_seen_s"], s["local_observation_id"]),
            )
            status = (
                "no_later_same_colour_board_onset"
                if not later
                else "not_attempted_first_horizon_abstained"
                if not first["board_blind_continuation_reached_horizon"]
                else "attempted"
            )
            steps = []
            abstention = None
            if status == "attempted":
                prior = first["steps"][-2:]
                if len(prior) < 2 or any(selected_center(s) is None for s in prior):
                    raise ValueError("Reached horizon has insufficient caps")
                previous_center, current_center = map(selected_center, prior)
                previous_time = prior[0]["source_time_s"]
                current_time = prior[1]["source_time_s"]
                for index in sample_indices(first_time, later[-1]["first_seen_s"], fps)[1:]:
                    time = round(index / fps, 6)
                    ratio = (time - current_time) / (current_time - previous_time)
                    prediction = [
                        current_center[i] + (current_center[i] - previous_center[i]) * ratio
                        for i in (0, 1)
                    ]
                    roi = search_roi(prediction)
                    video.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = video.read()
                    if not ok or frame.shape[:2] != (1080, 1920):
                        raise ValueError("Source frame unreadable")
                    components = [
                        c
                        for c in local_cap_components(frame, roi, first["colour_claim"])
                        if c["area_px2"] <= 700
                    ]
                    decision = choose_next_cap(current_center, previous_center, ratio, components)
                    steps.append(
                        {
                            "source_time_s": time,
                            "decoded_frame_index": index,
                            "roi_xyxy_px_1080": list(roi),
                            "components": components,
                            "decision": decision,
                        }
                    )
                    center = selected_center(steps[-1])
                    if center is None:
                        abstention = decision["status"]
                        break
                    previous_center, current_center = current_center, center
                    previous_time, current_time = current_time, time
            path_by_time = {s["source_time_s"]: selected_center(s) for s in first["steps"] + steps}
            board_frames = {f["source_time_s"]: f for f in board["frames"]}
            checkpoints = []
            for observation in later:
                t = observation["first_seen_s"]
                frame = board_frames.get(t)
                if frame is None:
                    raise ValueError("Missing board onset frame")
                detection = onset_frame_detection(observation, frame["stones"])
                center = path_by_time.get(t)
                checkpoints.append(
                    {
                        "local_observation_id": observation["local_observation_id"],
                        "first_seen_s": t,
                        "tracked_cap_center_px_1080": center,
                        "internal_board_frame_detection": detection,
                        "tracked_cap_to_onset_detection_px_1080": (
                            round(dist(center, detection["pixel_center_px_1080"]), 3)
                            if center is not None and detection
                            else None
                        ),
                        "physical_identity_verified": False,
                    }
                )
            rows.append(
                {
                    "episode_id": first["episode_id"],
                    "left_motion_candidate_id": first["left_motion_candidate_id"],
                    "colour_claim": first["colour_claim"],
                    "first_onset_time_s": first_time,
                    "later_onset_count": len(later),
                    "continuation_status": status,
                    "abstention_reason": abstention,
                    "steps_beyond_first_onset": steps,
                    "later_onset_checkpoints": checkpoints,
                    "persistent_stone_identity_verified": False,
                    "simulation_ready": False,
                }
            )
    finally:
        video.release()
    result = {
        "status": "later_board_onset_development_probe_not_identity_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {
            "replay_gaps": digest(GAPS),
            "boards": digest(BOARDS),
            "first_onset_cap_continuations": digest(CAPS),
        },
        "runner_sha256": digest(Path(__file__)),
        "selector_code_sha256": digest(ROOT / "prototype/causal_cap_continuation.py"),
        "onset_code_sha256": digest(ROOT / "prototype/board_onset_probes.py"),
        "component_code_sha256": digest(ROOT / "prototype/local_colour_cap_probe.py"),
        "eligible_gap_count": len(rows),
        "later_onset_case_count": sum(r["later_onset_count"] > 0 for r in rows),
        "attempted_later_onset_case_count": sum(
            r["continuation_status"] == "attempted" for r in rows
        ),
        "rows": rows,
        "limitations": [
            "Board observation onsets are used only as evaluation times and internal grouping targets; cap choice uses past motion and current source pixels.",
            "The board scan may group detections imperfectly; conditional ground proximity at onset does not validate a physical stone identity.",
            "Post-inspection development rule and half-second sampling leave identity switches, collisions and camera changes unresolved.",
            "No full-match throw precision/recall, complete game state or simulation readiness follows.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "eligible": len(rows),
                "later_onset_cases": result["later_onset_case_count"],
                "attempted": result["attempted_later_onset_case_count"],
                "checkpoints": {
                    r["episode_id"]: [
                        c["tracked_cap_to_onset_detection_px_1080"]
                        for c in r["later_onset_checkpoints"]
                    ]
                    for r in rows
                    if r["continuation_status"] == "attempted"
                },
            }
        )
    )


if __name__ == "__main__":
    main()
