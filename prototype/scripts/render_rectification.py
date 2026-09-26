"""Render real video frames into a metric house plane with explicit per-frame validity."""

import sys, json, time, subprocess, collections, hashlib
from pathlib import Path
import cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rectification_core import (
    VideoRectifier,
    rectify,
    HOUSE_BOUNDS,
    PIXELS_PER_METRE,
    canvas_transform,
)

out = ROOT / "rectification"
cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())
cal = json.loads((out / "calibration.json").read_text())
processors = {
    name: VideoRectifier(view, ROOT / "vision/frames", cal[name]["refined_H"])
    for name, view in cfg["views"].items()
}
cap = cv2.VideoCapture(str(ROOT / "continuous/clip.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
expected = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
C, size = canvas_transform()
if not cap.isOpened() or fps <= 0:
    raise ValueError("Video cannot be decoded")
writers = {
    name: cv2.VideoWriter(str(out / f"{name}-raw.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for name in processors
}
if not all(w.isOpened() for w in writers.values()):
    raise RuntimeError("Video writer failed")
records = []
i = 0
started = time.monotonic()
while True:
    ok, frame = cap.read()
    if not ok:
        break
    record = {"frame": i, "time_s": i / fps, "views": {}}
    for name, processor in processors.items():
        H, diagnostic = processor.step(frame, i / fps)
        if H is None:
            rect = np.full((size[1], size[0], 3), (24, 31, 36), np.uint8)
            cv2.putText(
                rect,
                "Calibration unavailable",
                (36, size[1] // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (240, 240, 240),
                2,
            )
        else:
            rect, _ = rectify(frame, H, processor.view["region"])
        writers[name].write(rect)
        record["views"][name] = {"H": H.tolist() if H is not None else None, **diagnostic}
        if i in [0, 600, 1200, 1800, 2400]:
            cv2.imwrite(str(out / f"{name}-t{i / fps:05.1f}.jpg"), rect)
    records.append(record)
    i += 1
    if i % 150 == 0:
        print(f"{i}/{expected} frames, {time.monotonic() - started:.1f}s elapsed", flush=True)
cap.release()
for w in writers.values():
    w.release()
if abs(i - expected) > 1:
    raise RuntimeError(f"Incomplete decode {i}/{expected}")
for name in writers:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(out / f"{name}-raw.mp4"),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-y",
            str(out / f"{name}.mp4"),
        ],
        check=True,
    )
    (out / f"{name}-raw.mp4").unlink()
summary = {
    name: dict(collections.Counter(r["views"][name]["status"] for r in records))
    for name in processors
}
result = {
    "source_clip": "../continuous/clip.mp4",
    "source_start_s": 2260,
    "fps": fps,
    "frames": i,
    "duration_s": i / fps,
    "bounds_m": HOUSE_BOUNDS,
    "pixels_per_metre": PIXELS_PER_METRE,
    "canvas_size_px": size,
    "processing_seconds": time.monotonic() - started,
    "summary": summary,
    "core_sha256": hashlib.sha256((ROOT / "rectification_core.py").read_bytes()).hexdigest(),
    "records": records,
}
(out / "timeline.json").write_text(json.dumps(result, separators=(",", ":")))
print(json.dumps({k: v for k, v in result.items() if k != "records"}), flush=True)
