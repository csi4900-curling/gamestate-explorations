"""Extract original-pixel T11 handle crops for a rotation feasibility audit.

This records visibility only; it never estimates orientation or revolutions.
"""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "prototype/continuous/clip.mp4"
TRACK = ROOT / "prototype/cross-view/results.json"
OUT = ROOT / "prototype/trajectory-accuracy"
CLIP_START_S = 2260.0
TIMES = [2312.5 + 0.25 * index for index in range(13)]
CROP_HALF_SIZE = 32
DISPLAY_SIZE = 128
YELLOW_HSV_LOWER = (13, 65, 80)
YELLOW_HSV_UPPER = (42, 255, 255)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def interpolated_center(samples, time_s):
    before = max((row for row in samples if row["time_s"] <= time_s),
                 key=lambda row: row["time_s"])
    after = min((row for row in samples if row["time_s"] >= time_s),
                key=lambda row: row["time_s"])
    alpha = ((time_s - before["time_s"]) /
             (after["time_s"] - before["time_s"])) if before is not after else 0
    return [round((1 - alpha) * before["pixel"][axis] +
                  alpha * after["pixel"][axis]) for axis in (0, 1)]


def main():
    track = json.loads(TRACK.read_text())
    t11 = next(row for row in track["throws"] if row["id"] == "T11")
    samples = t11["arrival"]
    if TIMES[0] < samples[0]["time_s"] or TIMES[-1] > samples[-1]["time_s"]:
        raise ValueError("Requested sample lies outside the receiving track")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise RuntimeError("Unreadable T11 clip")
    panels, rows = [], []
    for time_s in TIMES:
        frame_index = round((time_s - CLIP_START_S) * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Could not decode T11 at {time_s}")
        x, y = interpolated_center(samples, time_s)
        bounds = [x-CROP_HALF_SIZE, y-CROP_HALF_SIZE,
                  x+CROP_HALF_SIZE, y+CROP_HALF_SIZE]
        if bounds[0] < 0 or bounds[1] < 0 or bounds[2] > frame.shape[1] or bounds[3] > frame.shape[0]:
            raise ValueError(f"T11 crop outside frame at {time_s}")
        crop = frame[bounds[1]:bounds[3], bounds[0]:bounds[2]]
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        yellow = cv2.inRange(hsv, YELLOW_HSV_LOWER, YELLOW_HSV_UPPER)
        yellow[CROP_HALF_SIZE:, :] = 0
        _, yellow_x = np.where(yellow > 0)
        panel = cv2.resize(crop, (DISPLAY_SIZE, DISPLAY_SIZE),
                           interpolation=cv2.INTER_NEAREST)
        cv2.putText(panel, f"{time_s:.2f}", (2, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (10, 10, 10), 1)
        panels.append(panel)
        rows.append({"source_time_s": time_s, "video_frame_index": frame_index,
                     "tracked_center_px_interpolated": [x, y],
                     "crop_xyxy_px": bounds,
                     "yellow_upper_half_pixel_count": int(len(yellow_x)),
                     "yellow_upper_half_x_spread_px": round(
                         float(yellow_x.std()), 3) if len(yellow_x) else None})
    capture.release()
    blank = np.full_like(panels[0], 255)
    panels.append(blank)
    sheet = np.vstack([np.hstack(panels[index:index+7]) for index in (0, 7)])
    image_path = OUT / "t11-handle-visibility.jpg"
    if not cv2.imwrite(str(image_path), sheet):
        raise RuntimeError("Could not write contact sheet")
    manifest = {
        "status": "visual_spin_feasibility_only_no_angle_or_revolution_estimate",
        "source_video_sha256": digest(VIDEO),
        "track_sha256": digest(TRACK),
        "runner_sha256": digest(Path(__file__)),
        "contact_sheet_sha256": digest(image_path),
        "fps": fps,
        "source_time_to_clip_time_offset_s": CLIP_START_S,
        "crop_original_size_px": [2*CROP_HALF_SIZE, 2*CROP_HALF_SIZE],
        "display_scale": DISPLAY_SIZE // (2*CROP_HALF_SIZE),
        "yellow_signal_hsv_lower": YELLOW_HSV_LOWER,
        "yellow_signal_hsv_upper": YELLOW_HSV_UPPER,
        "yellow_signal_region": "upper_half_of_original_64px_crop",
        "samples": rows,
        "limitations": [
            "Track-center interpolation only positions the crop; it is not an angular measurement.",
            "The yellow-mask spread includes handle and stone cap, so it is a shape signal, not orientation.",
            "The camera is a side view, so handle silhouettes can alias multiple physical angles.",
            "The sheet covers three seconds of one already selected candidate, not the full throw.",
            "Occlusion, motion blur and camera changes are not evaluated.",
        ],
    }
    (OUT / "t11-handle-visibility.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
