"""Audit right-camera support at the times of accepted left-camera paths."""

import argparse
import json
from math import dist
from pathlib import Path
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from adaptive_view_reference import rebase_view_calibrator  # noqa: E402
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--motion", type=Path, required=True)
    p.add_argument("--source-motion", type=Path, required=True)
    p.add_argument("--screen", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--ids", nargs="+")
    p.add_argument("--comparison-radius-m", type=float, default=1.0)
    a = p.parse_args()
    if a.output.exists():
        p.error("Audit already exists")
    motion, screen, source = (
        json.loads(path.read_text()) for path in (a.motion, a.screen, a.source_motion)
    )
    if (
        file_sha256(a.video) != motion["high_resolution_source_sha256"]
        or file_sha256(a.motion) != screen["motion_sha256"]
        or file_sha256(a.source_motion) != motion["source_motion_sha256"]
    ):
        p.error("Video, motion and screen hashes do not chain")
    decisions = {row["candidate_id"]: row for row in screen["decisions"]}
    rows = {row["candidate_id"]: row for row in motion["rows"]}
    if len(decisions) != len(screen["decisions"]) or len(rows) != len(motion["rows"]):
        p.error("Repeated candidate ID")
    ids = a.ids or [
        pid
        for pid, decision in decisions.items()
        if decision["accepted"] and rows[pid]["receiving_view"] == "left"
    ]
    if len(ids) != len(set(ids)) or any(
        not decisions[pid]["accepted"] or rows[pid]["receiving_view"] != "left" for pid in ids
    ):
        p.error("IDs must be distinct accepted left-view candidates")
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    view = dict(json.loads(cfg_path.read_text())["views"]["right"])
    view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
    cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
    cal.H = np.array(json.loads(rect_path.read_text())["right"]["refined_H"])
    prior_H = cal.H.copy()
    clean_reference = cal.reference.copy()
    cap = cv2.VideoCapture(str(a.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        p.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)

    def frame_at(source_time_s):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round((source_time_s - source["source_offset_s"]) * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot read source time {source_time_s}")
        return frame

    try:
        anchor_time = source["right_reference_anchor_time_s"]
        cal, anchor_registration = rebase_view_calibrator(
            cal,
            frame_at(anchor_time),
            max_corner_displacement_px=source["max_corner_displacement_px"],
        )
        audit_rows = []
        for pid in ids:
            selected = rows[pid]
            samples = []
            path = selected["selection"].get("path") or []
            for node in path:
                xy = node["ground_position_m"]
                t = node["source_time_s"]
                if not (-1.975 <= xy[1] <= 22.0 and -2.375 <= xy[0] <= 2.375):
                    samples.append(
                        {"source_time_s": t, "status": "outside_right_view_conditional_bounds"}
                    )
                    continue
                frame = frame_at(t)
                H, registration = cal.register(
                    frame, max_corner_displacement_px=source["max_corner_displacement_px"]
                )
                record = {
                    "source_time_s": t,
                    "left_ground_position_m_conditional": xy,
                    "right_registration_status": registration["status"],
                }
                if H is None:
                    record["status"] = "right_registration_abstained"
                    samples.append(record)
                    continue
                A = np.linalg.inv(H) @ prior_H
                background = cv2.warpPerspective(
                    clean_reference, A, (frame.shape[1], frame.shape[0])
                )
                prior = transported_reference_camera(prior_H, H, cal.view["region"])
                proposals, details = detect_and_localize(frame, H, cal.view, background, prior)
                same = [
                    p
                    for p in proposals
                    if p["colour"] == selected["colour"] and p["ground_position_m"] is not None
                ]
                ranked = sorted(
                    ((dist(xy, p["ground_position_m"]), p) for p in same), key=lambda item: item[0]
                )
                record.update(
                    {
                        "status": "registered_right_view_sample",
                        "right_detection_branch": details.get("branch"),
                        "same_colour_proposal_count": len(same),
                        "nearest_distance_m_conditional": ranked[0][0] if ranked else None,
                        "nearest_right_ground_position_m_conditional": ranked[0][1][
                            "ground_position_m"
                        ]
                        if ranked
                        else None,
                        "nearest_right_pixel_center": ranked[0][1]["pixel_center"]
                        if ranked
                        else None,
                        "within_comparison_radius": bool(
                            ranked and ranked[0][0] <= a.comparison_radius_m
                        ),
                    }
                )
                samples.append(record)
            comparable = [s for s in samples if s["status"] == "registered_right_view_sample"]
            audit_rows.append(
                {
                    "candidate_id": pid,
                    "colour": selected["colour"],
                    "path_sample_count": len(path),
                    "inside_right_bounds_count": sum(
                        s["status"] != "outside_right_view_conditional_bounds" for s in samples
                    ),
                    "registered_right_sample_count": len(comparable),
                    "nearby_same_colour_sample_count": sum(
                        s["within_comparison_radius"] for s in comparable
                    ),
                    "samples": samples,
                }
            )
    finally:
        cap.release()
    output = {
        "status": "postscore_opposite_view_support_diagnostic_not_event_validation",
        "source_id": screen["source_id"],
        "source_sha256": screen["source_sha256"],
        "high_resolution_source_sha256": file_sha256(a.video),
        "motion_sha256": file_sha256(a.motion),
        "source_motion_sha256": file_sha256(a.source_motion),
        "screen_sha256": file_sha256(a.screen),
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "runner_sha256": file_sha256(Path(__file__)),
        "anchor_time_s": anchor_time,
        "anchor_registration": anchor_registration,
        "comparison_radius_m_conditional": a.comparison_radius_m,
        "candidate_count": len(audit_rows),
        "rows": audit_rows,
        "limitations": [
            "Both camera projections are conditional and their common coordinate frame is not metrically validated.",
            "A nearby same-colour proposal does not prove the same physical stone, and an absent proposal does not prove no stone.",
            "The right camera may be occluded or have no usable registration even when the left path is real.",
            "This recording has been inspected; diagnostic thresholds are not independent validation.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        len(audit_rows),
        "left candidates",
        [
            (
                r["candidate_id"],
                r["registered_right_sample_count"],
                r["nearby_same_colour_sample_count"],
            )
            for r in audit_rows
        ],
    )


if __name__ == "__main__":
    main()
