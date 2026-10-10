"""Join a frozen full-source right scan to accepted and withheld left triggers."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from corridor_right_corrob import corroborate_left_proposals
from corridor_right_episodes import build_corrob_episodes


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "left", "right", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    plan, left, right = (json.loads(path.read_text()) for path in
                         (args.plan, args.left, args.right))
    if (left["source_sha256"] != plan["source_sha256"] or
            right["source_sha256"] != plan["source_sha256"] or
            right["source_interval_s"] != plan["source_interval_s"] or
            right["runner_sha256"] != plan["runner_sha256"] or
            right["association_code_sha256"] != plan["association_code_sha256"] or
            right["late_seed_code_sha256"] != plan["late_seed_code_sha256"] or
            right["colour_proposal_code_sha256"] != plan["colour_code_sha256"]):
        raise ValueError("Full-source scan differs from frozen plan or left source")
    triggers = left["events"] + left["withheld_events"]
    decisions = {row["id"]: row for row in left["decisions"]}
    if (len(decisions) != len(left["decisions"]) or
            {row["id"] for row in triggers} != set(decisions) or
            len(triggers) != len(decisions)):
        raise ValueError("Left trigger and decision inventory differs")
    left_events = [{"id": row["id"], "crossing_time_s": row["crossing_time_s"],
                    "colour": row["colour"], "view_motion": row["view_motion"]}
                   for row in triggers]
    right_proposals = [{
        "proposal_id": "R01:" + row["raw_track_id"],
        "colour_claim": row["colour_claim"],
        "direction": row["direction"],
        "passage_time_s": row["passage"]["time_s"],
    } for row in right["directional_review_proposals"]]
    joins = corroborate_left_proposals(left_events, right_proposals)
    episodes = build_corrob_episodes(
        joins, right_proposals=right_proposals,
        interval_s=right["source_interval_s"])
    for episode in episodes:
        ids = episode["member_left_candidate_ids"]
        episode["left_screen_statuses"] = {
            left_id: decisions[left_id]["status"] for left_id in ids}
        episode["provisional_accepted_left_count"] = sum(
            decisions[left_id]["status"] == "confirmed" for left_id in ids)
        episode["within_left_coverage_interval"] = (
            left["source_interval_s"][0] <= episode["observation_time_s"] <=
            left["source_interval_s"][1])
    left_ids = [left_id for row in episodes
                for left_id in row["member_left_candidate_ids"]]
    right_ids = [right_id for row in episodes for right_id in row["right_proposal_ids"]]
    if (set(left_ids) != set(decisions) or len(left_ids) != len(decisions) or
            {row["proposal_id"] for row in right_proposals} != set(right_ids) or
            len(right_ids) != len(right_proposals)):
        raise ValueError("Episode grouping lost or duplicated a proposal")
    output = {
        "status": "prediction_only_full_area_right_cross_view_episodes_not_throw_truth",
        "source_id": left["source_id"],
        "source_sha256": plan["source_sha256"],
        "source_interval_s": right["source_interval_s"],
        "left_coverage_interval_s": left["source_interval_s"],
        "input_sha256": {"plan": digest(args.plan), "left": digest(args.left),
                         "right": digest(args.right)},
        "join_code_sha256": digest(ROOT / "prototype/corridor_right_corrob.py"),
        "episode_code_sha256": digest(ROOT / "prototype/corridor_right_episodes.py"),
        "runner_sha256": digest(Path(__file__)),
        "original_left_trigger_count": len(triggers),
        "original_provisional_accepted_left_count": len(left["events"]),
        "right_proposal_count": len(right_proposals),
        "left_join_tier_counts": dict(Counter(row["corroboration_tier"] for row in joins)),
        "episode_count": len(episodes),
        "episode_kind_counts": dict(Counter(row["episode_kind"] for row in episodes)),
        "left_joins": joins,
        "episodes": episodes,
        "limitations": [
            "Left triggers are previous model decisions, not physical throw labels.",
            "Right-only proposals outside the left coverage interval cannot imply a left miss.",
            "Temporal compatibility does not establish same-stone identity or a physical delivery.",
            "No complete board, release or settle time, independent F1 or simulation-ready state is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"left": len(triggers), "right": len(right_proposals),
                      "episodes": len(episodes),
                      "kinds": output["episode_kind_counts"]}))


if __name__ == "__main__":
    main()
