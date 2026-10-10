"""Track left yellow cap from panel entry, then compare with prior S02 path.

The source-only contour tracker does not read S02 positions until its own path
is complete. It is a selected, postreview cross-view diagnostic, not an
independent identity or throw-event benchmark.
"""

from hashlib import sha256
import json
from math import hypot
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
S02 = BASE / "left-bound-full-interval/s02-paired.json"
EDGE = BASE / "yellow-s02-edge-timing-postreview.json"
OUT = BASE / "yellow-s02-left-entry-to-prior-path-postreview.json"
START_S, STOP_S, STEP_S, OFFSET_S = 1758.5, 1771.5, 0.5, 1650
ROI_XYXY = (350, 0, 700, 750)
FIRST_XYXY = (400, 0, 550, 80)
MAX_STEP_PX = 75


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def candidates(frame):
    x1, y1, x2, y2 = ROI_XYXY
    crop = frame[y1:y2, x1:x2]
    hue, saturation, value = cv2.split(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV))
    yellow = ((hue > 16) & (hue < 43) & (saturation > 60) & (value > 65))
    contours, _ = cv2.findContours(yellow.astype("uint8")*255,
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rows = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if area < 15 or w > 160 or h > 100:
            continue
        rows.append({"center_1080p_px": [x1+x+w/2, y1+y+h/2],
                     "bbox_1080p_px": [x1+x, y1+y, w, h],
                     "yellow_contour_area_px2": round(float(area), 2)})
    return rows


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first bridge")
    paired = json.loads(S02.read_text())
    edge = json.loads(EDGE.read_text())
    source_hash = digest(VIDEO)
    if paired["source_sha256"] != source_hash or edge["video_sha256"] != source_hash:
        raise ValueError("High-resolution source changed")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps clip")
    rows = []
    try:
        ticks = round((STOP_S-START_S)/STEP_S)
        for tick in range(ticks+1):
            t = START_S+tick*STEP_S
            cap.set(cv2.CAP_PROP_POS_FRAMES, round((t-OFFSET_S)*30))
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            options = candidates(frame)
            if not rows:
                fx1, fy1, fx2, fy2 = FIRST_XYXY
                eligible = [p for p in options if
                            fx1 <= p["center_1080p_px"][0] <= fx2 and
                            fy1 <= p["center_1080p_px"][1] <= fy2]
                if len(eligible) != 1:
                    raise RuntimeError(f"Ambiguous first left entry: {len(eligible)}")
                chosen = eligible[0]
                step = None
                cost = None
            else:
                latest = rows[-1]["chosen"]["center_1080p_px"]
                if len(rows) > 1:
                    before = rows[-2]["chosen"]["center_1080p_px"]
                    prediction = [2*latest[a]-before[a] for a in (0, 1)]
                else:
                    prediction = latest
                choices = []
                for p in options:
                    xy = p["center_1080p_px"]
                    distance = hypot(xy[0]-latest[0], xy[1]-latest[1])
                    if distance <= MAX_STEP_PX:
                        pred_error = hypot(xy[0]-prediction[0],
                                           xy[1]-prediction[1])
                        choices.append((pred_error+0.25*distance, distance, p))
                if not choices:
                    raise RuntimeError(f"Left path lost at {t}")
                cost, step, chosen = min(choices)
            rows.append({"source_time_s": t, "candidate_count_in_roi": len(options),
                         "eligible_count": len(eligible) if len(rows)==0 else
                         len(choices),
                         "chosen": chosen,
                         "step_1080p_px": round(step, 2) if step is not None else None,
                         "association_cost_1080p_px": round(cost, 2)
                         if cost is not None else None})
    finally:
        cap.release()
    by_time = {r["source_time_s"]: r for r in rows}
    prior = paired["cases"]["base"]["selection"]["path"]
    comparison = []
    for p in prior:
        t = p["source_time_s"]
        if t not in by_time:
            continue
        xy = by_time[t]["chosen"]["center_1080p_px"]
        distance = hypot(xy[0]-p["pixel_center"][0],
                         xy[1]-p["pixel_center"][1])
        comparison.append({"source_time_s": t,
                           "new_contour_center_1080p_px": xy,
                           "prior_s02_pixel_center": p["pixel_center"],
                           "center_distance_px": round(distance, 3)})
    if not comparison:
        raise RuntimeError("No temporal overlap with prior S02 path")
    result = {
        "status": "postreview_source_only_left_entry_then_prior_path_comparison",
        "video_sha256": source_hash,
        "prior_s02_sha256": digest(S02),
        "edge_audit_sha256": digest(EDGE),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": [START_S, STOP_S],
        "sample_period_s": STEP_S,
        "left_roi_xyxy_1080p": ROI_XYXY,
        "first_entry_region_xyxy_1080p": FIRST_XYXY,
        "maximum_step_px_per_sample": MAX_STEP_PX,
        "rows": rows,
        "prior_s02_overlap": comparison,
        "mean_overlap_center_distance_px": round(
            sum(r["center_distance_px"] for r in comparison)/len(comparison), 3),
        "maximum_overlap_center_distance_px": max(
            r["center_distance_px"] for r in comparison),
        "limitations": [
            "The first-entry region was chosen after source review; this is not a blind tracker test.",
            "The prior S02 path is used only after new source-only tracking, to measure overlap.",
            "Pixel-centre agreement in the left view does not by itself prove physical identity with the right-view stone.",
            "No homography validation, physical stop, full-video event F1 or game-state claim follows.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"samples": len(rows), "overlap": len(comparison),
                      "mean_center_distance_px": result["mean_overlap_center_distance_px"],
                      "max_center_distance_px": result["maximum_overlap_center_distance_px"]}))


if __name__ == "__main__":
    main()
