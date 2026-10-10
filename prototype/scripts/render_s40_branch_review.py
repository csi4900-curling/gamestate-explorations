"""Render the source frames where the S40 motion proposal forks."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
MOTION = BASE / "full-match-motion-merged-postscore.json"
SHORT = BASE / "full-match-left-short-path-rescue-postscore.json"
OUTPUT = BASE / "gap-review/s40-branch-source-review.jpg"
MANIFEST = BASE / "gap-review/s40-branch-source-review.json"
TIMES = (1519.0, 1519.5, 1520.0, 1520.5, 1521.0, 1521.5)


def digest(path):
    checksum = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            checksum.update(block)
    return checksum.hexdigest()


def main():
    if OUTPUT.exists() or MANIFEST.exists():
        raise SystemExit("S40 source review output already exists")
    motion = json.loads(MOTION.read_text())
    short = json.loads(SHORT.read_text())
    original = next(row for row in motion["rows"] if row["candidate_id"] == "S40")
    rescued = next(row for row in short["rows"] if row["candidate_id"] == "S40")
    selection = original["selection"]
    assert selection["status"] == "ambiguous_far_entry_motion_paths"
    assert len(selection["alternative_paths"]) == 2
    assert selection["first_ambiguity_time_s"] == 1520.5
    assert rescued["selection"]["path"][:4] == selection["shared_prefix"]
    candidates = {}
    for path in selection["alternative_paths"]:
        for point in path:
            candidates.setdefault(point["source_time_s"], []).append(point["pixel_center"])
    source = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not source.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = source.get(cv2.CAP_PROP_FPS)
    canvas = Image.new("RGB", (960 * 3, 600 * 2), "white")
    draw = ImageDraw.Draw(canvas)
    frames = []
    try:
        for i, t in enumerate(TIMES):
            source.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = source.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {t}")
            frame_index = int(source.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            left = frame[:, :960].copy()
            points = []
            for point in candidates[t]:
                xy = tuple(round(v) for v in point)
                if xy in points:
                    continue
                points.append(xy)
                cv2.circle(left, xy, 28, (0, 255, 255), 4)
            panel = cv2.resize(left, (960, 540), interpolation=cv2.INTER_AREA)
            x0, y0 = (i % 3) * 960, (i // 3) * 600
            canvas.paste(Image.fromarray(cv2.cvtColor(panel, cv2.COLOR_BGR2RGB)), (x0, y0 + 40))
            draw.text(
                (x0 + 8, y0 + 9),
                f"S40 source {t:.1f}s / frame {frame_index} / yellow circles = candidate branches",
                fill="black",
            )
            frames.append(
                {
                    "source_time_s": t,
                    "decoded_frame_index": frame_index,
                    "candidate_pixel_centers": points,
                }
            )
    finally:
        source.release()
    canvas.save(OUTPUT, quality=92)
    MANIFEST.write_text(
        json.dumps(
            {
                "status": "source_review_of_ambiguous_motion_not_independent_event_label",
                "video_sha256": digest(VIDEO),
                "motion_sha256": digest(MOTION),
                "short_path_sha256": digest(SHORT),
                "runner_sha256": digest(Path(__file__)),
                "image_sha256": digest(OUTPUT),
                "shared_prefix_interval_s": [1518.5, 1520.0],
                "first_ambiguity_time_s": 1520.5,
                "frames": frames,
            },
            indent=2,
        )
        + "\n"
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
