#!/usr/bin/env python3
"""Render all raw right-view tracks of a colour after a declared source time."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    hasher = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--colour", choices=("red", "yellow"), required=True)
    parser.add_argument("--min-start-s", type=float, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    probe = json.loads(args.probe.read_text())
    source_hash = digest(args.video)
    if source_hash != probe["source_sha256"]:
        parser.error("Source video differs from raw right probe")
    tracks = [track for interval in probe["intervals"]
              for track in interval["tracks"]
              if track["colour"] == args.colour and
              track["first_observed_s"] >= args.min_start_s]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheets = []
    try:
        for first in range(0, len(tracks), 5):
            group = tracks[first:first + 5]
            sheet = np.full((270 * len(group), 960, 3), 25, dtype=np.uint8)
            records = []
            for row_index, track in enumerate(group):
                points = track["points"]
                nodes = (points[0], points[len(points) // 2], points[-1])
                records.append({"track_id": track["track_id"],
                                "sample_times_s": [n["time_s"] for n in nodes]})
                for column, node in enumerate(nodes):
                    time_s = node["time_s"]
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                    ok, frame = cap.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise RuntimeError(f"Cannot decode {time_s} s")
                    crop = frame[120:360, 320:640].copy()
                    cv2.drawMarker(crop, (round(node["pixel"][0] - 320),
                                          round(node["pixel"][1] - 120)),
                                   (0, 255, 255), cv2.MARKER_CROSS, 19, 2)
                    top, left = row_index * 270, column * 320
                    sheet[top + 30:top + 270, left:left + 320] = crop
                    cv2.putText(sheet, f"{track['track_id']} {time_s:.0f}s",
                                (left + 8, top + 21), cv2.FONT_HERSHEY_SIMPLEX,
                                .5, (255, 255, 255), 1, cv2.LINE_AA)
            path = args.output_dir / f"sheet-{len(sheets)+1:02d}.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append({"file": path.name, "sha256": digest(path),
                           "tracks": records})
    finally:
        cap.release()
    manifest = {"status": "raw_track_source_review_not_delivered_stone_labels",
                "source_sha256": source_hash,
                "probe_sha256": digest(args.probe),
                "runner_sha256": digest(Path(__file__)),
                "selection": {"colour": args.colour,
                              "min_first_observed_s": args.min_start_s},
                "selected_track_count": len(tracks),
                "selected_track_ids": [track["track_id"] for track in tracks],
                "sheets": sheets,
                "limitation": "Three stills and colour pixels cannot certify physical stone identity or motion."}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"tracks": len(tracks), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
