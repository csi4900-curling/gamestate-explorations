"""Preserve both right proposal lanes as review candidates, without deduping."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_proposal_union import union_right_proposals


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--first-lane", required=True)
    parser.add_argument("--second-lane", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    first = json.loads(args.first.read_text())
    second = json.loads(args.second.read_text())
    rows = union_right_proposals(first, second,
                                first_lane=args.first_lane,
                                second_lane=args.second_lane)
    result = {
        "status": "lossless_right_proposal_union_not_deduplicated_events",
        "source_sha256": first["source_sha256"],
        "source_interval_s": first["source_interval_s"],
        "source_time_offset_s": first.get("source_time_offset_s", 0),
        "lane_inputs": [
            {"lane": args.first_lane, "proposal_file_sha256": digest(args.first),
             "proposal_count": len(first["directional_review_proposals"])},
            {"lane": args.second_lane, "proposal_file_sha256": digest(args.second),
             "proposal_count": len(second["directional_review_proposals"])},
        ],
        "union_code_sha256": digest(ROOT / "prototype/right_proposal_union.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(rows),
        "candidates": rows,
        "limitations": [
            "Nearby same-colour proposals can describe the same physical stone or event.",
            "The union makes no deduplication, object-identity or throw decision.",
            "Both lanes and all uncertainty remain available for later review.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows), "lanes": [
        len(first["directional_review_proposals"]),
        len(second["directional_review_proposals"])]}))


if __name__ == "__main__":
    main()
