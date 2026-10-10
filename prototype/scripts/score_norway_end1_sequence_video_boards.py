"""Postscore frozen source-only end-one boards against official PDF states."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.board_state_comparison import compare_board_observations


BASE = ROOT / "validation/official-shot-sequence"
SCAN = BASE / "norway-end1-source-video-partial-boards-first.json"
SEQUENCE = BASE / "norway-end1-16-shot-sequence-hypothesis-first.json"
OFFICIAL = BASE / "pwg2022-canada-norway-official-boards.json"
OUTPUT = BASE / "norway-end1-video-board-first-score.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def rank(comparison):
    return (
        comparison["matched_count"],
        -len(comparison["unmatched_video"]) - len(comparison["unmatched_official"]),
    )


def build():
    scan = json.loads(SCAN.read_text())
    sequence = json.loads(SEQUENCE.read_text())
    official = json.loads(OFFICIAL.read_text())
    if (
        scan["source_video_sha256"] != official["source_video_sha256"]
        or scan["sequence_hypothesis_sha256"] != digest(SEQUENCE)
        or scan["shot_count"] != 16
    ):
        raise ValueError("Video source or sequence changed")
    end = official["ends"][0]
    if end["end"] != 1 or len(end["shots"]) != 16:
        raise ValueError("Official end-one shot diagrams changed")
    rows = []
    for index, (observation, hypothesis, shot) in enumerate(
        zip(scan["rows"], sequence["rows"], end["shots"])
    ):
        if (
            observation["shot_number"] != index + 1
            or hypothesis["official_shot_id"] != shot["official_shot_id"]
            or observation["video_candidate_shot_id"] != hypothesis["video_candidate_shot_id"]
        ):
            raise ValueError("Video, sequence and official shot order disagree")
        stones = observation["stable_partial_board"]
        current = compare_board_observations(
            stones, shot["stones"], official_house_center_y=shot["house_center_px"][1]
        )
        previous = end["shots"][index - 1] if index else None
        previous_score = (
            compare_board_observations(
                stones, previous["stones"], official_house_center_y=previous["house_center_px"][1]
            )
            if previous
            else None
        )
        relation = (
            "prior_better"
            if previous_score and rank(previous_score) > rank(current)
            else "current_better"
            if previous_score and rank(current) > rank(previous_score)
            else "tied"
            if previous_score
            else "no_prior_shot_in_end"
        )
        rows.append(
            {
                "shot_number": index + 1,
                "video_candidate_shot_id": observation["video_candidate_shot_id"],
                "official_shot_id": shot["official_shot_id"],
                "video_stone_count": len(stones),
                "official_symbol_count": len(shot["stones"]),
                "official_diagram_review_flags": shot["review_flags"],
                "current_comparison": current,
                "prior_comparison": previous_score,
                "current_vs_prior_cardinality": relation,
            }
        )
    observed = [row for row in rows if row["video_stone_count"]]
    return {
        "status": "postscore_norway_end1_source_video_partial_boards_not_promoted",
        "source_only_scan_sha256": digest(SCAN),
        "sequence_hypothesis_sha256": digest(SEQUENCE),
        "official_diagrams_sha256": digest(OFFICIAL),
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "shot_count": len(rows),
        "shots_with_video_board": len(observed),
        "video_stone_count": sum(row["video_stone_count"] for row in observed),
        "matched_stone_count": sum(row["current_comparison"]["matched_count"] for row in observed),
        "complete_board_match_count": sum(
            row["video_stone_count"]
            == row["official_symbol_count"]
            == row["current_comparison"]["matched_count"]
            for row in observed
        ),
        "prior_better_count": sum(
            row["current_vs_prior_cardinality"] == "prior_better" for row in observed
        ),
        "current_better_count": sum(
            row["current_vs_prior_cardinality"] == "current_better" for row in observed
        ),
        "tied_count": sum(row["current_vs_prior_cardinality"] == "tied" for row in observed),
        "rows": rows,
        "limitations": [
            "Scoring uses independent PDF positions only after source-video observations were frozen.",
            "Video boards are partial; missed stones are not necessarily absent from the ice.",
            "Better agreement with the prior board can indicate early sampling, occlusion, or a proposal mismatch, not proof of a false event.",
            "No exact settle time, persistent stone identity, physical game state, or simulation-ready output is established.",
        ],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-one board postscore")
    result = build()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "shot_count",
                "shots_with_video_board",
                "video_stone_count",
                "matched_stone_count",
                "complete_board_match_count",
                "prior_better_count",
                "current_better_count",
                "tied_count",
            )
        }
    )


if __name__ == "__main__":
    main()
