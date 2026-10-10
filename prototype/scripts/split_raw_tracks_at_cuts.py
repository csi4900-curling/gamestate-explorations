"""Create cut-separated visual candidates without reusing identity across edits."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from scene_cuts import split_points_at_cuts


def supported_span(points):
    if len(points) < 4 or points[-1]["time_s"] - points[0]["time_s"] < 3:
        return None
    xy = np.asarray([row["pixel"] for row in points], float)
    span = float(np.max(np.linalg.norm(xy - xy[0], axis=1)))
    return span if span >= 25 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--cuts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first cut-aware candidate result")
    raw = json.loads(args.raw.read_text())
    cuts = json.loads(args.cuts.read_text())
    if raw["source_sha256"] != cuts["source_sha256"] or raw["source_interval_s"] != cuts["source_interval_s"]:
        parser.error("Raw candidates and hard cuts differ in source or interval")
    cut_times = [row["time_s"] for row in cuts["cuts"]]
    candidates = []
    withheld = []
    for candidate in raw["motion_candidates"]:
        segments = split_points_at_cuts(candidate["visual_track_points"], cut_times)
        for index, points in enumerate(segments, 1):
            span = supported_span(points)
            if span is None:
                withheld.append({"parent_id": candidate["id"], "segment_index": index,
                                 "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
                                 "reason": "no_sustained_within_shot_motion"})
                continue
            start, end = points[0]["time_s"], points[-1]["time_s"]
            candidates.append({**candidate,
                               "id": f"{candidate['id']}-S{index:02}",
                               "parent_id": candidate["id"],
                               "segment_index": index,
                               "crossing_time_s": start,
                               "evidence_interval_s": [start, end],
                               "visual_track_span_px": span,
                               "visual_track_points": points,
                               "status": "unconfirmed_cut_separated_motion_candidate"})
    result = {**{key: value for key, value in raw.items()
                 if key not in ("motion_candidates", "candidate_count")},
              "status": "development_cut_separated_gap_motion_probe",
              "input_sha256": file_sha256(args.raw),
              "cut_scan_sha256": file_sha256(args.cuts),
              "cut_model_sha256": file_sha256(ROOT / "prototype/scene_cuts.py"),
              "runner_sha256": file_sha256(__file__),
              "motion_candidates": sorted(candidates,
                                          key=lambda row: (row["crossing_time_s"], row["id"])),
              "candidate_count": len(candidates),
              "withheld_segments": withheld,
              "limitations": [
                  "A cut ends same-shot identity; candidate segments are still not confirmed throws.",
                  "This cannot recover short tracks previously excluded before splitting.",
                  "The conservative cut detector can miss edits and cannot detect within-shot identity switches.",
              ]}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"raw_candidates": len(raw["motion_candidates"]),
                      "cut_separated_candidates": len(candidates),
                      "withheld_segments": len(withheld)}))


if __name__ == "__main__":
    main()
