"""Compare full-video candidate totals with independent official shot counts."""

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-candidate-count-audit.json"
CANDIDATES = {
    "PREL000101": ROOT
    / "validation/curlobserver-learned-probe/swiss-full-transfer/candidate-event-ledger.json",
    "PREL000102": ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/candidate-throw-event-ledger-v1.json",
    "PREL000103": ROOT
    / "validation/curlobserver-learned-probe/slovakia-full-transfer/candidate-event-ledger.json",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first official comparison")
    reference = json.loads(REFERENCE.read_text())
    games = []
    for official in reference["games"]:
        path = CANDIDATES[official["official_game_code"]]
        prediction = json.loads(path.read_text())
        if prediction["source_sha256"] != official["source_video_sha256"]:
            raise ValueError(f"Video hash mismatch for {path}")
        count = len(prediction["events"])
        colours = Counter(row.get("colour") for row in prediction["events"])
        games.append(
            {
                "official_game_code": official["official_game_code"],
                "teams": official["teams"],
                "source_video_sha256": official["source_video_sha256"],
                "candidate_ledger_path": str(path.relative_to(ROOT)),
                "candidate_ledger_sha256": digest(path),
                "candidate_source_interval_s": prediction["source_interval_s"],
                "official_shot_count": official["official_shot_count"],
                "candidate_count": count,
                "candidate_minus_official": count - official["official_shot_count"],
                "candidate_colour_counts": {
                    "red": colours["red"],
                    "yellow": colours["yellow"],
                    "unknown": colours[None],
                },
                "official_end_shot_counts": [row["shot_count"] for row in official["ends"]],
            }
        )
    result = {
        "status": "independent_official_count_constraint_not_timestamped_f1",
        "official_reference_path": str(REFERENCE.relative_to(ROOT)),
        "official_reference_sha256": digest(REFERENCE),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "Official shot order and counts have no video timestamps, so candidate-to-shot matching is unproven.",
            "An excess candidate can be a false event, duplicate, wrong match boundary or other off-play detection; misses can coexist with extras.",
            "These counts cannot establish precision, recall or F1, but they expose discrepancies a high-F1 detector must resolve.",
            "The candidate ledgers are development outputs, not frozen independent predictions against this newly extracted reference.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for game in games:
        print(
            game["official_game_code"],
            game["official_shot_count"],
            game["candidate_count"],
            game["candidate_minus_official"],
        )


if __name__ == "__main__":
    main()
