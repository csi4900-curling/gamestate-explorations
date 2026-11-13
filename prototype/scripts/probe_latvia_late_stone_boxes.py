#!/usr/bin/env python3
"""Selected-frame transfer of existing research stone-box models to Latvia."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stone_patch_detector import detect_stones, load_model

VIDEO = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-360p.mp4"
TIMELINE = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/timeline.json"
)
OUTPUT = (
    ROOT
    / "validation/throw-event-benchmark/canada-latvia-2024/late-right-stone-box-selected-development.json"
)
TIMES_S = (5500, 5580, 5627, 5803, 5805, 5900, 6145, 6495)
MODELS = {
    name: ROOT / f"validation/curlobserver-learned-probe/{name}/model.npz"
    for name in ("model-v1", "model-v2", "public-tracking-v2")
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Selected-frame box artifact already exists")
    timeline = json.loads(TIMELINE.read_text())
    source_hash = digest(VIDEO)
    if source_hash != timeline["source_sha256"]:
        raise ValueError("Source video differs from timeline")
    models = {name: load_model(path) for name, path in MODELS.items()}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for time_s in TIMES_S:
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (360, 640):
                raise RuntimeError(f"Cannot decode {time_s} s")
            row = {"source_time_s": time_s, "models": {}}
            for name, model in models.items():
                boxes = []
                for box in detect_stones(frame, model):
                    x, y, w, h = box["bbox"]
                    if not (330 <= x + w / 2 < 630 and 145 <= y + h / 2 < 325):
                        continue
                    boxes.append(
                        {
                            "colour": box["colour"],
                            "bbox_xywh": [round(float(v), 2) for v in box["bbox"]],
                            "confidence": round(float(box["confidence"]), 5),
                        }
                    )
                row["models"][name] = boxes
            rows.append(row)
    finally:
        cap.release()
    result = {
        "status": "postreview_selected_box_transfer_not_event_detection",
        "source_sha256": source_hash,
        "timeline_sha256": digest(TIMELINE),
        "model_sha256": {name: digest(path) for name, path in MODELS.items()},
        "detector_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": digest(Path(__file__)),
        "selected_times_s": TIMES_S,
        "right_roi_xyxy": [330, 145, 630, 325],
        "rows": rows,
        "limitations": [
            "Frames were selected after seeing the Latvia failure; this is not a held-out benchmark.",
            "A box can be a parked or handled stone, person/equipment false positive, or wrong-colour proposal.",
            "Eight sparse frames cannot measure object recall, delivered-stone identity or throw F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({name: [len(row["models"][name]) for row in rows] for name in MODELS}))


if __name__ == "__main__":
    main()
