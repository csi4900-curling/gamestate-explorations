"""Export conditional post-event board-view routes for a split 2024 sequence."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from split_board_view_routing import route_split_post_board_views


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    source = json.loads(args.sequence.read_text())
    routed = route_split_post_board_views(source)
    routed["status"] = "postreview_conditional_split_board_view_routing_not_board_truth"
    routed["source_id"] = source["source_id"]
    routed["sequence_sha256"] = digest(args.sequence)
    routed["router_sha256"] = digest(ROOT / "prototype/split_board_view_routing.py")
    routed["runner_sha256"] = digest(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(routed, indent=2) + "\n")
    print(
        json.dumps(
            {
                "source_id": routed["source_id"],
                "view_counts": routed["conditional_receiving_view_counts"],
                "abstentions": routed["left_candidate_count"]
                - sum(routed["conditional_receiving_view_counts"].values()),
                "prior_right_scan_wrong_view_conditional": routed[
                    "existing_right_scan_wrong_view_count_conditional"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
