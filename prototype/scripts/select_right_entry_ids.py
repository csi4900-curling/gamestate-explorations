"""Select named right-entry prefixes for a source-strip review artifact."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--ids", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    source = json.loads(args.proposals.read_text())
    ids = set(args.ids)
    if len(ids) != len(args.ids):
        parser.error("Duplicate requested ID")
    selected = [row for row in source["entry_review_proposals"] if row["raw_track_id"] in ids]
    if {row["raw_track_id"] for row in selected} != ids:
        parser.error("Requested ID not found")
    output = {
        "status": "selected_entry_source_review_not_throw_labels",
        "source_sha256": source["source_sha256"],
        "parent_sha256": digest(args.proposals),
        "runner_sha256": digest(Path(__file__)),
        "selected_ids": args.ids,
        "entry_review_proposals": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"selected": len(selected)}))


if __name__ == "__main__":
    main()
