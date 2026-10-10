"""Count review candidates inside stable broadcast end-marker windows."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from end_marker_temporal import stable_marker_evidence

POSSIBLE_EVENT_KINDS = {
    "left_provisional_passage", "right_only_review_entry",
    "right_area_reviewed_stone_pixels", "right_area_end5_reviewed_stone_pixels",
    "right_area_end1_reviewed_stone_pixels",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def audit(handoff, markers):
    if handoff["source_sha256"] != markers["video_sha256"]:
        raise ValueError("Handoff and markers have different sources")
    temporal = stable_marker_evidence(markers["samples"])
    rows = handoff["ordered_candidates"]
    if len(rows) != handoff["candidate_count"]:
        raise ValueError("Handoff candidate count differs")
    counts = []
    assigned = set()
    for run in temporal["stable_runs"]:
        members = [row for row in rows if run["first_hit_s"] <= row["source_time_s"] <= run["last_hit_s"]]
        possible = [row for row in members if row["observation_kind"] in POSSIBLE_EVENT_KINDS]
        violations = [{"before_id": before["candidate_id"],
                       "after_id": after["candidate_id"],
                       "colour": before["colour_claim"]}
                      for before, after in zip(possible, possible[1:])
                      if before["colour_claim"] == after["colour_claim"]]
        assigned.update(row["candidate_id"] for row in members)
        counts.append({
            "broadcast_end_marker": run["end"],
            "stable_marker_hit_interval_s": [run["first_hit_s"], run["last_hit_s"]],
            "all_review_row_count": len(members),
            "possible_event_review_count": len(possible),
            "possible_event_counts_by_kind": dict(Counter(row["observation_kind"] for row in possible)),
            "possible_event_candidate_ids": [row["candidate_id"] for row in possible],
            "possible_event_colour_sequence": [row["colour_claim"] for row in possible],
            "adjacent_same_colour_pairs": violations,
        })
    return {
        "status": "stable_broadcast_end_marker_candidate_counts_not_physical_shot_count",
        "source_sha256": handoff["source_sha256"],
        "candidate_count": len(rows),
        "possible_event_review_count": sum(row["observation_kind"] in POSSIBLE_EVENT_KINDS for row in rows),
        "stable_end_windows": counts,
        "outside_stable_marker_candidate_ids": [row["candidate_id"] for row in rows
                                                 if row["candidate_id"] not in assigned],
        "limitations": [
            "Broadcast end-marker recognition has gaps; candidates outside stable windows are not assigned an end.",
            "Colour alternation is a review cue and cannot verify physical throw identity or detect every miss.",
            "Candidate counts include source-reviewed people and ambiguous pixels, and are not delivery counts or F1.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--markers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    output = audit(json.loads(args.handoff.read_text()),
                   json.loads(args.markers.read_text()))
    output["input_sha256"] = {"handoff": digest(args.handoff),
                              "markers": digest(args.markers)}
    output["temporal_code_sha256"] = digest(ROOT / "prototype/end_marker_temporal.py")
    output["runner_sha256"] = digest(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidates": output["candidate_count"],
                      "end_counts": {row["broadcast_end_marker"]: row["possible_event_review_count"]
                                     for row in output["stable_end_windows"]}}))


if __name__ == "__main__":
    main()
