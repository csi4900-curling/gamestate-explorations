"""Inspect T11 handle orientation in source frames without inferring revolutions."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "prototype/continuous/clip.mp4"
PREDICTIONS = ROOT / "prototype/trajectory-accuracy/results.json"
OUTPUT = ROOT / "prototype/spin-feasibility"
TIMES = [round(54.0 + i * 0.1, 1) for i in range(31)]
CROP_SIZE = 80
DISPLAY_SIZE = 180
COLUMNS = 8


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def interpolate_center(points, time_s):
    for before, after in zip(points, points[1:]):
        if before["time_s"] <= time_s <= after["time_s"]:
            fraction = (time_s - before["time_s"]) / (after["time_s"] - before["time_s"])
            return [
                before["pixel"][axis] + fraction * (after["pixel"][axis] - before["pixel"][axis])
                for axis in (0, 1)
            ]
    raise ValueError(f"No center prediction brackets {time_s}")


def main():
    predictions = json.loads(PREDICTIONS.read_text())["trajectory"]
    points = [row for row in predictions if 53.5 <= row["time_s"] <= 57.5]
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    rows = (len(TIMES) + COLUMNS - 1) // COLUMNS
    sheet = Image.new("RGB", (COLUMNS * DISPLAY_SIZE, rows * (DISPLAY_SIZE + 24)), "white")
    draw = ImageDraw.Draw(sheet)
    samples = []
    for index, time_s in enumerate(TIMES):
        center = interpolate_center(points, time_s)
        x, y = [round(v) for v in center]
        cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot read source at {time_s:.1f} s")
        frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        crop = frame[y-40:y+40, x-40:x+40]
        if crop.shape[:2] != (CROP_SIZE, CROP_SIZE):
            raise ValueError(f"T11 crop reaches boundary at {time_s:.1f} s")
        crop = cv2.resize(crop, (DISPLAY_SIZE, DISPLAY_SIZE), interpolation=cv2.INTER_NEAREST)
        column, row = index % COLUMNS, index // COLUMNS
        px, py = column * DISPLAY_SIZE, row * (DISPLAY_SIZE + 24)
        sheet.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (px, py + 24))
        draw.text((px + 4, py + 4), f"{time_s:.1f}s / f{frame_index}", fill="black")
        samples.append({
            "requested_clip_time_s": time_s,
            "decoded_frame_index": frame_index,
            "approx_decoded_clip_time_s": frame_index / fps,
            "interpolated_crop_center_px": [x, y],
        })
    cap.release()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUTPUT / "t11-handle-dense-contact-sheet.png")
    (OUTPUT / "dense-provenance.json").write_text(json.dumps({
        "status": "dense_source_frame_visibility_check_not_spin_measurement",
        "clip_sha256": digest(VIDEO),
        "trajectory_predictions_sha256": digest(PREDICTIONS),
        "clip_fps": fps,
        "clip_frame_count": frame_count,
        "sample_spacing_s": 0.1,
        "crop_size_source_px": CROP_SIZE,
        "display_size_px": DISPLAY_SIZE,
        "center_method": "linear_interpolation_of_existing_half_second_predictions",
        "samples": samples,
        "spin_direction": None,
        "revolutions": None,
    }, indent=2) + "\n")
    print(OUTPUT / "t11-handle-dense-contact-sheet.png")


if __name__ == "__main__":
    main()
