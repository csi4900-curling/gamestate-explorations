"""Sample source-visible right-panel caps before each provisional left event."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from scan_full_match_split_post_event_caps import (
    CAP_ROI, MAX_SCENE_MAE, SCENE_ROI, digest, sample_caps,
)

OFFSETS_BEFORE_S = (25, 20, 15)
PREVIOUS_EVENT_GUARD_S = 5


def eligible_times(event_time, previous_time, run_start):
    first = event_time - OFFSETS_BEFORE_S[0]
    if first < run_start:
        return None, "abstain_run_boundary"
    if previous_time is not None and first < previous_time + PREVIOUS_EVENT_GUARD_S:
        return None, "abstain_previous_left_event"
    return [round(event_time - offset, 3) for offset in OFFSETS_BEFORE_S], None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
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
        for run_id, run_events in grouped.items():
            run_events.sort(key=lambda row: row["observation_time_s"])
            run_start = runs[run_id][0]
            for index, event in enumerate(run_events):
                previous_time = (run_events[index - 1]["observation_time_s"]
                                 if index else None)
                times, abstention = eligible_times(event["observation_time_s"],
                                                    previous_time, run_start)
                if times is None:
                    frames, maes, stable = [], [], []
                else:
                    frames, maes, stable, failure = sample_caps(cap, times)
                    abstention = failure
                status = abstention or ("partial_stable_colour_cap_proposals" if stable else
                                        "no_stable_colour_cap_proposals")
                rows.append({
                    "candidate_id": event["candidate_id"],
                    "left_event_id": event["left_event_id"],
                    "run_id": run_id,
                    "observed_left_passage_time_s": event["observation_time_s"],
                    "previous_left_passage_time_s": previous_time,
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
                })
    finally:
        cap.release()
    rows.sort(key=lambda row: row["observed_left_passage_time_s"])
    result = {
        "status": "source_video_pre_left_candidate_partial_cap_scan_not_board_truth",
        "source_sha256": source_hash,
        "candidate_sequence_sha256": digest(args.sequence),
        "post_sampler_code_sha256": digest(ROOT / "prototype/scripts/scan_full_match_split_post_event_caps.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_offsets_before_left_passage_s": list(OFFSETS_BEFORE_S),
        "previous_left_event_guard_s": PREVIOUS_EVENT_GUARD_S,
        "candidate_roi_xyxy": list(CAP_ROI),
        "scene_comparison_roi_xyxy": list(SCENE_ROI),
        "max_scene_mae_for_observation": MAX_SCENE_MAE,
        "candidate_count": len(rows),
        "observation_status_counts": dict(Counter(row["observation_status"] for row in rows)),
        "stable_cap_proposal_count": sum(len(row["stable_cap_proposals"]) for row in rows),
        "rows": rows,
        "limitations": [
            "The fixed post-event right-panel sampler was reused without changing colour or stability thresholds.",
            "An intervening missed delivery is not excluded by the previous-left-event guard.",
            "Stable colour caps are partial image observations and may be nonstones.",
            "No physical pre-throw board, stone identity, or game state is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": result["candidate_count"],
                      "statuses": result["observation_status_counts"],
                      "stable_caps": result["stable_cap_proposal_count"]}))


if __name__ == "__main__":
    main()
