"""Replay frozen counter observations through a revised state machine."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from broadcast_scoreboard import ScoreboardEvents
from cache_contract import file_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first replay")
    audit = json.loads(args.audit.read_text())
    start, end = audit["source_interval_s"]
    samples = audit["counter_samples"]
    if len(samples) != end - start or any(
        row["time_s"] != start + index for index, row in enumerate(samples)
    ):
        parser.error("Audit samples do not cover the declared interval")
    tracker = ScoreboardEvents()
    for row in samples:
        counts = tuple(row["counts"]) if row["counts"] is not None else None
        tracker.update(counts, float(row["time_s"]))
    previous = {(row["colour"], row["crossing_time_s"]) for row in audit["counter_events"]}
    current = {(row["colour"], row["crossing_time_s"]) for row in tracker.events}
    result = {
        "status": "postscore_counter_state_replay",
        "source_id": audit["source_id"],
        "source_sha256": audit["source_sha256"],
        "source_interval_s": audit["source_interval_s"],
        "input_audit_sha256": file_sha256(args.audit),
        "counter_model_sha256": file_sha256(ROOT / "prototype/broadcast_scoreboard.py"),
        "runner_sha256": file_sha256(__file__),
        "counter_events": tracker.events,
        "unresolved_counter_changes": tracker.unresolved,
        "removed_previous_event_keys": sorted(previous - current, key=lambda row: row[1]),
        "added_event_keys": sorted(current - previous, key=lambda row: row[1]),
        "limitations": [
            "The state-machine fix was chosen after inspecting a flickering China counter slot.",
            "This replay is retrospective; a different recording is needed to test transfer.",
            "The saved one-second observations are not an exhaustive throw reference.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "events": len(tracker.events),
                "removed": result["removed_previous_event_keys"],
                "added": result["added_event_keys"],
            }
        )
    )


if __name__ == "__main__":
    main()
