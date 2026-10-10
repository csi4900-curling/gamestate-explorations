"""Isolate newly admitted right-entry prefixes for source-frame inspection."""

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
    parser.add_argument("--variant", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    variant = json.loads(args.variant.read_text())
    new_ids = set(variant["new_ids"])
    rows = [row for row in variant["entry_review_proposals"]
            if row["raw_track_id"] in new_ids]
    if len(rows) != len(new_ids):
        parser.error("New IDs are not one-to-one with proposals")
    result = {
        "status": "postreview_new_prefixes_for_source_inspection",
        "source_sha256": variant["source_sha256"],
        "variant_sha256": digest(args.variant),
        "runner_sha256": digest(Path(__file__)),
        "entry_review_proposals": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"new_prefixes": len(rows)}))


if __name__ == "__main__":
    main()
