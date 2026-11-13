"""Compare pre/post partial cap observations when the right scene is stable."""

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
from split_partial_cap_transition import compare_observation_rows

SCENE_ROI = (330, 155, 630, 245)
MAX_CROSS_SCENE_MAE = 20
MAX_CAP_MATCH_DISTANCE_PX = 5


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def scene_patch(cap, time_s):
    cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
    ok, frame = cap.read()
    if not ok or frame.shape[:2] != (360, 640):
        return None
    x0, y0, x1, y1 = SCENE_ROI
    return frame[y0:y1, x0:x1].astype(np.int16)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "sequence", "pre", "post", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    sequence = json.loads(args.sequence.read_text())
    pre = json.loads(args.pre.read_text())
    post = json.loads(args.post.read_text())
    video_hash = digest(args.video)
    sequence_hash = digest(args.sequence)
    if (
        len({video_hash, sequence["source_sha256"], pre["source_sha256"], post["source_sha256"]})
        != 1
        or pre["candidate_sequence_sha256"] != sequence_hash
        or post["candidate_sequence_sha256"] != sequence_hash
    ):
        parser.error("Source or candidate sequence fingerprints differ")
    pre_by_id = {row["candidate_id"]: row for row in pre["rows"]}
    post_by_id = {row["candidate_id"]: row for row in post["rows"]}
    left_ids = {
        row["candidate_id"]
        for row in sequence["rows"]
        if row["observation_kind"] == "left_tracked_passage"
    }
    if (
        len(pre_by_id) != len(pre["rows"])
        or len(post_by_id) != len(post["rows"])
        or set(pre_by_id) != set(post_by_id)
        or set(pre_by_id) != left_ids
    ):
        parser.error("Pre/post scans must cover every left candidate exactly once")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable source video")
    rows = []
    try:
        for event in sequence["rows"]:
            if event["candidate_id"] not in left_ids:
                continue
            before = pre_by_id[event["candidate_id"]]
            after = post_by_id[event["candidate_id"]]
            if (
                before["observed_left_passage_time_s"] != event["observation_time_s"]
                or after["observed_left_passage_time_s"] != event["observation_time_s"]
            ):
                parser.error("Scan event time differs from sequence")
            if before["observation_status"].startswith("abstain_") or after[
                "observation_status"
            ].startswith("abstain_"):
                mae = None
            else:
                a = scene_patch(cap, before["sample_times_s"][1])
                b = scene_patch(cap, after["sample_times_s"][1])
                mae = float(np.mean(np.abs(a - b))) if a is not None and b is not None else None
                if mae is None:
                    rows.append(
                        {
                            "candidate_id": event["candidate_id"],
                            "comparison_status": "abstain_cross_window_decode_failure",
                            "cross_window_scene_mae": None,
                            "image_cap_delta": None,
                            "physical_transition_verified": False,
                            "complete_board_verified": False,
                            "simulation_ready": False,
                        }
                    )
                    continue
            rows.append(
                compare_observation_rows(
                    before,
                    after,
                    mae,
                    max_scene_mae=MAX_CROSS_SCENE_MAE,
                    max_distance_px=MAX_CAP_MATCH_DISTANCE_PX,
                )
            )
    finally:
        cap.release()
    result = {
        "status": "partial_image_cap_transition_diagnostic_not_physical_state",
        "source_sha256": video_hash,
        "input_sha256": {
            "candidate_sequence": sequence_hash,
            "pre_cap_scan": digest(args.pre),
            "post_cap_scan": digest(args.post),
        },
        "model_code_sha256": digest(ROOT / "prototype/split_partial_cap_transition.py"),
        "runner_sha256": digest(Path(__file__)),
        "cross_window_scene_roi_xyxy": list(SCENE_ROI),
        "max_cross_window_scene_mae": MAX_CROSS_SCENE_MAE,
        "max_cap_match_distance_px": MAX_CAP_MATCH_DISTANCE_PX,
        "candidate_count": len(rows),
        "comparison_status_counts": dict(Counter(row["comparison_status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "A low scene MAE cannot prove identical camera geometry or unoccluded stones.",
            "Newly/no-longer observed caps may reflect occlusion, handling, tracking error, or a missed throw.",
            "Local same-colour pixel proximity does not establish persistent physical stone identity.",
            "No complete pre/post board or simulation-ready game-state transition is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidates": result["candidate_count"],
                "statuses": result["comparison_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
