"""Expose why frozen public boxes miss small selected 2024 caps."""

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
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--selection", action="append", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first diagnostic")
    events = json.loads(args.events.read_text())
    selections = [json.loads(path.read_text()) for path in args.selection]
    source_hash = digest(args.video)
    if source_hash != events["source_sha256"] or any(
            item["source_sha256"] != source_hash for item in selections):
        parser.error("Source fingerprints differ")
    by_id = {row["id"]: row for row in events["events"]}
    selected = [row for item in selections for row in item["selected"]]
    if len({row["candidate_id"] for row in selected}) != len(selected):
        parser.error("Selection files overlap")
    model = load_model(args.model)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        parser.error("Unreadable video")
    rows = []
    for choice in selected:
        event = by_id[choice["candidate_id"]]
        t = event["crossing_time_s"]
        if t != choice["candidate_time_s"] or event["colour"] != choice["colour_claim"]:
            raise ValueError("Selection differs from event")
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Could not decode {t:.3f}")
        image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hue, saturation, value = cv2.split(hsv)
        mask = (((hue < 12) | (hue > 170)) & (saturation > 60) & (value > 40)
                if event["colour"] == "red" else
                (hue > 16) & (hue < 43) & (saturation > 60) & (value > 65))
        contours, _ = cv2.findContours(mask.astype(np.uint8) * 255,
                                       cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        nearby = []
        proposed_boxes = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            center = (x + width / 2, y + height / 2)
            if math.hypot(center[0] - event["crossing_x_px"],
                          center[1] - event["passage_y_px"]) > 15:
                continue
            nearby.append({"area_px2": area, "bbox": [x, y, width, height]})
            if area < 3 or width > 30 or height > 20:
                continue
            for side in (8, 10, 12, 14, 18, 24):
                for offset in (0, 0.2):
                    proposed_boxes.append([center[0] - side / 2,
                                           center[1] + side * offset - side / 2,
                                           side, side])
        if proposed_boxes:
            features = np.stack([patch_features(image, box) for box in proposed_boxes])
            scores = ((features - model["mean"]) / model["scale"]) @ model["weights"].ravel()
            scores += model["intercept"].item()
            best = float(max(scores))
        else:
            best = None
        rows.append({
            "candidate_id": event["id"], "colour": event["colour"],
            "crossing_time_s": t,
            "nearby_same_colour_contours": nearby,
            "small_box_proposal_count": len(proposed_boxes),
            "best_frozen_model_score": best,
            "frozen_model_threshold": float(model["threshold"]),
            "would_pass_score_only": best is not None and best >= float(model["threshold"]),
        })
    cap.release()
    result = {
        "status": "selected_postscore_small_cap_diagnostic_not_promoted_inference_rule",
        "source_sha256": source_hash,
        "events_sha256": digest(args.events),
        "selection_sha256": [digest(path) for path in args.selection],
        "model_sha256": digest(args.model),
        "runner_sha256": digest(Path(__file__)),
        "standard_min_contour_area_px2": 15,
        "diagnostic_min_contour_area_px2": 3,
        "diagnostic_box_sides_px": [8, 10, 12, 14, 18, 24],
        "rows": rows,
        "limitations": [
            "Cases were selected after event predictions and are not an independent test.",
            "A box score is not physical stone or throw identity.",
            "The modified proposal sizes have not been tested on complete recordings.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"cases": len(rows), "score_positive": sum(
        row["would_pass_score_only"] for row in rows)}))


if __name__ == "__main__":
    main()
