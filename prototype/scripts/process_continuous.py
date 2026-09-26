"""Process every half-second of the supplied source-specific clip, not selected stills."""

import sys, json, time
from pathlib import Path
import cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vision_core import ViewCalibrator, detect_caps
from continuous_tracker import Tracker

out = ROOT / "continuous"
cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())
cal = {k: ViewCalibrator(v, ROOT / "vision/frames") for k, v in cfg["views"].items()}
trackers = {k: Tracker() for k in cal}
cap = cv2.VideoCapture(str(out / "clip.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
if not cap.isOpened() or fps <= 0:
    raise ValueError("Cannot decode clip")
records = []
start = time.monotonic()
step = max(1, round(fps / 2))
i = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    if i % step == 0:
        t = i / fps
        row = {"time_s": t, "source_time_s": 2260 + t, "views": {}}
        for name, c in cal.items():
            H, reg = c.register(frame)
            ref = None
            if H is not None:
                A = np.array(reg.get("reference_to_current", np.eye(3)))
                ref = cv2.warpPerspective(c.reference, A, (frame.shape[1], frame.shape[0]))
            detections, _ = detect_caps(frame, H, c.view, ref)
            tracked = trackers[name].update(detections, t)
            row["views"][name] = {
                "registration": reg,
                "stones": tracked,
                "completeness": "unknown",
                "state": "partial_observation" if H is not None else "unavailable",
            }
        records.append(row)
        if len(records) % 20 == 0:
            print(f"{len(records)} samples, {t:.1f}s / {count / fps:.1f}s", flush=True)
    i += 1
cap.release()
result = {
    "source": "https://www.youtube.com/watch?v=aWXo6XeUFQw&t=2260s",
    "source_start_s": 2260,
    "sample_interval_s": step / fps,
    "decoded_frames": i,
    "duration_s": i / fps,
    "processing_seconds": time.monotonic() - start,
    "position_semantics": "Uncorrected cap projections, not validated stone centres",
    "records": records,
}
(out / "timeline.json").write_text(json.dumps(result, separators=(",", ":")))
print(json.dumps({k: v for k, v in result.items() if k != "records"}), flush=True)
