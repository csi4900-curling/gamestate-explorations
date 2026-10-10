"""Postreview frame-level yellow visibility at Estonia S02 panel edges.

Fixed crops follow the source-reviewed right exit and left entry. They do not
prove physical identity or estimate an unbiased detector performance metric.
"""

from hashlib import sha256
import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
SHEET = BASE / "yellow-s02-simultaneous-edge-overlap.jpg"
OUT = BASE / "yellow-s02-edge-timing-postreview.json"
START_S, STOP_S, OFFSET_S = 1757.5, 1759.5, 1650
FPS = 30
ROIS = {
    "left_entry": (400, 0, 560, 180),
    "right_exit": (1300, 920, 1500, 1080),
}
YELLOW_PIXEL_THRESHOLD = 50


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first timing audit")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != FPS:
        raise RuntimeError("Cannot open expected 30-fps source")
    first = round((START_S-OFFSET_S)*FPS)
    last = round((STOP_S-OFFSET_S)*FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    rows = []
    try:
        for index in range(first, last+1):
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode frame {index}")
            counts = {}
            for name, (x1, y1, x2, y2) in ROIS.items():
                hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
                hue, saturation, value = cv2.split(hsv)
                yellow = ((hue > 16) & (hue < 43) &
                          (saturation > 60) & (value > 65))
                counts[name] = int(yellow.sum())
            rows.append({"source_time_s": round(OFFSET_S+index/FPS, 5),
                         "frame_index": index,
                         "yellow_pixels": counts,
                         "yellow_visible_by_threshold": {
                             name: count >= YELLOW_PIXEL_THRESHOLD
                             for name, count in counts.items()}})
    finally:
        cap.release()
    right_times = [r["source_time_s"] for r in rows
                   if r["yellow_visible_by_threshold"]["right_exit"]]
    left_times = [r["source_time_s"] for r in rows
                  if r["yellow_visible_by_threshold"]["left_entry"]]
    summary = {
        "right_last_visible_s": max(right_times) if right_times else None,
        "left_first_visible_s": min(left_times) if left_times else None,
        "edge_visibility_gap_s": round(min(left_times)-max(right_times), 5)
        if left_times and right_times else None,
        "simultaneous_threshold_frames": sum(
            r["yellow_visible_by_threshold"]["right_exit"] and
            r["yellow_visible_by_threshold"]["left_entry"] for r in rows),
    }
    result = {
        "status": "postreview_selected_roi_edge_visibility_not_identity_validation",
        "video_sha256": digest(VIDEO),
        "source_sheet_sha256": digest(SHEET),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": [START_S, STOP_S],
        "fps": FPS,
        "rois_xyxy_1080p": ROIS,
        "yellow_hsv_hue_exclusive": [16, 43],
        "yellow_pixel_threshold": YELLOW_PIXEL_THRESHOLD,
        "summary": summary,
        "frames": rows,
        "limitations": [
            "Crops and threshold were selected after viewing the apparent transition.",
            "Yellow pixels can come from another object; the source images are required for interpretation.",
            "A visibility gap between cameras does not itself prove physical stone identity or sync accuracy.",
            "This does not estimate event start, stop, full-video F1 or game state.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
