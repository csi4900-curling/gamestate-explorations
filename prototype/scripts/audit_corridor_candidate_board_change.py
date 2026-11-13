"""Board-view image-change features for all saved 2024 corridor proposals.

This runner reads prediction timestamps and source pixels only. Reference
windows are deliberately absent; scoring is a later separate operation.
"""

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
from right_view_partial_board import stable_cap_candidates
from scripts.probe_static_left_right_cap_motion import right_colour_proposals
from split_left_cap_proposals import LEFT_ROI_XYXY, left_colour_cap_proposals
from split_partial_cap_transition import compare_observation_rows

PRE_OFFSETS_S = (-35, -30, -25)
POST_OFFSETS_S = (25, 30, 35)
ADJACENT_CANDIDATE_GUARD_S = 1
LEFT_SCENE_ROI = (0, 70, 320, 130)
RIGHT_SCENE_ROI = (330, 155, 630, 245)
MAX_SCENE_MAE = {"left": 10, "right": 20}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def conditional_receiving_view(direction):
    if direction == "positive_y":
        return "left"
    if direction == "negative_y":
        return "right"
    return None


def frame_at(cap, time_s):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * 30))
    ok, frame = cap.read()
    if not ok or frame.shape != (360, 640, 3):
        raise RuntimeError(f"Cannot decode source at {time_s}")
    return frame


def proposals(frame, view):
    if view == "left":
        return left_colour_cap_proposals(frame)
    right = right_colour_proposals(frame)
    return [{"colour": colour, **proposal} for colour, items in right.items() for proposal in items]


def scene_patch(frame, view):
    x1, y1, x2, y2 = LEFT_SCENE_ROI if view == "left" else RIGHT_SCENE_ROI
    return frame[y1:y2, x1:x2].astype(np.int16)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "candidates", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    predictions = json.loads(args.candidates.read_text())
    if predictions["source_sha256"] != digest(args.video):
        raise ValueError("Source video differs from candidate artifact")
    candidates = sorted(predictions["events"], key=lambda row: row["crossing_time_s"])
    if len({row["id"] for row in candidates}) != len(candidates):
        raise ValueError("Duplicate candidate ID")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps source")
    rows = []
    try:
        for i, candidate in enumerate(candidates):
            t = candidate["crossing_time_s"]
            view = conditional_receiving_view(candidate["view_motion"])
            previous_t = (
                candidates[i - 1]["crossing_time_s"] if i else predictions["source_interval_s"][0]
            )
            next_t = (
                candidates[i + 1]["crossing_time_s"]
                if i + 1 < len(candidates)
                else predictions["source_interval_s"][1]
            )
            item = {
                "candidate_id": candidate["id"],
                "crossing_time_s": t,
                "colour_claim": candidate["colour"],
                "source_motion_direction": candidate["view_motion"],
                "conditional_receiving_view": view,
                "previous_candidate_time_s": previous_t,
                "next_candidate_time_s": next_t,
                "physical_throw_verified": False,
                "complete_board_verified": False,
                "simulation_ready": False,
            }
            pre_times = [round(t + offset, 3) for offset in PRE_OFFSETS_S]
            post_times = [round(t + offset, 3) for offset in POST_OFFSETS_S]
            if view is None:
                item["status"] = "abstain_unknown_direction"
            elif (
                pre_times[0] <= previous_t + ADJACENT_CANDIDATE_GUARD_S
                or post_times[-1] >= next_t - ADJACENT_CANDIDATE_GUARD_S
            ):
                item["status"] = "abstain_adjacent_candidate_or_interval_boundary"
            else:
                before_frames = [frame_at(cap, sample) for sample in pre_times]
                after_frames = [frame_at(cap, sample) for sample in post_times]
                before_samples = [
                    {"time_s": time_s, "cap_candidates": proposals(frame, view)}
                    for time_s, frame in zip(pre_times, before_frames)
                ]
                after_samples = [
                    {"time_s": time_s, "cap_candidates": proposals(frame, view)}
                    for time_s, frame in zip(post_times, after_frames)
                ]
                before_stable = stable_cap_candidates(before_samples)
                after_stable = stable_cap_candidates(after_samples)
                mae = float(
                    np.mean(
                        np.abs(
                            scene_patch(before_frames[1], view) - scene_patch(after_frames[1], view)
                        )
                    )
                )
                before = {
                    "candidate_id": candidate["id"],
                    "coordinate_frame": f"source_{view}_camera_pixels_not_metric",
                    "observation_status": "partial_repeated_caps"
                    if before_stable
                    else "no_repeated_caps",
                    "stable_cap_proposals": before_stable,
                }
                after = {
                    "candidate_id": candidate["id"],
                    "coordinate_frame": before["coordinate_frame"],
                    "observation_status": "partial_repeated_caps"
                    if after_stable
                    else "no_repeated_caps",
                    "stable_cap_proposals": after_stable,
                }
                transition = compare_observation_rows(
                    before, after, mae, max_scene_mae=MAX_SCENE_MAE[view], max_distance_px=5
                )
                item.update(
                    {
                        "status": transition["comparison_status"],
                        "pre_sample_times_s": pre_times,
                        "post_sample_times_s": post_times,
                        "pre_repeated_cap_count": len(before_stable),
                        "post_repeated_cap_count": len(after_stable),
                        "cross_window_scene_mae": transition["cross_window_scene_mae"],
                        "image_cap_delta": transition["image_cap_delta"],
                    }
                )
            rows.append(item)
    finally:
        cap.release()
    result = {
        "status": "postreview_prediction_only_board_change_features_not_event_truth",
        "source_id": predictions["source_id"],
        "source_sha256": predictions["source_sha256"],
        "source_interval_s": predictions["source_interval_s"],
        "candidates_sha256": digest(args.candidates),
        "proposal_code_sha256": {
            "left": digest(ROOT / "prototype/split_left_cap_proposals.py"),
            "right": digest(ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"),
        },
        "stability_code_sha256": digest(ROOT / "prototype/right_view_partial_board.py"),
        "transition_code_sha256": digest(ROOT / "prototype/split_partial_cap_transition.py"),
        "runner_sha256": digest(Path(__file__)),
        "pre_offsets_s": PRE_OFFSETS_S,
        "post_offsets_s": POST_OFFSETS_S,
        "adjacent_candidate_guard_s": ADJACENT_CANDIDATE_GUARD_S,
        "left_cap_roi_xyxy_360p": LEFT_ROI_XYXY,
        "scene_rois_xyxy_360p": {"left": LEFT_SCENE_ROI, "right": RIGHT_SCENE_ROI},
        "max_scene_mae": MAX_SCENE_MAE,
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "The view and sampling rules were developed after inspecting exposed 2024 recordings.",
            "Close candidate fragments are deliberately left unscored, which may remove hard false positives.",
            "Stable colour blobs include markings and people; image delta is not a physical stone transition.",
            "No reference labels were read by this feature runner.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"source": result["source_id"], "status_counts": result["status_counts"]}))


if __name__ == "__main__":
    main()
