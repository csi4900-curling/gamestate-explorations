"""Attach following periodic partial-image observations to end-six right proposals."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def following_windows(
    windows, passage_s, next_proposal_s, *, min_lag_s=15, max_lag_s=35, gap_before_next_s=5
):
    latest = min(passage_s + max_lag_s, next_proposal_s - gap_before_next_s)
    return [row for row in windows if passage_s + min_lag_s <= row["anchor_time_s"] <= latest]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("episodes", "source-review", "manifest", "periodic", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    episodes, review, periodic = (
        json.loads(path.read_text()) for path in (args.episodes, args.source_review, args.periodic)
    )
    source_hash = episodes["source_sha256"]
    if (
        review["source_sha256"] != source_hash
        or periodic["source_sha256"] != source_hash
        or review["manifest_sha256"] != digest(args.manifest)
        or periodic["interval_s"] != [5670, 6670]
    ):
        raise ValueError("Source, review or periodic-board lineage differs")
    by_right = {
        row["right_proposal_ids"][0]: row
        for row in episodes["episodes"]
        if row["episode_kind"] == "right_only_candidate" and len(row["right_proposal_ids"]) == 1
    }
    reviewed = {row["right_proposal_id"]: row["sampled_prefix_class"] for row in review["rows"]}
    if len(reviewed) != len(review["rows"]):
        raise ValueError("Duplicate source-review right ID")
    in_interval = {
        rid: row for rid, row in by_right.items() if 5670 <= row["observation_time_s"] <= 6670
    }
    if set(reviewed) != set(in_interval):
        raise ValueError("Source review does not cover every interval right-only proposal")
    windows = sorted(periodic["windows"], key=lambda row: row["anchor_time_s"])
    if len({row["anchor_time_s"] for row in windows}) != len(windows):
        raise ValueError("Duplicate periodic-board anchor")
    ordered = sorted(in_interval.items(), key=lambda item: item[1]["observation_time_s"])
    rows = []
    for index, (rid, episode) in enumerate(ordered):
        passage = episode["observation_time_s"]
        next_time = (
            ordered[index + 1][1]["observation_time_s"] if index + 1 < len(ordered) else 6670
        )
        eligible = following_windows(windows, passage, next_time)
        usable = next(
            (
                row
                for row in eligible
                if row["observation_status"] == "partial_stable_colour_cap_proposals"
                and row["stable_cap_proposals"]
            ),
            None,
        )
        source_class = reviewed[rid]
        selected = usable if source_class == "moving_stone_pixels" else None
        rows.append(
            {
                "episode_id": episode["episode_id"],
                "right_proposal_id": rid,
                "passage_time_s": passage,
                "colour_claim": episode["colour_claim"],
                "source_prefix_class": source_class,
                "next_right_only_proposal_time_s": next_time,
                "eligible_window_anchor_times_s": [row["anchor_time_s"] for row in eligible],
                "eligible_window_statuses": [row["observation_status"] for row in eligible],
                "following_partial_image_observation": (
                    {
                        "anchor_time_s": selected["anchor_time_s"],
                        "stable_cap_proposals": selected["stable_cap_proposals"],
                        "sample_times_s": [
                            sample["time_s"] for sample in selected["sample_frames"]
                        ],
                        "complete_board_verified": False,
                    }
                    if selected
                    else None
                ),
                "state_status": (
                    "not_applied_person_pixels"
                    if source_class != "moving_stone_pixels"
                    else "following_partial_image_observation"
                    if selected
                    else "no_usable_following_observation"
                ),
                "physical_throw_verified": False,
                "same_stone_identity_verified": False,
                "settle_time_s": None,
                "simulation_ready": False,
            }
        )
    status_counts = dict(Counter(row["state_status"] for row in rows))
    output = {
        "status": "candidate_to_periodic_partial_image_state_not_settled_game_state",
        "source_sha256": source_hash,
        "interval_s": [5670, 6670],
        "input_sha256": {
            "episodes": digest(args.episodes),
            "source_review": digest(args.source_review),
            "manifest": digest(args.manifest),
            "periodic": digest(args.periodic),
        },
        "runner_sha256": digest(Path(__file__)),
        "following_window_rule": {
            "minimum_lag_s": 15,
            "maximum_lag_s": 35,
            "stop_before_next_right_only_proposal_s": 5,
            "selection": "first nonempty partial-stable-cap window in range",
            "status": "postreview_development_selection_not_settle_validation",
        },
        "right_only_proposal_count": len(rows),
        "state_status_counts": status_counts,
        "rows": rows,
        "limitations": [
            "The 15–35 s follow-up rule was chosen after inspecting candidate and board coverage.",
            "Periodic source frames can observe stones and foreground objects without a complete board.",
            "A following partial observation does not verify a throw, its settlement, a board change, or physical stone identity.",
            "A proposal outside the periodic 5670–6670 s coverage has no observation here.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows), "statuses": status_counts}))


if __name__ == "__main__":
    main()
