"""Join two provisional paths only where observed same-view samples overlap."""

import argparse
from hashlib import sha256
import json
from math import dist
from pathlib import Path


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--early", type=Path, required=True)
    parser.add_argument("--late", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    early = json.loads(args.early.read_text())
    late = json.loads(args.late.read_text())
    if early["candidate_id"] != args.candidate_id:
        parser.error("Early candidate ID differs")
    later = next((row for row in late["rows"] if row["candidate_id"] == args.candidate_id), None)
    if later is None:
        parser.error("Late candidate ID absent")
    if (
        early["source_sha256"] != late["high_resolution_source_sha256"]
        or early["colour"] != later["colour"]
        or later["receiving_view"] != "left"
    ):
        parser.error("Source, colour, or view differs")
    first = early["cases"]["extended"]["selection"]["path"]
    second = later["selection"]["path"]
    if not first or not second:
        parser.error("Both paths must have observations")
    first_by_time = {node["source_time_s"]: node for node in first}
    second_by_time = {node["source_time_s"]: node for node in second}
    if len(first_by_time) != len(first) or len(second_by_time) != len(second):
        parser.error("Duplicate time within a path")
    shared = sorted(first_by_time.keys() & second_by_time.keys())
    if not shared or max(first_by_time) != min(second_by_time):
        parser.error("Paths must meet at an observed endpoint")
    overlap = []
    for time_s in shared:
        a, b = first_by_time[time_s], second_by_time[time_s]
        pixel_distance = dist(a["pixel_center"], b["pixel_center"])
        world_distance = dist(a["ground_position_m"], b["ground_position_m"])
        if pixel_distance > 2.0 or world_distance > 0.2:
            parser.error("Shared observation disagrees beyond tolerance")
        overlap.append(
            {
                "source_time_s": time_s,
                "pixel_distance_px": pixel_distance,
                "conditional_position_distance_m": world_distance,
            }
        )
    combined = []
    for time_s in sorted(first_by_time.keys() | second_by_time.keys()):
        node = first_by_time.get(time_s) or second_by_time[time_s]
        provenance = (
            "both"
            if time_s in first_by_time and time_s in second_by_time
            else "extended_bound"
            if time_s in first_by_time
            else "existing_later_path"
        )
        combined.append({**node, "path_source": provenance})
    gaps = [
        round(right["source_time_s"] - left["source_time_s"], 6)
        for left, right in zip(combined, combined[1:])
    ]
    if not gaps or max(gaps) > 0.6:
        parser.error("Observed paths leave a gap greater than 0.6 s")
    output = {
        "status": "conditional_same_view_observation_join_not_verified_throw_or_trajectory",
        "candidate_id": args.candidate_id,
        "colour": early["colour"],
        "receiving_view": "left",
        "source_sha256": early["source_sha256"],
        "early_artifact_sha256": digest(args.early),
        "later_artifact_sha256": digest(args.late),
        "runner_sha256": digest(Path(__file__)),
        "shared_observations": overlap,
        "first_observation_s": combined[0]["source_time_s"],
        "last_observation_s": combined[-1]["source_time_s"],
        "sample_count": len(combined),
        "largest_observation_gap_s": max(gaps),
        "observations": combined,
        "physical_stone_identity_verified": False,
        "metric_accuracy_verified": False,
        "release_time_observed": False,
        "settle_time_observed": False,
        "simulation_ready": False,
        "limitations": [
            "Exact shared same-view observations support a provisional join, not physical identity proof.",
            "Extended-bound positions exceed the original calibration footprint.",
            "The observed segment does not include verified release, settle, spin, or collisions.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        args.candidate_id,
        len(combined),
        combined[0]["source_time_s"],
        combined[-1]["source_time_s"],
    )


if __name__ == "__main__":
    main()
