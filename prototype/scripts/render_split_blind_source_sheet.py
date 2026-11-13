#!/usr/bin/env python3
"""Render fixed-interval right-panel source frames for a blind-span audit."""

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
    parser.add_argument("--motion", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    motion = json.loads(args.motion.read_text())
    if digest(args.video) != motion["source_sha256"]:
        parser.error("Source video differs from motion audit")
    if len(motion["intervals"]) != 1:
        parser.error("Expected one blind interval")
    start, stop = motion["intervals"][0]["interval_s"]
    times = list(range(int(start) + 5, int(stop), 10))
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheet_records = []
    try:
        for first in range(0, len(times), 12):
            group = times[first : first + 12]
            sheet = Image.new("RGB", (960, 615), "white")
            draw = ImageDraw.Draw(sheet)
            for index, time_s in enumerate(group):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Could not decode {time_s} s")
                image = Image.fromarray(cv2.cvtColor(frame[:, 320:640], cv2.COLOR_BGR2RGB)).resize(
                    (240, 180)
                )
                x, y = index % 4 * 240, index // 4 * 205
                sheet.paste(image, (x, y + 20))
                draw.text((x + 4, y + 3), str(time_s), fill="black")
            path = args.output_dir / f"sheet-{len(sheet_records) + 1:02d}.jpg"
            sheet.save(path, quality=88)
            sheet_records.append({"file": path.name, "times_s": group, "sha256": digest(path)})
    finally:
        cap.release()
    manifest = {
        "status": "source_frame_sampling_not_exhaustive_throw_review",
        "source_sha256": motion["source_sha256"],
        "motion_audit_sha256": digest(args.motion),
        "runner_sha256": digest(Path(__file__)),
        "right_panel_x_range": [320, 640],
        "sample_period_s": 10,
        "sheets": sheet_records,
        "limitation": "A throw can occur and finish between these sampled frames.",
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"sheets": len(sheet_records), "frames": len(times)}))


if __name__ == "__main__":
    main()
