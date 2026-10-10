"""Postscore diagnostic: rerun held-sample path selection with later entry gates."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402
from throw_event_benchmark import evaluate_events  # noqa: E402

GATES = [(-4.5, 12.0), (-2.0, 4.0), (0.0, 0.0)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", nargs=4, action="append", required=True,
                        metavar=("NAME", "CANDIDATES", "REFERENCE", "HOLD"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Postscore diagnostic already exists")
    cases = []
    for name, candidate_arg, reference_arg, hold_arg in args.case:
        paths = {"candidates": Path(candidate_arg),
                 "reference": Path(reference_arg), "hold": Path(hold_arg)}
        candidates, reference, hold = (json.loads(paths[key].read_text())
                                       for key in paths)
        if candidates["source_id"] != reference["source_id"] or (
                candidates["source_sha256"] != reference["source_sha256"]):
            parser.error(name + " source differs")
        ids = [event["id"] for event in candidates["events"]]
        if len(set(ids)) != len(ids) or (
                {row["candidate_id"] for row in hold["rows"]} != set(ids)):
            parser.error(name + " candidate IDs differ")
        trials = []
        for left_gate, right_gate in GATES:
            selected = []
            statuses = {}
            for row in hold["rows"]:
                view = row["receiving_view"]
                kwargs = ({"view": "left", "entry_y_threshold_m": left_gate,
                           "forward_direction": 1, "min_samples": 4,
                           "max_forward_speed_change_m_s": 2.0}
                          if view == "left" else
                          {"view": "right", "entry_y_threshold_m": right_gate})
                selection = select_far_entry_motion_path(
                    row["samples"], row["colour"], max_gap_s=4.1,
                    allow_missing_samples=True,
                    skip_status_required="abstained_no_stable_anchor", **kwargs)
                statuses[row["candidate_id"]] = selection["status"]
                if selection["status"] == "provisional_unique_far_entry_motion_path":
                    selected.append(row["candidate_id"])
            selected_set = set(selected)
            events = [event for event in candidates["events"]
                      if event["id"] in selected_set]
            trials.append({
                "left_entry_y_m": left_gate,
                "right_entry_y_m": right_gate,
                "selected_candidate_ids": selected,
                "selection_status_by_candidate": statuses,
                "motion_only_score": evaluate_events(
                    events, reference["events"], reference["source_interval_s"]),
            })
        cases.append({"name": name, "source_id": candidates["source_id"],
                      "input_sha256": {key: file_sha256(path)
                                       for key, path in paths.items()},
                      "trials": trials})
    result = {
        "status": "postscore_entry_gate_sensitivity_not_transfer_validation",
        "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "scorer_sha256": file_sha256(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": file_sha256(__file__),
        "cases": cases,
        "limitations": [
            "Entry thresholds were varied after reviewing Italy misses; these are in-sample diagnostics.",
            "Scores use motion selection only; patch appearance and timed-path deduplication are not rerun.",
            "Reference windows are coarse and same-agent, not independent exhaustive labels.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for case in cases:
        for trial in case["trials"]:
            score = trial["motion_only_score"]
            print(case["name"], trial["left_entry_y_m"],
                  trial["right_entry_y_m"], len(trial["selected_candidate_ids"]),
                  score["true_positives"], score["false_positives"],
                  score["false_negatives"])


if __name__ == "__main__":
    main()
