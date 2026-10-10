"""Compare frozen and fixed-grid-selected registration on candidate frames.

This is a postscore diagnostic of image registration, not an event score.
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
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--anchor-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--first-samples", type=int, default=5)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Audit output already exists")
    motion = json.loads(args.motion.read_text())
    selected = json.loads(args.anchor_selection.read_text())
    video_sha = file_sha256(args.video)
    if video_sha != motion["high_resolution_source_sha256"]:
        parser.error("Video differs from motion-scan source")
    if selected["video_sha256"] != video_sha or selected["view"] != "right":
        parser.error("Anchor selection does not match right-view source")
    if selected["selected_anchor_time_s"] is None:
        parser.error("No source-only anchor was selected")
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    if (
        file_sha256(cfg_path) != motion["vision_calibration_sha256"]
        or file_sha256(rect_path) != motion["rectification_sha256"]
    ):
        parser.error("Calibration differs from motion scan")
    view = dict(json.loads(cfg_path.read_text())["views"]["right"])
    view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
    base = ViewCalibrator(view, ROOT / "prototype/vision/frames")
    base.H = np.array(json.loads(rect_path.read_text())["right"]["refined_H"])
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)

    def read_time(t):
        capture.set(cv2.CAP_PROP_POS_FRAMES, round((t - motion["source_offset_s"]) * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode source time {t}")
        return frame

    try:
        anchor_time = selected["selected_anchor_time_s"]
        local, anchor_registration = rebase_view_calibrator(
            base,
            read_time(anchor_time),
            max_corner_displacement_px=motion["max_corner_displacement_px"],
        )
        rows = []
        for candidate in motion["rows"]:
            if candidate["receiving_view"] != "right":
                continue
            for sample in candidate["samples"][: args.first_samples]:
                time = sample["source_time_s"]
                frame = read_time(time)
                _, old = base.register(
                    frame, max_corner_displacement_px=motion["max_corner_displacement_px"]
                )
                _, new = local.register(
                    frame, max_corner_displacement_px=motion["max_corner_displacement_px"]
                )
                rows.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "source_time_s": time,
                        "frozen_status": old["status"],
                        "frozen_reason": old.get("reason"),
                        "local_status": new["status"],
                        "local_reason": new.get("reason"),
                    }
                )
    finally:
        capture.release()
    counts = Counter((r["frozen_status"], r["local_status"]) for r in rows)
    result = {
        "status": "postscore_development_fixed_grid_registration_support_not_event_validation",
        "source_sha256": video_sha,
        "motion_sha256": file_sha256(args.motion),
        "anchor_selection_sha256": file_sha256(args.anchor_selection),
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "registration_code_sha256": file_sha256(ROOT / "prototype/vision_core.py"),
        "rebase_code_sha256": file_sha256(ROOT / "prototype/adaptive_view_reference.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "anchor_time_s": anchor_time,
        "anchor_registration": anchor_registration,
        "sample_rule": f"first {args.first_samples} receiving samples per right-view corridor candidate",
        "frame_count": len(rows),
        "candidate_count": len(set(r["candidate_id"] for r in rows)),
        "frozen_registered": sum(r["frozen_status"] == "registered" for r in rows),
        "local_registered": sum(r["local_status"] == "registered" for r in rows),
        "status_pairs": {f"{a} -> {b}": n for (a, b), n in sorted(counts.items())},
        "rows": rows,
        "limitations": [
            "The fixed-grid rule was defined after inspecting this recording; this is development, not untouched transfer.",
            "Registration support does not prove stone detection, event identity, or metric accuracy.",
            "Only the first candidate-local samples are audited; this is not a full-video denominator.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        result["frame_count"],
        result["frozen_registered"],
        result["local_registered"],
        result["status_pairs"],
    )


if __name__ == "__main__":
    main()
