"""Render source frames around the four release-cue sequence skips."""

import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
QUEUE = BASE / "pwg2022-v3-sequence-review-queue-development.json"
OFFSETS_S = (-2, -1, -0.4, 0, 0.4, 1, 2, 3)
EXPECTED = {"VISUAL-S243", "VISUAL-S593", "VISUAL-S60", "VISUAL-S282"}


def render(row):
    source = ROOT / row["source_video_path"]
    video = cv2.VideoCapture(str(source))
    if not video.isOpened():
        raise ValueError(f"Cannot open {source}")
    tiles = []
    try:
        for offset in OFFSETS_S:
            t = row["source_release_cue_time_s"] + offset
            video.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = video.read()
            if not ok:
                raise ValueError(f"Cannot read {source} at {t:.1f}s")
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            image.thumbnail((480, 270))
            tile = Image.new("RGB", (480, 292), "white")
            tile.paste(image, ((480 - image.width) // 2, 22))
            ImageDraw.Draw(tile).text(
                (6, 3), f"{row['event_id']}  {t:.1f}s", fill="black")
            tiles.append(tile)
    finally:
        video.release()
    sheet = Image.new("RGB", (1920, 584), "#ddd")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % 4) * 480, (index // 4) * 292))
    output = BASE / (f"{row['recording_code']}-{row['event_id']}"
                     "-sequence-skip-source-review.jpg")
    sheet.save(output, quality=85)
    return output


def main():
    queue = json.loads(QUEUE.read_text())
    rows = [row for row in queue["rows"]
            if row["kind"] == "candidate_skipped_in_every_optimum"
            and row["release_cue_status"] == "unique_passage"]
    if {row["event_id"] for row in rows} != EXPECTED:
        raise ValueError("Source release-cue skip set changed")
    for row in rows:
        print(render(row))


if __name__ == "__main__":
    main()
