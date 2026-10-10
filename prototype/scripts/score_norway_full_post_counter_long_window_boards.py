"""Postscore longer-window Norway boards as a sensitivity diagnostic."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations


BASE = ROOT / "validation/official-shot-sequence"
SCAN = BASE / "norway-full-candidate-post-counter-long-window-boards-v4.json"
SLOTS = BASE / "norway-full-match-official-counter-slot-scaffold-first.json"
OFFICIAL = BASE / "pwg2022-canada-norway-official-boards.json"
OUTPUT = BASE / "norway-full-post-counter-long-window-board-postscore-v4.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def rank(comparison):
    return (
        comparison["matched_count"],
        -len(comparison["unmatched_video"]) - len(comparison["unmatched_official"]),
    )


def main():
    if OUTPUT.exists():
        raise SystemExit("V4 long-window postscore already exists")
    scan = json.loads(SCAN.read_text())
    scaffold = json.loads(SLOTS.read_text())
    official = json.loads(OFFICIAL.read_text())
    if scan["source_video_sha256"] != official["source_video_sha256"]:
        raise SystemExit("Source-video hashes disagree")
    if scaffold["input_sha256"]["candidate_ledger"] != scan["candidate_ledger_sha256"]:
        raise SystemExit("Candidate-ledger hashes disagree")
    by_candidate = {row["shot_id"]: row for row in scan["rows"]}
    if len(by_candidate) != len(scan["rows"]):
        raise SystemExit("Duplicate candidate shot IDs")
    official_by_id = {
        shot["official_shot_id"]: (end["end"], shot)
        for end in official["ends"]
        for shot in end["shots"]
    }
    group_rows = []
    for slot in scaffold["slots"]:
        if slot["counter_id"] is None or slot["video_candidate_shot_id"] is None:
            continue
        candidate = by_candidate[slot["video_candidate_shot_id"]]
        if candidate["counter_id"] != slot["counter_id"]:
            raise SystemExit("Candidate/counter link changed")
        if candidate["counter_crossing_time_s"] != slot["counter_crossing_time_s"]:
            raise SystemExit("Counter timestamp changed")
        end, shot = official_by_id[slot["official_shot_id"]]
        if end != slot["end"]:
            raise SystemExit("Official end mismatch")
        previous = (
            official["ends"][end - 1]["shots"][slot["shot_number"] - 2]
            if slot["shot_number"] > 1
            else None
        )
        for group in candidate["camera_shot_boards"]:
            stones = group["stable_image_relative_stones"]
            side = group["detected_delivery_side"]
            if not stones or side not in ("top", "bottom"):
                continue
            if group["observation_interval_s"][0] < slot["counter_crossing_time_s"] + 2.0:
                raise SystemExit("Scored group includes pre-counter observations")
            sign = 1 if side == "top" else -1
            video = [
                {
                    "colour": stone["colour"],
                    "canonical_lateral_house_radii": round(
                        sign * stone["image_house_radius_coordinates"][0], 4
                    ),
                    "longitudinal_house_radii": round(
                        sign * stone["image_house_radius_coordinates"][1], 4
                    ),
                }
                for stone in stones
            ]
            current = compare_board_observations(
                video, shot["stones"], official_house_center_y=shot["house_center_px"][1]
            )
            prior = (
                compare_board_observations(
                    video,
                    previous["stones"],
                    official_house_center_y=previous["house_center_px"][1],
                )
                if previous
                else None
            )
            relation = (
                "prior_better"
                if prior and rank(prior) > rank(current)
                else "current_better"
                if prior and rank(current) > rank(prior)
                else "tied"
                if prior
                else "no_prior_shot_in_end"
            )
            group_rows.append(
                {
                    "official_shot_id": slot["official_shot_id"],
                    "counter_id": slot["counter_id"],
                    "video_candidate_shot_id": slot["video_candidate_shot_id"],
                    "post_camera_shot_id": group["camera_shot_id"],
                    "source_detected_delivery_side": side,
                    "accepted_frame_count": group["accepted_frame_count"],
                    "source_observation_interval_s": group["observation_interval_s"],
                    "current_comparison": current,
                    "prior_comparison": prior,
                    "current_vs_prior_cardinality": relation,
                    "complete_diagram_symbol_match": (
                        current["video_stone_count"]
                        == current["official_symbol_count"]
                        == current["matched_count"]
                    ),
                }
            )
    result = {
        "status": "retrospective_long_window_postscore_sensitivity_not_event_validation",
        "input_sha256": {
            "source_scan": digest(SCAN),
            "slot_scaffold": digest(SLOTS),
            "official_boards": digest(OFFICIAL),
        },
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "counter_linked_candidate_count": sum(
            row["counter_id"] is not None for row in scan["rows"]
        ),
        "scored_candidate_count": len({row["video_candidate_shot_id"] for row in group_rows}),
        "scored_camera_group_count": len(group_rows),
        "video_stone_count": sum(
            row["current_comparison"]["video_stone_count"] for row in group_rows
        ),
        "matched_stone_count": sum(
            row["current_comparison"]["matched_count"] for row in group_rows
        ),
        "complete_diagram_symbol_match_group_count": sum(
            row["complete_diagram_symbol_match"] for row in group_rows
        ),
        "current_better_group_count": sum(
            row["current_vs_prior_cardinality"] == "current_better" for row in group_rows
        ),
        "prior_better_group_count": sum(
            row["current_vs_prior_cardinality"] == "prior_better" for row in group_rows
        ),
        "tied_group_count": sum(
            row["current_vs_prior_cardinality"] == "tied" for row in group_rows
        ),
        "groups": group_rows,
        "limitations": [
            "Only counter-linked candidates with source-known orientation and stable source stones are scored.",
            "Each scored group uses only source samples at least 2 s after its delayed counter decrement.",
            "The longer horizon can include an unlisted true throw or end transition before the next candidate.",
            "Multiple camera groups for a candidate are scored separately; no best group is chosen from official results.",
            "Counter alignment is delayed proxy evidence, not independently verified physical throw identity.",
            "Stone matching within 0.25 house radii is diagram agreement, not metric ground-truth accuracy.",
            "This postscore is retrospective on a development recording; no held-out F1 or complete game-state accuracy follows.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "counter_linked_candidate_count",
                "scored_candidate_count",
                "scored_camera_group_count",
                "video_stone_count",
                "matched_stone_count",
                "complete_diagram_symbol_match_group_count",
                "current_better_group_count",
                "prior_better_group_count",
                "tied_group_count",
            )
        }
    )


if __name__ == "__main__":
    main()
