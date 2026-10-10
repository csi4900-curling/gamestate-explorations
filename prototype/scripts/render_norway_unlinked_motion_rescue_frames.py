"""Render fixed source frames for the five Norway rescue review proposals."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
PROPOSALS = ROOT / "validation/official-shot-sequence/norway-unlinked-motion-rescue-proposals-first.json"
IMAGE = ROOT / "validation/official-shot-sequence/norway-unlinked-motion-rescue-source-frames.jpg"
META = ROOT / "validation/official-shot-sequence/norway-unlinked-motion-rescue-source-frames.json"
ROWS = (
    ("S86 → S87-Y01", (1196, 1200, 1203, 1213)),
    ("S243 → S244-Y01", (3337, 3344, 3350, 3360)),
    ("S443 → S444-Y01", (6230, 6233, 6236, 6243)),
    ("S561 → S562-Y01", (7767, 7771, 7773, 7778)),
    ("S647 → S648-Y01", (8606, 8610, 8614, 8622)),
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if IMAGE.exists() or META.exists():
        raise SystemExit("Output exists; preserve first rescue frame sheet")
    proposals = json.loads(PROPOSALS.read_text())
    actual = [(row["origin_shot_id"], row["receiving_episode_id"])
              for row in proposals["proposals"]]
    expected = [("S86", "S87-Y01"), ("S243", "S244-Y01"),
                ("S443", "S444-Y01"), ("S561", "S562-Y01"),
                ("S647", "S648-Y01")]
    if actual != expected:
        raise SystemExit("Proposal set changed since frame selection")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError("Cannot open Norway source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    canvas = Image.new("RGB", (640 * 4, 390 * len(ROWS)), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        for row, (label, times) in enumerate(ROWS):
            for col, second in enumerate(times):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {second}s")
                frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                canvas.paste(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
                             (col * 640, row * 390 + 30))
                draw.text((col * 640 + 8, row * 390 + 8), f"{label}  {second}s", fill="black")
    finally:
        cap.release()
    canvas.save(IMAGE, quality=85)
    META.write_text(json.dumps({
        "status": "source_frame_review_sheet_not_independent_throw_labels",
        "source_video_sha256": digest(VIDEO),
        "proposals_sha256": digest(PROPOSALS),
        "runner_sha256": digest(Path(__file__)),
        "rows": [{"label": label, "sample_times_s": times} for label, times in ROWS],
        "image_sha256": digest(IMAGE),
        "limitations": ["Four sparse frames per proposal cannot establish exact release time, full trajectory, or physical identity across cuts."],
    }, indent=2) + "\n")
    print(IMAGE)


if __name__ == "__main__":
    main()
