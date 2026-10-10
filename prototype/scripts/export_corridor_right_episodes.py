"""Export prediction-only cross-view candidate episodes with source lineage."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from corridor_right_episodes import build_corrob_episodes


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corroboration", type=Path, required=True)
    parser.add_argument("--right-tail", type=Path)
    parser.add_argument("--right-run-id")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    if bool(args.right_tail) != bool(args.right_run_id):
        parser.error("Right tail and run ID must be provided together")
    corrob = json.loads(args.corroboration.read_text())
    right_proposals = None
    if args.right_tail:
        tail = json.loads(args.right_tail.read_text())
        if corrob["source_sha256"] != tail["source_sha256"]:
            raise ValueError("Right tail source differs")
        right_proposals = [{
            "proposal_id": f"{args.right_run_id}:{row['raw_track_id']}",
            "colour_claim": row["colour_claim"],
            "direction": row["direction"],
            "passage_time_s": row["passage"]["time_s"],
        } for row in tail["directional_review_proposals"]]
    episodes = build_corrob_episodes(
        corrob["rows"], right_proposals=right_proposals,
        interval_s=corrob["source_interval_s"] if right_proposals is not None else None)
    left_ids = [left_id for row in episodes
                for left_id in row["member_left_candidate_ids"]]
    if len(left_ids) != len(corrob["rows"]) or len(set(left_ids)) != len(left_ids):
        raise ValueError("Episode output lost or duplicated left proposals")
    output = {
        "status": "prediction_only_cross_view_proposal_episodes_not_physical_throws",
        "source_id": corrob["source_id"],
        "source_sha256": corrob["source_sha256"],
        "source_interval_s": corrob["source_interval_s"],
        "corroboration_sha256": digest(args.corroboration),
        "right_tail_sha256": digest(args.right_tail) if args.right_tail else None,
        "model_code_sha256": digest(ROOT / "prototype/corridor_right_episodes.py"),
        "runner_sha256": digest(Path(__file__)),
        "original_left_candidate_count": len(corrob["rows"]),
        "right_proposal_count": len(right_proposals) if right_proposals is not None else None,
        "episode_count": len(episodes),
        "episode_kind_counts": dict(Counter(row["episode_kind"] for row in episodes)),
        "episodes": episodes,
        "limitations": [
            "A shared right proposal groups left candidates for review; it does not prove one throw.",
            "A right proposal can be a person or equipment and may be spuriously linked by time.",
            "No release, settle, board transition, or physical identity is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"left": len(corrob["rows"]), "episodes": len(episodes),
                      "kinds": output["episode_kind_counts"]}))


if __name__ == "__main__":
    main()
