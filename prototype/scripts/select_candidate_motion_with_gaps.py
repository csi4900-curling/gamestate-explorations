"""Postscore audit of bounded unobserved gaps in held-registration motion paths."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hold", type=Path, required=True)
    parser.add_argument("--max-gap-s", type=float, default=4.1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Gap-selection artifact already exists")
    source = json.loads(args.hold.read_text())
    rows = []
    for row in source["rows"]:
        view = row["receiving_view"]
        kwargs = ({"view": "left", "entry_y_threshold_m": -4.5,
                   "forward_direction": 1, "min_samples": 4,
                   "max_forward_speed_change_m_s": 2.0}
                  if view == "left" else {"view": "right"})
        selection = select_far_entry_motion_path(
            row["samples"], row["colour"],
            max_gap_s=args.max_gap_s, allow_missing_samples=True,
            skip_status_required="abstained_no_stable_anchor", **kwargs)
        rows.append({"candidate_id": row["candidate_id"],
                     "colour": row["colour"],
                     "receiving_view": view,
                     "hold_selection_status": row["selection"]["status"],
                     "selection": selection})
    result = {"status": "postscore_bounded_gap_motion_development_not_continuous_identity",
              "hold_sha256": file_sha256(args.hold),
              "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
              "runner_sha256": file_sha256(__file__),
              "max_gap_s": args.max_gap_s,
              "skip_status_required": "abstained_no_stable_anchor",
              "selection_status_counts": dict(Counter(
                  row["selection"]["status"] for row in rows)),
              "rows": rows,
              "limitations": [
                  "Missing samples are not interpolated; endpoint compatibility across at most 4.1 s is only provisional identity evidence.",
                  "The gap policy was introduced after observing two Estonia misses and cannot change the frozen transfer result.",
                  "Borrowed camera transforms and motion paths lack independent metric and physical-identity validation.",
              ]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["selection_status_counts"])


if __name__ == "__main__":
    main()
