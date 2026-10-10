"""Render a fixed time grid before detector inference, with no candidate input."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def times_in_interval(start, end, step):
    if step <= 0 or end <= start:
        raise ValueError("Invalid fixed time grid")
    count = int((end - start - 1e-9) / step) + 1
    return [round(start + i * step, 6) for i in range(count)]


def panel_frame(frame, panel):
    if panel == "full":
        return cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
    half = frame.shape[1] // 2
    if panel == "left":
        return cv2.resize(frame[:, :half], (320, 360), interpolation=cv2.INTER_AREA)
    return cv2.resize(frame[:, half:], (320, 360), interpolation=cv2.INTER_AREA)


def write_sheets(frames, times, panel, output_dir, source, start, end, step):
    tile_h = 200 if panel == "full" else 380
    image_h = tile_h - 20
    sheets = []
    for first in range(0, len(frames), 36):
        canvas = np.full((tile_h * 6, 320 * 6, 3), 245, np.uint8)
        group_times = times[first : first + 36]
        for j, (frame, t) in enumerate(zip(frames[first : first + 36], group_times)):
            y = (j // 6) * tile_h
            x = (j % 6) * 320
            canvas[y : y + image_h, x : x + 320] = panel_frame(frame, panel)
            cv2.putText(
                canvas,
                f"{t:.1f} s",
                (x + 7, y + tile_h - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (25, 30, 35),
                1,
                cv2.LINE_AA,
            )
        filename = f"sheet-{first // 36 + 1:02d}.jpg"
        if not cv2.imwrite(str(output_dir / filename), canvas, [cv2.IMWRITE_JPEG_QUALITY, 88]):
            raise RuntimeError(f"Cannot write {filename}")
        sheets.append({"file": filename, "times_s": group_times})
    manifest = {
        "status": "fixed_source_only_pre_inference_no_event_labels",
        "source": str(source),
        "source_sha256": file_sha256(source),
        "runner_sha256": file_sha256(Path(__file__)),
        "interval_s": [start, end],
        "step_s": step,
        "panel": panel,
        "sample_count": len(frames),
        "sheets": sheets,
        "limitations": [
            "Five-second stills are not an exhaustive physical-throw reference.",
            "No model prediction or candidate timestamp was used to choose frames.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--interval-start", type=float, required=True)
    parser.add_argument("--interval-end", type=float, required=True)
    parser.add_argument("--step-s", type=float, default=5.0)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    times = times_in_interval(args.interval_start, args.interval_end, args.step_s)
    folders = {
        panel: args.output_root
        / ("source-only-5s-sheets" if panel == "full" else f"source-only-{panel}-5s-sheets")
        for panel in ("full", "left", "right")
    }
    if any(folder.exists() for folder in folders.values()):
        parser.error("Source-only output exists; preserve the earlier review")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open source video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    if duration < args.interval_end - 0.5:
        parser.error("Source does not contain the fixed interval")
    frames = []
    try:
        for t in times:
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source time {t}")
            frames.append(frame)
    finally:
        capture.release()
    for folder in folders.values():
        folder.mkdir(parents=True)
    for panel, folder in folders.items():
        write_sheets(
            frames,
            times,
            panel,
            folder,
            args.video,
            args.interval_start,
            args.interval_end,
            args.step_s,
        )
    print(
        {panel: len(list(folder.glob("sheet-*.jpg"))) for panel, folder in folders.items()},
        "samples",
        len(times),
    )


if __name__ == "__main__":
    main()
