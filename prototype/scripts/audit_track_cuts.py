"""Audit identity continuity of existing raw tracks against hard video cuts."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from scene_cuts import split_points_at_cuts


def segment_summary(points):
    xy = np.asarray([row["pixel"] for row in points], dtype=float)
    span = float(np.max(np.linalg.norm(xy - xy[0], axis=1)))
    return {
        "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
        "point_count": len(points),
        "span_px": round(span, 3),
        "sustained_motion": len(points) >= 4
        and points[-1]["time_s"] - points[0]["time_s"] >= 3
        and span >= 25,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--cuts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first audit")
    raw = json.loads(args.raw.read_text())
    cuts = json.loads(args.cuts.read_text())
    if (
        raw["source_sha256"] != cuts["source_sha256"]
        or raw["source_interval_s"] != cuts["source_interval_s"]
    ):
        parser.error("Raw tracks and cuts must cover the same source interval")
    times = [row["time_s"] for row in cuts["cuts"]]
    tracks = []
    for candidate in raw["motion_candidates"]:
        segments = split_points_at_cuts(candidate["visual_track_points"], times)
        tracks.append(
            {
                "id": candidate["id"],
                "colour": candidate["colour"],
                "raw_interval_s": candidate["evidence_interval_s"],
                "crosses_hard_cut": len(segments) > 1,
                "segments": [segment_summary(points) for points in segments],
            }
        )
    result = {
        "status": "development_track_hard_cut_identity_audit",
        "source_id": raw["source_id"],
        "source_sha256": raw["source_sha256"],
        "source_interval_s": raw["source_interval_s"],
        "raw_sha256": file_sha256(args.raw),
        "cuts_sha256": file_sha256(args.cuts),
        "model_sha256": file_sha256(ROOT / "prototype/scene_cuts.py"),
        "runner_sha256": file_sha256(__file__),
        "raw_track_count": len(tracks),
        "tracks_crossing_hard_cut": sum(row["crosses_hard_cut"] for row in tracks),
        "tracks": tracks,
        "limitations": [
            "Hard cuts are conservative; within-shot switches and missed edits remain.",
            "Splitting is an identity audit only; no throw event is accepted or rejected.",
            "A segment with sustained motion can still be a player or displaced stone.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "raw_tracks": result["raw_track_count"],
                "crossing_cuts": result["tracks_crossing_hard_cut"],
            }
        )
    )


if __name__ == "__main__":
    main()
