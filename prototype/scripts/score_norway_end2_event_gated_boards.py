"""Postscore the frozen Norway end-two event-gated transfer."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations

BASE = ROOT / "validation/official-shot-sequence"
INPUT = BASE / "norway-end2-event-gated-source-video-boards-first.json"
OFFICIAL = BASE / "pwg2022-canada-norway-official-boards.json"
OUTPUT = BASE / "norway-end2-event-gated-video-board-first-score.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def rank(comparison):
    return (
        comparison["matched_count"],
        -len(comparison["unmatched_video"]) - len(comparison["unmatched_official"]),
    )


def build():
    scan = json.loads(INPUT.read_text())
    official = json.loads(OFFICIAL.read_text())
    if scan["source_video_sha256"] != official["source_video_sha256"] or scan["shot_count"] != 16:
        raise ValueError("Norway source or shot count changed")
    end = official["ends"][1]
    if end["end"] != 2 or len(end["shots"]) != 16:
        raise ValueError("Official end-two shot order changed")
    rows = []
    for i, (observation, shot) in enumerate(zip(scan["rows"], end["shots"])):
        if (
            observation["shot_order_in_end"] != i + 1
            or observation["counter_id"] != f"B{i + 16:02}"
            or shot["official_shot_id"].split("-S")[-1] != f"{i + 1:02}"
        ):
            raise ValueError("Video/official shot order mismatch")
        stones = observation["stable_partial_board"]
        current = compare_board_observations(
            stones, shot["stones"], official_house_center_y=shot["house_center_px"][1]
        )
        previous = end["shots"][i - 1] if i else None
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
                "counter_id": observation["counter_id"],
                "official_shot_id": shot["official_shot_id"],
                "video_stone_count": len(stones),
                "official_symbol_count": len(shot["stones"]),
                "current_comparison": current,
                "prior_comparison": previous_score,
                "current_vs_prior_cardinality": relation,
            }
        )
    observed = [r for r in rows if r["video_stone_count"]]
    return {
        "status": "first_postscore_norway_end2_event_gated_transfer_not_promoted",
        "source_only_scan_sha256": digest(INPUT),
        "official_diagrams_sha256": digest(OFFICIAL),
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "shot_count": len(rows),
        "shots_with_video_board": len(observed),
        "video_stone_count": sum(r["video_stone_count"] for r in observed),
        "matched_stone_count": sum(r["current_comparison"]["matched_count"] for r in observed),
        "complete_board_match_count": sum(
            r["video_stone_count"]
            == r["official_symbol_count"]
            == r["current_comparison"]["matched_count"]
            for r in observed
        ),
        "prior_better_count": sum(
            r["current_vs_prior_cardinality"] == "prior_better" for r in observed
        ),
        "current_better_count": sum(
            r["current_vs_prior_cardinality"] == "current_better" for r in observed
        ),
        "tied_count": sum(r["current_vs_prior_cardinality"] == "tied" for r in observed),
        "rows": rows,
        "limitations": [
            "Only one counter-anchored end of a separate match was tested.",
            "Provisional event-window ends are not measured settle times.",
            "Official comparison does not make the video observations complete or metric.",
        ],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first Norway gated transfer score")
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
