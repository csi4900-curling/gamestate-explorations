"""Score a frozen stone-box model on one public tracked curling clip."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from box_evaluation import score_boxes
from stone_patch_detector import detect_stones, load_model


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reference_boxes(path):
    rows = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) != 6 or fields[0] not in ("0", "1"):
            raise ValueError(f"Invalid tracking label: {path}")
        colour = "red" if fields[0] == "0" else "yellow"
        x, y, width, height = map(float, fields[1:5])
        if not all(0 <= value <= 1 for value in (x, y, width, height)):
            raise ValueError(f"Out-of-range tracking label: {path}")
        rows.append({"colour": colour,
                     "bbox": [(x - width / 2) * 640, (y - height / 2) * 360,
                              width * 640, height * 360],
                     "track_id": fields[5]})
    return rows


def labels_digest(directory):
    h = sha256()
    for path in sorted(directory.glob("*.txt")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frame-step", type=int, default=5)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first public tracking clip score")
    if args.frame_step < 1:
        parser.error("Frame step must be positive")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = round(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    model = load_model(args.model)
    rows = []
    total = {key: 0 for key in ("references", "predictions", "matches", "misses", "extras")}
    for index in range(0, frame_count, args.frame_step):
        label_path = args.labels / f"{index:08d}.txt"
        if not label_path.exists():
            raise FileNotFoundError(label_path)
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Decode failed at frame {index}")
        reference = reference_boxes(label_path)
        predicted = detect_stones(frame, model)
        score = score_boxes(reference, predicted)
        for key in total:
            total[key] += score[key]
        rows.append({"frame_index": index,
                     "time_s": round(index / fps, 3),
                     "reference": reference,
                     "predicted": predicted,
                     "score": score})
    capture.release()
    tp, fp, fn = total["matches"], total["extras"], total["misses"]
    total.update({"precision": round(tp / (tp + fp), 4) if tp + fp else None,
                  "recall": round(tp / (tp + fn), 4) if tp + fn else None,
                  "f1": round(2 * tp / (2 * tp + fp + fn), 4)
                  if 2 * tp + fp + fn else None})
    output = {
        "status": "public_tracking_clip_box_probe_not_throw_event_score",
        "video_sha256": digest(args.video),
        "labels_sha256": labels_digest(args.labels),
        "model_sha256": digest(args.model),
        "detector_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": digest(Path(__file__)),
        "frame_count": frame_count,
        "fps": fps,
        "sampled_frame_step": args.frame_step,
        "sampled_frame_count": len(rows),
        "box_iou_threshold": 0.5,
        "totals": total,
        "rows": rows,
        "limitations": [
            "This is box detection on one short public clip, not physical stone identity or throw-event F1.",
            "Adjacent sampled frames are correlated; frame totals are not independent trials.",
            "Public clip IDs do not establish match-level independence from detector training images.",
            "The published tracking IDs may change across camera cuts and are not scored here.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(total)


if __name__ == "__main__":
    main()
