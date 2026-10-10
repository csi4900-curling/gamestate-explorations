#!/usr/bin/env python3
"""Render reproducible source-first frame grids for candidate-gap inspection."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


def digest(path):
    hasher = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--stop", required=True, type=int)
    parser.add_argument("--step", required=True, type=int)
    parser.add_argument("--panel", required=True, choices=("left", "right", "both"))
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.step <= 0 or args.stop <= args.start:
        parser.error("Expected positive sampling step and nonempty interval")
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    timeline = json.loads(args.timeline.read_text())
    source_hash = digest(args.video)
    if source_hash != timeline["source_sha256"]:
        parser.error("Source video differs from timeline")
    if not (timeline["source_interval_s"][0] <= args.start and
            args.stop <= timeline["source_interval_s"][1]):
        parser.error("Requested interval leaves source timeline")
    times = list(range(args.start, args.stop + 1, args.step))
    if args.panel == "both":
        bounds = (0, 0, 640, 360)
        tile_size = (320, 180)
        row_height = 205
    else:
        bounds = (0, 0, 320, 360) if args.panel == "left" else (
            320, 0, 640, 360)
        tile_size = (320, 360)
        row_height = 380
    cols, rows_per_sheet = (4, 3) if args.panel == "both" else (5, 2)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheets = []
    try:
        group_size = cols * rows_per_sheet
        for first in range(0, len(times), group_size):
            group = times[first:first + group_size]
            sheet = Image.new("RGB", (cols * tile_size[0],
                                       rows_per_sheet * row_height), "white")
            draw = ImageDraw.Draw(sheet)
            for index, time_s in enumerate(group):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Cannot decode {time_s} s")
                x0, y0, x1, y1 = bounds
                image = Image.fromarray(cv2.cvtColor(
                    frame[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)).resize(tile_size)
                x, y = index % cols * tile_size[0], index // cols * row_height
                sheet.paste(image, (x, y + 20))
                draw.text((x + 4, y + 3), str(time_s), fill="black")
            path = args.output_dir / f"sheet-{len(sheets)+1:02d}.jpg"
            sheet.save(path, quality=90)
            sheets.append({"file": path.name, "times_s": group,
                           "sha256": digest(path)})
    finally:
        cap.release()
    manifest = {"status": "source_sample_grid_not_exhaustive_throw_labels",
                "source_sha256": source_hash,
                "timeline_sha256": digest(args.timeline),
                "runner_sha256": digest(Path(__file__)),
                "interval_s": [args.start, args.stop],
                "step_s": args.step,
                "panel": args.panel,
                "sheets": sheets,
                "limitation": "A physical event can occur between sampled source frames."}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"frames": len(times), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
