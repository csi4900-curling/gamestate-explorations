"""Render pinned source crops where the frozen 2024 marker reader transfers poorly."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
OUT = BASE / "layout-router/full-2024-coverage"
CASES = (("scotland", 930), ("latvia", 2000))


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    panels, rows = [], []
    for name, time_s in CASES:
        video = BASE / f"canada-{name}-2024/source-360p.mp4"
        scan = BASE / f"canada-{name}-2024/end-marker-full-transfer.json"
        data = json.loads(scan.read_text())
        if data["video_sha256"] != digest(video):
            raise ValueError(f"Source fingerprint differs for {name}")
        sample = next(row for row in data["samples"] if row["time_s"] == time_s)
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        capture.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
        ok, frame = capture.read()
        capture.release()
        if not ok:
            raise RuntimeError(f"Could not decode {name} at {time_s}")
        crop = frame[34:110, 375:580]
        panel = cv2.resize(crop, None, fx=3, fy=3,
                           interpolation=cv2.INTER_NEAREST)
        canvas = np.full((panel.shape[0]+30, panel.shape[1], 3), 255,
                         dtype=np.uint8)
        canvas[30:] = panel
        cv2.putText(canvas, f"{name}  {time_s}s  reader={sample['marker']}",
                    (4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.47, (0, 0, 0), 1)
        panels.append(canvas)
        rows.append({"match": name, "source_time_s": time_s,
                     "video_sha256": data["video_sha256"],
                     "scan_sha256": digest(scan),
                     "reader_output": sample["marker"],
                     "source_crop_xyxy_px": [375, 34, 580, 110]})
    image_path = OUT / "marker-transfer-failure.jpg"
    cv2.imwrite(str(image_path), np.hstack(panels))
    result = {
        "status": "source_crop_audit_of_frozen_marker_transfer_not_physical_end_truth",
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "cases": rows,
    }
    (OUT / "marker-transfer-failure.json").write_text(
        json.dumps(result, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
