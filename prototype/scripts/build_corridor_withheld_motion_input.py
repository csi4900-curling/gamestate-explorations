"""Preserve corridor-withheld candidates as a separate development motion input."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corridor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    data = json.loads(args.corridor.read_text())
    selected_ids = {row["id"] for row in data["events"]}
    withheld = data["withheld_events"]
    withheld_ids = [row["id"] for row in withheld]
    if len(withheld_ids) != len(set(withheld_ids)) or selected_ids.intersection(withheld_ids):
        parser.error("Corridor IDs are duplicated or overlap the selected set")
    if len(selected_ids) + len(withheld_ids) != len(data["screened_events"]):
        parser.error("Corridor partition does not cover the raw candidate ledger")
    output = {
        "status": "postscore_development_corridor_withheld_motion_input",
        "source_id": data["source_id"],
        "source_sha256": data["source_sha256"],
        "source_interval_s": data["source_interval_s"],
        "corridor_sha256": sha256(args.corridor.read_bytes()).hexdigest(),
        "runner_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "events": withheld,
        "limitations": [
            "Candidates are motion spans, not labelled throws.",
            "This postscore diagnostic does not alter the frozen corridor screen or establish F1.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Preserved {len(withheld)} withheld candidates")


if __name__ == "__main__":
    main()
