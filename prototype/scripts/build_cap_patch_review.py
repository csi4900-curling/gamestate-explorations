"""Create source-linked contact sheets for human review of cap-track patches.

The sheets are development evidence. A track is not a throw label, and the
reviewer must label individual samples because tracks can switch objects.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256


def crop_with_context(frame, bbox):
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    x, y, w, h = bbox
    side = max(48, min(210, round(3.0 * max(w, h))))
    cx, cy = x + w / 2, y + h / 2 + side * 0.13
    x0, y0 = round(cx - side / 2), round(cy - side / 2)
    pad = side + 1
    padded = cv2.copyMakeBorder(image, pad, pad, pad, pad, cv2.BORDER_CONSTANT,
                                value=(70, 70, 70))
    crop = padded[y0 + pad:y0 + pad + side, x0 + pad:x0 + pad + side].copy()
    cv2.rectangle(crop, (round(x - x0), round(y - y0)),
                  (round(x + w - x0), round(y + h - y0)), (0, 255, 0), 2)
    return cv2.resize(crop, (180, 180), interpolation=cv2.INTER_AREA), [x0, y0, side, side]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; keep review packets immutable")
    selection = json.loads(args.selection.read_text())
    args.output.mkdir(parents=True)
    manifest = {"status": "unlabelled_development_cap_patch_review",
                "selection_sha256": file_sha256(args.selection), "samples": []}
    for source in selection["sources"]:
        video = ROOT / source["video"]
        raw = ROOT / source["raw"]
        data = json.loads(raw.read_text())
        digest = file_sha256(video)
        if digest != data["source_sha256"]:
            raise ValueError(f"Video and raw track source differ: {video}")
        reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
        if digest == reserved["source_sha256"]:
            raise ValueError("Reserved independent source cannot be used for development")
        candidates = {row["id"]: row for row in data["motion_candidates"]}
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            raise ValueError(f"Unreadable video: {video}")
        tiles = []
        for track_id in source["tracks"]:
            points = candidates[track_id]["visual_track_points"]
            for fraction in (0.18, 0.5, 0.82):
                point = points[round((len(points) - 1) * fraction)]
                t = point["time_s"]
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Decode failed at {video}:{t}")
                tile, crop_bbox = crop_with_context(frame, point["bbox"])
                sample_id = f"{source['id']}-{track_id}-{len(tiles) % 3 + 1}"
                cv2.putText(tile, sample_id, (4, 16), cv2.FONT_HERSHEY_SIMPLEX,
                            0.35, (0, 0, 0), 2)
                cv2.putText(tile, sample_id, (4, 16), cv2.FONT_HERSHEY_SIMPLEX,
                            0.35, (255, 255, 255), 1)
                tiles.append(tile)
                manifest["samples"].append({"id": sample_id, "source_id": source["id"],
                                            "video": source["video"], "video_sha256": digest,
                                            "raw": source["raw"], "raw_sha256": file_sha256(raw),
                                            "track_id": track_id, "time_s": t,
                                            "cap_bbox": point["bbox"], "crop_bbox": crop_bbox,
                                            "review_label": None})
        capture.release()
        rows = (len(tiles) + 5) // 6
        sheet = cv2.UMat(rows * 180, 6 * 180, cv2.CV_8UC3).get()
        sheet[:] = (60, 60, 60)
        for i, tile in enumerate(tiles):
            r, c = divmod(i, 6)
            sheet[r * 180:(r + 1) * 180, c * 180:(c + 1) * 180] = tile
        cv2.imwrite(str(args.output / f"{source['id']}-sheet.jpg"), sheet,
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"samples": len(manifest["samples"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
