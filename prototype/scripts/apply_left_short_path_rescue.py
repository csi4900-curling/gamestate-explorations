"""Postscore uniform left-view short-path proposal rescue."""

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--hold", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Short-path rescue already exists")
    base = json.loads(a.base.read_text())
    hold = json.loads(a.hold.read_text())
    if base["hold_sha256"] != file_sha256(a.hold):
        p.error("Base motion and held observations do not chain")
    base_ids = [row["candidate_id"] for row in base["rows"]]
    held_ids = [row["candidate_id"] for row in hold["rows"]]
    if base_ids != held_ids or len(base_ids) != len(set(base_ids)):
        p.error("Candidate IDs or order differ")
    rows, decisions = [], []
    for original, observations in zip(base["rows"], hold["rows"]):
        row = deepcopy(original)
        pid = row["candidate_id"]
        if (
            row["colour"] != observations["colour"]
            or row["receiving_view"] != observations["receiving_view"]
        ):
            raise ValueError(f"Candidate observations differ for {pid}")
        if row["receiving_view"] != "left":
            status = "right_view_preserved"
        elif row["selection"].get("path"):
            status = "baseline_selected_path_preserved"
        else:
            trial = select_far_entry_motion_path(
                observations["samples"],
                row["colour"],
                view="left",
                max_gap_s=0.6,
                entry_y_threshold_m=-4.5,
                forward_direction=1,
                min_samples=4,
                max_forward_speed_change_m_s=2.0,
                min_forward_step_m=0.15,
                min_travel_m=1.0,
            )
            if trial["status"] == "provisional_unique_far_entry_motion_path":
                row["selection"] = trial
                status = "unique_short_path_proposal"
            else:
                status = "short_path_rescue_abstained"
        row["short_path_rescue_status"] = status
        rows.append(row)
        decisions.append({"candidate_id": pid, "status": status})
    result = {
        **base,
        "status": "postscore_exposed_left_short_path_rescue_not_transfer_validation",
        "base_motion_sha256": file_sha256(a.base),
        "short_path_hold_sha256": file_sha256(a.hold),
        "short_path_selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "short_path_runner_sha256": file_sha256(Path(__file__)),
        "short_path_parameters": {
            "receiving_view": "left",
            "sample_period_s": 0.5,
            "max_gap_s": 0.6,
            "entry_y_threshold_m": -4.5,
            "forward_direction": 1,
            "min_samples": 4,
            "max_forward_speed_change_m_s": 2.0,
            "min_forward_step_m": 0.15,
            "min_travel_m": 1.0,
        },
        "short_path_status_counts": dict(Counter(d["status"] for d in decisions)),
        "short_path_decisions": decisions,
        "rows": rows,
        "limitations": base["limitations"]
        + [
            "This permissive left-view proposal rule was selected after inspecting failures in this recording.",
            "A one-metre candidate path is not a verified throw and still requires appearance screening and independent labels.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["short_path_status_counts"])
    print([d["candidate_id"] for d in decisions if d["status"] == "unique_short_path_proposal"])


if __name__ == "__main__":
    main()
