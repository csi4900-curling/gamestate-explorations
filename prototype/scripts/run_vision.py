from pathlib import Path
import sys, json, hashlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2, numpy as np
from vision_core import ViewCalibrator, detect_caps, project, DETECTOR_VERSION

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "vision"
config = json.loads((V / "annotations/calibration.json").read_text())
refs = json.loads((V / "annotations/detection-reference.json").read_text())
calibrators = {k: ViewCalibrator(v, V / "frames") for k, v in config["views"].items()}
results = []
for file in sorted((V / "frames").glob("*.jpg")):
    im = cv2.imread(str(file))
    t = int(file.stem)
    for panel, cal in calibrators.items():
        H, registration = cal.register(im, file.name == cal.view["reference_frame"])
        registered_reference = None
        if H is not None:
            A = np.array(registration.get("reference_to_current", np.eye(3)))
            registered_reference = cv2.warpPerspective(cal.reference, A, (im.shape[1], im.shape[0]))
        proposals, diagnostic = detect_caps(im, H, cal.view, registered_reference)
        result = {
            "timestamp_s": t,
            "panel": panel,
            "frame": f"frames/{file.name}",
            "registration": registration,
            "calibration_reference": cal.view["reference_frame"],
            "calibration_landmark_check": cal.check,
            "homography": H.tolist() if H is not None else None,
            "candidates": proposals,
            "diagnostic": diagnostic,
            "completeness": "unknown",
            "metric_stone_positions": "unavailable",
            "simulator_export": "blocked",
        }
        overlay = im.copy()
        x0, y0, x1, y1 = cal.view["region"]
        if H is not None:
            inv = np.linalg.inv(H)
            for radius in [1.829, 1.219, 0.61]:
                angle = np.linspace(0, 2 * np.pi, 160)
                ring = (
                    project(inv, np.c_[radius * np.cos(angle), radius * np.sin(angle)])
                    .round()
                    .astype(np.int32)
                )
                cv2.polylines(overlay, [ring], True, (0, 200, 255), 2)
            for d in proposals:
                x, y, w, h = d["bbox"]
                colour = (0, 230, 255) if d["colour"] == "yellow" else (60, 60, 255)
                cv2.rectangle(overlay, (x - 3, y - 3), (x + w + 3, y + h + 3), colour, 2)
                cv2.drawMarker(
                    overlay,
                    tuple(np.round(d["pixel_center"]).astype(int)),
                    (255, 255, 255),
                    cv2.MARKER_CROSS,
                    12,
                    1,
                )
                cv2.putText(
                    overlay, d["id"], (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 2
                )
        else:
            cv2.putText(
                overlay,
                "CALIBRATION REGISTRATION REJECTED",
                (x0 + 20, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )
        target = f"overlays/{t:05d}-{panel}.jpg"
        cv2.imwrite(str(V / target), overlay[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 90])
        result["overlay"] = target
        results.append(result)
        print(t, panel, registration["status"], len(proposals), flush=True)
payload = {
    "schema_version": "0.2-experimental",
    "detector_version": DETECTOR_VERSION,
    "detector_sha256": hashlib.sha256((ROOT / "vision_core.py").read_bytes()).hexdigest(),
    "coordinate_convention": config["coordinate_convention"],
    "limitations": config["limitations"],
    "views": {
        k: {"check": v.check, "bounds": v.view["world_bounds"]} for k, v in calibrators.items()
    },
    "observations": results,
}
(V / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
print("Saved", len(results), "panel results")
