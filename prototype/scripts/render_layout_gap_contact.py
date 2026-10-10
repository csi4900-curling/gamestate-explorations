"""Render source frames inside every router gap for a coverage audit."""

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
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".json").exists():
        parser.error("Output exists; preserve the original review")
    preflight = json.loads(args.preflight.read_text())
    if digest(args.video) != preflight["source_sha256"]:
        parser.error("Preflight source hash differs from video")
    gaps = preflight["coverage_gaps_s"]
    if not gaps:
        parser.error("Preflight has no gaps")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    width, height = 640, 360
    banner = 30
    sheet = np.full((len(gaps) * (height + banner), 3 * width, 3),
                    (25, 28, 30), dtype=np.uint8)
    rows = []
    for index, (start, end) in enumerate(gaps):
        times = [start + (end - start) * fraction for fraction in (0.25, 0.5, 0.75)]
        entries = []
        for col, seconds in enumerate(times):
            frame_number = round(seconds * fps)
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Could not decode frame {frame_number}")
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            y, x = index * (height + banner), col * width
            sheet[y + banner:y + banner + height, x:x + width] = frame
            cv2.putText(sheet, f"gap {index + 1}: {start:.0f}-{end:.0f}s  frame {seconds:.1f}s",
                        (x + 8, y + 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 1, cv2.LINE_AA)
            entries.append({"time_s": round(seconds, 3), "frame_number": frame_number})
        rows.append({"gap_s": [start, end], "samples": entries})
    capture.release()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), sheet):
        raise RuntimeError("Could not write sheet")
    manifest = {
        "status": "sparse_source_gap_review_not_event_reference",
        "source_sha256": preflight["source_sha256"],
        "preflight_sha256": digest(args.preflight),
        "image_sha256": digest(args.output),
        "rows": rows,
        "limitations": ["Three stills per gap cannot prove throw-free coverage."],
    }
    args.output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"gaps": len(gaps), "frames": 3 * len(gaps)}))


if __name__ == "__main__":
    main()
