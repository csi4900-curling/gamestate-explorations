"""Transfer the fixed expanded-upper-edge board-cap ROI across 2024 views."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from right_view_partial_board import stable_cap_candidates
from probe_static_left_right_cap_motion import right_colour_proposals
from scan_full_match_split_pre_event_caps import eligible_times as eligible_pre
from scan_full_match_split_post_event_caps import eligible_times as eligible_post

CAP_ROI = (360, 135, 615, 235)
SCENE_ROI = (330, 155, 630, 245)
MAX_SCENE_MAE = 20


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def sample_caps(cap, times):
    patches, frames = [], []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, image = cap.read()
        if not ok or image.shape[:2] != (360, 640):
            return [], [], [], "abstain_decode_failure"
        sx0, sy0, sx1, sy1 = SCENE_ROI
        patches.append(image[sy0:sy1, sx0:sx1].astype(np.int16))
        cx0, cy0, cx1, cy1 = CAP_ROI
        proposals = right_colour_proposals(image)
        coloured = [{"colour": colour, **item}
                    for colour, items in proposals.items() for item in items
                    if cx0 <= item["pixel"][0] <= cx1
                    and cy0 <= item["pixel"][1] <= cy1
                    and item["cap_area_px2"] >= 6]
        frames.append({"time_s": t, "cap_candidates": coloured})
    maes = [round(float(np.mean(np.abs(a - b))), 3)
            for a, b in zip(patches, patches[1:])]
    if max(maes) >= MAX_SCENE_MAE:
        return frames, maes, [], "abstain_scene_or_player_motion"
    return frames, maes, stable_cap_candidates(frames), None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("pre", "post"), required=True)
    for name in ("video", "sequence", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    sequence = json.loads(args.sequence.read_text())
    source_hash = digest(args.video)
    if source_hash != sequence["source_sha256"]:
        parser.error("Source fingerprints differ")
    runs = {row["id"]: tuple(row["interval_s"])
            for row in sequence["supported_runs"]}
    grouped = {run_id: [] for run_id in runs}
    for event in sequence["rows"]:
        if event["observation_kind"] != "left_tracked_passage":
            continue
        run_id = event["left_event_id"].split("-", 1)[0]
        if run_id not in runs or not runs[run_id][0] <= event["observation_time_s"] < runs[run_id][1]:
            parser.error("Left event outside its routed run")
        grouped[run_id].append(event)
    if sum(map(len, grouped.values())) != sequence["left_candidate_count"]:
        parser.error("Candidate sequence left count differs")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable source video")
    rows = []
    try:
        for run_id, events in grouped.items():
            events.sort(key=lambda row: row["observation_time_s"])
            start, end = runs[run_id]
            for index, event in enumerate(events):
                t = event["observation_time_s"]
                neighbor = (events[index - 1]["observation_time_s"] if index
                            else None) if args.phase == "pre" else (
                            events[index + 1]["observation_time_s"]
                            if index + 1 < len(events) else None)
                times, abstention = (eligible_pre(t, neighbor, start)
                                     if args.phase == "pre" else
                                     eligible_post(t, neighbor, end))
                if times is None:
                    frames, maes, stable = [], [], []
                else:
                    frames, maes, stable, abstention = sample_caps(cap, times)
                status = abstention or ("partial_stable_colour_cap_proposals" if stable else
                                        "no_stable_colour_cap_proposals")
                row = {
                    "candidate_id": event["candidate_id"],
                    "left_event_id": event["left_event_id"],
                    "run_id": run_id,
                    "observed_left_passage_time_s": t,
                    "observation_status": status,
                    "sample_times_s": times or [],
                    "scene_mae_between_samples": maes,
                    "sample_frames": frames,
                    "stable_cap_proposals": stable,
                    "stable_cap_colour_counts": dict(Counter(item["colour"] for item in stable)),
                    "coordinate_frame": "source_right_camera_pixels_not_metric",
                    "complete_board_verified": False,
                    "physical_settle_verified": False,
                    "persistent_stone_identity_verified": False,
                    "simulation_ready": False,
                }
                row[("previous" if args.phase == "pre" else "next") +
                    "_left_passage_time_s"] = neighbor
                rows.append(row)
    finally:
        cap.release()
    rows.sort(key=lambda row: row["observed_left_passage_time_s"])
    result = {
        "status": f"development_expanded_roi_{args.phase}_partial_cap_scan_not_board_truth",
        "phase": args.phase,
        "source_sha256": source_hash,
        "candidate_sequence_sha256": digest(args.sequence),
        "proposal_code_sha256": digest(ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"),
        "stable_cap_code_sha256": digest(ROOT / "prototype/right_view_partial_board.py"),
        "pre_gate_code_sha256": digest(ROOT / "prototype/scripts/scan_full_match_split_pre_event_caps.py"),
        "post_gate_code_sha256": digest(ROOT / "prototype/scripts/scan_full_match_split_post_event_caps.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_roi_xyxy": list(CAP_ROI),
        "scene_comparison_roi_xyxy": list(SCENE_ROI),
        "max_scene_mae_for_observation": MAX_SCENE_MAE,
        "candidate_count": len(rows),
        "observation_status_counts": dict(Counter(row["observation_status"] for row in rows)),
        "stable_cap_proposal_count": sum(len(row["stable_cap_proposals"]) for row in rows),
        "rows": rows,
        "limitations": [
            "The upper ROI edge was expanded after exposed Italy source review; this is not independent validation.",
            "Only local cap visibility is observed; people, handling and occlusion remain unresolved.",
            "No physical stone identity, complete board or simulation state is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"phase": args.phase, "candidates": len(rows),
                      "statuses": result["observation_status_counts"],
                      "stable_caps": result["stable_cap_proposal_count"]}))


if __name__ == "__main__":
    main()
