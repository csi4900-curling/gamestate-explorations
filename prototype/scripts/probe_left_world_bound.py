"""Compare original and extended left-view bounds for one passage candidate.

This is an exposed-source diagnostic. It does not change the frozen screen or
establish stone identity, metric accuracy, precision, or recall.
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
from body_localization import detect_and_localize, transported_reference_camera  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from scripts.audit_candidate_centric_receiving_motion import sample_times  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402
from vision_core import ViewCalibrator  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-offset-s", type=float, default=0.0)
    parser.add_argument("--extended-min-y-m", type=float, default=-18.0)
    parser.add_argument("--sample-period-s", type=float, default=0.5)
    parser.add_argument("--lookahead-s", type=float, default=12.0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    if args.sample_period_s <= 0 or args.lookahead_s <= 0:
        parser.error("Sampling and lookahead must be positive")
    candidates = json.loads(args.candidates.read_text())
    candidate = next((row for row in candidates["events"] if row["id"] == args.candidate_id), None)
    if candidate is None or candidate["view_motion"] != "positive_y":
        parser.error("Candidate must exist and use the left receiving view")
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    base_view = json.loads(cfg_path.read_text())["views"]["left"]
    if args.extended_min_y_m >= base_view["world_bounds"][1]:
        parser.error("Extended minimum must be below the original minimum")
    wide_view = dict(base_view)
    wide_view["world_bounds"] = list(base_view["world_bounds"])
    wide_view["world_bounds"][1] = args.extended_min_y_m
    cal = ViewCalibrator(base_view, ROOT / "prototype/vision/frames")
    cal.H = np.array(json.loads(rect_path.read_text())["left"]["refined_H"])
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    times = sample_times(
        candidate["crossing_time_s"],
        candidates["source_interval_s"][1],
        args.lookahead_s,
        args.sample_period_s,
    )
    samples = {name: [] for name in ("base", "extended")}
    try:
        for source_time_s in times:
            capture.set(
                cv2.CAP_PROP_POS_FRAMES, round((source_time_s - args.source_offset_s) * fps)
            )
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source time {source_time_s}")
            H, registration = cal.register(frame, max_corner_displacement_px=160)
            background = prior = None
            if H is not None:
                transform = np.linalg.inv(H) @ cal.H
                background = cv2.warpPerspective(
                    cal.reference, transform, (frame.shape[1], frame.shape[0])
                )
                prior = transported_reference_camera(cal.H, H, cal.view["region"])
            for name, view in (("base", base_view), ("extended", wide_view)):
                found, detail = detect_and_localize(frame, H, view, background, prior)
                colour = candidate["colour"]
                proposals = [
                    {
                        "colour": item["colour"],
                        "pixel_center": item["pixel_center"],
                        "ground_position_m": item["ground_position_m"],
                    }
                    for item in found
                ]
                samples[name].append(
                    {
                        "source_time_s": source_time_s,
                        "registration_status": registration["status"],
                        "views": {"left": {"proposals": proposals}},
                        "same_colour_proposal_count": sum(
                            item["colour"] == colour for item in found
                        ),
                        "same_colour_rejection_reasons": dict(
                            Counter(
                                item["reason"]
                                for item in detail.get("rejected", [])
                                if item["colour"] == colour
                            )
                        ),
                    }
                )
    finally:
        capture.release()
    cases = {}
    for name, rows in samples.items():
        selection = select_far_entry_motion_path(
            rows,
            candidate["colour"],
            view="left",
            max_gap_s=args.sample_period_s + 0.1,
            entry_y_threshold_m=-4.5,
            forward_direction=1,
            min_samples=4,
            max_forward_speed_change_m_s=2.0,
        )
        cases[name] = {
            "world_bounds_m": (base_view if name == "base" else wide_view)["world_bounds"],
            "selection": selection,
            "samples": rows,
        }
    output = {
        "status": "postscore_exposed_candidate_world_bound_diagnostic_not_validation",
        "candidate_id": args.candidate_id,
        "colour": candidate["colour"],
        "crossing_time_s": candidate["crossing_time_s"],
        "sample_period_s": args.sample_period_s,
        "lookahead_s": args.lookahead_s,
        "source_offset_s": args.source_offset_s,
        "source_sha256": file_sha256(args.video),
        "candidates_sha256": file_sha256(args.candidates),
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "detector_sha256": file_sha256(ROOT / "prototype/body_localization.py"),
        "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "cases": cases,
        "limitations": [
            "Expanded metric bounds were chosen after inspecting this source interval.",
            "Only the receiving proposal bound changes; this does not verify candidate or path identity.",
            "Metric positions outside the original calibration footprint have no independent accuracy validation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    for name, case in cases.items():
        print(
            name,
            case["selection"]["status"],
            sum(row["same_colour_proposal_count"] for row in case["samples"]),
        )


if __name__ == "__main__":
    main()
