"""Search raw right tracks for short motion near left-only provisional events."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_gap_raw_motion import rescue_left_only


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--run", nargs=2, action="append", metavar=("RUN_ID", "RAW_PROBE"),
                        required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    inventory = json.loads(args.inventory.read_text())
    if (timeline["source_sha256"] != inventory["source_sha256"]
            or inventory["timeline_sha256"] != digest(args.timeline)):
        parser.error("Timeline and inventory lineage differs")
    supported = {row["id"]: tuple(row["interval_s"])
                 for row in timeline["supported_runs"]
                 if row["layout"] == "split_2024"}
    if (set(run_id for run_id, _ in args.run) != set(supported)
            or len(args.run) != len(supported)):
        parser.error("One raw probe per supported run required")
    tracks_by_run, hashes = {}, {}
    for run_id, path_str in args.run:
        path = Path(path_str)
        probe = json.loads(path.read_text())
        start, stop = supported[run_id]
        if (probe["source_sha256"] != timeline["source_sha256"]
                or probe["source_interval_s"] != [int(start), int(stop) - 1]):
            parser.error(f"{run_id} source or run interval differs")
        tracks_by_run[run_id] = probe["raw_tracks"]
        hashes[run_id] = digest(path)
    ids = set(inventory["left_events_without_any_right_time_colour_candidate"])
    left = [row for row in timeline["observed_events"] if row["id"] in ids]
    if len(left) != len(ids):
        parser.error("Left-only event IDs differ")
    rows = rescue_left_only(left, tracks_by_run, supported_runs=supported)
    counts = Counter("none" if row["candidate_count"] == 0 else
                     "one" if row["candidate_count"] == 1 else "multiple"
                     for row in rows)
    payload = {
        "status": "targeted_relaxed_raw_motion_review_not_physical_throw_confirmation",
        "source_sha256": timeline["source_sha256"],
        "timeline_sha256": digest(args.timeline),
        "inventory_sha256": digest(args.inventory),
        "raw_probe_sha256_by_run": hashes,
        "model_code_sha256": digest(ROOT / "prototype/right_gap_raw_motion.py"),
        "runner_sha256": digest(Path(__file__)),
        "parameters": {"displacement_px": 30, "max_tail_duration_s": 5,
                       "min_first_cap_area_px2": 5,
                       "max_direction_aware_cross_view_lag_s": 20,
                       "minimum_observed_prefix_points": 3},
        "left_only_event_count": len(rows),
        "candidate_status_counts": dict(counts),
        "rows": rows,
        "limitations": [
            "The relaxed thresholds were chosen after inspecting Italy left-only misses.",
            "A left candidate can be false and a raw right path can follow a player or an old stone.",
            "This targeted search makes no new accepted event or physical identity claim.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"left_only": len(rows), "status": dict(counts),
                      "raw_candidates": sum(row["candidate_count"] for row in rows)}))


if __name__ == "__main__":
    main()
