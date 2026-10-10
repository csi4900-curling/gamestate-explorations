"""Render source frames for every newly unique path in a paired-bound batch."""

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
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = args.output_dir / "manifest.json"
    if manifest.exists():
        parser.error("Review manifest already exists")
    batch = json.loads(args.batch.read_text())
    if digest(args.video) != batch["video_sha256"]:
        parser.error("Video differs from paired-bound batch")
    source = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                              [cv2.CAP_PROP_N_THREADS, 1])
    if not source.isOpened():
        parser.error("Cannot open video")
    fps = source.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    items = []
    try:
        for row in batch["rows"]:
            if (row["original_selection"] == row["extended_selection"] or
                    row["extended_selection"] != "provisional_unique_far_entry_motion_path"):
                continue
            probe_path = args.batch.parent / row["artifact"]
            if digest(probe_path) != row["artifact_sha256"]:
                raise ValueError(f"Paired artifact hash differs: {probe_path}")
            probe = json.loads(probe_path.read_text())
            path = probe["cases"]["extended"]["selection"]["path"]
            nodes = [path[index] for index in sorted({0, len(path) // 2,
                                                      len(path) - 1})]
            sheet = Image.new("RGB", (980, len(nodes) * 384), "white")
            draw = ImageDraw.Draw(sheet)
            frames = []
            for index, node in enumerate(nodes):
                time_s = node["source_time_s"]
                source.set(cv2.CAP_PROP_POS_FRAMES,
                           round((time_s - batch["source_offset_s"]) * fps))
                ok, frame = source.read()
                if not ok:
                    raise RuntimeError(f"Cannot read {probe['candidate_id']} at {time_s}")
                frame_index = int(source.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                x, y = (round(v) for v in node["pixel_center"])
                marked = frame.copy()
                cv2.circle(marked, (x, y), 17, (0, 255, 255), 4)
                context = cv2.resize(marked, (640, 360), interpolation=cv2.INTER_AREA)
                padded = cv2.copyMakeBorder(frame, 100, 100, 100, 100,
                                            cv2.BORDER_CONSTANT,
                                            value=(255, 255, 255))
                crop = padded[y+100-80:y+100+80, x+100-80:x+100+80]
                crop = cv2.resize(crop, (320, 320), interpolation=cv2.INTER_NEAREST)
                top = index * 384
                sheet.paste(Image.fromarray(cv2.cvtColor(context, cv2.COLOR_BGR2RGB)),
                            (0, top + 24))
                sheet.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)),
                            (650, top + 24))
                draw.text((6, top + 5),
                          f"{probe['candidate_id']} {time_s:.1f}s frame {frame_index} center ({x},{y})",
                          fill="black")
                frames.append({"source_time_s": time_s,
                               "decoded_frame_index": frame_index,
                               "path_pixel_center": node["pixel_center"]})
            image_path = args.output_dir / f"{probe['candidate_id'].lower()}-path-review.jpg"
            sheet.save(image_path, quality=90)
            items.append({"candidate_id": probe["candidate_id"],
                          "paired_artifact_sha256": row["artifact_sha256"],
                          "sheet": image_path.name,
                          "sheet_sha256": digest(image_path),
                          "frames": frames})
    finally:
        source.release()
    manifest.write_text(json.dumps({
        "status": "prediction_selected_source_review_not_independent_labels",
        "source_sha256": batch["video_sha256"],
        "batch_sha256": digest(args.batch),
        "runner_sha256": digest(Path(__file__)),
        "source_offset_s": batch["source_offset_s"],
        "item_count": len(items),
        "items": items,
    }, indent=2) + "\n")
    print(len(items), "review sheets", manifest)


if __name__ == "__main__":
    main()
