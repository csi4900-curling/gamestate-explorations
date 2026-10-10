#!/usr/bin/env python3
"""Export source-independent diagram changes for the Canada–Norway match."""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_board_transitions import build_transitions  # noqa: E402

SOURCE = ROOT / "validation/official-shot-sequence/pwg2022-canada-norway-official-boards.json"
TARGET = ROOT / "validation/official-shot-sequence/norway-official-board-transitions.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = json.loads(SOURCE.read_text())
    rows = build_transitions(source["ends"])
    if len(rows) != 128 or len({row["official_shot_id"] for row in rows}) != 128:
        raise ValueError("Expected 128 distinct official shots")
    counts = Counter()
    for row in rows:
        counts["coordinate_stable_pairs"] += len(row["coordinate_stable_pairs"])
        counts["unresolved_previous_symbols"] += len(row["unresolved_previous_symbol_indices"])
        counts["unresolved_current_symbols"] += len(row["unresolved_current_symbol_indices"])
        counts["shots_with_any_unresolved_symbol"] += bool(
            row["unresolved_previous_symbol_indices"] or row["unresolved_current_symbol_indices"]
        )
        counts["shots_with_review_flags"] += bool(row["diagram_review_flags"])
        counts["shots_with_ambiguous_close_pair"] += row["ambiguous_close_pair_count"] > 0
    result = {
        "status": "official_pdf_diagram_coordinate_changes_not_physical_stone_tracks",
        "official_board_source_sha256": sha256(SOURCE),
        "matching_code_sha256": sha256(ROOT / "prototype/official_board_transitions.py"),
        "runner_sha256": sha256(Path(__file__)),
        "coordinate_tolerance_house_radii": 0.05,
        "shot_count": len(rows),
        "summary": dict(counts),
        "transitions": rows,
        "limitations": [
            "The diagram shows only a bounded area, not the full sheet.",
            "A coordinate-stable symbol pair is not verified physical stone identity.",
            "Unresolved symbols may have moved, exited or entered the diagram, or been extracted incorrectly.",
            "No release time, physical trajectory, stone spin, or simulation dynamics are inferred.",
        ],
    }
    TARGET.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"output": str(TARGET), "shot_count": len(rows), "summary": result["summary"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
