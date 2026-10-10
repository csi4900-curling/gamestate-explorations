"""Link adjacent source-video board observations before diagram comparison."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from partial_board_transition import compare_partial_boards

BASE = ROOT / "validation/official-shot-sequence"
INPUT = BASE / "china-end2-adjacent-video-boards-first.json"
OUTPUT = BASE / "china-end2-partial-board-transitions-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first transition result")
    source = json.loads(INPUT.read_text())
    if source["selected_shot_numbers"] != [10, 11, 12, 13, 14]:
        raise ValueError("Predeclared adjacent shots changed")
    rows = source["rows"]
    if len(rows) != 5:
        raise ValueError("Expected five adjacent shot windows")
    transitions = []
    for before, after in zip(rows, rows[1:]):
        if not before["stable_partial_board"] or not after["stable_partial_board"]:
            transitions.append({"before_shot_id": before["shot_id"],
                                "after_shot_id": after["shot_id"],
                                "status": "one_or_both_video_boards_missing",
                                "simulation_ready": False})
            continue
        transition = compare_partial_boards(before, after)
        transitions.append({"status": "local_partial_board_comparison",
                            **transition})
    output = {
        "status": "first_source_only_partial_board_transition_evidence",
        "source_sha256": source["source_sha256"],
        "board_scan_sha256": digest(INPUT),
        "transition_code_sha256": digest(ROOT / "prototype/partial_board_transition.py"),
        "runner_sha256": digest(Path(__file__)),
        "selected_shot_numbers": source["selected_shot_numbers"],
        "transition_count": len(transitions),
        "observed_transition_count": sum(
            row["status"] == "local_partial_board_comparison" for row in transitions),
        "transitions": transitions,
        "limitations": [
            "Only locally repeated same-colour positions are associated across partial boards.",
            "Newly/no-longer observed does not establish physical addition or removal.",
            "No official diagram positions enter the source-only transition decisions.",
            "No exact release, collision, settle time, metric calibration or trajectory is inferred.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    for row in transitions:
        print(row["before_shot_id"], "->", row["after_shot_id"], row["status"],
              len(row.get("locally_retained", [])), row.get("newly_observed"),
              row.get("no_longer_observed"))


if __name__ == "__main__":
    main()
