"""Constrain full-video candidates by official order without forcing ties."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_candidate_sequence import align_official_sequence

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
ALIGNMENT = ROOT / "validation/official-shot-sequence/pwg2022-official-counter-alignment.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-official-candidate-sequence-audit.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postcut-colours", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output exists; preserve first candidate sequence audit")
    reference = json.loads(REFERENCE.read_text())
    alignment = json.loads(ALIGNMENT.read_text())
    augmentation = json.loads(args.postcut_colours.read_text()) if args.postcut_colours else None
    augmentation_games = (
        {row["official_game_code_for_join_only"]: row for row in augmentation["games"]}
        if augmentation
        else {}
    )
    if alignment["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Official reference and alignment differ")
    aligned = {row["official_game_code"]: row for row in alignment["games"]}
    games = []
    for game in reference["games"]:
        info = aligned[game["official_game_code"]]
        candidate_path = ROOT / info["candidate_ledger_path"]
        if digest(candidate_path) != info["candidate_ledger_sha256"]:
            raise ValueError("Candidate ledger differs from counter alignment")
        candidates = json.loads(candidate_path.read_text())["events"]
        augmented_count = 0
        if augmentation:
            augmented = augmentation_games[game["official_game_code"]]
            if augmented["candidate_ledger_sha256"] != digest(candidate_path):
                raise ValueError("Post-cut sidecar uses a different candidate ledger")
            sidecar_by_id = {row["candidate_id"]: row for row in augmented["rows"]}
            candidates = [
                dict(row, colour=sidecar_by_id[row["candidate_id"]]["postcut_colour"])
                if row["candidate_id"] in sidecar_by_id
                and sidecar_by_id[row["candidate_id"]]["postcut_colour"]
                else row
                for row in candidates
            ]
            augmented_count = sum(
                row["candidate_id"] in sidecar_by_id
                and bool(sidecar_by_id[row["candidate_id"]]["postcut_colour"])
                for row in candidates
            )
        by_candidate = {row["candidate_id"]: row for row in candidates}
        shot_to_end = {
            shot["official_shot_id"]: end["end"] for end in game["ends"] for shot in end["shots"]
        }
        fixed_by_end = defaultdict(dict)
        anchor_times = defaultdict(list)
        for link in info["candidate_links"]:
            shot_id = link["official_shot_id"]
            if shot_id is None:
                continue
            end = shot_to_end[shot_id]
            fixed_by_end[end][link["candidate_id"]] = shot_id
            anchor_times[end].append(by_candidate[link["candidate_id"]]["observation_anchor_s"])
        ends = [end["end"] for end in game["ends"]]
        if set(anchor_times) != set(ends):
            raise ValueError("Every end needs a clean candidate anchor")
        boundaries = [
            (max(anchor_times[left]) + min(anchor_times[right])) / 2
            for left, right in zip(ends, ends[1:])
        ]
        if any(right <= left for left, right in zip(boundaries, boundaries[1:])):
            raise ValueError("Inferred end partitions overlap or reverse")
        grouped = defaultdict(list)
        for candidate in candidates:
            end = 1 + sum(candidate["observation_anchor_s"] > boundary for boundary in boundaries)
            grouped[end].append(candidate)
        end_rows = []
        for end in game["ends"]:
            end_number = end["end"]
            ordered = sorted(
                grouped[end_number],
                key=lambda row: (row["observation_anchor_s"], row["candidate_id"]),
            )
            if not set(fixed_by_end[end_number]).issubset({row["candidate_id"] for row in ordered}):
                raise ValueError("Clean anchor candidate fell in a different inferred end")
            result = align_official_sequence(
                ordered, end["shots"], game["team_handle_colours"], fixed_by_end[end_number]
            )
            candidate_statuses = Counter(row["status"] for row in result["candidate_rows"])
            official_statuses = Counter(row["status"] for row in result["official_rows"])
            end_rows.append(
                {
                    "end": end_number,
                    "candidate_count": len(ordered),
                    "official_shot_count": end["shot_count"],
                    "clean_fixed_link_count": len(fixed_by_end[end_number]),
                    "minimum_edit_cost": result["minimum_cost"],
                    "equally_optimal_alignment_count": result["optimal_path_count"],
                    "candidate_status_counts": dict(candidate_statuses),
                    "official_status_counts": dict(official_statuses),
                    "candidate_rows": result["candidate_rows"],
                    "official_rows": result["official_rows"],
                }
            )
        all_candidate_statuses = Counter(
            status
            for row in end_rows
            for status, count in row["candidate_status_counts"].items()
            for _ in range(count)
        )
        all_official_statuses = Counter(
            status
            for row in end_rows
            for status, count in row["official_status_counts"].items()
            for _ in range(count)
        )
        games.append(
            {
                "official_game_code": game["official_game_code"],
                "candidate_ledger_path": info["candidate_ledger_path"],
                "candidate_ledger_sha256": info["candidate_ledger_sha256"],
                "end_partition_midpoints_s": boundaries,
                "candidate_count": len(candidates),
                "official_shot_count": game["official_shot_count"],
                "clean_fixed_link_count": sum(len(x) for x in fixed_by_end.values()),
                "postcut_resolved_colour_count": augmented_count,
                "candidate_status_counts": dict(all_candidate_statuses),
                "official_status_counts": dict(all_official_statuses),
                "ends": end_rows,
            }
        )
    output = {
        "status": "official_constrained_candidate_sequence_diagnostic_not_detector_f1",
        "official_reference_sha256": digest(REFERENCE),
        "counter_alignment_sha256": digest(ALIGNMENT),
        "postcut_colour_sidecar_path": (
            str(args.postcut_colours.resolve().relative_to(ROOT)) if args.postcut_colours else None
        ),
        "postcut_colour_sidecar_sha256": (
            digest(args.postcut_colours) if args.postcut_colours else None
        ),
        "sequence_code_sha256": digest(ROOT / "prototype/official_candidate_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        "match_costs": {
            "skip_candidate": 2,
            "skip_official_shot": 2,
            "matching_colour": 0,
            "unknown_colour": 1,
            "wrong_colour": 5,
        },
        "games": games,
        "limitations": [
            "Official shot order and colour are used in this audit; this is not a deployable video-only detector.",
            "A uniquely optimal assignment depends on the stated edit costs and does not prove physical throw identity or timing.",
            "A candidate skipped in every optimum is a review priority, not an independently verified false positive.",
            "End partitions are midpoint diagnostics from clean candidate anchors, not source-reviewed physical end boundaries.",
            "The candidate ledgers are development outputs and the official pages lack video timestamps, so event precision/recall/F1 remain unmeasured.",
        ],
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    for game in games:
        print(
            game["official_game_code"],
            game["candidate_status_counts"],
            game["official_status_counts"],
        )


if __name__ == "__main__":
    main()
