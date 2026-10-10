"""Render source frames for unusual stable-board proposal shapes."""

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
    for name in ("video", "shapes", "output", "manifest"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.manifest.exists():
        parser.error("Shape source review already exists")
    shapes = json.loads(args.shapes.read_text())
    if digest(args.video) != shapes["input_sha256"]["video"]:
        parser.error("Video and shape audit differ")
    cases = [
        row
        for row in shapes["rows"]
        if row["colour_component_height_width_ratio"] >= 0.75 or row["body_support"] < 0.5
    ]
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    canvas = Image.new("RGB", (1920, 580 * ((len(cases) + 1) // 2)), "white")
    draw = ImageDraw.Draw(canvas)
    frames = []
    try:
        for i, row in enumerate(cases):
            t = row["source_time_s"]
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {t}")
            frame_index = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            panel = frame[:, :960].copy()
            x, y = (round(v) for v in row["pixel_center"])
            cv2.circle(panel, (x, y), 30, (0, 255, 255), 4)
            panel = cv2.resize(panel, (960, 540), interpolation=cv2.INTER_AREA)
            x0, y0 = (i % 2) * 960, (i // 2) * 580
            canvas.paste(Image.fromarray(cv2.cvtColor(panel, cv2.COLOR_BGR2RGB)), (x0, y0 + 34))
            draw.text(
                (x0 + 8, y0 + 9),
                f"{row['candidate_id']} {row['local_observation_id']} {t:.1f}s frame {frame_index} / aspect {row['colour_component_height_width_ratio']:.2f} / body {row['body_support']:.2f}",
                fill="black",
            )
            frames.append(
                {
                    "candidate_id": row["candidate_id"],
                    "local_observation_id": row["local_observation_id"],
                    "source_time_s": t,
                    "decoded_frame_index": frame_index,
                    "proposal_pixel_center": row["pixel_center"],
                    "source_shape_row": row,
                }
            )
    finally:
        capture.release()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, quality=92)
    args.manifest.write_text(
        json.dumps(
            {
                "status": "source_review_of_shape_selected_board_proposals_not_independent_labels",
                "video_sha256": digest(args.video),
                "shapes_sha256": digest(args.shapes),
                "runner_sha256": digest(Path(__file__)),
                "image_sha256": digest(args.output),
                "selection": "height/width >= 0.75 or body_support < 0.5",
                "frames": frames,
            },
            indent=2,
        )
        + "\n"
    )
    print(len(cases), "shape-selected source frames", args.output)


if __name__ == "__main__":
    main()
