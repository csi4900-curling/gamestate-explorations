"""Prediction-only pre/post image-cap evidence around passage clusters."""

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
from candidate_motion_clusters import group_candidate_passages
from right_view_partial_board import stable_cap_candidates
from scripts.audit_corridor_candidate_board_change import (
    conditional_receiving_view, frame_at, proposals, scene_patch,
    MAX_SCENE_MAE,
)
from split_partial_cap_transition import compare_observation_rows

MAX_GROUP_SPAN_S = 25
PRE_OFFSETS_FROM_FIRST_S = (-25, -20, -15)
POST_OFFSETS_FROM_LAST_S = (15, 20, 25)
ADJACENT_GROUP_GUARD_S = 1


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "candidates", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    candidate_set = json.loads(args.candidates.read_text())
    if candidate_set["source_sha256"] != digest(args.video):
        raise ValueError("Source video differs from candidate artifact")
    groups = group_candidate_passages(candidate_set["events"],
                                      max_group_span_s=MAX_GROUP_SPAN_S)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps source")
    rows = []
    try:
        for index, group in enumerate(groups):
            first, last = group["first_time_s"], group["last_time_s"]
            prev_end = (groups[index - 1]["last_time_s"] if index else
                        candidate_set["source_interval_s"][0])
            next_start = (groups[index + 1]["first_time_s"]
                          if index + 1 < len(groups) else
                          candidate_set["source_interval_s"][1])
            view = conditional_receiving_view(group["view_motion"])
            row = dict(group, conditional_receiving_view=view,
                       previous_group_last_s=prev_end,
                       next_group_first_s=next_start,
                       complete_board_verified=False,
                       simulation_ready=False)
            pre_times = [round(first + offset, 3)
                         for offset in PRE_OFFSETS_FROM_FIRST_S]
            post_times = [round(last + offset, 3)
                          for offset in POST_OFFSETS_FROM_LAST_S]
            if view is None:
                row["status"] = "abstain_unknown_direction"
            elif (pre_times[0] <= prev_end + ADJACENT_GROUP_GUARD_S or
                  post_times[-1] >= next_start - ADJACENT_GROUP_GUARD_S):
                row["status"] = "abstain_adjacent_group_or_interval_boundary"
            else:
                before_frames = [frame_at(cap, t) for t in pre_times]
                after_frames = [frame_at(cap, t) for t in post_times]
                before_samples = [{"time_s": t,
                                   "cap_candidates": proposals(frame, view)}
                                  for t, frame in zip(pre_times, before_frames)]
                after_samples = [{"time_s": t,
                                  "cap_candidates": proposals(frame, view)}
                                 for t, frame in zip(post_times, after_frames)]
                before_caps = stable_cap_candidates(before_samples)
                after_caps = stable_cap_candidates(after_samples)
                mae = float(np.mean(np.abs(scene_patch(before_frames[1], view) -
                                           scene_patch(after_frames[1], view))))
                pre = {"candidate_id": group["group_id"],
                       "coordinate_frame": f"source_{view}_camera_pixels_not_metric",
                       "observation_status": "partial_repeated_caps" if before_caps
                                             else "no_repeated_caps",
                       "stable_cap_proposals": before_caps}
                post = {"candidate_id": group["group_id"],
                        "coordinate_frame": pre["coordinate_frame"],
                        "observation_status": "partial_repeated_caps" if after_caps
                                              else "no_repeated_caps",
                        "stable_cap_proposals": after_caps}
                comparison = compare_observation_rows(
                    pre, post, mae, max_scene_mae=MAX_SCENE_MAE[view],
                    max_distance_px=5)
                row.update({"status": comparison["comparison_status"],
                            "pre_sample_times_s": pre_times,
                            "post_sample_times_s": post_times,
                            "pre_repeated_cap_count": len(before_caps),
                            "post_repeated_cap_count": len(after_caps),
                            "cross_window_scene_mae": comparison["cross_window_scene_mae"],
                            "image_cap_delta": comparison["image_cap_delta"]})
            rows.append(row)
    finally:
        cap.release()
    result = {
        "status": "postreview_prediction_only_motion_cluster_board_change_not_event_truth",
        "source_id": candidate_set["source_id"],
        "source_sha256": candidate_set["source_sha256"],
        "source_interval_s": candidate_set["source_interval_s"],
        "candidates_sha256": digest(args.candidates),
        "group_code_sha256": digest(ROOT / "prototype/candidate_motion_clusters.py"),
        "pixel_feature_code_sha256": digest(
            ROOT / "prototype/scripts/audit_corridor_candidate_board_change.py"),
        "runner_sha256": digest(Path(__file__)),
        "max_group_span_s": MAX_GROUP_SPAN_S,
        "pre_offsets_from_first_s": PRE_OFFSETS_FROM_FIRST_S,
        "post_offsets_from_last_s": POST_OFFSETS_FROM_LAST_S,
        "adjacent_group_guard_s": ADJACENT_GROUP_GUARD_S,
        "group_count": len(rows),
        "multi_candidate_group_count": sum(len(row["member_ids"]) > 1 for row in rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "The 25-second grouping and cap rules were chosen on exposed 2024 examples.",
            "A cluster of passages is not one verified physical throw.",
            "Grouping can merge different real throws or leave false passages isolated.",
            "Image cap changes can arise from occlusion, player handling, or rink graphics.",
            "No reference labels were read by this feature runner.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"source": result["source_id"],
                      "groups": len(rows),
                      "multi": result["multi_candidate_group_count"],
                      "statuses": result["status_counts"]}))


if __name__ == "__main__":
    main()
