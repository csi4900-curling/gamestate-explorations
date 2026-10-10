"""Capture tracked-object patches for reviewed 2024 development events.

This replays the frozen raw candidate detector on separate source variants.
It does not infer labels, decide throws, or alter the production timeline.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from span_passage_detection import SpanPassageDetector
from throw_detection import stone_candidates


def replay_track(cap, fps, reference):
    """Return the unique raw event and its points near a saved crossing."""
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
                matches.append((event, [dict(point) for point in track.points]))
    if len(matches) != 1:
        raise ValueError(f"Expected one matching raw track at {center}, found {len(matches)}")
    return matches[0]


def crop_at(cap, fps, point, *, side=48):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"Crop frame decode failed at {point['time_s']:.3f} s")
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    x, y = point["pixel"]
    patch = cv2.getRectSubPix(image, (side, side), (float(x), float(y)))
    return patch


def make_contact(rows, output):
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
    if tiles and not cv2.imwrite(str(output / f"{rows[0]['source_id']}-contact.jpg"),
                                 cv2.vconcat(tiles), [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise RuntimeError("Could not save contact sheet")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory exists; preserve prior packets")
    selection = json.loads(args.selection.read_text())
    cv2.setNumThreads(1)
    output_rows = []
    sources = []
    args.output.mkdir(parents=True)
    for source in selection["sources"]:
        video_path = ROOT / source["video"]
        timeline_path = ROOT / source["timeline"]
        timeline = json.loads(timeline_path.read_text())
        if timeline["source_id"] != source["source_id"]:
            raise ValueError(f"Timeline source mismatch: {timeline_path}")
        by_id = {row["id"]: row for row in timeline["observed_events"]}
        if len(by_id) != len(timeline["observed_events"]):
            raise ValueError("Timeline event IDs are not unique")
        cap = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not cap.isOpened() or fps <= 0:
            raise ValueError(f"Unreadable video: {video_path}")
        source_rows = []
        for selected in source["events"]:
            reference = by_id[selected["id"]]
            event, points = replay_track(cap, fps, reference)
            indices = sorted({round((len(points) - 1) * q) for q in (0.2, 0.5, 0.8)})
            if len(indices) != 3:
                raise ValueError(f"Too few tracked points for three patches: {selected['id']}")
            samples = []
            for index, point_index in enumerate(indices, 1):
                point = points[point_index]
                crop_path = Path("crops") / source["source_id"] / f"{selected['id']}-{index}.jpg"
                (args.output / crop_path).parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(args.output / crop_path), crop_at(cap, fps, point),
                                   [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    raise RuntimeError(f"Could not save {crop_path}")
                samples.append({
                    "time_s": point["time_s"],
                    "pixel": point["pixel"],
                    "bbox": point["bbox"],
                    "body_support": point["body_support"],
                    "crop_path": str(crop_path),
                    "crop_sha256": file_sha256(args.output / crop_path),
                })
            row = {
                "source_id": source["source_id"],
                "event_id": selected["id"],
                "source_review": selected["review"],
                "review_kind": selected["review_kind"],
                "timeline_crossing_time_s": reference["crossing_time_s"],
                "replayed_crossing_time_s": event["crossing_time_s"],
                "track_observations_at_confirmation": len(points),
                "samples": samples,
            }
            source_rows.append(row)
            output_rows.append(row)
        cap.release()
        make_contact(source_rows, args.output)
        sources.append({
            "source_id": source["source_id"],
            "video_path": source["video"],
            "video_sha256": file_sha256(video_path),
            "timeline_path": source["timeline"],
            "timeline_sha256": file_sha256(timeline_path),
            "same_video_bytes_as_timeline": file_sha256(video_path) == timeline["source_sha256"],
        })
    result = {
        "status": "development_source_review_identity_packet",
        "selection_sha256": file_sha256(args.selection),
        "runner_sha256": file_sha256(__file__),
        "samples_per_event": 3,
        "crop_size_px": [48, 48],
        "sources": sources,
        "rows": output_rows,
        "limitations": selection["limitations"] + [
            "Patch crops are centered on cap tracks and may include surrounding people or ice.",
            "A three-frame crop packet does not prove physical identity or end-to-end throw accuracy.",
        ],
    }
    (args.output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({row["source_id"]: sum(r["source_id"] == row["source_id"]
                                                for r in output_rows) for row in sources}))


if __name__ == "__main__":
    main()
