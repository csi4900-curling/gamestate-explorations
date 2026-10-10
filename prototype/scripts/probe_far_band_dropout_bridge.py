"""Postscore probe: bridge registered frames lacking a distant same-colour cap."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path  # noqa: E402
from throw_event_benchmark import evaluate_events  # noqa: E402

ELIGIBLE = "bridge_eligible_missing_far_cap_or_registration"


def mark_bridge_eligible(samples, colour, view, far_band_y_m=2.0):
    marked = deepcopy(samples)
    for sample in marked:
        if sample.get("status") == "abstained_no_stable_anchor" or (
            sample.get("registration_status") not in (None, "registered")
        ):
            sample["status"] = ELIGIBLE
            continue
        proposals = sample["views"][view]["proposals"]
        distant = [
            p
            for p in proposals
            if p["colour"] == colour
            and p["ground_position_m"] is not None
            and (
                p["ground_position_m"][1] <= -far_band_y_m
                if view == "left"
                else p["ground_position_m"][1] >= far_band_y_m
            )
        ]
        if not distant:
            sample["status"] = ELIGIBLE
    return marked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        nargs=4,
        action="append",
        required=True,
        metavar=("NAME", "CANDIDATES", "REFERENCE", "MOTION"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Postscore dropout-bridge artifact already exists")
    cases = []
    for name, candidate_arg, reference_arg, motion_arg in args.case:
        paths = {
            "candidates": Path(candidate_arg),
            "reference": Path(reference_arg),
            "motion": Path(motion_arg),
        }
        candidates, reference, motion = (json.loads(paths[key].read_text()) for key in paths)
        if candidates["source_id"] != reference["source_id"] or (
            candidates["source_sha256"] != reference["source_sha256"]
        ):
            parser.error(name + " source differs")
        ids = [event["id"] for event in candidates["events"]]
        if len(set(ids)) != len(ids) or (
            {row["candidate_id"] for row in motion["rows"]} != set(ids)
        ):
            parser.error(name + " candidate IDs differ")
        rows = []
        for row in motion["rows"]:
            view = row["receiving_view"]
            samples = mark_bridge_eligible(row["samples"], row["colour"], view)
            kwargs = (
                {
                    "view": "left",
                    "entry_y_threshold_m": -4.5,
                    "forward_direction": 1,
                    "min_samples": 4,
                    "max_forward_speed_change_m_s": 2.0,
                }
                if view == "left"
                else {"view": "right", "entry_y_threshold_m": 11.5}
            )
            selection = select_far_entry_motion_path(
                samples,
                row["colour"],
                max_gap_s=4.1,
                allow_missing_samples=True,
                skip_status_required=ELIGIBLE,
                **kwargs,
            )
            rows.append(
                {
                    "candidate_id": row["candidate_id"],
                    "selection": selection,
                    "bridge_eligible_sample_count": sum(
                        sample.get("status") == ELIGIBLE for sample in samples
                    ),
                }
            )
        accepted = {
            row["candidate_id"]
            for row in rows
            if row["selection"]["status"] == "provisional_unique_far_entry_motion_path"
        }
        events = [event for event in candidates["events"] if event["id"] in accepted]
        cases.append(
            {
                "name": name,
                "source_id": candidates["source_id"],
                "input_sha256": {key: file_sha256(path) for key, path in paths.items()},
                "right_entry_y_m": 11.5,
                "left_entry_y_m": -4.5,
                "far_band_y_m": 2.0,
                "max_gap_s": 4.1,
                "rows": rows,
                "selected_candidate_ids": [event["id"] for event in events],
                "motion_only_score": evaluate_events(
                    events, reference["events"], reference["source_interval_s"]
                ),
            }
        )
    result = {
        "status": "postscore_far_band_cap_dropout_probe_not_transfer_validation",
        "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "scorer_sha256": file_sha256(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": file_sha256(__file__),
        "cases": cases,
        "limitations": [
            "Right entry and far-band thresholds were selected after inspecting Italy misses.",
            "Marked frames are missing proposal evidence, not proof that no stone or other moving object was present.",
            "Motion-only scores do not rerun patch appearance or timed-path deduplication.",
            "Coarse references and candidate sets are exposed same-agent development data.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for case in cases:
        score = case["motion_only_score"]
        print(
            case["name"],
            len(case["selected_candidate_ids"]),
            score["true_positives"],
            score["false_positives"],
            score["false_negatives"],
            score["extra_prediction_ids"],
        )


if __name__ == "__main__":
    main()
