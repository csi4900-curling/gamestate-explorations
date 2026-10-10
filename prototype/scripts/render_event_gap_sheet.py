"""Sample source-only frames across a broadcast interval for review."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--end", type=float, required=True)
    parser.add_argument("--step", type=float, default=10.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.end <= args.start or args.step <= 0 or args.output.exists():
        parser.error("Invalid interval, step, or output already exists")
    times = []
    t = args.start
    while t <= args.end + 1e-6:
        times.append(round(t, 3))
        t += args.step
    video = cv2.VideoCapture(str(args.video))
    if not video.isOpened():
        parser.error("Cannot open video")
    fps = video.get(cv2.CAP_PROP_FPS)
    width, height = 480, 270
    columns = 5
    rows = (len(times) + columns - 1) // columns
    sheet = Image.new("RGB", (width * columns, (height + 24) * rows), "white")
    draw = ImageDraw.Draw(sheet)
    samples = []
    try:
        for index, source_time_s in enumerate(times):
            video.set(cv2.CAP_PROP_POS_MSEC, source_time_s * 1000)
            ok, frame = video.read()
            if not ok:
                raise RuntimeError(f"Cannot read source at {source_time_s}")
            frame_index = int(video.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            thumb = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            x, y = (index % columns) * width, (index // columns) * (height + 24)
            sheet.paste(Image.fromarray(cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)), (x, y + 24))
            draw.text((x + 4, y + 4), f"{source_time_s:.1f}s / frame {frame_index}", fill="black")
            samples.append({"requested_source_time_s": source_time_s,
                            "decoded_frame_index": frame_index,
                            "approx_decoded_source_time_s": frame_index / fps})
    finally:
        video.release()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, quality=88)
    manifest = args.output.with_suffix(".json")
    manifest.write_text(json.dumps({
        "status": "source_only_sparse_gap_sheet_not_exhaustive_throw_labels",
        "source_sha256": digest(args.video),
        "source_interval_s": [args.start, args.end],
        "step_s": args.step,
        "source_fps": fps,
        "samples": samples,
        "image_sha256": digest(args.output),
    }, indent=2) + "\n")
    print(len(samples), "source frames", args.output)


if __name__ == "__main__":
    main()
