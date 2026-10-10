"""Audit the T11 receiving-view cutoff without changing the production timeline."""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from body_localization import detect_and_localize, transported_reference_camera
from vision_core import ViewCalibrator


def main():
    cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())["views"]["right"]
    cfg = dict(cfg, world_bounds=[-2.375, -1.975, 2.375, 22.0])
    calibrator = ViewCalibrator(cfg, ROOT / "vision/frames")
    calibrator.H = np.array(
        json.loads((ROOT / "rectification/calibration.json").read_text())["right"]["refined_H"]
    )
    video = cv2.VideoCapture(str(ROOT / "continuous/clip.mp4"))
    if not video.isOpened():
        raise RuntimeError("Could not open the T11 clip")
    times = sorted(set(np.round(np.arange(46.5, 52.501, 0.5), 2)) | set(np.round(np.arange(46.5, 47.101, 0.1), 2)))
    rows = []
    for t in times:
        video.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
        ok, frame = video.read()
        if not ok:
            raise RuntimeError(f"Could not decode clip time {t}")
        H, registration = calibrator.register(frame)
        row = {"clip_time_s": float(t), "registration": registration["status"], "candidates": []}
        if H is not None:
            reference = cv2.warpPerspective(
                calibrator.reference,
                np.array(registration["reference_to_current"]),
                (1920, 1080),
            )
            prior = transported_reference_camera(calibrator.H, H, cfg["region"])
            detections, _ = detect_and_localize(frame, H, cfg, reference, prior)
            row["candidates"] = [
                {
                    "pixel": d["pixel_center"],
                    "ground_position_m": d["ground_position_m"],
                    "uncorrected_projection_m": d["ice_plane_projection_m"],
                }
                for d in detections
                if d["colour"] == "yellow"
                and 1190 < d["pixel_center"][0] < 1400
                and d["pixel_center"][1] > 550
            ]
        rows.append(row)
    video.release()
    result = {
        "purpose": "Targeted post-hoc T11 receiving-view range audit; not part of the frozen throw detector",
        "source": "prototype/continuous/clip.mp4, source start 2260 s",
        "expanded_world_bounds_m": cfg["world_bounds"],
        "standard_right_world_bounds_m": [-2.375, -1.975, 2.375, 6.401],
        "identity_status": "Provisional visual/time/motion association, not independently validated",
        "physical_accuracy_status": "Unvalidated outside the original accepted bounds",
        "records": rows,
    }
    out = ROOT / "cross-view/T11-far-receiving-probe.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(out)
    print("first candidate", next((row["clip_time_s"] for row in rows if row["candidates"]), None))


if __name__ == "__main__":
    main()
