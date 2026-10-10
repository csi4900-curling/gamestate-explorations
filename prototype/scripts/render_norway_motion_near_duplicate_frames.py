"""Render source frames for the three suspected split-track pairs."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
BASELINE = ROOT / "validation/official-shot-sequence/norway-full-event-motion-transfer-first.json"
IMAGE = ROOT / "validation/official-shot-sequence/norway-motion-near-duplicate-source-frames.jpg"
META = ROOT / "validation/official-shot-sequence/norway-motion-near-duplicate-source-frames.json"
TIMES = ((631, 638, 643), (993, 1000, 1003), (5291, 5298, 5303))
LABELS = ("S39 / S40", "S63 / S64", "S376 / S379")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if IMAGE.exists() or META.exists():
        raise SystemExit("Frame sheet exists; preserve first rendered source evidence")
    baseline = json.loads(BASELINE.read_text())
    if digest(VIDEO) != baseline["source_video_sha256"]:
        raise SystemExit("Video changed since motion transfer")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError("Cannot open Norway source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    canvas = Image.new("RGB", (640 * 3, 390 * 3), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        for row, times in enumerate(TIMES):
            for column, second in enumerate(times):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {second}s")
                frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                canvas.paste(
                    Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
                    (column * 640, row * 390 + 30),
                )
                draw.text(
                    (column * 640 + 10, row * 390 + 8), f"{LABELS[row]}   {second}s", fill="black"
                )
    finally:
        cap.release()
    canvas.save(IMAGE, quality=85)
    META.write_text(
        json.dumps(
            {
                "status": "source_frames_for_near_duplicate_motion_review",
                "source_video_sha256": digest(VIDEO),
                "baseline_motion_transfer_sha256": digest(BASELINE),
                "runner_sha256": digest(Path(__file__)),
                "sample_times_s": TIMES,
                "image_sha256": digest(IMAGE),
                "limitations": [
                    "Sparse source frames show camera context, not complete physical stone identity."
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(IMAGE)


if __name__ == "__main__":
    main()
