"""Select unreviewed right paths that lack a unique left time/colour candidate."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    inventory = json.loads(args.inventory.read_text())
    probe = json.loads(args.probe.read_text())
    if inventory["source_sha256"] != probe["source_sha256"] or inventory[
        "right_probe_sha256_by_run"
    ].get(args.run_id) != digest(args.probe):
        parser.error("Inventory and probe lineage differs")
    selected = [
        row
        for row in inventory["rows"]
        if row["run_id"] == args.run_id
        and row["temporal_status"] != "one_left_time_colour_candidate"
    ]
    proposal_by_id = {row["raw_track_id"]: row for row in probe["directional_review_proposals"]}
    if len(proposal_by_id) != len(probe["directional_review_proposals"]):
        parser.error("Duplicate raw proposal IDs")
    if any(row["raw_track_id"] not in proposal_by_id for row in selected):
        parser.error("Inventory mentions absent proposal")
    result = {
        "status": "unreviewed_temporal_disagreement_selection_not_negative_labels",
        "source_sha256": probe["source_sha256"],
        "source_interval_s": probe["source_interval_s"],
        "source_time_offset_s": probe["source_time_offset_s"],
        "run_id": args.run_id,
        "inventory_sha256": digest(args.inventory),
        "parent_probe_sha256": digest(args.probe),
        "runner_sha256": digest(Path(__file__)),
        "selection_rows": [
            {
                "raw_track_id": row["raw_track_id"],
                "temporal_status": row["temporal_status"],
                "direction_aware_same_colour_left_ids_within_lag": row[
                    "direction_aware_same_colour_left_ids_within_lag"
                ],
            }
            for row in selected
        ],
        "directional_review_proposals": [proposal_by_id[row["raw_track_id"]] for row in selected],
        "limitations": [
            "Temporal mismatch is a review priority, not a false-positive label.",
            "The existing left timeline can miss true throws or contain false proposals.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": args.run_id, "selected": len(selected)}))


if __name__ == "__main__":
    main()
