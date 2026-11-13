"""Export an abstention-aware sequence of right-only partial cap observations."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_view_cap_sequence import adjacent_cap_sequence


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--fusion", type=Path, required=True)
    parser.add_argument("--alignment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    observations = json.loads(args.observations.read_text())
    fusion = json.loads(args.fusion.read_text())
    alignment = json.loads(args.alignment.read_text())
    if observations["source_sha256"] != fusion["source_sha256"] or observations[
        "fusion_sha256"
    ] != digest(args.fusion):
        parser.error("Source or fusion fingerprint differs")
    if alignment["source_sha256"] != fusion["source_sha256"] or alignment[
        "observations_sha256"
    ] != digest(args.observations):
        parser.error("Alignment source or observations fingerprint differs")
    rows = observations["rows"]
    eligible = [
        row for row in fusion["right_entries"] if row["fusion_status"].startswith("right_only_")
    ]
    if [row["right_raw_track_id"] for row in rows] != [
        row["right_raw_track_id"] for row in eligible
    ]:
        parser.error("Observation rows do not cover right-only entries in order")
    transitions = adjacent_cap_sequence(rows, alignment["adjacent_pairs"])
    output = {
        "status": "partial_camera_local_cap_sequence_not_physical_game_state",
        "source_sha256": fusion["source_sha256"],
        "fusion_sha256": digest(args.fusion),
        "observations_sha256": digest(args.observations),
        "alignment_sha256": digest(args.alignment),
        "sequence_code_sha256": digest(ROOT / "prototype/right_view_cap_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        "right_only_entry_count": len(rows),
        "min_blue_house_mask_iou_for_cap_comparison": 0.7,
        "observation_status_counts": observations["observation_status_counts"],
        "transition_status_counts": dict(Counter(row["status"] for row in transitions)),
        "conditional_local_cap_match_count": sum(
            len(row.get("matched_local_caps", [])) for row in transitions
        ),
        "entries": [
            {
                "right_raw_track_id": row["right_raw_track_id"],
                "entry_time_s": row["entry_time_s"],
                "observation_status": row["observation_status"],
                "stable_cap_proposals": row["stable_cap_proposals"],
                "simulation_ready": False,
            }
            for row in rows
        ],
        "adjacent_transitions": transitions,
        "simulation_ready_count": 0,
        "limitations": [
            "Local cap associations do not establish physical stone identity.",
            "Painted-house alignment supports only the selected sample instants, not full camera pose or same-end identity.",
            "An abstained entry blocks comparison across its interval.",
            "Visible-colour changes are not physical additions, removals or scoring.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "entries": len(rows),
                "transitions": output["transition_status_counts"],
                "conditional_local_cap_matches": output["conditional_local_cap_match_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
