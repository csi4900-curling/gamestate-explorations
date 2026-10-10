"""Render conditional rink-marking projections for visual geometry diagnosis."""

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--anchor-selection", type=Path, required=True)
    parser.add_argument("--image-output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    args = parser.parse_args()
    if args.image_output.exists() or args.json_output.exists():
        parser.error("Overlay output exists")
    selection = json.loads(args.anchor_selection.read_text())
    source_sha = file_sha256(args.video)
    if source_sha != selection["video_sha256"] or selection["view"] != "right":
        parser.error("Anchor selection does not match right-view video")
    t = selection["selected_anchor_time_s"]
    if t is None:
        parser.error("No anchor selected")
    cfg_path = ROOT / "prototype/vision/annotations/calibration.json"
    rect_path = ROOT / "prototype/rectification/calibration.json"
    view = dict(json.loads(cfg_path.read_text())["views"]["right"])
    view["world_bounds"] = [-2.375, -1.975, 2.375, 22.0]
    cal = ViewCalibrator(view, ROOT / "prototype/vision/frames")
    cal.H = np.asarray(json.loads(rect_path.read_text())["right"]["refined_H"])
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    capture.set(cv2.CAP_PROP_POS_FRAMES,
                round((t - selection["source_offset_s"]) * fps))
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f"Cannot decode anchor at {t}")
    local, registration = rebase_view_calibrator(
        cal, frame,
        max_corner_displacement_px=selection["max_corner_displacement_px"])
    inv = np.linalg.inv(local.H)
    center = project(inv, [[0, 0]])[0]
    rings = {}
    overlay = frame.copy()
    for radius, name, colour in ((1.829, "outer_12ft", (40, 245, 40)),
                                  (1.219, "middle_8ft", (0, 200, 255)),
                                  (0.610, "inner_4ft", (250, 60, 220))):
        angles = np.linspace(0, 2 * np.pi, 129)
        world = np.column_stack((radius * np.cos(angles),
                                 radius * np.sin(angles)))
        points = project(inv, world)
        rings[name] = points[[0, 32, 64, 96]].tolist()
        cv2.polylines(overlay, [np.round(points).astype(np.int32)],
                      False, colour, 4, cv2.LINE_AA)
    cv2.drawMarker(overlay, tuple(np.round(center).astype(int)), (10, 10, 250),
                   cv2.MARKER_CROSS, 46, 4)
    cv2.putText(overlay, f"Conditional projection at {t:.1f} s", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (10, 10, 250), 2, cv2.LINE_AA)
    args.image_output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.image_output), overlay,
                       [cv2.IMWRITE_JPEG_QUALITY, 91]):
        raise RuntimeError("Cannot write overlay")
    result = {
        "status": "postscore_visual_geometry_diagnostic_not_metric_validation",
        "source_sha256": source_sha,
        "anchor_selection_sha256": file_sha256(args.anchor_selection),
        "calibration_sha256": file_sha256(cfg_path),
        "rectification_sha256": file_sha256(rect_path),
        "rebase_code_sha256": file_sha256(ROOT / "prototype/adaptive_view_reference.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "image_sha256": file_sha256(args.image_output),
        "anchor_time_s": t,
        "anchor_registration": registration,
        "projected_button_pixel": center.tolist(),
        "projected_ring_quadrants_pixel": rings,
        "limitations": [
            "The image overlays a transported old calibration; it does not measure independent landmark error.",
            "Visual agreement at one frame does not establish stone-centre or far-field accuracy.",
        ],
    }
    args.json_output.write_text(json.dumps(result, indent=2) + "\n")
    print("projected button", [round(v, 1) for v in center])


if __name__ == "__main__":
    main()
