"""Render every offset-clip bidirectional proposal before appearance scoring."""

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
    for name in ("video", "probe", "output_dir"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    probe = json.loads(args.probe.read_text())
    source_hash = digest(args.video)
    if probe["source_sha256"] != source_hash:
        parser.error("Source fingerprints differ")
    offset = probe["source_time_offset_s"]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source clip")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    rows, sheets = [], []
    try:
        proposals = probe["directional_review_proposals"]
        for start in range(0, len(proposals), 5):
            group = proposals[start:start + 5]
            sheet = np.full((230 * len(group), 960, 3), 20, dtype=np.uint8)
            name = f"sheet-{start // 5 + 1:02}.jpg"
            for i, proposal in enumerate(group):
                points = proposal["observed_prefix_points"]
                event_t = proposal["passage"]["time_s"]
                chosen = [points[0],
                          min(points, key=lambda point: abs(point["time_s"] - event_t)),
                          points[-1]]
                samples = []
                for col, point in enumerate(chosen):
                    source_t = point["time_s"]
                    local_t = source_t - offset
                    frame_index = round(local_t * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f"Could not decode clip time {local_t}")
                    resized = cv2.resize(frame, (640, 360),
                                         interpolation=cv2.INTER_AREA)
                    crop = resized[120:330, 320:640].copy()
                    x, y = point["pixel"]
                    cv2.circle(crop, (round(x - 320), round(y - 120)), 8,
                               (0, 255, 0), 2)
                    top, left = i * 230, col * 320
                    sheet[top + 20:top + 230, left:left + 320] = crop
                    cv2.putText(sheet, f"{proposal['raw_track_id']} {source_t:.1f}s",
                                (left + 5, top + 16), cv2.FONT_HERSHEY_SIMPLEX,
                                .44, (255, 255, 255), 1)
                    samples.append({"source_time_s": source_t,
                                    "local_time_s": local_t,
                                    "decoded_frame_index": frame_index,
                                    "tracked_pixel_640x360": point["pixel"]})
                rows.append({"raw_track_id": proposal["raw_track_id"],
                             "direction": proposal["direction"],
                             "sheet": name, "samples": samples})
            path = args.output_dir / name
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append({"file": name, "sha256": digest(path),
                           "raw_track_ids": [row["raw_track_id"] for row in group]})
    finally:
        cap.release()
    result = {
        "status": "all_offset_clip_right_proposal_source_strips_not_throw_labels",
        "source_sha256": source_hash,
        "probe_sha256": digest(args.probe),
        "runner_sha256": digest(Path(__file__)),
        "source_time_offset_s": offset,
        "rows": rows,
        "sheets": sheets,
        "limitations": [
            "All proposed paths are shown, but three sampled frames cannot prove complete deliveries.",
            "Source-visible colour motion can belong to players or equipment.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"paths": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
