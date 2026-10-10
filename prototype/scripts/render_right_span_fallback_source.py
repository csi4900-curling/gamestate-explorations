"""Render source frames for line-free right-span review proposals."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    probe = json.loads(args.probe.read_text())
    source_hash = digest(args.video)
    if probe["source_sha256"] != source_hash:
        parser.error("Source fingerprints differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheets = []
    try:
        for proposal in probe["additional_span_review_proposals"]:
            tiles, frames = [], []
            for point in proposal["observed_prefix_points"]:
                t = point["time_s"]
                frame_index = round(t * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Could not decode 640x360 source at {t}")
                crop = frame[110:290, 320:640].copy()
                x, y = point["pixel"]
                cv2.circle(crop, (round(x - 320), round(y - 110)), 8, (0, 255, 0), 2)
                cv2.rectangle(crop, (0, 0), (100, 24), (0, 0, 0), -1)
                cv2.putText(crop, f"{t:.1f} s", (6, 18),
                            cv2.FONT_HERSHEY_SIMPLEX, .52, (255, 255, 255), 1)
                tiles.append(crop)
                frames.append({"source_time_s": t, "decoded_frame_index": frame_index,
                               "tracked_pixel": point["pixel"]})
            while len(tiles) % 2:
                tiles.append(np.zeros_like(tiles[0]))
            sheet = np.vstack([np.hstack(tiles[i:i + 2])
                               for i in range(0, len(tiles), 2)])
            path = args.output_dir / f"{proposal['raw_track_id'].lower()}-span.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append({"raw_track_id": proposal["raw_track_id"],
                           "sheet": path.name, "sheet_sha256": digest(path),
                           "frames": frames})
    finally:
        cap.release()
    result = {
        "status": "development_source_frames_for_line_free_right_span_not_throw_labels",
        "source_sha256": source_hash,
        "probe_sha256": digest(args.probe),
        "runner_sha256": digest(Path(__file__)),
        "sheets": sheets,
        "limitations": [
            "Marked source frames support visual object review, not independent event labels.",
            "Four sparse frames cannot prove a complete physical delivery or cross-camera identity.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"proposals": len(sheets), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
