"""Export conservative official-diagram changes for the new transfer match."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_board_transitions import build_transitions  # noqa: E402

SOURCE = ROOT / "validation/official-shot-sequence/pwg2022-korea-china-official-boards.json"
TARGET = ROOT / "validation/official-shot-sequence/korea-china-official-board-transitions.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if TARGET.exists():
        raise SystemExit("Official transition output already exists")
    source = json.loads(SOURCE.read_text())
    rows = build_transitions(source["ends"])
    if len(rows) != 96 or len({row["official_shot_id"] for row in rows}) != 96:
        raise ValueError("Expected 96 distinct official shots")
    summary = Counter()
    for row in rows:
        summary["coordinate_stable_pairs"] += len(row["coordinate_stable_pairs"])
        summary["unresolved_previous_symbols"] += len(row["unresolved_previous_symbol_indices"])
        summary["unresolved_current_symbols"] += len(row["unresolved_current_symbol_indices"])
        summary["shots_with_unresolved_symbols"] += bool(
            row["unresolved_previous_symbol_indices"] or row["unresolved_current_symbol_indices"])
        summary["shots_with_review_flags"] += bool(row["diagram_review_flags"])
    result = {
        "status": "official_pdf_diagram_coordinate_changes_not_physical_stone_tracks",
        "official_board_source_sha256": digest(SOURCE),
        "matching_code_sha256": digest(ROOT / "prototype/official_board_transitions.py"),
        "runner_sha256": digest(Path(__file__)),
        "coordinate_tolerance_house_radii": 0.05,
        "shot_count": len(rows),
        "summary": dict(summary),
        "transitions": rows,
        "limitations": [
            "Official diagrams cover a bounded rink area and provide no video throw times.",
            "A coordinate-stable symbol pair is not a verified physical stone identity.",
            "Unresolved symbols may have moved, entered or exited the diagram, or been parsed incorrectly.",
        ],
    }
    TARGET.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"shot_count": len(rows), "summary": dict(summary)}, indent=2))


if __name__ == "__main__":
    main()
