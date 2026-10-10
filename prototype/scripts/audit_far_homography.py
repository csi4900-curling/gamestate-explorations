"""Check left-camera extrapolation against an independent hog-line marking.

The hog line was not among the house-ring calibration fit/check landmarks.
This measures painted-line alignment at the hog line, not the physical error
of a moving stone farther along the rink.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vision_core import ViewCalibrator, project

OUT = ROOT / "continuous"
CLIP_S = 43.5
SOURCE_S = 2260 + CLIP_S
HOG_INSIDE_EDGE_M = -6.401
HOG_WIDTH_M = 0.102
HOG_CENTRE_M = HOG_INSIDE_EDGE_M - HOG_WIDTH_M / 2


def line_samples(image, columns, H):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    samples = []
    for x in columns:
        ys = [
            y for xx in range(x - 5, x + 6) for y in range(280, 365)
            if 116 <= int(hsv[y, xx, 0]) <= 140
            and int(hsv[y, xx, 1]) > 55
            and int(hsv[y, xx, 2]) < 160
        ]
        if len(ys) < 15:
            raise RuntimeError(f"Cannot locate purple hog line near x={x}")
        y = float(np.median(ys))
        mapped_y = float(project(H, [[x, y]])[0, 1])
        samples.append({
            "pixel": [x, y], "projected_y_m": mapped_y,
            "error_from_nominal_line_centre_m": mapped_y - HOG_CENTRE_M,
        })
    return {
        "sample_count": len(samples),
        "median_absolute_error_cm": round(float(np.median(
            [abs(s["error_from_nominal_line_centre_m"]) for s in samples])) * 100, 2),
        "maximum_absolute_error_cm": round(max(
            abs(s["error_from_nominal_line_centre_m"]) for s in samples) * 100, 2),
        "samples": samples,
    }


def main():
    cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())["views"]["left"]
    cal = ViewCalibrator(cfg, ROOT / "vision/frames")
    refined = np.asarray(json.loads((ROOT / "rectification/calibration.json").read_text())
                         ["left"]["refined_H"])
    video = cv2.VideoCapture(str(OUT / "clip.mp4"))
    fps = video.get(cv2.CAP_PROP_FPS)
    video.set(cv2.CAP_PROP_POS_FRAMES, round(CLIP_S * fps))
    ok, frame = video.read()
    video.release()
    if not ok:
        raise RuntimeError("Cannot decode T11 review frame")
    current_initial, registration = cal.register(frame)
    if current_initial is None:
        raise RuntimeError("T11 frame registration failed")
    transport = np.asarray(registration["reference_to_current"])
    current_refined = refined @ np.linalg.inv(transport)
    columns_reference = [100, 200, 300, 400, 480, 600, 700, 800, 880]
    columns_current = [80, 100, 120, 200, 700, 800, 850, 880]
    line_checks = {
        "reference_initial": line_samples(cal.reference, columns_reference, cal.H),
        "reference_refined": line_samples(cal.reference, columns_reference, refined),
        "t11_initial": line_samples(frame, columns_current, current_initial),
        "t11_refined": line_samples(frame, columns_current, current_refined),
    }
    departure = json.loads((ROOT / "cross-view/T11-departure.json").read_text())
    stone = []
    video = cv2.VideoCapture(str(OUT / "clip.mp4"))
    for row in departure["records"]:
        if row["time_s"] not in (2303.5, 2304.5, 2305.0):
            continue
        video.set(cv2.CAP_PROP_POS_FRAMES, round((row["time_s"] - 2260) * fps))
        ok, stone_frame = video.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {row['time_s']}")
        H_initial, stone_registration = cal.register(stone_frame)
        if H_initial is None:
            raise RuntimeError(f"No registration at {row['time_s']}")
        H_refined = refined @ np.linalg.inv(np.asarray(stone_registration["reference_to_current"]))
        cap_point = row["pixel"]
        uncorrected = row["localization"]["uncorrected_position_m"]
        ground = row["position_local_m"]
        stone.append({
            "source_time_s": row["time_s"],
            "observed_cap_pixel": cap_point,
            "cap_plane_projection_refined_m": uncorrected,
            "conditional_height_corrected_ground_m": ground,
            "height_correction_y_m": round(ground[1] - uncorrected[1], 3),
            "initial_minus_refined_cap_y_m_same_frame": round(float(
                project(H_initial, [cap_point])[0, 1] - project(H_refined, [cap_point])[0, 1]), 3),
        })
    video.release()
    if len(stone) != 3:
        raise RuntimeError("Missing T11 departure audit records")
    result = {
        "status": "partial_geometry_check_no_far_stone_ground_truth",
        "reference_frame": cfg["reference_frame"],
        "t11_clip_time_s": CLIP_S,
        "t11_source_time_s": SOURCE_S,
        "left_world_bounds_m": cfg["world_bounds"],
        "calibration_fit": "Four outer-house-ring intersections; nine house-ring/tee check points, all near the house.",
        "hog_line_source": "feasibility/sources/Rules-2025.pdf, PDF page 4: 102 mm width, inside edge 6.401 m from tee centre.",
        "hog_line_expected_inside_edge_y_m": HOG_INSIDE_EDGE_M,
        "hog_line_expected_paint_centre_y_m": HOG_CENTRE_M,
        "hog_line_detection": "Median dark-purple pixels in narrow image columns; post-hoc image measurement, not a stone reference.",
        "hog_line_checks": line_checks,
        "t11_registration": {key: registration[key] for key in ("status", "inliers", "rmse_px")},
        "t11_stone_projections": stone,
        "conclusion": "The configured lower bound is a software scope choice, not evidence of failure beyond it. The original homography agrees with the independent hog-line centre at about -6.45 m, but no known longitudinal landmark checks stone-ground accuracy at -9 to -13 m. Cap height adds a separate conditional 0.63-0.71 m shift in T11.",
    }
    (OUT / "far-homography-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v["median_absolute_error_cm"] for k, v in line_checks.items()}))


if __name__ == "__main__":
    main()
