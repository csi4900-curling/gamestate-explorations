"""Join corridor proposals with a saved right-track tail without labels."""

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
    for name in ("left", "right-tail", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    left = json.loads(args.left.read_text())
    tail = json.loads(args.right_tail.read_text())
    if (left["source_sha256"] != tail["source_sha256"] or
            left["source_interval_s"][0] < tail["source_interval_s"][0] or
            left["source_interval_s"][1] > tail["source_interval_s"][1]):
        raise ValueError("Left and right source intervals differ")
    proposals = [{
        "proposal_id": f"{args.run_id}:{row['raw_track_id']}",
        "colour_claim": row["colour_claim"],
        "direction": row["direction"],
        "passage_time_s": row["passage"]["time_s"],
    } for row in tail["directional_review_proposals"]]
    rows = corroborate_left_proposals(left["events"], proposals)
    output = {
        "status": "first_transfer_prediction_only_two_view_candidate_corrob_not_throw_truth",
        "source_id": left["source_id"],
        "source_sha256": left["source_sha256"],
        "source_interval_s": left["source_interval_s"],
        "input_sha256": {"left": digest(args.left), "right_tail": digest(args.right_tail)},
        "model_code_sha256": digest(ROOT / "prototype/corridor_right_corrob.py"),
        "runner_sha256": digest(Path(__file__)),
        "right_run_id": args.run_id,
        "right_proposal_count": len(proposals),
        "maximum_direction_aware_view_order_lag_s": 20,
        "tier_counts": dict(Counter(row["corroboration_tier"] for row in rows)),
        "rows": rows,
        "limitations": [
            "The underlying right tracker and left corridor were previously developed on this broadcast family.",
            "Time, colour and direction do not verify a shared physical stone.",
            "No event labels are read in this stage.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"source": left["source_id"], "tiers": output["tier_counts"]}))


if __name__ == "__main__":
    main()
