"""Compare full supported-run right proposals with the provisional left timeline."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_full_match_temporal_inventory import inventory


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--run", nargs=2, action="append", metavar=("RUN_ID", "PROBE"),
                        required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    supported = {run["id"]: run for run in timeline["supported_runs"]
                 if run["layout"] == "split_2024"}
    if set(run_id for run_id, _ in args.run) != set(supported) or len(args.run) != len(supported):
        parser.error("Exactly one probe per supported split-view run required")
    run_proposals, input_hashes = [], {}
    for run_id, path_str in args.run:
        path = Path(path_str)
        probe = json.loads(path.read_text())
        start, stop = supported[run_id]["interval_s"]
        if (probe["source_sha256"] != timeline["source_sha256"]
                or probe["source_interval_s"] != [int(start), int(stop) - 1]
                or probe["source_time_offset_s"] != 0):
            parser.error(f"{run_id} source or routed interval differs")
        if any(not start <= row["passage"]["time_s"] < stop
               for row in probe["directional_review_proposals"]):
            parser.error(f"{run_id} has passage outside supported run")
        run_proposals.append((run_id, probe["directional_review_proposals"],
                              (start, stop)))
        input_hashes[run_id] = digest(path)
    result = inventory(timeline["observed_events"], run_proposals)
    payload = {
        "status": "unreviewed_full_match_right_temporal_inventory_not_throw_labels",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": timeline["source_interval_s"],
        "supported_runs": [{"id": run["id"], "interval_s": run["interval_s"]}
                           for run in supported.values()],
        "coverage_gaps_s": timeline["coverage_gaps_s"],
        "timeline_sha256": digest(args.timeline),
        "right_probe_sha256_by_run": input_hashes,
        "model_code_sha256": digest(ROOT / "prototype/right_full_match_temporal_inventory.py"),
        "runner_sha256": digest(Path(__file__)),
        "left_event_count": len(timeline["observed_events"]),
        "right_proposal_count": len(result["rows"]),
        **result,
        "limitations": [
            "Right proposals and left events are unreviewed development candidates.",
            "A unique time/colour candidate is not a physical cross-view identity.",
            "No automatic clear-context or physical throw acceptance is made.",
            "Router gaps remain outside this right scan; missing candidates are not negative truth.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"left_events": payload["left_event_count"],
                      "right_proposals": payload["right_proposal_count"],
                      "statuses": payload["status_counts"],
                      "left_without_right": len(payload[
                          "left_events_without_any_right_time_colour_candidate"])}))


if __name__ == "__main__":
    main()
