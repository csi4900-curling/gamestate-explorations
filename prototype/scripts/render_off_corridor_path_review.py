"""Render source context and selected high-resolution path patches for review."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
MOTION = BASE / "off-corridor-motion-fixed-grid-postscore.json"
OUTPUT = BASE / "off-corridor-source-review"
IDS = ("S05", "S26", "S74", "S93")


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=VIDEO)
    parser.add_argument("--motion", type=Path, default=MOTION)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--ids", nargs="+", default=IDS)
    parser.add_argument("--source-offset-s", type=float, default=0.0)
    args = parser.parse_args()
    motion = json.loads(args.motion.read_text())
    by_id = {row["candidate_id"]: row for row in motion["rows"]}
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = []
    for candidate_id in args.ids:
        path = by_id[candidate_id]["selection"]["path"]
        nodes = [path[index] for index in sorted({0, len(path) // 2, len(path) - 1})]
        sheet = Image.new("RGB", (980, len(nodes) * 384), "white")
        draw = ImageDraw.Draw(sheet)
        frames = []
        for index, node in enumerate(nodes):
            t = node["source_time_s"]
            cap.set(cv2.CAP_PROP_POS_FRAMES,
                    round((t - args.source_offset_s) * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot read {candidate_id} at {t}")
            frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            x, y = (round(v) for v in node["pixel_center"])
            marked = frame.copy()
            cv2.circle(marked, (x, y), 17, (0, 255, 255), 4)
            context = cv2.resize(marked, (640, 360), interpolation=cv2.INTER_AREA)
            padded = cv2.copyMakeBorder(frame, 100, 100, 100, 100, cv2.BORDER_CONSTANT,
                                        value=(255, 255, 255))
            crop = padded[y+100-80:y+100+80, x+100-80:x+100+80]
            crop = cv2.resize(crop, (320, 320), interpolation=cv2.INTER_NEAREST)
            py = index * 384
            sheet.paste(Image.fromarray(cv2.cvtColor(context, cv2.COLOR_BGR2RGB)), (0, py + 24))
            sheet.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (650, py + 24))
            draw.text((6, py + 5), f"{candidate_id}  {t:.1f}s  frame {frame_index}  center ({x}, {y})", fill="black")
            frames.append({"source_time_s": t, "decoded_frame_index": frame_index,
                           "path_pixel_center": node["pixel_center"]})
        name = f"{candidate_id.lower()}-path-review.jpg"
        sheet.save(args.output_dir / name, quality=90)
        output.append({"candidate_id": candidate_id, "sheet": name, "frames": frames})
    cap.release()
    (args.output_dir / "path-review-manifest.json").write_text(json.dumps({
        "status": "prediction_selected_source_review_not_independent_labels",
        "source_sha256": digest(args.video),
        "motion_sha256": digest(args.motion),
        "source_offset_s": args.source_offset_s,
        "items": output,
    }, indent=2) + "\n")
    print([row["sheet"] for row in output])


if __name__ == "__main__":
    main()
