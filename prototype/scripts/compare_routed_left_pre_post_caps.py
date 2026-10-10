"""Compare bounded left-house cap sets around routed split-view candidates."""

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

SCENE_ROI_XYXY = (0, 70, 320, 130)
MAX_CROSS_SCENE_MAE = 10
MAX_CAP_MATCH_DISTANCE_PX = 5


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scene_patch(cap, time_s):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * 30))
    ok, frame = cap.read()
    if not ok or frame.shape != (360, 640, 3):
        raise RuntimeError(f"Cannot decode source at {time_s}")
    x1, y1, x2, y2 = SCENE_ROI_XYXY
    return frame[y1:y2, x1:x2].astype(np.int16)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "routes", "pre", "post", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    routes = json.loads(args.routes.read_text())
    pre = json.loads(args.pre.read_text())
    post = json.loads(args.post.read_text())
    source_hash = digest(args.video)
    if (len({source_hash, routes["source_sha256"], pre["source_sha256"],
             post["source_sha256"]}) != 1 or
            pre["routes_sha256"] != digest(args.routes) or
            post["routes_sha256"] != digest(args.routes) or
            pre["sequence_sha256"] != post["sequence_sha256"]):
        raise ValueError("Pre/post/route provenance differs")
    pre_by_id = {row["candidate_id"]: row for row in pre["rows"]}
    post_by_id = {row["candidate_id"]: row for row in post["rows"]}
    left_ids = {row["candidate_id"] for row in routes["rows"]
                if row["conditional_receiving_view"] == "left"}
    if (len(pre_by_id) != len(pre["rows"]) or
            len(post_by_id) != len(post["rows"]) or
            set(pre_by_id) != left_ids or set(post_by_id) != left_ids):
        raise ValueError("Pre/post scans do not cover exactly the left routes")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps source")
    rows = []
    try:
        for route in routes["rows"]:
            cid = route["candidate_id"]
            if cid not in left_ids:
                continue
            before, after = pre_by_id[cid], post_by_id[cid]
            if before["status"].startswith("abstain_") or after["status"].startswith("abstain_"):
                mae = None
            else:
                a = scene_patch(cap, before["sample_times_s"][1])
                b = scene_patch(cap, after["sample_times_s"][1])
                mae = float(np.mean(np.abs(a - b)))
            before_view = {"candidate_id": cid,
                           "coordinate_frame": "full_source_left_camera_pixels_not_metric",
                           "observation_status": before["status"],
                           "stable_cap_proposals": before["stable_cap_proposals"]}
            after_view = {"candidate_id": cid,
                          "coordinate_frame": "full_source_left_camera_pixels_not_metric",
                          "observation_status": after["status"],
                          "stable_cap_proposals": after["stable_cap_proposals"]}
            rows.append(compare_observation_rows(
                before_view, after_view, mae, max_scene_mae=MAX_CROSS_SCENE_MAE,
                max_distance_px=MAX_CAP_MATCH_DISTANCE_PX))
    finally:
        cap.release()
    output = {
        "status": "postreview_partial_left_image_cap_delta_not_physical_state",
        "source_sha256": source_hash,
        "routes_sha256": digest(args.routes),
        "pre_sha256": digest(args.pre),
        "post_sha256": digest(args.post),
        "comparator_code_sha256": digest(ROOT / "prototype/split_partial_cap_transition.py"),
        "runner_sha256": digest(Path(__file__)),
        "scene_roi_xyxy_360p": SCENE_ROI_XYXY,
        "max_cross_scene_mae": MAX_CROSS_SCENE_MAE,
        "max_cap_match_distance_px": MAX_CAP_MATCH_DISTANCE_PX,
        "status_counts": dict(Counter(row["comparison_status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Top-ice scene ROI and MAE cutoff were chosen after Estonia S38 source review.",
            "Retained or new colour blobs can be rink graphics, players or occluded stones.",
            "Image-position matching does not establish persistent physical stone identity.",
            "Unobserved deliveries between the bounded samples remain possible.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"source": routes["source_id"],
                      "statuses": output["status_counts"]}))


if __name__ == "__main__":
    main()
