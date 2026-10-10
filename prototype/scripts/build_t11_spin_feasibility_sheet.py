"""Show handle visibility at sparse T11 times; do not estimate rotation count."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "prototype/continuous/clip.mp4"
PREDICTIONS = ROOT / "prototype/trajectory-accuracy/results.json"
OUTPUT = ROOT / "prototype/spin-feasibility"
TIMES = (54.0, 54.5, 55.0, 55.5, 56.0, 56.5, 57.0)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    points = {row["time_s"]: row for row in json.loads(PREDICTIONS.read_text())["trajectory"]}
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    sheet = Image.new("RGB", (180 * len(TIMES), 204), "white")
    draw = ImageDraw.Draw(sheet)
    for index, time_s in enumerate(TIMES):
        x, y = [round(v) for v in points[time_s]["pixel"]]
        cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot read video at {time_s}")
        crop = frame[y-40:y+40, x-40:x+40]
        if crop.shape[:2] != (80, 80):
            raise ValueError("Stone crop reached the source frame boundary")
        crop = cv2.resize(crop, (180, 180), interpolation=cv2.INTER_NEAREST)
        sheet.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (180*index, 24))
        draw.text((180*index+4, 4), f"{time_s:.1f} s", fill="black")
    cap.release()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUTPUT / "t11-handle-contact-sheet.png")
    (OUTPUT / "provenance.json").write_text(json.dumps({
        "status": "handle_visibility_feasibility_not_spin_measurement",
        "clip_sha256": digest(VIDEO), "trajectory_predictions_sha256": digest(PREDICTIONS),
        "sampled_clip_times_s": TIMES, "source_offset_s": 2260,
        "crop_source_size_px": [80, 80], "display_size_px": [180, 180],
        "interpolation": "nearest_neighbour_display_only",
        "spin_direction": None, "revolutions": None,
    }, indent=2) + "\n")
    print(OUTPUT / "t11-handle-contact-sheet.png")


if __name__ == "__main__":
    main()
