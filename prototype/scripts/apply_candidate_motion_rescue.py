"""Apply a label-free dropout rescue to previously unsupported candidate paths."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_motion_rescue import rescue_candidate_path  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--source-motion", type=Path,
                        help="Original scan when observations are a registration hold")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Rescue artifact already exists")
    base = json.loads(args.base.read_text())
    observations = json.loads(args.observations.read_text())
    if args.source_motion:
        original = json.loads(args.source_motion.read_text())
        if base["hold_sha256"] != file_sha256(args.observations) or (
                observations["motion_sha256"] != file_sha256(args.source_motion)):
            parser.error("Gap, hold and source-motion artifacts do not chain")
    else:
        original = observations
        if args.base.resolve() != args.observations.resolve():
            parser.error("Without source-motion, base and observations must match")
    if file_sha256(args.base) != file_sha256(args.observations) and not args.source_motion:
        parser.error("Base and observation artifacts differ")
    observed = {row["candidate_id"]: row for row in observations["rows"]}
    if len(observed) != len(observations["rows"]) or (
            set(observed) != {row["candidate_id"] for row in base["rows"]}):
        parser.error("Candidate IDs differ")
    rows = []
    for row in base["rows"]:
        source = observed[row["candidate_id"]]
        if (source["colour"], source["receiving_view"]) != (
                row["colour"], row["receiving_view"]):
            parser.error("Candidate colour or view differs")
        decision = rescue_candidate_path(
            row["selection"], source["samples"],
            row["colour"], row["receiving_view"])
        rows.append({"candidate_id": row["candidate_id"],
                     "colour": row["colour"],
                     "receiving_view": row["receiving_view"],
                     "base_selection_status": row["selection"]["status"],
                     **decision})
    result = {
        "status": "postscore_exposed_development_dropout_rescue_not_transfer_validation",
        "base_sha256": file_sha256(args.base),
        "observations_sha256": file_sha256(args.observations),
        "source_motion_sha256": (file_sha256(args.source_motion)
                                 if args.source_motion else None),
        "high_resolution_source_sha256": original["high_resolution_source_sha256"],
        "source_offset_s": original["source_offset_s"],
        "max_corner_displacement_px": original["max_corner_displacement_px"],
        "rescue_code_sha256": file_sha256(ROOT / "prototype/candidate_motion_rescue.py"),
        "runner_sha256": file_sha256(__file__),
        "parameters": {"left_entry_y_m": -4.5, "right_entry_y_m": 11.5,
                       "far_band_y_m": 2.0, "max_gap_s": 4.1,
                       "min_prefix_samples": 5,
                       "min_prefix_fraction": 0.7,
                       "min_prefix_travel_m": 2.0},
        "rescue_status_counts": dict(Counter(row["rescue_status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Dropout and prefix rules were selected after inspecting Italy, Estonia and China development outcomes.",
            "A shared path prefix is event evidence only; identity after ambiguity is unverified.",
            "Absent cap proposals do not establish absent stones or a continuous physical path.",
        ],
    }
    if args.source_motion:
        result["hold_sha256"] = file_sha256(args.observations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["rescue_status_counts"])


if __name__ == "__main__":
    main()
