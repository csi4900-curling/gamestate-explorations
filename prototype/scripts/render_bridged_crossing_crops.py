"""Render local source pixels at every recovered Scotland passage crossing."""

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
    parser.add_argument("--triage", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory exists; preserve original review")
    triage = json.loads(args.triage.read_text())
    if digest(args.video) != triage["source_sha256"]:
        parser.error("Video differs from triage source")
    rows = triage["new_review_candidates"]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise RuntimeError("Unreadable video")
    args.output_dir.mkdir(parents=True)
    sheets = []
    for first in range(0, len(rows), 5):
        selected = rows[first : first + 5]
        sheet = np.full((len(selected) * 320, 3 * 320, 3), 25, dtype=np.uint8)
        for index, row in enumerate(selected):
            event = row["candidate_evidence"]
            x, y, time_s = (
                round(event["crossing_x_px"]),
                round(event["passage_y_px"]),
                row["candidate_time_s"],
            )
            for col, offset in enumerate((-0.2, 0, 0.2)):
                seconds = time_s + offset
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode {seconds:.3f}")
                frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                padded = cv2.copyMakeBorder(
                    frame, 45, 45, 45, 45, cv2.BORDER_CONSTANT, value=(25, 25, 25)
                )
                crop = padded[y : y + 90, x : x + 90].copy()
                cv2.line(crop, (45, 38), (45, 52), (0, 255, 255), 1)
                cv2.line(crop, (38, 45), (52, 45), (0, 255, 255), 1)
                zoom = cv2.resize(crop, (320, 290), interpolation=cv2.INTER_NEAREST)
                top, left = index * 320, col * 320
                sheet[top + 30 : top + 320, left : left + 320] = zoom
                cv2.putText(
                    sheet,
                    f"{row['id']} {row['colour_claim']} {seconds:.2f}s",
                    (left + 7, top + 21),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
        path = args.output_dir / f"sheet-{first // 5 + 1:02d}.jpg"
        if not cv2.imwrite(str(path), sheet):
            raise RuntimeError("Could not write crop sheet")
        sheets.append(
            {
                "path": path.name,
                "sha256": digest(path),
                "event_ids": [row["id"] for row in selected],
            }
        )
    cap.release()
    manifest = {
        "status": "prediction_targeted_crossing_pixel_review_not_independent_labels",
        "source_sha256": triage["source_sha256"],
        "triage_sha256": digest(args.triage),
        "sheets": sheets,
        "crop_size_px": 90,
        "source_frame_size_px": [640, 360],
        "sample_offsets_s": [-0.2, 0, 0.2],
        "limitations": [
            "Center crosshair marks the interpolated tracked passage point, not verified stone identity.",
            "Source crops were chosen from model predictions and do not provide independent accuracy labels.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"events": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
