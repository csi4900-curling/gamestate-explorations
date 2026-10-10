"""Catalog every provisional 2024 cap track without assigning event labels.

This is a development inspection surface. It replays each frozen timeline
crossing on a specified video variant and records unmatched cases explicitly.
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
from build_2024_identity_patch_packet import crop_at
from span_passage_detection import SpanPassageDetector
from throw_detection import stone_candidates


def replay_track_spatial(cap, fps, reference):
    """Match saved event to one raw track by time, colour and image position."""
    detector = SpanPassageDetector()
    center = reference["crossing_time_s"]
    start = max(0, int(center) - 5)
    end = int(center) + 5
    first = round(start * fps)
    step = max(1, round(fps / 10))
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    matches = []
    for n in range(first, round(end * fps)):
        if not cap.grab():
            raise RuntimeError(f"Decode failed at {n / fps:.3f} s")
        if (n - first) % step:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            raise RuntimeError(f"Retrieve failed at {n / fps:.3f} s")
        for event in detector.update(stone_candidates(frame, detector.config), n / fps):
            if (event["colour"] == reference["colour"]
                    and abs(event["crossing_time_s"] - center) <= 0.15):
                track = next(row for row in detector.tracker.tracks
                             if row.id == event["track_id"])
                distance = float(np.linalg.norm(np.subtract(
                    [event["crossing_x_px"], event["passage_y_px"]],
                    [reference["crossing_x_px"], reference["passage_y_px"]])))
                matches.append((distance, event, [dict(point) for point in track.points]))
    matches.sort(key=lambda row: row[0])
    if (not matches or matches[0][0] > 8
            or (len(matches) > 1 and matches[1][0] - matches[0][0] < 10)):
        raise ValueError(f"No unique spatial match at {center}: "
                         f"{[round(row[0], 2) for row in matches]}")
    return matches[0][1:]


def write_page(rows, output, source_id, page_number):
    tiles = []
    for row in rows:
        line = []
        for sample in row["samples"]:
            crop = cv2.imread(str(output / sample["crop_path"]))
            tile = cv2.resize(crop, (144, 144), interpolation=cv2.INTER_NEAREST)
            tile = cv2.copyMakeBorder(tile, 24, 0, 0, 0, cv2.BORDER_CONSTANT,
                                      value=(30, 30, 30))
            caption = f"{row['event_id']} {sample['time_s']:.1f}"
            cv2.putText(tile, caption, (3, 17), cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, (255, 255, 255), 1, cv2.LINE_AA)
            line.append(tile)
        tiles.append(cv2.hconcat(line))
    name = f"{source_id}-contact-{page_number:02}.jpg"
    if not cv2.imwrite(str(output / name), cv2.vconcat(tiles),
                       [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise RuntimeError(f"Could not save {name}")
    return name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--page-rows", type=int, default=20)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory exists; preserve prior catalog")
    if args.page_rows <= 0:
        parser.error("Page rows must be positive")
    timeline = json.loads(args.timeline.read_text())
    events = timeline["observed_events"]
    if len(events) != len({row["id"] for row in events}):
        raise ValueError("Duplicate timeline event ID")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError("Unreadable source video")
    cv2.setNumThreads(1)
    args.output.mkdir(parents=True)
    rows = []
    unmatched = []
    for reference in events:
        try:
            event, points = replay_track_spatial(cap, fps, reference)
        except ValueError as exc:
            unmatched.append({"event_id": reference["id"],
                              "crossing_time_s": reference["crossing_time_s"],
                              "reason": str(exc)})
            continue
        indices = sorted({round((len(points) - 1) * q) for q in (0.2, 0.5, 0.8)})
        if len(indices) != 3:
            unmatched.append({"event_id": reference["id"],
                              "crossing_time_s": reference["crossing_time_s"],
                              "reason": "Too few points for three crops"})
            continue
        samples = []
        for index, point_index in enumerate(indices, 1):
            point = points[point_index]
            relative = Path("crops") / f"{reference['id']}-{index}.jpg"
            path = args.output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(path), crop_at(cap, fps, point),
                               [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f"Could not save {path}")
            samples.append({"time_s": point["time_s"], "pixel": point["pixel"],
                            "crop_path": str(relative), "crop_sha256": file_sha256(path)})
        rows.append({"event_id": reference["id"],
                     "timeline_crossing_time_s": reference["crossing_time_s"],
                     "replayed_crossing_time_s": event["crossing_time_s"],
                     "colour": reference["colour"],
                     "samples": samples})
    cap.release()
    pages = []
    for start in range(0, len(rows), args.page_rows):
        chunk = rows[start:start + args.page_rows]
        name = write_page(chunk, args.output, timeline["source_id"], len(pages) + 1)
        pages.append({"file": name, "event_ids": [row["event_id"] for row in chunk]})
    result = {
        "status": "prediction_catalog_unlabelled_development",
        "source_id": timeline["source_id"],
        "video_sha256": file_sha256(args.video),
        "timeline_source_sha256": timeline["source_sha256"],
        "same_video_bytes_as_timeline": file_sha256(args.video) == timeline["source_sha256"],
        "timeline_sha256": file_sha256(args.timeline),
        "runner_sha256": file_sha256(__file__),
        "replay_code_sha256": file_sha256(ROOT / "prototype/scripts/build_2024_identity_patch_packet.py"),
        "review_status": "unlabelled",
        "page_rows": args.page_rows,
        "rows": rows,
        "unmatched": unmatched,
        "pages": pages,
        "limitations": [
            "This catalog samples only predicted events and cannot measure missed throws.",
            "Crops are track-centered visual evidence, not verified stone identities.",
            "A video variant may reproduce timestamps while differing in source bytes.",
        ],
    }
    (args.output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"matched": len(rows), "unmatched": len(unmatched),
                      "pages": len(pages)}))


if __name__ == "__main__":
    main()
