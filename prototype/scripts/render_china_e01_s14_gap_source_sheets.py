"""Render selected source frames around the China end-one receiving gap."""

import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
AUDIT = BASE / "china-e01-s14-receiving-gap-development.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
SHEETS = {
    "china-s63-e01-s14-gap-source-review.jpg": (
        905.6,
        906.8,
        908.0,
        909.2,
        910.4,
        911.6,
        912.8,
        914.0,
        915.2,
    ),
    "china-s64-s65-e01-s14-gap-source-review.jpg": (
        915.4,
        917.0,
        919.0,
        921.0,
        923.0,
        925.0,
        927.0,
        929.0,
        931.0,
    ),
}


def main():
    audit = json.loads(AUDIT.read_text())
    if audit["official_gap_id_for_selection_only"] != "PREL000102-E01-S14" or audit["camera_shots"][
        1
    ]["interval_s"] != [915.4, 928.4]:
        raise ValueError("Selected gap changed")
    capture = cv2.VideoCapture(str(VIDEO))
    if not capture.isOpened():
        raise ValueError("Cannot open China source video")
    try:
        for name, times in SHEETS.items():
            sheet = Image.new("RGB", (1440, 876), "#ddd")
            for index, t in enumerate(times):
                capture.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ok, frame = capture.read()
                if not ok:
                    raise ValueError(f"Cannot read source at {t}s")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image.thumbnail((480, 270))
                tile = Image.new("RGB", (480, 292), "white")
                tile.paste(image, ((480 - image.width) // 2, 22))
                ImageDraw.Draw(tile).text((6, 3), f"China {t:.1f}s", fill="black")
                sheet.paste(tile, ((index % 3) * 480, (index // 3) * 292))
            output = BASE / name
            sheet.save(output, quality=88)
            print(output)
    finally:
        capture.release()


if __name__ == "__main__":
    main()
