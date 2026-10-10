"""Preserve every raw full-match candidate with its conditional screen evidence."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def by_id(rows, field):
    result = {row[field]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {field}")
    return result


def build(raw, corridor, screen, motion, review=None):
    raw_rows = by_id(raw["events"], "id")
    corridor_rows = by_id(corridor["events"], "id")
    withheld_rows = by_id(corridor["withheld_events"], "id")
    decisions = by_id(screen["decisions"], "candidate_id")
    motions = by_id(motion["rows"], "candidate_id")
    if (
        raw["source_id"] != corridor["source_id"]
        or raw["source_sha256"] != corridor["source_sha256"]
        or raw["source_interval_s"] != corridor["source_interval_s"]
    ):
        raise ValueError("Raw and corridor sources differ")
    if (
        set(raw_rows) != set(corridor_rows) | set(withheld_rows)
        or set(corridor_rows) & set(withheld_rows)
        or set(decisions) != set(corridor_rows)
        or set(motions) != set(corridor_rows)
    ):
        raise ValueError("Candidate coverage differs between stages")
    if screen["source_sha256"] != raw["source_sha256"]:
        raise ValueError("Screen source differs")
    reviewed_id = None
    if review:
        reviewed_id = review["candidate_id"]
        if (
            review["source_sha256"] != raw["source_sha256"]
            or reviewed_id not in decisions
            or not decisions[reviewed_id]["accepted"]
            or review["screen_status"] != decisions[reviewed_id]["status"]
            or review["review_conclusion"] != "false_positive_postgame_player_wheelchair_movement"
        ):
            raise ValueError("Source review does not match screened candidate")
    output = []
    for candidate in sorted(raw_rows.values(), key=lambda row: row["crossing_time_s"]):
        candidate_id = candidate["id"]
        decision = decisions.get(candidate_id)
        motion_row = motions.get(candidate_id)
        if candidate_id == reviewed_id:
            status = "source_reviewed_false_positive"
        elif decision and decision["accepted"]:
            status = "provisional_unreviewed_candidate"
        elif decision:
            status = "screen_abstention"
        else:
            status = "outside_screen_corridor"
        entry = {
            "candidate_id": candidate_id,
            "event_status": status,
            "candidate_colour": candidate["colour"],
            "passage_time_s": candidate["crossing_time_s"],
            "passage_time_semantics": candidate["time_semantics"],
            "screen_decision": decision["status"] if decision else None,
            "physical_throw_identity_verified": False,
            "release_time_s": None,
            "physical_settle_time_s": None,
            "spin_revolution_count": None,
            "end_identity": None,
            "complete_game_state": False,
            "simulation_ready": False,
            "receiving_view": motion_row["receiving_view"] if motion_row else None,
            "observed_receiving_motion": None,
            "post_event_board": None,
            "source_review": review if candidate_id == reviewed_id else None,
        }
        if motion_row:
            selection = motion_row["selection"]
            path = selection.get("path") or selection.get("shared_prefix") or []
            entry["observed_receiving_motion"] = {
                "status": selection["status"],
                "coordinate_frame": "receiving_camera_view_local_conditional_ice_plane",
                "metric_accuracy_verified": False,
                "inter_camera_identity_verified": False,
                "samples": [
                    {
                        "source_time_s": sample["source_time_s"],
                        "pixel_center": sample["pixel_center"],
                        "ground_position_m_conditional": sample["ground_position_m"],
                    }
                    for sample in path
                ],
            }
        output.append(entry)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("raw", "corridor", "screen", "motion"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--source-review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Timeline already exists")
    paths = {name: getattr(args, name) for name in ("raw", "corridor", "screen", "motion")}
    inputs = {name: json.loads(path.read_text()) for name, path in paths.items()}
    if inputs["screen"]["candidates_sha256"] != file_sha256(args.corridor) or inputs["screen"][
        "motion_sha256"
    ] != file_sha256(args.motion):
        parser.error("Screen hash chain differs")
    review = json.loads(args.source_review.read_text()) if args.source_review else None
    timeline = build(**inputs, review=review)
    output = {
        "status": "full_match_candidate_evidence_not_verified_throw_sequence",
        "source_id": inputs["raw"]["source_id"],
        "source_sha256": inputs["raw"]["source_sha256"],
        "source_interval_s": inputs["raw"]["source_interval_s"],
        "input_sha256": {name: file_sha256(path) for name, path in paths.items()},
        "source_review_sha256": file_sha256(args.source_review) if args.source_review else None,
        "runner_sha256": file_sha256(Path(__file__)),
        "event_status_counts": dict(Counter(row["event_status"] for row in timeline)),
        "timeline": timeline,
        "limitations": [
            "Candidate timestamps are observed passage estimates, not exact releases or settles.",
            "One agent-reviewed false positive is not an independent precision estimate.",
            "No exhaustive independent labels, complete post-throw boards, or verified metric rink positions exist for this match.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(len(timeline), "raw candidates", output["event_status_counts"])


if __name__ == "__main__":
    main()
