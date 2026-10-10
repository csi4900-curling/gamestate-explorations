"""Render stable-cap markers on middle source tail frames for source review."""

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
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output already exists")
    data = json.loads(args.observations.read_text())
    video_hash = digest(args.video)
    if video_hash != data["source_sha256"]:
        parser.error("Source fingerprints differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheets = []
    try:
        for start in range(0, len(data["rows"]), 4):
            group = data["rows"][start:start + 4]
            sheet = np.full((520 * len(group), 640, 3), 25, dtype=np.uint8)
            for i, row in enumerate(group):
                t = row["sample_frames"][1]["time_s"]
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode {t}")
                crop = cv2.resize(image[120:360, 320:640], (640, 480))
                for stone in row["stable_cap_proposals"]:
                    x = round((stone["pixel_center"][0] - 320) * 2)
                    y = round((stone["pixel_center"][1] - 120) * 2)
                    colour = (0, 0, 255) if stone["colour"] == "red" else (0, 255, 255)
                    cv2.circle(crop, (x, y), 10, colour, 2)
                    cv2.putText(crop, stone["local_observation_id"],
                                (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX,
                                .38, colour, 1, cv2.LINE_AA)
                top = i * 520
                sheet[top + 30:top + 510, :640] = crop
                cv2.putText(sheet,
                            f"{row['right_raw_track_id']} {row['observation_status']} {t:.1f}s",
                            (7, top + 21), cv2.FONT_HERSHEY_SIMPLEX,
                            .5, (255, 255, 255), 1, cv2.LINE_AA)
            path = args.output_dir / f"sheet-{start // 4 + 1:02}.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append({"file": path.name, "sha256": digest(path),
                           "right_track_ids": [row["right_raw_track_id"] for row in group]})
    finally:
        cap.release()
    manifest = {
        "status": "diagnostic_source_frame_markers_not_verified_stone_labels",
        "source_sha256": video_hash,
        "observations_sha256": digest(args.observations),
        "runner_sha256": digest(Path(__file__)),
        "sheets": sheets,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"rows": len(data["rows"]), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
