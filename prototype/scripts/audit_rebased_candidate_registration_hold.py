"""Retry rejected rebased frames using same-shot ice-stable camera transforms."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from adaptive_view_reference import rebase_view_calibrator  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from registration_hold import ice_similarity  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--max-anchor-gap-s", type=float, default=10.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Registration hold audit already exists")
    original = json.loads(args.motion.read_text())
    if (
        original.get("detection_background")
        != "original_clean_reference_transported_to_current_frame"
    ):
        parser.error("Motion scan does not use clean-reference rebased geometry")
    if file_sha256(args.video) != original["high_resolution_source_sha256"]:
        parser.error("Source differs from candidate motion audit")
    cfg = json.loads((ROOT / "prototype/vision/annotations/calibration.json").read_text())["views"]
    refined = json.loads((ROOT / "prototype/rectification/calibration.json").read_text())
    calibrators = {}
    original_H = {}
    clean_reference = {}
    for name in ("left", "right"):
        view = dict(cfg[name])
        if name == "right":
            view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
        cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
        cal.H = np.array(refined[name]["refined_H"])
        calibrators[name] = cal
        original_H[name] = cal.H.copy()
        clean_reference[name] = cal.reference.copy()
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        anchor_time = original["right_reference_anchor_time_s"]
        capture.set(
            cv2.CAP_PROP_POS_FRAMES, round((anchor_time - original["source_offset_s"]) * fps)
        )
        ok, anchor_frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode right-camera anchor {anchor_time}")
        calibrators["right"], anchor_registration = rebase_view_calibrator(
            calibrators["right"],
            anchor_frame,
            max_corner_displacement_px=original["max_corner_displacement_px"],
        )
        for event in original["rows"]:
            view_name = event["receiving_view"]
            cal = calibrators[view_name]
            frames = {}

            def frame_at(t):
                if t not in frames:
                    capture.set(
                        cv2.CAP_PROP_POS_FRAMES, round((t - original["source_offset_s"]) * fps)
                    )
                    ok, frame = capture.read()
                    if not ok:
                        raise RuntimeError(f"Cannot decode {t}")
                    frames[t] = frame
                return frames[t]

            anchors = []
            for sample in event["samples"]:
                if sample["registration_status"] != "registered":
                    continue
                t = sample["source_time_s"]
                frame = frame_at(t)
                H, registration = cal.register(
                    frame, max_corner_displacement_px=original["max_corner_displacement_px"]
                )
                if H is None:
                    raise ValueError(f"Previously accepted registration changed at {t}")
                anchors.append({"time_s": t, "frame": frame, "H": H})
            samples = []
            for old in event["samples"]:
                t = old["source_time_s"]
                proposals = old["views"][view_name]["proposals"]
                record = {
                    "source_time_s": t,
                    "original_registration_status": old["registration_status"],
                    "views": {view_name: {"proposals": proposals}},
                }
                if old["registration_status"] == "registered":
                    record["status"] = "original_registered"
                else:
                    target = frame_at(t)
                    options = sorted(
                        (
                            anchor
                            for anchor in anchors
                            if abs(anchor["time_s"] - t) <= args.max_anchor_gap_s
                        ),
                        key=lambda anchor: abs(anchor["time_s"] - t),
                    )
                    record["status"] = "abstained_no_stable_anchor"
                    record["tried_anchor_count"] = 0
                    for anchor in options:
                        similarity = ice_similarity(target, anchor["frame"])
                        record["tried_anchor_count"] += 1
                        if not similarity["accepted"]:
                            continue
                        A = np.linalg.inv(anchor["H"]) @ original_H[view_name]
                        background = cv2.warpPerspective(
                            clean_reference[view_name], A, (target.shape[1], target.shape[0])
                        )
                        prior = transported_reference_camera(
                            original_H[view_name], anchor["H"], cal.view["region"]
                        )
                        found, _ = detect_and_localize(
                            target, anchor["H"], cal.view, background, prior
                        )
                        record["views"][view_name]["proposals"] = [
                            {
                                "colour": p["colour"],
                                "pixel_center": p["pixel_center"],
                                "ground_position_m": p["ground_position_m"],
                            }
                            for p in found
                        ]
                        record.update(
                            status="borrowed_transform_with_ice_similarity",
                            anchor_time_s=anchor["time_s"],
                            anchor_gap_s=abs(anchor["time_s"] - t),
                            similarity=similarity,
                        )
                        break
                samples.append(record)
            kwargs = (
                {
                    "view": "left",
                    "entry_y_threshold_m": -4.5,
                    "forward_direction": 1,
                    "min_samples": 4,
                    "max_forward_speed_change_m_s": 2.0,
                }
                if view_name == "left"
                else {"view": "right"}
            )
            selection = select_far_entry_motion_path(
                samples, event["colour"], max_gap_s=original["sample_period_s"] + 0.1, **kwargs
            )
            rows.append(
                {
                    "candidate_id": event["candidate_id"],
                    "colour": event["colour"],
                    "receiving_view": view_name,
                    "original_motion_status": event["selection"]["status"],
                    "selection": selection,
                    "borrowed_sample_count": sum(
                        sample["status"] == "borrowed_transform_with_ice_similarity"
                        for sample in samples
                    ),
                    "still_abstained_sample_count": sum(
                        sample["status"] == "abstained_no_stable_anchor" for sample in samples
                    ),
                    "samples": samples,
                }
            )
            print(event["candidate_id"], selection["status"], flush=True)
    finally:
        capture.release()
    result = {
        "status": "postscore_development_rebased_hold_not_physical_validation",
        "motion_sha256": file_sha256(args.motion),
        "source_video_sha256": original["high_resolution_source_sha256"],
        "right_reference_anchor_time_s": anchor_time,
        "right_reference_anchor_registration": anchor_registration,
        "rebase_code_sha256": file_sha256(ROOT / "prototype/adaptive_view_reference.py"),
        "detection_background": original["detection_background"],
        "max_anchor_gap_s": args.max_anchor_gap_s,
        "similarity_code_sha256": file_sha256(ROOT / "prototype/registration_hold.py"),
        "runner_sha256": file_sha256(__file__),
        "selection_status_counts": dict(Counter(row["selection"]["status"] for row in rows)),
        "borrowed_sample_count": sum(r["borrowed_sample_count"] for r in rows),
        "rows": rows,
        "limitations": [
            "Transform reuse is explicit and conditional on a same-shot lower-ice similarity check, not independent target-frame registration.",
            "This rebased branch was developed after Scotland's frozen transfer failed and cannot repair its transfer score.",
            "A stable camera does not validate cap identity or metric stone-centre accuracy.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["selection_status_counts"], "borrowed", result["borrowed_sample_count"])


if __name__ == "__main__":
    main()
