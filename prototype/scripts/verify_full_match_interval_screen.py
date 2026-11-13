"""Compare full-match screening to the frozen interval at the same raw IDs."""

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
    p.add_argument("--full-screen", type=Path, required=True)
    p.add_argument("--interval-screen", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Reconciliation already exists")
    audit = json.loads(a.stage1_audit.read_text())
    full = json.loads(a.full_screen.read_text())
    interval = json.loads(a.interval_screen.read_text())
    pairs = audit["interval_reconciliation"]["candidate_id_pairs"]
    if len(pairs) != audit["interval_reconciliation"]["matched_candidate_count"]:
        raise ValueError("Stage-one interval mapping is incomplete")
    full_decisions = {row["candidate_id"]: row for row in full["decisions"]}
    interval_decisions = {row["candidate_id"]: row for row in interval["decisions"]}
    rows = []
    for pair in pairs:
        full_id, interval_id = pair["full_id"], pair["interval_id"]
        current = full_decisions.get(full_id)
        frozen = interval_decisions.get(interval_id)
        if (current is None) != (frozen is None):
            raise ValueError(f"Corridor coverage differs at {full_id}")
        rows.append(
            {
                "full_id": full_id,
                "interval_id": interval_id,
                "full_status": current["status"] if current else None,
                "interval_status": frozen["status"] if frozen else None,
                "full_accepted": current["accepted"] if current else None,
                "interval_accepted": frozen["accepted"] if frozen else None,
                "same_status": current["status"] == frozen["status"] if current else True,
                "same_acceptance": current["accepted"] == frozen["accepted"] if current else True,
            }
        )
    result = {
        "status": "postscore_full_vs_frozen_interval_decision_reconciliation",
        "input_sha256": {
            "stage1_audit": file_sha256(a.stage1_audit),
            "full_screen": file_sha256(a.full_screen),
            "interval_screen": file_sha256(a.interval_screen),
        },
        "runner_sha256": file_sha256(Path(__file__)),
        "matched_raw_candidates": len(rows),
        "matched_corridor_candidates": sum(row["full_status"] is not None for row in rows),
        "matched_withheld_candidates": sum(row["full_status"] is None for row in rows),
        "all_statuses_match": all(row["same_status"] for row in rows),
        "all_acceptance_matches": all(row["same_acceptance"] for row in rows),
        "rows": rows,
        "limitations": [
            "Decision agreement is an internal consistency check on overlapping source footage, not precision or recall.",
            "The full-match result uses a different recording-wide right-camera anchor.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        result["matched_raw_candidates"],
        "raw;",
        result["matched_corridor_candidates"],
        "corridor;",
        result["all_statuses_match"],
        "same statuses",
    )


if __name__ == "__main__":
    main()
