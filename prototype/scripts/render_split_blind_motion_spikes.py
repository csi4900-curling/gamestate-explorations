#!/usr/bin/env python3
"""Render source-frame strips around grouped lower-ice activity spikes."""

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


def clusters(rows, threshold, max_gap_s=15):
    active = [row for row in rows if row["within_interior"] and row["lower_ice_mae"] > threshold]
    groups = []
    for row in active:
        if (
            not groups
            or row["second_frame_time_s"] - groups[-1][-1]["second_frame_time_s"] > max_gap_s
        ):
            groups.append([row])
        else:
            groups[-1].append(row)
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "motion", "output_dir"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    motion = json.loads(args.motion.read_text())
    if digest(args.video) != motion["source_sha256"]:
        parser.error("Source video differs from motion audit")
    if len(motion["intervals"]) != 1:
        parser.error("Expected one blind interval")
    groups = clusters(motion["intervals"][0]["pairs"], motion["active_mae_threshold"])
    peaks = [max(group, key=lambda row: row["lower_ice_mae"]) for group in groups]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheets = []
    try:
        for first in range(0, len(peaks), 5):
            canvas = Image.new("RGB", (720, 5 * 295), "white")
            draw = ImageDraw.Draw(canvas)
            records = []
            for row_index, peak in enumerate(peaks[first : first + 5]):
                peak_time = peak["second_frame_time_s"]
                times = [peak_time - 5, peak_time, peak_time + 5]
                records.append(
                    {
                        "cluster_interval_s": [
                            groups[first + row_index][0]["second_frame_time_s"],
                            groups[first + row_index][-1]["second_frame_time_s"],
                        ],
                        "peak_time_s": peak_time,
                        "peak_lower_ice_mae": peak["lower_ice_mae"],
                        "sample_times_s": times,
                    }
                )
                for col, time_s in enumerate(times):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                    ok, frame = cap.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise RuntimeError(f"Could not decode {time_s} s")
                    image = Image.fromarray(
                        cv2.cvtColor(frame[:, 320:640], cv2.COLOR_BGR2RGB)
                    ).resize((240, 270))
                    x, y = col * 240, row_index * 295
                    canvas.paste(image, (x, y + 20))
                    draw.text(
                        (x + 3, y + 3), f"{time_s} | {peak['lower_ice_mae']:.1f}", fill="black"
                    )
            path = args.output_dir / f"sheet-{len(sheets) + 1:02d}.jpg"
            canvas.save(path, quality=88)
            sheets.append({"file": path.name, "sha256": digest(path), "clusters": records})
    finally:
        cap.release()
    manifest = {
        "status": "source_review_of_activity_spikes_not_throw_labels",
        "source_sha256": motion["source_sha256"],
        "motion_audit_sha256": digest(args.motion),
        "runner_sha256": digest(Path(__file__)),
        "group_max_gap_s": 15,
        "cluster_count": len(groups),
        "sheets": sheets,
        "limitation": "Three sparse stills per spike cannot establish physical throw identity or absence.",
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"clusters": len(groups), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
