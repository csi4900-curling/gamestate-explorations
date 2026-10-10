"""Isolate right entries without a unique earlier left-event link for review."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--links", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    right = json.loads(args.right.read_text())
    links = json.loads(args.links.read_text())
    if links["source_sha256"] != right["source_sha256"] or links["right_sha256"] != digest(
        args.right
    ):
        parser.error("Source or right-entry fingerprint differs")
    unmatched_ids = {
        row["right_raw_track_id"]
        for row in links["links"]
        if row["match_status"] != "unique_conditional_time_colour_link"
    }
    rows = [row for row in right["entry_review_proposals"] if row["raw_track_id"] in unmatched_ids]
    if len(rows) != len(unmatched_ids):
        parser.error("Unmatched IDs are not one-to-one with right entries")
    result = {
        "status": "unmatched_right_entry_prefixes_for_source_review",
        "source_sha256": right["source_sha256"],
        "right_sha256": digest(args.right),
        "links_sha256": digest(args.links),
        "runner_sha256": digest(Path(__file__)),
        "entry_review_proposals": rows,
        "limitations": [
            "A missing time/colour link does not establish a newly found physical throw."
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"unmatched_right_entries": len(rows)}))


if __name__ == "__main__":
    main()
