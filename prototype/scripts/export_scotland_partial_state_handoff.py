"""Attach right-camera image observations to the Scotland candidate sequence."""

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
    for name in ("sequence", "observations", "alignment", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    sequence = json.loads(args.sequence.read_text())
    observations = json.loads(args.observations.read_text())
    alignment = json.loads(args.alignment.read_text())
    source_hash = sequence["source_sha256"]
    if (observations["source_sha256"] != source_hash
            or alignment["source_sha256"] != source_hash
            or observations["candidate_sequence_sha256"] != digest(args.sequence)
            or alignment["observations_sha256"] != digest(args.observations)):
        parser.error("Sequence, observations and alignment provenance differ")
    observations_by_candidate = {row["candidate_id"]: row for row in observations["rows"]}
    if len(observations_by_candidate) != len(observations["rows"]):
        parser.error("More than one right observation maps to a candidate")
    candidate_ids = {row["candidate_id"] for row in sequence["rows"]}
    if not set(observations_by_candidate) <= candidate_ids:
        parser.error("Right observation maps to an unknown candidate")
    transitions = adjacent_cap_sequence(observations["rows"],
                                        alignment["adjacent_pairs"])
    transition_by_after = {row["after_right_track_id"]: row for row in transitions}
    rows = []
    for candidate in sequence["rows"]:
        row = dict(candidate)
        observed = observations_by_candidate.get(row["candidate_id"])
        if observed:
            if (row["right_entry"] is None
                    or row["right_entry"]["raw_track_id"] != observed["right_raw_track_id"]):
                parser.error("Candidate and right observation IDs differ")
            row["post_entry_right_image_observation"] = {
                "status": observed["observation_status"],
                "source_sample_times_s": [frame["time_s"] for frame in
                                          observed["sample_frames"]],
                "stable_cap_proposals": observed["stable_cap_proposals"],
                "coordinate_frame": observed["coordinate_frame"],
                "complete_board_verified": False,
                "physical_settle_verified": False,
                "persistent_stone_identity_verified": False,
            }
            row["image_transition_from_previous_right_entry"] = transition_by_after.get(
                observed["right_raw_track_id"])
        else:
            row["post_entry_right_image_observation"] = None
            row["image_transition_from_previous_right_entry"] = None
        if row["game_state_after"]["simulation_ready"]:
            parser.error("Partial image observations cannot promote simulation readiness")
        rows.append(row)
    result = {
        "status": "scotland_candidate_sequence_with_partial_image_boards_not_physical_state",
        "source_sha256": source_hash,
        "candidate_sequence_sha256": digest(args.sequence),
        "observations_sha256": digest(args.observations),
        "alignment_sha256": digest(args.alignment),
        "cap_sequence_code_sha256": digest(ROOT / "prototype/right_view_cap_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_sequence_count": len(rows),
        "right_observation_count": len(observations["rows"]),
        "observation_status_counts": observations["observation_status_counts"],
        "image_transition_status_counts": dict(Counter(row["status"]
                                                       for row in transitions)),
        "conditional_local_cap_match_count": sum(len(row.get("matched_local_caps", []))
                                                 for row in transitions),
        "complete_game_state_count": 0,
        "simulation_ready_count": 0,
        "rows": rows,
        "limitations": [
            "Image cap sets are incomplete and may contain nonstones; source review remains necessary.",
            "Painted-house alignment supports only sampled frames and cannot verify same physical end or camera pose throughout a throw.",
            "Conditional cap matches are camera-local pixel associations, not persistent physical stone identities.",
            "No event has verified release, settle, complete board, end identity, metric trajectory or spin count.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows),
                      "image_transitions": result["image_transition_status_counts"],
                      "local_cap_matches": result["conditional_local_cap_match_count"]}))


if __name__ == "__main__":
    main()
