"""Apply the replacement model to the existing continuous clip and accepted geometry."""

from pathlib import Path
import sys, json, hashlib, time
import cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from body_localization import detect_and_localize, transported_reference_camera, VERSION
from continuous_tracker import Tracker

OUT = ROOT / "body-localization"
cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())
cal = json.loads((ROOT / "rectification/calibration.json").read_text())
geometry = json.loads((ROOT / "rectification/timeline.json").read_text())
reference = {
    name: cv2.imread(str(ROOT / "vision/frames" / view["reference_frame"]))
    for name, view in cfg["views"].items()
}
trackers = {name: Tracker() for name in cfg["views"]}
cap = cv2.VideoCapture(str(ROOT / "continuous/clip.mp4"))
records = []
started = time.monotonic()
for frame_number in range(0, geometry["frames"], 15):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ok, image = cap.read()
    if not ok:
        raise RuntimeError(f"Decode failed at {frame_number}")
    t = frame_number / geometry["fps"]
    row = {"time_s": t, "frame": frame_number, "views": {}}
    for name, view in cfg["views"].items():
        g = geometry["records"][frame_number]["views"][name]
        H = np.array(g["H"]) if g["H"] is not None else None
        ref = None
        if H is not None:
            A = np.linalg.inv(H) @ np.array(cal[name]["refined_H"])
            ref = cv2.warpPerspective(reference[name], A, (image.shape[1], image.shape[0]))
        prior = (
            transported_reference_camera(np.array(cal[name]["refined_H"]), H, view["region"])
            if H is not None
            else None
        )
        proposals, diagnostics = detect_and_localize(image, H, view, ref, prior)
        tracked = trackers[name].update(proposals, t)
        row["views"][name] = {
            "stones": tracked,
            "geometry_status": g["status"],
            "detector": {k: v for k, v in diagnostics.items() if k != "rejected"},
            "completeness": "unknown",
        }
    records.append(row)
    if len(records) % 30 == 0:
        print(len(records), "samples", flush=True)
cap.release()
result = {
    "version": VERSION,
    "model_sha256": hashlib.sha256((ROOT / "body_localization.py").read_bytes()).hexdigest(),
    "source_start_s": 2260,
    "sample_interval_s": 0.5,
    "duration_s": 90,
    "position_claim": "Conditional model estimates; no independent metric position reference for this recording.",
    "processing_seconds": time.monotonic() - started,
    "records": records,
}
(OUT / "video-timeline.json").write_text(json.dumps(result, separators=(",", ":"), allow_nan=False))
print("Finished", len(records), "samples", flush=True)
