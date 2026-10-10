"""Capture three track patches around each crossing, avoiding early track merges.

Development packet only; source review labels and detector decisions are not
changed. This samples event-local identity, not arbitrary track quantiles.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from build_2024_identity_patch_packet import crop_at, make_contact, replay_track


def crossing_points(points, crossing):
    targets = [crossing - 0.2, crossing, crossing + 0.2]
    used = set()
    selected = []
    for target in targets:
        candidates = sorted((abs(point["time_s"] - target), index)
                            for index, point in enumerate(points) if index not in used)
        if not candidates or candidates[0][0] > 0.25:
            raise ValueError(f"No tracked point within 0.25 s of {target:.3f}")
        index = candidates[0][1]
        used.add(index)
        selected.append(points[index])
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory exists; preserve prior packets")
    selection = json.loads(args.selection.read_text())
    cv2.setNumThreads(1)
    args.output.mkdir(parents=True)
    rows = []
    sources = []
    for source in selection["sources"]:
        video_path = ROOT / source["video"]
        timeline_path = ROOT / source["timeline"]
        timeline = json.loads(timeline_path.read_text())
        if timeline["source_id"] != source["source_id"]:
            raise ValueError("Timeline source ID mismatch")
        by_id = {event["id"]: event for event in timeline["observed_events"]}
        cap = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not cap.isOpened() or fps <= 0:
            raise ValueError(f"Unreadable video: {video_path}")
        source_rows = []
        for selected in source["events"]:
            reference = by_id[selected["id"]]
            event, points = replay_track(cap, fps, reference)
            local = crossing_points(points, event["crossing_time_s"])
            samples = []
            for index, point in enumerate(local, 1):
                relative = Path("crops") / source["source_id"] / f"{selected['id']}-{index}.jpg"
                path = args.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(path), crop_at(cap, fps, point),
                                   [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    raise RuntimeError(f"Could not save {path}")
                samples.append({
                    "time_s": point["time_s"],
                    "pixel": point["pixel"],
                    "bbox": point["bbox"],
                    "body_support": point["body_support"],
                    "crop_path": str(relative),
                    "crop_sha256": file_sha256(path),
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
            rows.append(row)
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
        "status": "development_crossing_local_identity_packet",
        "selection_sha256": file_sha256(args.selection),
        "runner_sha256": file_sha256(__file__),
        "replay_code_sha256": file_sha256(ROOT / "prototype/scripts/build_2024_identity_patch_packet.py"),
        "sampling_policy": "nearest_distinct_track_points_at_crossing_minus_0.2_zero_plus_0.2_s",
        "samples_per_event": 3,
        "crop_size_px": [48, 48],
        "sources": sources,
        "rows": rows,
        "limitations": selection["limitations"] + [
            "Even crossing-local crops can contain occlusion or a tracker identity switch.",
            "Patch identity is not a verified delivered-stone event.",
        ],
    }
    (args.output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({source["source_id"]: sum(row["source_id"] == source["source_id"]
                                                for row in rows) for source in sources}))


if __name__ == "__main__":
    main()
