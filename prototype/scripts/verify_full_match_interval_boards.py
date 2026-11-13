"""Compare conditional partial-board outputs on the full/interval overlap."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage1-audit", type=Path, required=True)
    p.add_argument("--full-boards", type=Path, required=True)
    p.add_argument("--interval-boards", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Board reconciliation already exists")
    audit = json.loads(a.stage1_audit.read_text())
    full = json.loads(a.full_boards.read_text())
    interval = json.loads(a.interval_boards.read_text())
    full_rows = {row["candidate_id"]: row for row in full["rows"]}
    interval_rows = {row["candidate_id"]: row for row in interval["rows"]}
    if len(full_rows) != len(full["rows"]) or len(interval_rows) != len(interval["rows"]):
        raise ValueError("Duplicate board ID")
    rows = []
    for pair in audit["interval_reconciliation"]["candidate_id_pairs"]:
        full_id, interval_id = pair["full_id"], pair["interval_id"]
        if (full_id in full_rows) != (interval_id in interval_rows):
            raise ValueError(f"Board coverage differs at {full_id}")
        if full_id not in full_rows:
            continue
        current, frozen = full_rows[full_id], interval_rows[interval_id]
        rows.append(
            {
                "full_id": full_id,
                "interval_id": interval_id,
                "same_status": current["board"]["status"] == frozen["board"]["status"],
                "full_status": current["board"]["status"],
                "interval_status": frozen["board"]["status"],
                "same_stone_count": len(current["board"]["stones"])
                == len(frozen["board"]["stones"]),
                "full_stone_count": len(current["board"]["stones"]),
                "interval_stone_count": len(frozen["board"]["stones"]),
                "same_tail_bounds": current["tail"] == frozen["tail"],
                "full_tail": current["tail"],
                "interval_tail": frozen["tail"],
            }
        )
    result = {
        "status": "postscore_conditional_partial_board_overlap_audit",
        "input_sha256": {
            "stage1_audit": file_sha256(a.stage1_audit),
            "full_boards": file_sha256(a.full_boards),
            "interval_boards": file_sha256(a.interval_boards),
        },
        "runner_sha256": file_sha256(Path(__file__)),
        "matched_board_candidates": len(rows),
        "same_board_status_count": sum(row["same_status"] for row in rows),
        "same_stone_count_count": sum(row["same_stone_count"] for row in rows),
        "same_tail_bounds_count": sum(row["same_tail_bounds"] for row in rows),
        "rows": rows,
        "limitations": [
            "Matching status and stone counts do not establish matching stone identities or positions.",
            "These are conditional camera-local proposals; neither run has independently verified metric accuracy or complete board state.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        len(rows),
        "boards;",
        result["same_board_status_count"],
        "same status;",
        result["same_stone_count_count"],
        "same stone count",
    )


if __name__ == "__main__":
    main()
