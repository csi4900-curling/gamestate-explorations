"""Export source-bounded right-view motion segments without physical throw claims."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_motion_onset import observed_quiet_to_motion


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "probe", "episodes", "source-review", "partial-state", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    plan, probe, episodes, review, state = (
        json.loads(path.read_text())
        for path in (args.plan, args.probe, args.episodes, args.source_review, args.partial_state)
    )
    expected = {
        "probe_sha256": digest(args.probe),
        "episodes_sha256": digest(args.episodes),
        "source_review_sha256": digest(args.source_review),
        "partial_state_sha256": digest(args.partial_state),
        "onset_code_sha256": digest(ROOT / "prototype/right_motion_onset.py"),
    }
    if any(plan[key] != value for key, value in expected.items()):
        raise ValueError("Frozen motion-timing input or code changed")
    if any(
        row["source_sha256"] != plan["source_sha256"] for row in (probe, episodes, review, state)
    ):
        raise ValueError("Source lineage differs")
    if (
        episodes["input_sha256"]["right"] != expected["probe_sha256"]
        or state["input_sha256"]["episodes"] != expected["episodes_sha256"]
        or state["input_sha256"]["source_review"] != expected["source_review_sha256"]
    ):
        raise ValueError("Episode/state lineage differs")
    episode_by_right = {}
    for episode in episodes["episodes"]:
        for rid in episode["right_proposal_ids"]:
            if rid in episode_by_right:
                raise ValueError("Right proposal appears in multiple episodes")
            episode_by_right[rid] = episode
    review_by_id = {row["right_proposal_id"]: row["sampled_prefix_class"] for row in review["rows"]}
    state_by_id = {row["right_proposal_id"]: row for row in state["rows"]}
    tracks = {"R01:" + row["raw_track_id"]: row for row in probe["directional_review_proposals"]}
    if (
        len(tracks) != len(probe["directional_review_proposals"])
        or set(tracks) != set(episode_by_right)
        or set(review_by_id) != set(state_by_id)
    ):
        raise ValueError("Track, episode or reviewed-state IDs differ")
    rules = plan["rules"]
    rows = []
    for rid, track in sorted(tracks.items()):
        onset = observed_quiet_to_motion(
            track["observed_prefix_points"],
            track["direction"],
            quiet_rate_px_s=rules["quiet_absolute_vertical_rate_max_px_s"],
            strong_rate_px_s=rules["strong_directional_vertical_rate_min_px_s"],
            quiet_steps=rules["quiet_consecutive_steps_min"],
            strong_steps=rules["strong_consecutive_steps_min"],
            max_sample_gap_s=rules["maximum_sample_gap_s"],
            max_quiet_to_strong_s=rules["maximum_quiet_to_first_strong_s"],
        )
        episode = episode_by_right[rid]
        partial = state_by_id.get(rid)
        source_class = review_by_id.get(rid)
        rows.append(
            {
                "right_proposal_id": rid,
                "episode_id": episode["episode_id"],
                "episode_kind": episode["episode_kind"],
                "member_left_candidate_ids": episode["member_left_candidate_ids"],
                "source_prefix_class": source_class,
                "colour_claim": track["colour_claim"],
                "direction": track["direction"],
                "passage_time_s": track["passage"]["time_s"],
                "saved_track_interval_s": track["observed_prefix_interval_s"],
                "observed_motion_onset": onset,
                "following_partial_image_state_status": (
                    partial["state_status"] if partial else None
                ),
                "following_partial_image_observation": (
                    partial["following_partial_image_observation"] if partial else None
                ),
                "physical_throw_verified": False,
                "physical_release_time_s": None,
                "physical_settle_time_s": None,
                "complete_game_state_verified": False,
                "simulation_ready": False,
            }
        )
    counts = Counter(row["observed_motion_onset"]["status"] for row in rows)
    reviewed_counts = Counter(
        (row["source_prefix_class"], row["observed_motion_onset"]["status"])
        for row in rows
        if row["source_prefix_class"]
    )
    output = {
        "status": "observed_right_view_motion_segments_not_complete_physical_throws",
        "source_sha256": plan["source_sha256"],
        "source_interval_s": probe["source_interval_s"],
        "input_sha256": {
            "plan": digest(args.plan),
            "probe": digest(args.probe),
            "episodes": digest(args.episodes),
            "source_review": digest(args.source_review),
            "partial_state": digest(args.partial_state),
        },
        "onset_code_sha256": expected["onset_code_sha256"],
        "runner_sha256": digest(Path(__file__)),
        "proposal_count": len(rows),
        "onset_status_counts": dict(counts),
        "reviewed_class_onset_counts": {
            cls: {
                status: count
                for (label, status), count in sorted(reviewed_counts.items())
                if label == cls
            }
            for cls in sorted(set(review_by_id.values()))
        },
        "rows": rows,
        "limitations": [
            "Thresholds were chosen after viewing Latvia end-six paths, so counts here are development evidence.",
            "Quiet-to-motion transitions also occur on people and equipment.",
            "The onset bracket bounds source-observed directional motion, not physical release.",
            "The last observed track point is not a settle or throw-end time.",
            "Pixel paths have no verified cross-camera identity or metric calibration.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "proposals": len(rows),
                "onsets": dict(counts),
                "reviewed": output["reviewed_class_onset_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
