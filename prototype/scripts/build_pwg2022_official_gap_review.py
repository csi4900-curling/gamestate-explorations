"""Build compact video-review targets for official shots lacking counter anchors."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_shot_gap_audit import build_gap_runs

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
ALIGNMENT = ROOT / "validation/official-shot-sequence/pwg2022-official-counter-alignment.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-official-gap-review.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first gap review packet")
    reference = json.loads(REFERENCE.read_text())
    alignment = json.loads(ALIGNMENT.read_text())
    if alignment["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Alignment uses a different official ledger")
    aligned_games = {game["official_game_code"]: game for game in alignment["games"]}
    games = []
    for game in reference["games"]:
        aligned = aligned_games[game["official_game_code"]]
        candidate_path = ROOT / aligned["candidate_ledger_path"]
        if digest(candidate_path) != aligned["candidate_ledger_sha256"]:
            raise ValueError("Candidate ledger changed since alignment")
        candidates = json.loads(candidate_path.read_text())["events"]
        runs = build_gap_runs(game, aligned["counter_rows"], candidates)
        uncovered = sum(len(run["official_shots"]) for run in runs)
        clean = sum(aligned["counter_status_counts"].get(status, 0) for status in
                    ("unique_colour_concordant", "unique_colour_concordant_amid_duplicate"))
        if clean + uncovered != game["official_shot_count"]:
            raise ValueError("Official-shot coverage arithmetic failed")
        games.append({
            "official_game_code": game["official_game_code"],
            "official_shot_count": game["official_shot_count"],
            "clean_counter_anchored_shot_count": clean,
            "unanchored_official_shot_count": uncovered,
            "gap_run_count": len(runs),
            "bounded_gap_run_count": sum(run["bounded_within_end"] for run in runs),
            "unanchored_by_end": dict(Counter(str(run["official_end"])
                                              for run in runs for _ in run["official_shots"])),
            "visual_candidate_triage_counts": dict(Counter(
                run["visual_candidate_triage"] for run in runs if run["bounded_within_end"])),
            "gap_runs": runs,
        })
    packet = {
        "status": "official_shot_gap_review_search_spans_not_throw_labels",
        "official_reference_path": str(REFERENCE.relative_to(ROOT)),
        "official_reference_sha256": digest(REFERENCE),
        "alignment_path": str(ALIGNMENT.relative_to(ROOT)),
        "alignment_sha256": digest(ALIGNMENT),
        "gap_code_sha256": digest(ROOT / "prototype/official_shot_gap_audit.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "Review spans are bounded by delayed broadcast counter updates, not physical releases.",
            "Unbounded first or last shots in an end have no within-end two-sided search span.",
            "Candidate intersections are detector suggestions, not independently confirmed matches.",
            "Clean counter anchoring does not itself establish a correct detector release window.",
        ],
    }
    OUTPUT.write_text(json.dumps(packet, indent=2) + "\n")
    for game in games:
        print(game["official_game_code"], game["unanchored_official_shot_count"],
              game["gap_run_count"], game["bounded_gap_run_count"])


if __name__ == "__main__":
    main()
