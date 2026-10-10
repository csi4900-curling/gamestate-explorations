"""Build source-linked three-frame shot contact sheets from a hard-cut scan."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from shot_context import shot_intervals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--cuts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first shot review")
    cuts = json.loads(args.cuts.read_text())
    digest = file_sha256(args.video)
    if digest != cuts["source_sha256"]:
        parser.error("Source video and hard-cut scan differ")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development")
    intervals = shot_intervals(*cuts["source_interval_s"], [row["time_s"] for row in cuts["cuts"]])
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        parser.error("Unreadable video")
    args.output.mkdir(parents=True)
    rows = []
    manifest = {
        "status": "unlabelled_development_broadcast_shot_review",
        "source_id": cuts["source_id"],
        "source_sha256": digest,
        "source_interval_s": cuts["source_interval_s"],
        "cuts_sha256": file_sha256(args.cuts),
        "runner_sha256": file_sha256(__file__),
        "shots": [],
    }
    for index, (start, end) in enumerate(intervals, 1):
        duration = end - start
        times = [
            start + min(0.6, duration * 0.2),
            start + duration * 0.5,
            end - min(0.6, duration * 0.2),
        ]
        tiles = []
        for t in times:
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {t:.2f} s")
            tile = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
            label = f"S{index:02} {t:.1f}s"
            cv2.putText(tile, label, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 3)
            cv2.putText(tile, label, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
            tiles.append(tile)
        rows.append(np.concatenate(tiles, axis=1))
        manifest["shots"].append(
            {
                "id": f"S{index:02}",
                "interval_s": [start, end],
                "frame_times_s": [round(t, 3) for t in times],
                "view_role": None,
            }
        )
    capture.release()
    for index in range(0, len(rows), 8):
        page = np.concatenate(rows[index : index + 8], axis=0)
        cv2.imwrite(
            str(args.output / f"sheet-{index // 8 + 1:02}.jpg"),
            page,
            [cv2.IMWRITE_JPEG_QUALITY, 92],
        )
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"shots": len(rows), "pages": (len(rows) + 7) // 8}))


if __name__ == "__main__":
    main()
