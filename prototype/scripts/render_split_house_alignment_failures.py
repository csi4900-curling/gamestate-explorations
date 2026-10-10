"""Render every low-house-paint sample from a frozen source alignment audit."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--alignment", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    audit = json.loads(args.alignment.read_text())
    if digest(args.video) != audit["source_sha256"]:
        parser.error("Source fingerprint differs")
    selected = [row for row in audit["rows"]
                if row["status"] == "house_paint_unresolved_review"]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable source video")
    args.output_dir.mkdir(parents=True)
    frames = []
    try:
        for row in selected:
            t = row["source_time_s"]
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, image = cap.read()
            if not ok or image.shape != (360, 640, 3):
                raise RuntimeError(f"Cannot decode {t}")
            label = (f"{row['run_id']} {t:.1f}s "
                     f"overlap={row['paint_reference_overlap']:.3f}")
            cv2.putText(image, label, (6, 22), cv2.FONT_HERSHEY_SIMPLEX,
                        .55, (0, 0, 0), 3)
            cv2.putText(image, label, (6, 22), cv2.FONT_HERSHEY_SIMPLEX,
                        .55, (255, 255, 255), 1)
            frames.append(image)
    finally:
        cap.release()
    sheets = []
    for start in range(0, len(frames), 8):
        chunk = frames[start:start + 8]
        if len(chunk) % 2:
            chunk.append(chunk[-1].copy())
        rows = [cv2.hconcat(chunk[i:i + 2])
                for i in range(0, len(chunk), 2)]
        name = f"sheet-{start // 8 + 1:02d}.jpg"
        cv2.imwrite(str(args.output_dir / name), cv2.vconcat(rows))
        sheets.append(name)
    manifest = {
        "status": "all_frozen_low_paint_overlap_source_frames_not_throw_labels",
        "source_sha256": audit["source_sha256"],
        "alignment_sha256": digest(args.alignment),
        "runner_sha256": digest(Path(__file__)),
        "selected_samples": [{"run_id": row["run_id"],
                              "source_time_s": row["source_time_s"],
                              "overlap": row["paint_reference_overlap"]}
                             for row in selected],
        "sheets": sheets,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"frames": len(selected), "sheets": sheets}))


if __name__ == "__main__":
    main()
