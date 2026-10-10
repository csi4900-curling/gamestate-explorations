"""Render first, early-line and confirming frames for right-view entry proposals."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from hashlib import sha256


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
        parser.error("Output already exists")
    triage = json.loads(args.triage.read_text())
    video_hash = digest(args.video)
    if video_hash != triage["source_sha256"]:
        parser.error("Source fingerprints differ")
    rows = [row for interval in triage["intervals"]
            for row in interval["entry_review_proposals"]]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    sheets = []
    args.output_dir.mkdir(parents=True)
    try:
        for start in range(0, len(rows), 4):
            group = rows[start:start + 4]
            sheet = np.full((270 * len(group), 960, 3), 25, dtype=np.uint8)
            for index, row in enumerate(group):
                points = row["observed_prefix_points"]
                entry_time = row["entry_crossing"]["time_s"]
                entry = min(points, key=lambda p: abs(p["time_s"] - entry_time))
                for column, (label, node) in enumerate((
                        ("first", points[0]), ("early line", entry),
                        ("confirmed", points[-1]))):
                    t = node["time_s"]
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f"Could not decode source {t} s")
                    crop = frame[120:360, 320:640].copy()
                    px = round(node["pixel"][0] - 320)
                    py = round(node["pixel"][1] - 120)
                    cv2.drawMarker(crop, (px, py), (0, 255, 255),
                                   cv2.MARKER_CROSS, 19, 2)
                    top, left = index * 270, column * 320
                    sheet[top + 30:top + 270, left:left + 320] = crop
                    cv2.putText(sheet,
                                f"{row['raw_track_id']} {row['colour_claim']} {label} {t:.1f}s",
                                (left + 5, top + 21), cv2.FONT_HERSHEY_SIMPLEX,
                                .45, (255, 255, 255), 1, cv2.LINE_AA)
            path = args.output_dir / f"sheet-{start // 4 + 1:02}.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append({"file": path.name, "sha256": digest(path),
                           "track_ids": [row["raw_track_id"] for row in group]})
    finally:
        cap.release()
    manifest = {
        "status": "postreview_entry_prefix_source_frames_not_throw_labels",
        "source_sha256": video_hash,
        "triage_sha256": digest(args.triage),
        "runner_sha256": digest(Path(__file__)),
        "proposal_count": len(rows),
        "sheets": sheets,
        "limitations": [
            "Three sampled source frames do not verify a complete physical throw.",
            "Entry rule and review are development analyses on exposed recordings.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
