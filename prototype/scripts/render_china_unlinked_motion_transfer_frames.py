"""Render fixed source frames for the six China transfer proposals."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
PROPOSALS = (
    ROOT / "validation/official-shot-sequence/china-unlinked-motion-rescue-transfer-first.json"
)
PREFIX = ROOT / "validation/official-shot-sequence/china-unlinked-motion-transfer-source-frames"
META = PREFIX.with_suffix(".json")
ROWS = (
    ("S108 → S109-R01", (1455, 1458, 1459, 1464)),
    ("S216 → S217-R01", (2665, 2669, 2671, 2680)),
    ("S320 → S321-R01", (4250, 4253, 4254, 4262)),
    ("S357 → S358-Y01", (4710, 4717, 4719, 4724)),
    ("S377 → S378-R01", (5042, 5047, 5048, 5060)),
    ("S449 → S450-R01", (6050, 6054, 6056, 6066)),
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    images = [Path(f"{PREFIX}-{part}.jpg") for part in (1, 2)]
    if META.exists() or any(path.exists() for path in images):
        raise SystemExit("Output exists; preserve first China transfer frame sheet")
    proposals = json.loads(PROPOSALS.read_text())["proposals"]
    actual = [(row["origin_shot_id"], row["receiving_episode_id"]) for row in proposals]
    expected = [(label.split(" → ")[0], label.split(" → ")[1]) for label, _ in ROWS]
    if actual != expected:
        raise SystemExit("Proposal set changed since frame selection")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError("Cannot open China source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    try:
        for part, image_path in enumerate(images):
            canvas = Image.new("RGB", (640 * 4, 390 * 3), "white")
            draw = ImageDraw.Draw(canvas)
            for row, (label, times) in enumerate(ROWS[part * 3 : (part + 1) * 3]):
                for col, second in enumerate(times):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f"Frame decode failed at {second}s")
                    frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                    canvas.paste(
                        Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
                        (col * 640, row * 390 + 30),
                    )
                    draw.text((col * 640 + 8, row * 390 + 8), f"{label}  {second}s", fill="black")
            canvas.save(image_path, quality=85)
    finally:
        cap.release()
    META.write_text(
        json.dumps(
            {
                "status": "source_frame_review_sheet_not_independent_event_labels",
                "source_video_sha256": digest(VIDEO),
                "proposals_sha256": digest(PROPOSALS),
                "runner_sha256": digest(Path(__file__)),
                "rows": [{"label": label, "sample_times_s": times} for label, times in ROWS],
                "image_sha256": {path.name: digest(path) for path in images},
                "limitations": [
                    "Sparse frames do not prove which stone moved after a collision or across a camera cut."
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(images)


if __name__ == "__main__":
    main()
