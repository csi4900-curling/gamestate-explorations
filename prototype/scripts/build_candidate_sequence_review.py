"""Build source-linked before/after sheets for candidate delivery identity review.

Each row is a candidate, not a throw. The full scene is shown before and after
the first visual observation; boxes mark only observed track points. Reviewers
can label delivered / other / unknown without seeing model decisions.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256


def frame_at(capture, fps, t):
    capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Frame decode failed at {t:.2f} s")
    return cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)


def tile(frame, *, t, point=None):
    image = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
    if point is not None:
        x, y, w, h = point["bbox"]
        cv2.rectangle(
            image,
            (round(x / 2), round(y / 2)),
            (round((x + w) / 2), round((y + h) / 2)),
            (0, 255, 0),
            2,
        )
    cv2.putText(image, f"{t:.1f}s", (7, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
    cv2.putText(image, f"{t:.1f}s", (7, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first review packet")
    selection = json.loads(args.selection.read_text())
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    args.output.mkdir(parents=True)
    manifest = {
        "status": "unlabelled_development_candidate_sequence_review",
        "selection_sha256": file_sha256(args.selection),
        "rows": [],
    }
    for source in selection["sources"]:
        video = ROOT / source["video"]
        digest = file_sha256(video)
        if digest == reserved["source_sha256"]:
            raise ValueError("Reserved independent source cannot be reviewed for development")
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
        if fps <= 0:
            raise ValueError(f"Unreadable source: {video}")
        sheets = []
        for candidate_source in source["candidate_sources"]:
            raw_path = ROOT / candidate_source["raw"]
            raw = json.loads(raw_path.read_text())
            if raw["source_sha256"] != digest:
                raise ValueError(f"Raw candidate/source mismatch: {raw_path}")
            candidates = {row["id"]: row for row in raw["motion_candidates"]}
            for candidate_id in candidate_source["ids"]:
                candidate = candidates[candidate_id]
                start, end = candidate["evidence_interval_s"]
                # Show the context before track onset and well into its path.
                times = [start - 8, start - 3, start, min(start + 5, end), min(start + 12, end + 4)]
                if any(not 0 <= t < duration for t in times):
                    raise ValueError(f"Review time outside source: {candidate_id}")
                points = candidate["visual_track_points"]
                tiles = []
                for t in times:
                    point = min(points, key=lambda row: abs(row["time_s"] - t))
                    if abs(point["time_s"] - t) > 0.5:
                        point = None
                    tiles.append(tile(frame_at(capture, fps, t), t=t, point=point))
                row_image = np.concatenate(tiles, axis=1)
                cv2.putText(
                    row_image,
                    f"{source['id']} {candidate_source['kind']}:{candidate_id}",
                    (5, 173),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42,
                    (0, 0, 0),
                    3,
                )
                cv2.putText(
                    row_image,
                    f"{source['id']} {candidate_source['kind']}:{candidate_id}",
                    (5, 173),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42,
                    (255, 255, 255),
                    1,
                )
                sheets.append(row_image)
                manifest["rows"].append(
                    {
                        "source_id": source["id"],
                        "video": source["video"],
                        "video_sha256": digest,
                        "raw": candidate_source["raw"],
                        "raw_sha256": file_sha256(raw_path),
                        "kind": candidate_source["kind"],
                        "candidate_id": candidate_id,
                        "colour": candidate["colour"],
                        "track_interval_s": [start, end],
                        "frame_times_s": times,
                        "review_label": None,
                    }
                )
        capture.release()
        for start_index in range(0, len(sheets), 8):
            page = np.concatenate(sheets[start_index : start_index + 8], axis=0)
            cv2.imwrite(
                str(args.output / f"{source['id']}-{start_index // 8 + 1:02}.jpg"),
                page,
                [cv2.IMWRITE_JPEG_QUALITY, 92],
            )
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"candidate_rows": len(manifest["rows"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
