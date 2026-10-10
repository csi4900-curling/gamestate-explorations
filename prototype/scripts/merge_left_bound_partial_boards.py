"""Merge frozen and added partial boards in integrated candidate order."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("frozen_boards", "added_boards", "frozen_screen",
                 "integrated_screen", "added_screen", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    old = json.loads(args.frozen_boards.read_text())
    new = json.loads(args.added_boards.read_text())
    frozen = json.loads(args.frozen_screen.read_text())
    integrated = json.loads(args.integrated_screen.read_text())
    added_screen = json.loads(args.added_screen.read_text())
    if (old["screen_sha256"] != digest(args.frozen_screen) or
            new["screen_sha256"] != digest(args.added_screen) or
            added_screen["integrated_screen_sha256"] != digest(args.integrated_screen) or
            integrated["frozen_screen_sha256"] != digest(args.frozen_screen) or
            any(old[key] != new[key] for key in
                ("source_id", "source_sha256", "high_resolution_source_sha256",
                 "source_interval_s", "candidates_sha256",
                 "vision_calibration_sha256", "rectification_sha256",
                 "board_code_sha256"))):
        parser.error("Input board provenance differs")
    frozen_ids = [event["id"] for event in frozen["events"]]
    added_ids = [event["id"] for event in added_screen["events"]]
    integrated_ids = [event["id"] for event in integrated["events"]]
    if ([row["candidate_id"] for row in old["rows"]] != frozen_ids or
            [row["candidate_id"] for row in new["rows"]] != added_ids or
            set(frozen_ids).intersection(added_ids) or
            set(frozen_ids).union(added_ids) != set(integrated_ids) or
            set(added_ids) != set(integrated["added_candidate_ids"])):
        parser.error("Board rows do not partition integrated accepted events")
    by_id = {row["candidate_id"]: row for row in old["rows"] + new["rows"]}
    rows = [by_id[pid] for pid in integrated_ids]
    for event, row in zip(integrated["events"], rows):
        if (event["crossing_time_s"] != row["crossing_time_s"] or
                event["colour"] != row["colour"] or
                row["completeness"] != "unknown_from_video" or
                row["simulation_ready"] or row["post_throw_settle_verified"] or
                row["persistent_stone_ids_verified"]):
            raise ValueError(f"Incomplete or mismatched board for {event['id']}")
    output = {
        "status": "postscore_91_candidate_partial_boards_not_game_states",
        "source_id": old["source_id"],
        "source_sha256": old["source_sha256"],
        "high_resolution_source_sha256": old["high_resolution_source_sha256"],
        "source_interval_s": old["source_interval_s"],
        "candidates_sha256": old["candidates_sha256"],
        "screen_sha256": digest(args.integrated_screen),
        "vision_calibration_sha256": old["vision_calibration_sha256"],
        "rectification_sha256": old["rectification_sha256"],
        "board_code_sha256": old["board_code_sha256"],
        "integrated_screen_sha256": digest(args.integrated_screen),
        "frozen_boards_sha256": digest(args.frozen_boards),
        "added_boards_sha256": digest(args.added_boards),
        "runner_sha256": digest(Path(__file__)),
        "frozen_board_count": len(old["rows"]),
        "added_board_count": len(new["rows"]),
        "candidate_board_count": len(rows),
        "board_status_counts": dict(Counter(row["board"]["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Every row is a camera-local partial observation, not a complete board after a verified throw.",
            "The 12 new candidate paths and the two known frozen false paths remain in this development sequence.",
            "Stone identity across rows/views, physical settle time, geometry error, score, spin and simulation readiness remain unknown.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(len(rows), "candidate board attempts", output["board_status_counts"])


if __name__ == "__main__":
    main()
