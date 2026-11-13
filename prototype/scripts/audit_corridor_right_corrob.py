"""Join early left corridor proposals to saved full-match right proposals."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from corridor_right_corrob import corroborate_left_proposals


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("left", "right-sequence", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    left = json.loads(args.left.read_text())
    right = json.loads(args.right_sequence.read_text())
    if left["source_sha256"] != right["source_sha256"] or left["source_id"] != right["source_id"]:
        raise ValueError("Left and right sources differ")
    rows = corroborate_left_proposals(left["events"], right["right_proposals"])
    output = {
        "status": "postreview_prediction_only_two_view_candidate_corrob_not_throw_truth",
        "source_id": left["source_id"],
        "source_sha256": left["source_sha256"],
        "source_interval_s": left["source_interval_s"],
        "input_sha256": {"left": digest(args.left), "right_sequence": digest(args.right_sequence)},
        "model_code_sha256": digest(ROOT / "prototype/corridor_right_corrob.py"),
        "runner_sha256": digest(Path(__file__)),
        "maximum_direction_aware_view_order_lag_s": 20,
        "tier_counts": dict(Counter(row["corroboration_tier"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Both left and right proposal inventories were developed on exposed recordings.",
            "Matching time, colour and travel direction does not verify one physical stone.",
            "Right proposal recall is incomplete and people can generate right tracks.",
            "No event decision or independent precision/recall/F1 is inferred here.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"source": output["source_id"], "tiers": output["tier_counts"]}))


if __name__ == "__main__":
    main()
