"""Extract ambiguous candidate motion rows for an unchanged patch audit."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    source = json.loads(args.motion.read_text())
    subset = {key: value for key, value in source.items() if key != "rows"}
    subset["status"] = "ambiguous_motion_rows_for_unchanged_patch_audit"
    subset["parent_motion"] = str(args.motion)
    subset["parent_motion_sha256"] = sha256(args.motion.read_bytes()).hexdigest()
    subset["runner_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    subset["rows"] = [
        row
        for row in source["rows"]
        if row["selection"]["status"] == "ambiguous_far_entry_motion_paths"
    ]
    if not subset["rows"]:
        parser.error("No ambiguous motion rows")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(subset, indent=2) + "\n")
    print(len(subset["rows"]), "ambiguous rows", args.output)


if __name__ == "__main__":
    main()
