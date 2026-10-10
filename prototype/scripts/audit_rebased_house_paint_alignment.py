"""Compare a transported house projection with visible blue paint on fixed frames.

This is a source-pixel diagnostic, not independent metric stone-position validation.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from adaptive_view_reference import rebase_view_calibrator  # noqa: E402
from cache_contract import file_sha256  # noqa: E402
from vision_core import ViewCalibrator, project  # noqa: E402


TIMES_S = [1855.0, 2055.0, 2255.0, 2455.0, 2605.0, 2705.0]
SHIFTS_PX = [(100, 0), (-100, 0), (0, 30), (0, -30)]


def read_frame(capture, time_s, source_offset_s, fps):
    capture.set(cv2.CAP_PROP_POS_FRAMES, round((time_s - source_offset_s) * fps))
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Cannot decode frame at source time {time_s}")
    return frame


def ring_mask(shape, image_to_world):
    angles = np.linspace(0, 2 * np.pi, 257)
    world_to_image = np.linalg.inv(image_to_world)
    mask = np.zeros(shape[:2], np.uint8)
    for radius, value in [(1.829, 1), (1.219, 0)]:
        points = np.column_stack((radius * np.cos(angles),
                                  radius * np.sin(angles)))
        polygon = np.round(project(world_to_image, points)).astype(np.int32)
        cv2.fillPoly(mask, [polygon], value)
    return mask > 0


def overlap(paint, projection):
    intersection = int(np.count_nonzero(paint & projection))
    paint_count = int(np.count_nonzero(paint))
    projected_count = int(np.count_nonzero(projection))
    union = paint_count + projected_count - intersection
    return {
        "classified_blue_paint_pixels": paint_count,
        "projected_annulus_pixels": projected_count,
        "intersection_pixels": intersection,
        "blue_paint_inside_projection_fraction": intersection / paint_count if paint_count else None,
        "projection_classified_blue_fraction": intersection / projected_count if projected_count else None,
        "intersection_over_union": intersection / union if union else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--anchor-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    selection = json.loads(args.anchor_selection.read_text())
    if selection["view"] != "right" or selection["video_sha256"] != file_sha256(args.video):
        parser.error("Right-view anchor selection or source hash differs")
    offset = selection["source_offset_s"]
    if any(not selection["source_interval_s"][0] <= t <= selection["source_interval_s"][1]
           for t in TIMES_S):
        parser.error("Fixed sample time outside source interval")
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    view = dict(json.loads(cfg_path.read_text())["views"]["right"])
    view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
    base = ViewCalibrator(view, ROOT / "prototype/vision/frames")
    base.H = np.asarray(json.loads(rect_path.read_text())["right"]["refined_H"])
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    anchor_t = selection["selected_anchor_time_s"]
    anchor = read_frame(capture, anchor_t, offset, fps)
    local, anchor_registration = rebase_view_calibrator(
        base, anchor,
        max_corner_displacement_px=selection["max_corner_displacement_px"])
    samples = []
    for t in TIMES_S:
        frame = read_frame(capture, t, offset, fps)
        H, registration = local.register(
            frame, is_reference=t == anchor_t,
            max_corner_displacement_px=selection["max_corner_displacement_px"])
        record = {"source_time_s": t, "registration": registration}
        if H is not None:
            projection = ring_mask(frame.shape, H)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            # Broad blue threshold, fixed after the exploratory anchor-frame check.
            blue = cv2.inRange(hsv, np.array([90, 70, 70]),
                               np.array([120, 255, 255])) > 0
            roi = np.zeros(frame.shape[:2], bool)
            roi[470:630, 980:1910] = True
            blue &= roi
            record["overlap"] = overlap(blue, projection)
            controls = {}
            for dx, dy in SHIFTS_PX:
                shifted = cv2.warpAffine(projection.astype(np.uint8),
                                         np.float32([[1, 0, dx], [0, 1, dy]]),
                                         (frame.shape[1], frame.shape[0]),
                                         flags=cv2.INTER_NEAREST) > 0
                controls[f"{dx},{dy}"] = overlap(blue, shifted)["intersection_over_union"]
            record["shifted_control_iou"] = controls
        samples.append(record)
    capture.release()
    result = {
        "status": "postscore_paint_alignment_diagnostic_not_metric_validation",
        "source_sha256": file_sha256(args.video),
        "anchor_selection_sha256": file_sha256(args.anchor_selection),
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "rebase_code_sha256": file_sha256(ROOT / "prototype/adaptive_view_reference.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "anchor_time_s": anchor_t,
        "anchor_registration": anchor_registration,
        "paint_mask_hsv_opencv": {"lower": [90, 70, 70], "upper": [120, 255, 255]},
        "paint_roi_xyxy": [980, 470, 1910, 630],
        "projected_blue_annulus_radii_m": [1.219, 1.829],
        "samples": samples,
        "limitations": [
            "Blue paint is partly hidden by stones and players and varies with lighting; color segmentation is not a ground-truth ring mask.",
            "The sample frames and HSV threshold were chosen during development; shifted controls only test gross alignment.",
            "Paint alignment near the house does not validate distant ice-plane geometry, stone footprint centers, or inter-camera fusion.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {len(samples)} fixed-frame paint-alignment diagnostics to {args.output}")


if __name__ == "__main__":
    main()
