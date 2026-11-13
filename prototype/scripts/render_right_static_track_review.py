"""Render source frames for predeclared right-view upward track proposals."""

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


def selected(track):
    points = track["points"]
    first, last = points[0]["pixel"], points[-1]["pixel"]
    return (
        first[1] >= 250
        and last[1] - first[1] <= -70
        and track["last_observed_s"] - track["first_observed_s"] <= 60
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--track-ids", nargs="+", help="Render these raw track IDs for diagnostic source review"
    )
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output already exists")
    probe = json.loads(args.probe.read_text())
    video_hash = digest(args.video)
    if video_hash != probe["source_sha256"]:
        parser.error("Video and probe sources differ")
    tracks = [track for interval in probe["intervals"] for track in interval["tracks"]]
    if args.track_ids:
        requested = set(args.track_ids)
        found = {track["track_id"] for track in tracks if track["track_id"] in requested}
        if found != requested:
            parser.error(f"Unknown track IDs: {', '.join(sorted(requested - found))}")
        candidates = [track for track in tracks if track["track_id"] in requested]
    else:
        candidates = [track for track in tracks if selected(track)]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheets = []
    try:
        for group_start in range(0, len(candidates), 4):
            group = candidates[group_start : group_start + 4]
            sheet = np.full((270 * len(group), 960, 3), 25, dtype=np.uint8)
            for index, track in enumerate(group):
                points = track["points"]
                for column, node in enumerate((points[0], points[len(points) // 2], points[-1])):
                    time_s = node["time_s"]
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f"Could not decode {time_s} s")
                    crop = frame[120:360, 320:640].copy()
                    x = round(node["pixel"][0] - 320)
                    y = round(node["pixel"][1] - 120)
                    cv2.drawMarker(crop, (x, y), (0, 255, 255), cv2.MARKER_CROSS, 19, 2)
                    top, left = index * 270, column * 320
                    sheet[top + 30 : top + 270, left : left + 320] = crop
                    cv2.putText(
                        sheet,
                        f"{track['track_id']} {track['colour']} {time_s:.1f}s",
                        (left + 8, top + 21),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )
            path = args.output_dir / f"sheet-{group_start // 4 + 1:02}.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append(
                {
                    "file": path.name,
                    "sha256": digest(path),
                    "track_ids": [row["track_id"] for row in group],
                }
            )
    finally:
        cap.release()
    manifest = {
        "status": "prediction_selected_right_view_track_source_review_not_throw_labels",
        "source_sha256": video_hash,
        "probe_sha256": digest(args.probe),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": (
            "Explicit diagnostic track IDs: " + ", ".join(args.track_ids)
            if args.track_ids
            else "Start y>=250, endpoint y decreases by >=70 px, observed duration <=60 s."
        ),
        "selected_track_count": len(candidates),
        "selected_track_ids": [row["track_id"] for row in candidates],
        "sheets": sheets,
        "limitations": [
            "First/middle/last visual samples cannot prove complete physical stone identity.",
            "Selection was made after the raw motion probe and is not independent throw validation.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"selected": len(candidates), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
