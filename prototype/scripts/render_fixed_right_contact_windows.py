"""Rebuild or verify fixed one-second right-view contact strips from a manifest."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if sha256(args.video) != manifest["source_sha256"]:
        parser.error("Source video hash differs from manifest")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open source video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if abs(fps - manifest["source_frame_rate_fps"]) > 0.01:
        parser.error("Source frame rate differs from manifest")
    x0, y0, x1, y1 = manifest["panel_xyxy"]
    width, height = manifest["tile_size_px"]
    for row in manifest["rows"]:
        tiles = []
        for t in row["source_times_s"]:
            capture.set(cv2.CAP_PROP_POS_FRAMES,
                        round((t - manifest["source_offset_s"]) * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {t}")
            tile = cv2.resize(frame[y0:y1, x0:x1], (width, height))
            cv2.rectangle(tile, (0, 0), (130, 32), (0, 0, 0), -1)
            cv2.putText(tile, f"{t:.1f} s", (8, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2)
            tiles.append(tile)
        columns = 4
        rows = (len(tiles) + columns - 1) // columns
        sheet = np.full((rows * height, columns * width, 3), 245, np.uint8)
        for i, tile in enumerate(tiles):
            y, x = divmod(i, columns)
            sheet[y * height:(y + 1) * height,
                  x * width:(x + 1) * width] = tile
        ok, encoded = cv2.imencode(".jpg", sheet,
                                   [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            raise RuntimeError("JPEG encoding failed")
        target = args.manifest.parent / row["right_view_contact_sheet"]
        digest = hashlib.sha256(encoded.tobytes()).hexdigest()
        if digest != row["image_sha256"]:
            raise ValueError(f"Rebuilt strip differs: {target}")
        if args.verify:
            if not target.exists() or sha256(target) != digest:
                raise ValueError(f"Stored strip differs: {target}")
        else:
            if target.exists():
                parser.error(f"Output exists: {target}")
            target.write_bytes(encoded.tobytes())
    capture.release()
    print(f"{'Verified' if args.verify else 'Rendered'} {len(manifest['rows'])} strips")


if __name__ == "__main__":
    main()
