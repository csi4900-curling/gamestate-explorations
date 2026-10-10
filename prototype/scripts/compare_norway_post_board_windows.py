"""Freeze short-vs-long source board-window coverage and postscore sensitivity."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
SHORT = BASE / "norway-full-candidate-post-counter-image-boards-v3.json"
LONG = BASE / "norway-full-candidate-post-counter-long-window-boards-v4.json"
SHORT_SCORE = BASE / "norway-full-post-counter-image-board-postscore-first.json"
LONG_SCORE = BASE / "norway-full-post-counter-long-window-board-postscore-v4.json"
OUTPUT = BASE / "norway-post-board-window-sensitivity-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def has_stable(row):
    return any(group["stable_image_relative_stones"] for group in row["camera_shot_boards"])


def earliest_by_candidate(score):
    selected = {}
    for row in score["groups"]:
        candidate = row["video_candidate_shot_id"]
        current = selected.get(candidate)
        if (
            current is None
            or row["source_observation_interval_s"][0] < current["source_observation_interval_s"][0]
        ):
            selected[candidate] = row
    return selected


def summarize_earliest(rows):
    return {
        "candidate_count": len(rows),
        "observed_stone_count": sum(
            row["current_comparison"]["video_stone_count"] for row in rows.values()
        ),
        "matched_observed_stone_count": sum(
            row["current_comparison"]["matched_count"] for row in rows.values()
        ),
        "complete_diagram_symbol_match_count": sum(
            row["complete_diagram_symbol_match"] for row in rows.values()
        ),
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("First board-window sensitivity output already exists")
    short = json.loads(SHORT.read_text())
    long = json.loads(LONG.read_text())
    short_score = json.loads(SHORT_SCORE.read_text())
    long_score = json.loads(LONG_SCORE.read_text())
    if len({short["source_video_sha256"], long["source_video_sha256"]}) != 1:
        raise SystemExit("Source videos differ")
    if short_score["input_sha256"]["source_scan"] != digest(SHORT) or long_score["input_sha256"][
        "source_scan"
    ] != digest(LONG):
        raise SystemExit("Postscore inputs differ from frozen source scans")
    by_short = {row["shot_id"]: row for row in short["rows"]}
    by_long = {row["shot_id"]: row for row in long["rows"]}
    if set(by_short) != set(by_long):
        raise SystemExit("Candidate sets differ")
    gained = [
        shot_id
        for shot_id in by_long
        if not has_stable(by_short[shot_id]) and has_stable(by_long[shot_id])
    ]
    lost = [
        shot_id
        for shot_id in by_short
        if has_stable(by_short[shot_id]) and not has_stable(by_long[shot_id])
    ]
    early_short = earliest_by_candidate(short_score)
    early_long = earliest_by_candidate(long_score)
    if not set(early_short).issubset(early_long):
        raise SystemExit("Long-window postscore lost an earlier scored candidate")
    new_scored = []
    for shot_id in early_long:
        if shot_id in early_short:
            continue
        row = early_long[shot_id]
        comparison = row["current_comparison"]
        new_scored.append(
            {
                "candidate_id": shot_id,
                "official_shot_id": row["official_shot_id"],
                "post_camera_shot_id": row["post_camera_shot_id"],
                "observed_stones": comparison["video_stone_count"],
                "matched_observed_stones": comparison["matched_count"],
                "official_symbols": comparison["official_symbol_count"],
                "complete_diagram_symbol_match": row["complete_diagram_symbol_match"],
            }
        )
    result = {
        "status": "source_gate_horizon_sensitivity_with_retrospective_postscore_not_validation",
        "input_sha256": {
            "short_source_scan": digest(SHORT),
            "long_source_scan": digest(LONG),
            "short_postscore": digest(SHORT_SCORE),
            "long_postscore": digest(LONG_SCORE),
        },
        "runner_sha256": digest(Path(__file__)),
        "short_horizon_s": 32,
        "long_horizon_s": 90,
        "short_stable_candidate_count": short["candidates_with_stable_image_board"],
        "long_stable_candidate_count": long["candidates_with_stable_image_board"],
        "gained_stable_candidate_ids": gained,
        "lost_stable_candidate_ids": lost,
        "short_earliest_group_postscore": summarize_earliest(early_short),
        "long_earliest_group_postscore": summarize_earliest(early_long),
        "new_earliest_scored_candidates": new_scored,
        "limitations": [
            "Earliest camera group is chosen by source time, never by official diagram score.",
            "Both scores are retrospective, on a selected subset with orientation support.",
            "A longer window can include unlisted true throws or transitions despite stopping before the next detected candidate.",
            "This sensitivity result does not choose a production horizon or estimate unseen-match accuracy.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "short_stable_candidate_count",
                "long_stable_candidate_count",
                "gained_stable_candidate_ids",
                "lost_stable_candidate_ids",
                "short_earliest_group_postscore",
                "long_earliest_group_postscore",
            )
        }
    )


if __name__ == "__main__":
    main()
