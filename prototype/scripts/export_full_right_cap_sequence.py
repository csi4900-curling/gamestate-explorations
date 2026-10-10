"""Export adjacent right-view image-cap comparisons for any full recording."""

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
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("observations", "fusion", "alignment", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    observations = json.loads(args.observations.read_text())
    fusion = json.loads(args.fusion.read_text())
    alignment = json.loads(args.alignment.read_text())
    if (
        observations["source_sha256"] != fusion["source_sha256"]
        or observations["fusion_sha256"] != digest(args.fusion)
        or alignment["source_sha256"] != fusion["source_sha256"]
        or alignment["observations_sha256"] != digest(args.observations)
    ):
        parser.error("Source, observations and alignment provenance differ")
    rows = observations["rows"]
    expected = sorted(fusion["right_entries"], key=lambda row: row["right_entry_time_s"])
    if [row["right_raw_track_id"] for row in rows] != [
        row["right_raw_track_id"] for row in expected
    ]:
        parser.error("Observation rows do not cover all right entries in source order")
    transitions = adjacent_cap_sequence(rows, alignment["adjacent_pairs"])
    result = {
        "status": "full_match_right_camera_partial_image_cap_sequence_not_physical_game_state",
        "source_sha256": fusion["source_sha256"],
        "fusion_sha256": digest(args.fusion),
        "observations_sha256": digest(args.observations),
        "alignment_sha256": digest(args.alignment),
        "sequence_code_sha256": digest(ROOT / "prototype/right_view_cap_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        "right_entry_count": len(rows),
        "min_blue_house_mask_iou_for_cap_comparison": 0.7,
        "observation_status_counts": observations["observation_status_counts"],
        "transition_status_counts": dict(Counter(row["status"] for row in transitions)),
        "conditional_local_cap_match_count": sum(
            len(row.get("matched_local_caps", [])) for row in transitions
        ),
        "entries": [
            {
                "right_raw_track_id": row["right_raw_track_id"],
                "conditional_left_candidate_id": row.get("conditional_left_candidate_id"),
                "source_reviewed_prefix_class": row.get("source_reviewed_prefix_class"),
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
            "Post-entry stable caps can appear even after a source-reviewed nonstone right prefix.",
            "A camera-local cap match is not a persistent physical stone identity or same-end proof.",
            "Sampled image alignment is not calibrated geometry or an event-length camera-pose guarantee.",
            "No transition establishes a complete board, physical addition/removal, score or simulation-ready state.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "entries": len(rows),
                "transitions": result["transition_status_counts"],
                "local_cap_matches": result["conditional_local_cap_match_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
