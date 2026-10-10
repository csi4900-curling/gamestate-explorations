"""Extend E096's board-blind red cap path to the later red board onset."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from causal_cap_continuation import choose_next_cap  # noqa: E402
from local_colour_cap_probe import local_cap_components  # noqa: E402
from scripts.extend_czech_reviewed_stone_caps import search_roi  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
GAPS = BASE / "full-reviewed-stone-replay-gaps-development.json"
BOARDS = BASE / "full-match-partial-boards-postscore.json"
OUT = BASE / "e096-late-red-board-continuation-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("E096 late-board probe already exists")
    gaps = json.loads(GAPS.read_text())
    boards = json.loads(BOARDS.read_text())
    gap = next(r for r in gaps["rows"] if r["episode_id"] == "E096")
    board = next(r for r in boards["rows"] if r["candidate_id"] == "S109")
    source_hash = digest(VIDEO)
    if source_hash != boards["high_resolution_source_sha256"]:
        raise ValueError("Source/board lineage differs")
    red_onsets = sorted((r["local_observation_id"], r["first_seen_s"])
                        for r in board["board"]["stones"]
                        if r["colour"] == "red")
    if red_onsets != [("V01", 4584.0), ("V02", 4591.0)]:
        raise ValueError("E096 red board onsets changed")
    path = gap["observed_left_motion_path"]
    previous, current = path[-2:]
    previous_center = previous["pixel_center_1080"]
    current_center = current["pixel_center_1080"]
    previous_time = previous["source_time_s"]
    current_time = current["source_time_s"]
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("Source unreadable or FPS changed")
    steps = []
    abstention = None
    try:
        for index in range(round(4583.0 * fps), round(4591.0 * fps) + 1,
                           round(0.5 * fps)):
            time = round(index / fps, 6)
            ratio = (time - current_time) / (current_time - previous_time)
            prediction = [current_center[i] +
                          (current_center[i] - previous_center[i]) * ratio
                          for i in (0, 1)]
            roi = search_roi(prediction)
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise ValueError(f"Source frame unreadable: {index}")
            components = [c for c in local_cap_components(frame, roi, "red")
                          if c["area_px2"] <= 700]
            decision = choose_next_cap(current_center, previous_center,
                                       ratio, components)
            steps.append({"source_time_s": time, "decoded_frame_index": index,
                          "roi_xyxy_px_1080": list(roi),
                          "components": components, "decision": decision})
            if decision["selected"] is None:
                abstention = decision["status"]
                break
            previous_center, current_center = current_center, decision[
                "selected"]["centroid_px_1080"]
            previous_time, current_time = current_time, time
    finally:
        cap.release()
    board_red_by_time = {
        f["source_time_s"]: [s["pixel_center"] for s in f["stones"]
                             if s["colour"] == "red"]
        for f in board["frames"]
    }
    checkpoints = []
    by_time = {s["source_time_s"]: s for s in steps}
    for label, time in red_onsets:
        step = by_time.get(time)
        center = (step["decision"]["selected"]["centroid_px_1080"]
                  if step and step["decision"]["selected"] else None)
        checkpoints.append({
            "board_local_observation_id": label,
            "first_seen_s": time,
            "tracked_cap_center_px_1080": center,
            "board_red_frame_centers_px_1080": board_red_by_time[time],
            "distances_to_board_red_centers_px_1080": [
                round(dist(center, p), 3) for p in board_red_by_time[time]]
            if center else None,
        })
    result = {
        "status": "same_agent_e096_late_board_cap_probe_not_persistent_identity_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {"replay_gaps": digest(GAPS), "boards": digest(BOARDS)},
        "runner_sha256": digest(Path(__file__)),
        "selector_code_sha256": digest(ROOT /
                                       "prototype/causal_cap_continuation.py"),
        "component_code_sha256": digest(ROOT /
                                        "prototype/local_colour_cap_probe.py"),
        "episode_id": "E096", "left_motion_candidate_id": "S109",
        "start_observed_path_points": [previous, current],
        "board_blind_tracking": True,
        "late_horizon_reached": abstention is None and steps[-1][
            "source_time_s"] == 4591.0,
        "abstention_reason": abstention,
        "red_board_onset_checkpoints": checkpoints,
        "steps": steps,
        "persistent_stone_identity_verified": False,
        "simulation_ready": False,
        "limitations": [
            "The later board onset sets only the evaluation horizon; board positions never select a cap.",
            "Half-second frames can miss collision, occlusion or a physical identity switch.",
            "The board scan's first red detection at 4584 s is an existing red-stone proposal, so first same-colour observation time is not a delivered-stone settle time.",
            "Related-pixel endpoint agreement is not independent identity or metric accuracy validation.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"steps": len(steps),
                      "late_horizon_reached": result["late_horizon_reached"],
                      "abstention": abstention,
                      "checkpoints": checkpoints}))


if __name__ == "__main__":
    main()
