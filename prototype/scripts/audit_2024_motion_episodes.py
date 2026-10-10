"""Audit stationary-to-motion onsets on reviewed 2024 cap tracks."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from motion_episode import stationary_to_motion_episode
from catalog_2024_event_patches import replay_track_spatial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path, action="append")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve prior episode audit")
    cv2.setNumThreads(1)
    rows = []
    sources = []
    seen = set()
    for selection_path in args.selection:
        selection = json.loads(selection_path.read_text())
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
            for item in source["events"]:
                key = (source["source_id"], item["id"])
                if key in seen:
                    raise ValueError(f"Duplicate selected event: {key}")
                seen.add(key)
                reference = by_id[item["id"]]
                replay, points = replay_track_spatial(cap, fps, reference)
                onset = stationary_to_motion_episode(
                    points, replay["crossing_time_s"], replay["view_motion"])
                rows.append({
                    "source_id": source["source_id"],
                    "event_id": item["id"],
                    "source_review": item["review"],
                    "review_kind": item["review_kind"],
                    "crossing_time_s": replay["crossing_time_s"],
                    "first_observed_s": points[0]["time_s"],
                    "observations_at_confirmation": len(points),
                    "stationary_to_motion": onset,
                })
            cap.release()
            sources.append({
                "source_id": source["source_id"],
                "video_sha256": file_sha256(video_path),
                "timeline_sha256": file_sha256(timeline_path),
                "same_video_bytes_as_timeline": file_sha256(video_path) == timeline["source_sha256"],
            })
    result = {
        "status": "development_stationary_to_motion_audit",
        "selection_sha256s": {str(path): file_sha256(path) for path in args.selection},
        "runner_sha256": file_sha256(__file__),
        "episode_code_sha256": file_sha256(ROOT / "prototype/motion_episode.py"),
        "replay_code_sha256": file_sha256(ROOT / "prototype/scripts/catalog_2024_event_patches.py"),
        "sources": sources,
        "rows": rows,
        "transition_count": sum(row["stationary_to_motion"] is not None for row in rows),
        "limitations": [
            "A stationary-to-motion transition can occur within one real stone track or across a tracker identity switch.",
            "This diagnostic does not decide whether the moving object is a stone or whether a throw occurred.",
            "Selected source reviews are same-agent development evidence, not an independent full-video reference.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"events": len(rows), "transitions": result["transition_count"]}))


if __name__ == "__main__":
    main()
