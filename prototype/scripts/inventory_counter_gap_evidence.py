"""Inventory Beijing counter evidence in unsupported route gaps."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from counter_gap_evidence import classify_counter_gap_events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--counter-replay", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous inventory")
    preflight = json.loads(args.preflight.read_text())
    replay = json.loads(args.counter_replay.read_text())
    if (
        preflight["source_id"] != replay["source_id"]
        or preflight["source_sha256"] != replay["source_sha256"]
        or preflight["source_interval_s"] != replay["source_interval_s"]
    ):
        parser.error("Preflight and counter replay refer to different video intervals")
    rows = classify_counter_gap_events(replay["counter_events"], preflight["coverage_gaps_s"])
    interior = [row for row in rows if row["classification"] == "counter_evidence_inside_gap"]
    boundary = [
        row for row in rows if row["classification"] == "boundary_ambiguous_counter_evidence"
    ]
    result = {
        "status": "counter_gap_evidence_inventory_not_confirmed_throws",
        "source_id": preflight["source_id"],
        "source_sha256": preflight["source_sha256"],
        "source_interval_s": preflight["source_interval_s"],
        "coverage_gaps_s": preflight["coverage_gaps_s"],
        "preflight_sha256": file_sha256(args.preflight),
        "counter_replay_sha256": file_sha256(args.counter_replay),
        "model_sha256": file_sha256(ROOT / "prototype/counter_gap_evidence.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "counter_event_count": len(rows),
        "interior_gap_candidate_count": len(interior),
        "boundary_ambiguous_count": len(boundary),
        "interior_gap_candidates": interior,
        "boundary_ambiguous": boundary,
        "limitations": [
            "Counter updates are delayed broadcast evidence, not observed release times.",
            "No counter evidence in a gap does not establish that no throw occurred.",
            "Route gaps remain gaps; these candidates are not confirmed timeline events.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"interior": len(interior), "boundary_ambiguous": len(boundary)}))


if __name__ == "__main__":
    main()
