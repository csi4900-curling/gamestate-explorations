"""Development scan using a registered local right-camera reference."""

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
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from scripts.audit_candidate_centric_receiving_motion import sample_times  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--source-offset", type=float, required=True)
    p.add_argument("--right-anchor-time", type=float, required=True)
    p.add_argument("--lookahead-s", type=float, default=12.0)
    p.add_argument("--sample-period-s", type=float, default=0.5)
    p.add_argument("--max-corner-displacement-px", type=float, default=160.0)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Rebased scan already exists")
    candidates = json.loads(a.candidates.read_text())
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    views = json.loads(cfg_path.read_text())["views"]
    refined = json.loads(rect_path.read_text())
    calibrators = {}
    for name in ("left", "right"):
        view = dict(views[name])
        if name == "right":
            view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
        cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
        cal.H = np.array(refined[name]["refined_H"])
        calibrators[name] = cal
    camera_prior_reference_H = {name: cal.H.copy()
                                for name, cal in calibrators.items()}
    clean_reference_images = {name: cal.reference.copy()
                              for name, cal in calibrators.items()}
    capture = cv2.VideoCapture(str(a.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        p.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES,
                    round((a.right_anchor_time - a.source_offset) * fps))
        ok, anchor_frame = capture.read()
        if not ok:
            raise RuntimeError("Cannot decode right-camera anchor")
        calibrators["right"], anchor_registration = rebase_view_calibrator(
            calibrators["right"], anchor_frame,
            max_corner_displacement_px=a.max_corner_displacement_px)
        rows = []
        for candidate in candidates["events"]:
            view_name = {"positive_y": "left", "negative_y": "right"}.get(
                candidate["view_motion"])
            if view_name is None:
                raise ValueError(f"Unknown view direction for {candidate['id']}")
            cal = calibrators[view_name]
            samples = []
            for t in sample_times(candidate["crossing_time_s"],
                                  candidates["source_interval_s"][1],
                                  a.lookahead_s, a.sample_period_s):
                capture.set(cv2.CAP_PROP_POS_FRAMES,
                            round((t - a.source_offset) * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode source time {t}")
                H, registration = cal.register(
                    frame, max_corner_displacement_px=a.max_corner_displacement_px)
                proposals = []
                if H is not None:
                    A = np.linalg.inv(H) @ camera_prior_reference_H[view_name]
                    background = cv2.warpPerspective(
                        clean_reference_images[view_name], A,
                        (frame.shape[1], frame.shape[0]))
                    prior = transported_reference_camera(
                        camera_prior_reference_H[view_name], H,
                        cal.view["region"])
                    found, _ = detect_and_localize(
                        frame, H, cal.view, background, prior)
                    proposals = [{"colour": row["colour"],
                                  "pixel_center": row["pixel_center"],
                                  "ground_position_m": row["ground_position_m"]}
                                 for row in found]
                samples.append({"source_time_s": t,
                                "registration_status": registration["status"],
                                "registration_reason": registration.get("reason"),
                                "views": {view_name: {"proposals": proposals}}})
            kwargs = ({"view": "left", "entry_y_threshold_m": -4.5,
                       "forward_direction": 1, "min_samples": 4,
                       "max_forward_speed_change_m_s": 2.0}
                      if view_name == "left" else {"view": "right"})
            selection = select_far_entry_motion_path(
                samples, candidate["colour"],
                max_gap_s=a.sample_period_s + 0.1, **kwargs)
            rows.append({"candidate_id": candidate["id"],
                         "crossing_time_s": candidate["crossing_time_s"],
                         "colour": candidate["colour"],
                         "view_motion": candidate["view_motion"],
                         "receiving_view": view_name,
                         "sample_count": len(samples),
                         "registration_abstentions": sum(
                             sample["registration_status"] != "registered"
                             for sample in samples),
                         "selection": selection,
                         "samples": samples})
            print(candidate["id"], selection["status"], flush=True)
    finally:
        capture.release()
    result = {
        "status": "postscore_development_rebased_right_reference_not_transfer_validation",
        "candidate_source_id": candidates["source_id"],
        "candidate_source_sha256": candidates["source_sha256"],
        "high_resolution_source_sha256": file_sha256(a.video),
        "source_offset_s": a.source_offset,
        "lookahead_s": a.lookahead_s,
        "sample_period_s": a.sample_period_s,
        "max_corner_displacement_px": a.max_corner_displacement_px,
        "candidates_sha256": file_sha256(a.candidates),
        "vision_calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "registration_code_sha256": file_sha256(ROOT / "prototype/vision_core.py"),
        "detector_code_sha256": file_sha256(ROOT / "prototype/body_localization.py"),
        "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "rebase_code_sha256": file_sha256(ROOT / "prototype/adaptive_view_reference.py"),
        "right_reference_anchor_time_s": a.right_anchor_time,
        "right_reference_anchor_registration": anchor_registration,
        "conditional_camera_prior": "original_calibration_transported_to_current_frame",
        "detection_background": "original_clean_reference_transported_to_current_frame",
        "candidate_count": len(rows),
        "selection_status_counts": dict(Counter(
            row["selection"]["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Anchor 2044.5 s was chosen after seeing this recording's frozen registration failures.",
            "The new reference is transported from an old conditional calibration, not independently measured rink geometry.",
            "A registered image and a selected cap path do not prove a physical throw.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["selection_status_counts"])


if __name__ == "__main__":
    main()
