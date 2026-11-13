"""Score frozen event-gated video boards after source-only extraction."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations

BASE = ROOT / "validation/official-shot-sequence"
SCAN = BASE / "china-full-match-event-gated-source-video-boards-first.json"
ALIGN = BASE / "pwg2022-official-counter-alignment.json"
DIAGRAMS = BASE / "pwg2022-official-board-diagrams.json"
OUTPUT = BASE / "china-full-match-event-gated-video-board-first-score.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def rank(comparison):
    # Small localization differences between unchanged boards do not identify
    # which shot's board was filmed. Compare only match cardinalities.
    return (
        comparison["matched_count"],
        -len(comparison["unmatched_video"]) - len(comparison["unmatched_official"]),
    )


def build():
    scan = json.loads(SCAN.read_text())
    alignment = json.loads(ALIGN.read_text())
    diagrams = json.loads(DIAGRAMS.read_text())
    game = next(g for g in alignment["games"] if g["official_game_code"] == "PREL000102")
    dg = next(g for g in diagrams["games"] if g["official_game_code"] == "PREL000102")
    if scan["source_video_sha256"] != dg["source_video_sha256"]:
        raise ValueError("Source-video provenance mismatch")
    counters = {r["counter_id"]: r for r in game["counter_rows"]}
    shots = {s["official_shot_id"]: s for end in dg["ends"] for s in end["shots"]}
    prior = {
        shot["official_shot_id"]: end["shots"][i - 1] if i else None
        for end in dg["ends"]
        for i, shot in enumerate(end["shots"])
    }
    rows = []
    for observation in scan["rows"]:
        counter = counters[observation["counter_id"]]
        stones = observation["stable_partial_board"]
        row = {
            "counter_id": observation["counter_id"],
            "counter_status": counter["status"],
            "official_shot_id": counter["official_shot_id"],
            "video_stone_count": len(stones),
            "observation_interval_s": observation["observation_interval_s"],
        }
        if counter["status"] not in (
            "unique_colour_concordant",
            "unique_colour_concordant_amid_duplicate",
        ):
            row["status"] = "withheld_ambiguous_counter"
            rows.append(row)
            continue
        current = shots[counter["official_shot_id"]]
        current_score = compare_board_observations(
            stones, current["stones"], official_house_center_y=current["house_center_px"][1]
        )
        previous = prior[current["official_shot_id"]]
        previous_score = (
            compare_board_observations(
                stones, previous["stones"], official_house_center_y=previous["house_center_px"][1]
            )
            if previous
            else None
        )
        relation = (
            "prior_better"
            if previous_score and rank(previous_score) > rank(current_score)
            else "current_better"
            if previous_score and rank(current_score) > rank(previous_score)
            else "tied"
            if previous_score
            else "no_prior_shot_in_end"
        )
        row.update(
            {
                "status": "counter_order_proxy_comparison",
                "official_symbol_count": len(current["stones"]),
                "current_comparison": current_score,
                "prior_official_shot_id": previous["official_shot_id"] if previous else None,
                "prior_comparison": previous_score,
                "current_vs_prior_cardinality": relation,
            }
        )
        rows.append(row)
    scored = [
        r
        for r in rows
        if r["status"] == "counter_order_proxy_comparison" and r["video_stone_count"]
    ]
    return {
        "status": "first_postscore_event_gated_board_comparison_not_promoted",
        "source_only_scan_sha256": digest(SCAN),
        "counter_alignment_sha256": digest(ALIGN),
        "official_diagrams_sha256": digest(DIAGRAMS),
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "counter_interval_count": len(rows),
        "scored_rows_with_video_board": len(scored),
        "scored_video_stone_count": sum(r["video_stone_count"] for r in scored),
        "current_matched_stone_count": sum(
            r["current_comparison"]["matched_count"] for r in scored
        ),
        "current_complete_board_count": sum(
            r["video_stone_count"]
            == r["official_symbol_count"]
            == r["current_comparison"]["matched_count"]
            for r in scored
        ),
        "prior_better_count": sum(
            r["current_vs_prior_cardinality"] == "prior_better" for r in scored
        ),
        "current_better_count": sum(
            r["current_vs_prior_cardinality"] == "current_better" for r in scored
        ),
        "tied_count": sum(r["current_vs_prior_cardinality"] == "tied" for r in scored),
        "no_prior_count": sum(
            r["current_vs_prior_cardinality"] == "no_prior_shot_in_end" for r in scored
        ),
        "rows": rows,
        "limitations": [
            "Postscore PDF comparison is not independent throw-time validation.",
            "The event gate uses a provisional delivery-window end, not measured settling.",
            "A match to an official diagram does not prove board completeness from video alone.",
        ],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first event-gated board score")
    result = build()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "counter_interval_count",
                "scored_rows_with_video_board",
                "scored_video_stone_count",
                "current_matched_stone_count",
                "current_complete_board_count",
                "prior_better_count",
                "current_better_count",
                "tied_count",
                "no_prior_count",
            )
        }
    )


if __name__ == "__main__":
    main()
