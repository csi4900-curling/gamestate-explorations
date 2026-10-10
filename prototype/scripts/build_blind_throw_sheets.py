"""Create fixed-interval source contact sheets without reading detector outputs."""

import argparse
from pathlib import Path
import json
import cv2
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--start", type=float, default=1650)
    p.add_argument("--end", type=float, default=2760)
    p.add_argument("--step", type=float, default=5)
    p.add_argument("--panel", choices=("full", "left", "right"), default="full")
    p.add_argument("--purpose", default="Source contact sheet; selection protocol recorded separately")
    a = p.parse_args()
    if a.output.exists() or a.step <= 0 or a.start < 0 or a.end <= a.start:
        p.error("Use a new output directory and valid interval")
    a.output.mkdir(parents=True)
    cv2.setNumThreads(1)
    cap = cv2.VideoCapture(str(a.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0 or a.end > cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps:
        raise ValueError("Source interval not available")
    rows = []
    cell_w, cell_h = (320, 380) if a.panel != "full" else (320, 200)
    sample_count = int(np.ceil((a.end - a.start) / a.step))
    for index in range(sample_count):
        t = round(a.start + index * a.step, 6)
        if t >= a.end:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {t} s")
        if a.panel != "full":
            middle = frame.shape[1] // 2
            frame = frame[:, :middle] if a.panel == "left" else frame[:, middle:]
        frame = cv2.resize(frame, (cell_w, cell_h - 20))
        cell = np.full((cell_h, cell_w, 3), (28, 35, 40), dtype=np.uint8)
        cell[20:, :] = frame
        cv2.putText(cell, f"{t:g} s", (8, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
        rows.append((t, cell))
    cap.release()
    manifest = {
        "source": str(a.video),
        "interval_s": [a.start, a.end],
        "step_s": a.step,
        "panel": a.panel,
        "purpose": a.purpose,
        "sheets": [],
    }
    for offset in range(0, len(rows), 36):
        group = rows[offset : offset + 36]
        image = np.full((6 * cell_h, 6 * cell_w, 3), (28, 35, 40), dtype=np.uint8)
        for index, (_, cell) in enumerate(group):
            y, x = divmod(index, 6)
            image[y * cell_h : (y + 1) * cell_h, x * cell_w : (x + 1) * cell_w] = cell
        name = f"sheet-{offset // 36 + 1:02}.jpg"
        cv2.imwrite(str(a.output / name), image)
        manifest["sheets"].append({"file": name, "times_s": [t for t, _ in group]})
    (a.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(rows)} fixed samples in {len(manifest['sheets'])} sheets")


if __name__ == "__main__":
    main()
