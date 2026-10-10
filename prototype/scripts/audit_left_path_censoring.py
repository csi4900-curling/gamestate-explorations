"""Postscore four-case left-path window and step-threshold diagnostic."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402

IDS = ("S125", "S127", "S133", "S137")
STEPS = (0.3, 0.2, 0.15)


def select(row, step):
    return select_far_entry_motion_path(
        row["samples"], row["colour"], view="left", max_gap_s=0.6,
        entry_y_threshold_m=-4.5, forward_direction=1,
        min_samples=4, max_forward_speed_change_m_s=2.0,
        min_forward_step_m=step, min_travel_m=2.0)


def compact(selection):
    path = selection.get("path") or []
    return {
        "status": selection["status"],
        "path_sample_count": len(path),
        "first_observation_s": selection.get("first_observation_s"),
        "last_observation_s": selection.get("last_observation_s"),
        "endpoint_displacement_m": selection.get("endpoint_displacement_m"),
        "reason": selection.get("reason"),
        "winner_count": selection.get("winner_count"),
        "shared_prefix_sample_count": selection.get("shared_prefix_sample_count"),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hold", type=Path, required=True)
    p.add_argument("--extended-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Diagnostic output already exists")
    hold = json.loads(a.hold.read_text())
    held = {row["candidate_id"]: row for row in hold["rows"]}
    rows = []
    files = {}
    for pid in IDS:
        candidate_path = a.extended_dir / f"candidate-{pid}.json"
        motion_path = a.extended_dir / f"motion-20s-{pid}.json"
        extended = json.loads(motion_path.read_text())
        candidate = json.loads(candidate_path.read_text())
        if (len(extended["rows"]) != 1 or
                extended["rows"][0]["candidate_id"] != pid or
                extended["candidates_sha256"] != file_sha256(candidate_path) or
                candidate["events"][0]["id"] != pid or
                held[pid]["colour"] != extended["rows"][0]["colour"] or
                held[pid]["receiving_view"] != "left" or
                extended["lookahead_s"] != 20 or
                extended["sample_period_s"] != 0.5 or
                extended["right_reference_anchor_time_s"] != 6525):
            raise ValueError(f"Extended source/proposal mismatch for {pid}")
        old = compact(select(held[pid], 0.3))
        if old["status"] != held[pid]["selection"]["status"]:
            raise ValueError(f"Frozen 12 s selection does not reproduce for {pid}")
        new = extended["rows"][0]
        variants = {str(step): compact(select(new, step)) for step in STEPS}
        rows.append({
            "candidate_id": pid,
            "candidate_colour": new["colour"],
            "candidate_crossing_time_s": new["crossing_time_s"],
            "sample_count_12s": len(held[pid]["samples"]),
            "sample_count_20s": len(new["samples"]),
            "direct_registered_20s": new["sample_count"] - new["registration_abstentions"],
            "original_12s_step_0.3": old,
            "extended_20s_by_minimum_step_m": variants,
        })
        files[pid] = {
            "candidate_input_sha256": file_sha256(candidate_path),
            "extended_motion_sha256": file_sha256(motion_path),
        }
    result = {
        "status": "postscore_source_selected_diagnostic_not_recall_validation",
        "hold_sha256": file_sha256(a.hold),
        "input_sha256": files,
        "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "parameters": {
            "sample_period_s": 0.5,
            "lookahead_s_original": 12.0,
            "lookahead_s_extended": 20.0,
            "min_forward_step_m": list(STEPS),
            "min_travel_m": 2.0,
            "min_samples": 4,
        },
        "rows": rows,
        "limitations": [
            "The four candidates were selected after source inspection of known screen failures.",
            "A recovered moving path does not prove a physical throw or acceptable precision.",
            "Longer windows may overlap subsequent events and must be guarded in a future full-candidate experiment.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    for row in rows:
        print(row["candidate_id"], row["original_12s_step_0.3"]["status"],
              [(step, row["extended_20s_by_minimum_step_m"][str(step)]["status"])
               for step in STEPS])


if __name__ == "__main__":
    main()
