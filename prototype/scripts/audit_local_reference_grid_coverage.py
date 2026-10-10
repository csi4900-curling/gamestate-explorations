"""Audit a selected local camera reference over the full fixed source grid.

This samples source time, not event candidates. It diagnoses registration
coverage and never upgrades a throw candidate or validates rink geometry.
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
from adaptive_view_reference import rebase_view_calibrator  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--anchor-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    selection = json.loads(args.anchor_selection.read_text())
    video_hash = file_sha256(args.video)
    if selection["video_sha256"] != video_hash or selection["view"] != "right":
        parser.error("Right-view selection does not match video")
    anchor_t = selection["selected_anchor_time_s"]
    if anchor_t is None:
        parser.error("No selected reference")
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    if (selection["calibration_sha256"] != file_sha256(cfg_path) or
            selection["rectification_sha256"] != file_sha256(rect_path)):
        parser.error("Selection uses different calibration")
    view = dict(json.loads(cfg_path.read_text())["views"]["right"])
    view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
    base = ViewCalibrator(view, ROOT / "prototype/vision/frames")
    base.H = np.asarray(json.loads(rect_path.read_text())["right"]["refined_H"])
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)

    def read_time(t):
        capture.set(cv2.CAP_PROP_POS_FRAMES,
                    round((t - selection["source_offset_s"]) * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode source time {t}")
        return frame

    try:
        local, bridge = rebase_view_calibrator(
            base, read_time(anchor_t),
            max_corner_displacement_px=selection["max_corner_displacement_px"])
        rows = []
        for old in selection["rows"]:
            t = old["source_time_s"]
            _, registration = local.register(
                read_time(t), is_reference=t == anchor_t,
                max_corner_displacement_px=selection["max_corner_displacement_px"])
            rows.append({
                "source_time_s": t,
                "original_status": old["status"],
                "original_reason": old["reason"],
                "local_status": registration["status"],
                "local_reason": registration.get("reason"),
                "local_inliers": registration.get("inliers"),
                "local_rmse_px": registration.get("rmse_px"),
            })
    finally:
        capture.release()
    by_pair = Counter((r["original_status"], r["local_status"]) for r in rows)
    by_local_reason = Counter(r["local_reason"] for r in rows
                              if r["local_status"] == "rejected")
    result = {
        "status": "postscore_source_grid_registration_diagnostic_not_event_validation",
        "video_sha256": video_hash,
        "anchor_selection_sha256": file_sha256(args.anchor_selection),
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "registration_code_sha256": file_sha256(ROOT / "prototype/vision_core.py"),
        "rebase_code_sha256": file_sha256(ROOT / "prototype/adaptive_view_reference.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "sample_rule": "all original fixed-grid timestamps, including unregistered originals",
        "sample_count": len(rows),
        "anchor_time_s": anchor_t,
        "anchor_bridge": bridge,
        "original_registration_count": sum(r["original_status"] == "registered" for r in rows),
        "local_registration_count": sum(r["local_status"] in ("registered", "reference") for r in rows),
        "status_pairs": {f"{a} -> {b}": n for (a, b), n in sorted(by_pair.items())},
        "local_rejection_reasons": dict(sorted(by_local_reason.items())),
        "rows": rows,
        "limitations": [
            "Frames and source are exposed postscore development data, not a new held-out test.",
            "Fixed 10-second samples do not measure registration at every video frame.",
            "Successful feature registration is not a measured rink homography or throw detection.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["sample_count"], result["original_registration_count"],
          result["local_registration_count"], result["local_rejection_reasons"])


if __name__ == "__main__":
    main()
