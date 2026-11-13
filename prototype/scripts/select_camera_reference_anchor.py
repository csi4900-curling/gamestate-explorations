"""Select a recording-local reference from a fixed video grid, without events.

This development rule uses only camera-registration evidence. It makes no
claim about throw presence or metric calibration accuracy.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from vision_core import ViewCalibrator, project  # noqa: E402


def cluster_registered(rows, max_corner_distance_px):
    """Greedy complete-link clusters in fixed time order."""
    clusters = []
    for row in rows:
        if row["status"] != "registered":
            continue
        corners = np.asarray(row["current_corners_px"])
        for cluster in clusters:
            if all(
                np.max(np.linalg.norm(corners - np.asarray(member["current_corners_px"]), axis=1))
                <= max_corner_distance_px
                for member in cluster
            ):
                cluster.append(row)
                break
        else:
            clusters.append([row])
    return clusters


def select_anchor(clusters):
    if not clusters:
        return None, None
    chosen = sorted(clusters, key=lambda cluster: (-len(cluster), cluster[0]["source_time_s"]))[0]
    anchor = sorted(
        chosen, key=lambda row: (-row["inliers"], row["rmse_px"], row["source_time_s"])
    )[0]
    return chosen, anchor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-offset", type=float, required=True)
    parser.add_argument("--interval-start", type=float, required=True)
    parser.add_argument("--interval-end", type=float, required=True)
    parser.add_argument("--view", choices=("left", "right"), required=True)
    parser.add_argument("--period-s", type=float, default=10.0)
    parser.add_argument("--phase-s", type=float, default=5.0)
    parser.add_argument("--max-corner-displacement-px", type=float, default=160.0)
    parser.add_argument("--cluster-corner-distance-px", type=float, default=40.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Anchor selection output already exists")
    if args.period_s <= 0 or not 0 <= args.phase_s < args.period_s:
        parser.error("Invalid fixed-grid period or phase")
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    view = dict(json.loads(cfg_path.read_text())["views"][args.view])
    if args.view == "right":
        view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
    cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
    cal.H = np.asarray(json.loads(rect_path.read_text())[args.view]["refined_H"])
    x0, y0, x1, y1 = view["region"]
    corners = np.asarray([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        n = 0
        while True:
            t = args.interval_start + args.phase_s + n * args.period_s
            if t >= args.interval_end:
                break
            capture.set(cv2.CAP_PROP_POS_FRAMES, round((t - args.source_offset) * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source time {t}")
            _, registration = cal.register(
                frame, max_corner_displacement_px=args.max_corner_displacement_px
            )
            row = {
                "source_time_s": t,
                "status": registration["status"],
                "reason": registration.get("reason"),
                "inliers": registration.get("inliers"),
                "rmse_px": registration.get("rmse_px"),
            }
            if registration["status"] == "registered":
                A = np.asarray(registration["reference_to_current"])
                row["current_corners_px"] = project(A, corners).tolist()
            rows.append(row)
            print(t, row["status"], flush=True)
            n += 1
    finally:
        capture.release()
    clusters = cluster_registered(rows, args.cluster_corner_distance_px)
    chosen, anchor = select_anchor(clusters)
    output = {
        "status": "postscore_development_fixed_grid_anchor_not_event_validation",
        "video_sha256": file_sha256(args.video),
        "view": args.view,
        "source_offset_s": args.source_offset,
        "source_interval_s": [args.interval_start, args.interval_end],
        "period_s": args.period_s,
        "phase_s": args.phase_s,
        "max_corner_displacement_px": args.max_corner_displacement_px,
        "cluster_corner_distance_px": args.cluster_corner_distance_px,
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "registration_code_sha256": file_sha256(ROOT / "prototype/vision_core.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "sample_count": len(rows),
        "registration_status_counts": dict(Counter(r["status"] for r in rows)),
        "cluster_sizes": [len(group) for group in clusters],
        "selected_cluster_size": len(chosen) if chosen else 0,
        "selected_anchor_time_s": anchor["source_time_s"] if anchor else None,
        "selected_anchor_inliers": anchor["inliers"] if anchor else None,
        "rows": rows,
        "limitations": [
            "The rule was developed after inspection of this recording; only future untouched recordings can test transfer.",
            "Accepted feature registration and a dominant pose cluster do not prove that this view is useful for any throw.",
            "The rule inherits the original homography uncertainty and cannot validate rink-scale geometry.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        "selected anchor",
        output["selected_anchor_time_s"],
        "cluster size",
        output["selected_cluster_size"],
    )


if __name__ == "__main__":
    main()
