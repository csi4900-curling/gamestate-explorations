"""Render source-frame context for the selected S372 internal-edit diagnosis."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china"
SOURCE = BASE / "source.mp4"
RESCUE = BASE / "S372-ISOLATED-CUT-RESCUE.json"
OUTPUT = BASE / "S372-transition-frames.png"
TIMES = (5172.0, 5188.0, 5198.0, 5204.0, 5212.0)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Transition contact sheet already exists")
    rescue = json.loads(RESCUE.read_text())
    if digest(SOURCE) != rescue["source_video_sha256"]:
        raise ValueError("Selected source changed")
    cap = cv2.VideoCapture(str(SOURCE), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width, height = 400, 225
    canvas = np.full((height + 28, len(TIMES) * width, 3), 255, np.uint8)
    try:
        for i, t in enumerate(TIMES):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {t}")
            canvas[:height, i * width:(i + 1) * width] = cv2.resize(
                frame, (width, height), interpolation=cv2.INTER_AREA)
            cv2.putText(canvas, f"source {t:.1f} s", (i * width + 10, height + 19),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1)
    finally:
        cap.release()
    if not cv2.imwrite(str(OUTPUT), canvas):
        raise RuntimeError("Contact sheet write failed")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
