"""Render source frames at the last registered pre-split board observation."""

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
    for name in ("video", "boards", "output", "manifest"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.manifest.exists():
        parser.error("Tail review already exists")
    boards = json.loads(args.boards.read_text())
    source_hash = digest(args.video)
    if source_hash != boards["high_resolution_source_sha256"]:
        parser.error("Board and video sources differ")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open source video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = boards["rows"]
    canvas = Image.new("RGB", (1920, 580 * 3), "white")
    draw = ImageDraw.Draw(canvas)
    frames = []
    try:
        for index, row in enumerate(rows):
            time_s = row["board"]["last_registered_s"]
            if time_s is None:
                raise ValueError(f"No last registered frame for {row['candidate_id']}")
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {time_s}")
            frame_index = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            view = row["receiving_view"]
            panel = frame[:, :960] if view == "left" else frame[:, 960:]
            panel = cv2.resize(panel, (960, 540), interpolation=cv2.INTER_AREA)
            x0, y0 = (index % 2) * 960, (index // 2) * 580
            canvas.paste(Image.fromarray(cv2.cvtColor(panel, cv2.COLOR_BGR2RGB)),
                         (x0, y0 + 34))
            draw.text((x0 + 8, y0 + 9),
                      f"{row['candidate_id']} {view} {time_s:.1f}s frame {frame_index} / stable proposals {len(row['board']['stones'])}",
                      fill="black")
            frames.append({"candidate_id": row["candidate_id"],
                           "receiving_view": view,
                           "source_time_s": time_s,
                           "decoded_frame_index": frame_index,
                           "stable_proposal_count": len(row["board"]["stones"])})
    finally:
        capture.release()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, quality=92)
    args.manifest.write_text(json.dumps({
        "status": "source_frame_review_of_partial_boards_not_exhaustive_stone_labels",
        "video_sha256": source_hash,
        "boards_sha256": digest(args.boards),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(args.output),
        "frames": frames,
    }, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
