"""Merge ordinary and exact-duplicate-aware quiet-tail observations."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("proposals", "base", "dedup", "dedup_manifest", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Merged pre-split board output already exists")
    proposals, base, dedup, manifest = (
        json.loads(getattr(args, key).read_text())
        for key in ("proposals", "base", "dedup", "dedup_manifest")
    )
    proposal_ids = [row["candidate_id"] for row in proposals["proposals"]]
    base_ids = [row["candidate_id"] for row in base["rows"]]
    if proposal_ids != base_ids or len(dedup["rows"]) != 1:
        parser.error("Board target coverage differs")
    target = dedup["rows"][0]
    pid = target["candidate_id"]
    proposal = next((row for row in proposals["proposals"] if row["candidate_id"] == pid), None)
    if (
        proposal is None
        or manifest["target_candidate_id"] != pid
        or sorted(proposal["duplicate_candidate_ids"]) != manifest["excluded_exact_duplicate_ids"]
        or manifest["output_sha256"]["candidates"] != dedup["candidates_sha256"]
        or manifest["output_sha256"]["motion"] != dedup["motion_sha256"]
        or manifest["output_sha256"]["screen"] != dedup["screen_sha256"]
        or base["source_sha256"] != dedup["source_sha256"]
    ):
        parser.error("Deduplicated tail provenance differs")
    original = next(row for row in base["rows"] if row["candidate_id"] == pid)
    if (
        original["crossing_time_s"] != target["crossing_time_s"]
        or original["receiving_path_last_observed_s"] != target["receiving_path_last_observed_s"]
        or original["receiving_view"] != target["receiving_view"]
    ):
        parser.error("Deduplicated tail changed the target motion")
    rows = [
        {
            **(target if row["candidate_id"] == pid else row),
            "tail_clock_excluded_exact_duplicate_ids": proposal["duplicate_candidate_ids"]
            if row["candidate_id"] == pid
            else [],
        }
        for row in base["rows"]
    ]
    result = {
        "status": "partial_board_observations_after_pre_split_review_targets_not_game_states",
        "source_id": base["source_id"],
        "source_sha256": base["source_sha256"],
        "high_resolution_source_sha256": base["high_resolution_source_sha256"],
        "proposals_sha256": file_sha256(args.proposals),
        "base_board_sha256": file_sha256(args.base),
        "deduplicated_board_sha256": file_sha256(args.dedup),
        "dedup_manifest_sha256": file_sha256(args.dedup_manifest),
        "runner_sha256": file_sha256(Path(__file__)),
        "board_status_counts": dict(Counter(row["board"]["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "These boards are stable partial view-local observations after review targets, not accepted throws or complete game states.",
            "S131's tail clock excludes only the exact-prefix duplicate S132; the raw 116-candidate timeline and event screens remain unchanged.",
            "Board stones are not assigned to delivered or contacted physical stone identities.",
            "Quiet-tail sampling does not verify exact settle time, metric accuracy, score or simulation readiness.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["board_status_counts"])


if __name__ == "__main__":
    main()
