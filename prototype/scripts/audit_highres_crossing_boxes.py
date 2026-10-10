"""Compare frozen box scores on aligned 1080p and 360p selected crossings.

This is a development diagnostic, not an event decision rule or validation set.
"""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stone_patch_detector import load_model, patch_features


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def frame_at(capture, seconds):
    fps = capture.get(cv2.CAP_PROP_FPS)
    capture.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * fps))
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Could not decode frame at {seconds:.3f} s")
    return frame


def local_proposals(frame, colour, point, scale):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    if colour == "red":
        mask = ((hue < 12) | (hue > 170)) & (saturation > 60) & (value > 40)
    else:
        mask = (hue > 16) & (hue < 43) & (saturation > 60) & (value > 65)
    contours, _ = cv2.findContours(mask.astype(np.uint8) * 255,
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    proposals, nearby = [], []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        center_x, center_y = x + width / 2, y + height / 2
        distance = math.hypot(center_x - point[0], center_y - point[1])
        if distance > 15 * scale:
            continue
        area = cv2.contourArea(contour)
        nearby.append({"area_px2": round(area, 2),
                       "center_distance_px": round(distance, 2),
                       "bbox": [x, y, width, height]})
        # The physical area floor is the original 15 px² at 360p, scaled
        # with image area. The smaller-box experiment remains separate.
        if area < 15 * scale * scale or width > 160 * scale or height > 100 * scale:
            continue
        if width > 35 * scale:
            sizes = sorted({min(160 * scale, round(width * factor))
                            for factor in (1.2, 1.6)})
            offsets = (0.22, 0.38)
        else:
            sizes = [side * scale for side in (14, 18, 24, 30, 38, 48)]
            offsets = (0, 0.2)
        for side in sizes:
            for offset in offsets:
                proposals.append([center_x - side / 2,
                                  center_y + side * offset - side / 2,
                                  side, side])
    return proposals, sorted(nearby, key=lambda item: item["center_distance_px"])


def score(frame, boxes, model):
    if not boxes:
        return None
    features = np.stack([patch_features(frame, box) for box in boxes])
    scores = ((features - model["mean"]) / model["scale"]) @ model["weights"].ravel()
    scores += model["intercept"].item()
    index = int(np.argmax(scores))
    return {"best_score": float(scores[index]),
            "passes_frozen_threshold": bool(scores[index] >= float(model["threshold"])),
            "best_box": boxes[index]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--low-video", required=True, type=Path)
    parser.add_argument("--high-video", required=True, type=Path)
    parser.add_argument("--high-start-s", required=True, type=float)
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--model", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first diagnostic")
    prior = json.loads(args.probe.read_text())
    if digest(args.low_video) != prior["source_sha256"]:
        parser.error("360p source differs from crossing probe")
    models = {path.parent.name: load_model(path) for path in args.model}
    if len(models) != len(args.model):
        parser.error("Model parent names must be unique")
    low = cv2.VideoCapture(str(args.low_video))
    high = cv2.VideoCapture(str(args.high_video))
    if not low.isOpened() or not high.isOpened():
        parser.error("Could not open both videos")
    high_duration = high.get(cv2.CAP_PROP_FRAME_COUNT) / high.get(cv2.CAP_PROP_FPS)
    rows = []
    for case in prior["cases"]:
        t = case["crossing_time_s"]
        if not args.high_start_s + 0.2 <= t < args.high_start_s + high_duration - 0.2:
            continue
        samples = []
        for offset in (-0.2, 0, 0.2):
            low_frame = frame_at(low, t + offset)
            high_frame = frame_at(high, t + offset - args.high_start_s)
            if low_frame.shape[:2] != (360, 640) or high_frame.shape[:2] != (1080, 1920):
                raise ValueError("Expected aligned 360p and 1080p sources")
            alignment_mae = float(np.abs(low_frame.astype(np.float32) -
                             cv2.resize(high_frame, (640, 360)).astype(np.float32)).mean())
            point = case["crossing_point_px"]
            views = {}
            for name, frame, scale in (("360p", low_frame, 1), ("1080p", high_frame, 3)):
                proposals, contours = local_proposals(
                    frame, case["colour_claim"], [coordinate * scale for coordinate in point], scale)
                views[name] = {"nearby_contours": contours,
                               "local_proposal_count": len(proposals),
                               "models": {key: score(frame, proposals, model)
                                          for key, model in models.items()}}
            samples.append({"time_s": round(t + offset, 3),
                            "frame_alignment_mae": alignment_mae,
                            "views": views})
        rows.append({"event_id": case["event_id"], "colour_claim": case["colour_claim"],
                     "crossing_time_s": t, "samples": samples})
    low.release()
    high.release()
    result = {
        "status": "prediction_targeted_highres_box_diagnostic_not_event_validation",
        "low_video_sha256": digest(args.low_video),
        "high_video_sha256": digest(args.high_video),
        "probe_sha256": digest(args.probe),
        "model_sha256": {path.parent.name: digest(path) for path in args.model},
        "runner_sha256": digest(Path(__file__)),
        "high_start_s": args.high_start_s,
        "sampling_offsets_s": [-0.2, 0, 0.2],
        "area_floor_px2_at_360p": 15,
        "cases": rows,
        "limitations": [
            "Cases were selected after event prediction, not independently labelled.",
            "A high box score does not prove physical stone or throw identity.",
            "The clip classifier was frozen on different source data and has not been calibrated for 1080p input.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"cases": len(rows), "ids": [row["event_id"] for row in rows]}))


if __name__ == "__main__":
    main()
