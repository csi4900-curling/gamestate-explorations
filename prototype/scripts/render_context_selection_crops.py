"""Render crossing pixels for a frozen context-ranked review selection."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output exists; preserve original review")
    selection = json.loads(args.selection.read_text())
    events = json.loads(args.events.read_text())
    source_hash = digest(args.video)
    if source_hash != selection["source_sha256"] or source_hash != events["source_sha256"]:
        parser.error("Review inputs do not share the source video")
    by_id = {row["id"]: row for row in events["events"]}
    rows = selection["selected"]
    if len(rows) != selection["count"] or any(row["candidate_id"] not in by_id for row in rows):
        parser.error("Selection and event IDs disagree")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        parser.error("Unreadable video")
    sheets = []
    args.output_dir.mkdir(parents=True)
    for first in range(0, len(rows), 5):
        group = rows[first:first + 5]
        sheet = np.full((len(group) * 320, 960, 3), 25, dtype=np.uint8)
        for index, row in enumerate(group):
            event = by_id[row["candidate_id"]]
            if (event["crossing_time_s"] != row["candidate_time_s"] or
                    event["colour"] != row["colour_claim"]):
                raise ValueError("Selection differs from event content")
            x = round(event["crossing_x_px"])
            y = round(event["passage_y_px"])
            for col, offset in enumerate((-0.2, 0, 0.2)):
                seconds = event["crossing_time_s"] + offset
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode {seconds:.3f}")
                frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                padded = cv2.copyMakeBorder(frame, 45, 45, 45, 45,
                                            cv2.BORDER_CONSTANT, value=(25, 25, 25))
                crop = padded[y:y + 90, x:x + 90].copy()
                cv2.line(crop, (45, 38), (45, 52), (0, 255, 255), 1)
                cv2.line(crop, (38, 45), (52, 45), (0, 255, 255), 1)
                zoom = cv2.resize(crop, (320, 290), interpolation=cv2.INTER_NEAREST)
                top, left = index * 320, col * 320
                sheet[top + 30:top + 320, left:left + 320] = zoom
                cv2.putText(sheet, f"{event['id']} {event['colour']} {seconds:.2f}s",
                            (left + 7, top + 21), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (255, 255, 255), 1, cv2.LINE_AA)
        path = args.output_dir / f"sheet-{first // 5 + 1:02d}.jpg"
        if not cv2.imwrite(str(path), sheet):
            raise RuntimeError("Could not write source sheet")
        sheets.append({"path": path.name, "sha256": digest(path),
                       "candidate_ids": [row["candidate_id"] for row in group]})
    cap.release()
    manifest = {
        "status": "prediction_ranked_crossing_pixel_review_not_independent_labels",
        "source_sha256": source_hash,
        "selection_sha256": digest(args.selection),
        "events_sha256": digest(args.events),
        "sheets": sheets,
        "sample_offsets_s": [-0.2, 0, 0.2],
        "crop_size_px": 90,
        "limitations": [
            "Crosshair marks the interpolated tracked crossing, not physical release.",
            "The cases were selected from model scores and cannot estimate event accuracy.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"reviewed": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
