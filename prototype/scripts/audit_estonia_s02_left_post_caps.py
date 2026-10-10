"""Source-frame left-house cap stability after provisional Estonia S02."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stable_image_cap_observation import stable_cap_centers

BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
HANDOFF = BASE / "yellow-s02-cross-view-observation-handoff-postreview-v2.json"
OUTPUT = BASE / "yellow-s02-left-post-partial-image-caps-postreview.json"
SHEET = BASE / "yellow-s02-left-post-partial-image-caps-postreview.jpg"
TIMES = (1784.5, 1789.5, 1794.5)
ROI = (0, 500, 900, 980)
MIN_CONTOUR_AREA = 250


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def proposals(frame):
    left = frame[:, :960]
    hsv = cv2.cvtColor(left, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (17, 61, 66), (42, 255, 255))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    x1, y1, x2, y2 = ROI
    caps = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        cx, cy = x + w / 2, y + h / 2
        if (area < MIN_CONTOUR_AREA or w > 160 or h > 100 or
                not (x1 <= cx <= x2 and y1 <= cy <= y2)):
            continue
        caps.append({"colour": "yellow", "pixel_center": [cx, cy],
                     "bbox_xywh": [x, y, w, h],
                     "yellow_contour_area_px2": round(float(area), 2)})
    return sorted(caps, key=lambda row: row["pixel_center"][0])


def main():
    handoff = json.loads(HANDOFF.read_text())
    if handoff["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Source video changed")
    if (handoff["candidate_id"] != "S02" or
            handoff["candidate_crossing_time_s"] >= TIMES[0]):
        raise ValueError("Wrong event or chronology")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps source")
    frames, views = [], []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, (t - 1650) * 1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Cannot decode source at {t}")
            found = proposals(frame)
            frames.append({"source_time_s": t, "caps": found})
            view = cv2.resize(frame[:, :960], (480, 540),
                              interpolation=cv2.INTER_AREA)
            panel = np.full((574, 480, 3), (20, 20, 20), np.uint8)
            panel[34:] = view
            cv2.putText(panel, f"{t:.1f} s left house", (8, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255), 2)
            for item in found:
                x, y, w, h = item["bbox_xywh"]
                cv2.rectangle(panel, (round(x/2), 34+round(y/2)),
                              (round((x+w)/2), 34+round((y+h)/2)),
                              (255, 0, 255), 2)
            views.append(panel)
    finally:
        cap.release()
    stable = stable_cap_centers(frames)
    if not cv2.imwrite(str(SHEET), np.hstack(views),
                       [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise RuntimeError("Could not write source sheet")
    result = {
        "status": "postreview_left_view_partial_image_caps_not_complete_board",
        "candidate_id": handoff["candidate_id"],
        "source_video_sha256": digest(VIDEO),
        "handoff_sha256": digest(HANDOFF),
        "runner_sha256": digest(Path(__file__)),
        "stability_code_sha256": digest(ROOT / "prototype/stable_image_cap_observation.py"),
        "source_sheet_sha256": digest(SHEET),
        "selected_times_s": TIMES,
        "roi_xyxy_1080p": ROI,
        "minimum_yellow_contour_area_px2": MIN_CONTOUR_AREA,
        "frames": frames,
        "repeated_caps": stable,
        "camera_registration_verified": False,
        "complete_board_verified": False,
        "delivered_stone_identity_verified": False,
        "physical_settle_verified": False,
        "simulation_ready": False,
        "limitations": [
            "Times and left-house ROI were chosen after viewing S02 source frames.",
            "Only yellow colour components are scanned; hidden and red stones are unmeasured.",
            "Repeated image centres may be stone handles, but no body/ground calibration or camera registration is verified.",
            "This does not establish which repeated cap belongs to S02 or that the physical board is complete.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"frame_cap_counts": [len(row["caps"]) for row in frames],
                      "repeated_caps": stable}))


if __name__ == "__main__":
    main()
