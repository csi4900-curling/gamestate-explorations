"""Attach integrated partial boards to all raw candidates without game-state claims."""

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


def board_summary(row):
    return {
        "status": row["board"]["status"],
        "tail_interval_s": [row["tail"]["start_s"], row["tail"]["stop_s"]]
        if row["tail"]["eligible"] else None,
        "coordinate_frame": row["coordinate_frame"],
        "stones": row["board"]["stones"],
        "registered_frame_count": row["registered_frame_count"],
        "registration_abstention_count": row["registration_abstention_count"],
        "completeness": row["completeness"],
        "settle_verified": row["post_throw_settle_verified"],
        "persistent_stone_ids_verified": row["persistent_stone_ids_verified"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("frozen_timeline", "integrated_screen", "boards", "motion",
                 "s96_review", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    old = json.loads(args.frozen_timeline.read_text())
    screen = json.loads(args.integrated_screen.read_text())
    boards = json.loads(args.boards.read_text())
    motion = json.loads(args.motion.read_text())
    s96 = json.loads(args.s96_review.read_text())
    if (old["screen_sha256"] != screen["frozen_screen_sha256"] or
            boards["screen_sha256"] != digest(args.integrated_screen) or
            motion["integrated_screen_sha256"] != digest(args.integrated_screen) or
            boards["source_sha256"] != old["source_sha256"] or
            s96["source_sha256"] != old["source_sha256"] or
            s96["candidate_id"] != "S96"):
        parser.error("Timeline source chain differs")
    by_board = {row["candidate_id"]: row for row in boards["rows"]}
    by_motion = {row["candidate_id"]: row for row in motion["rows"]}
    by_decision = {row["candidate_id"]: row for row in screen["decisions"]}
    accepted = {event["id"] for event in screen["events"]}
    added = set(screen["added_candidate_ids"])
    if (len(by_board) != len(boards["rows"]) or set(by_board) != accepted or
            len(by_motion) != len(motion["rows"]) or
            len(by_decision) != len(screen["decisions"])):
        parser.error("Candidate coverage differs")
    output_rows = []
    for original in old["timeline"]:
        pid = original["candidate_id"]
        item = dict(original)
        if pid in by_decision and item["screen_decision"] != by_decision[pid]["status"]:
            if pid not in added:
                raise ValueError(f"Unchanged screen decision differs for {pid}")
            item["screen_decision"] = by_decision[pid]["status"]
        if pid in added:
            if original["post_event_board"] is not None or original["event_status"] != "screen_abstention":
                raise ValueError(f"Added candidate was not an abstention: {pid}")
            path = by_motion[pid]["selection"]["path"]
            item["event_status"] = "provisional_unreviewed_candidate"
            item["observed_receiving_motion"] = {
                "status": by_motion[pid]["selection"]["status"],
                "coordinate_frame": "receiving_camera_view_local_conditional_ice_plane",
                "metric_accuracy_verified": False,
                "inter_camera_identity_verified": False,
                "samples": [{"source_time_s": node["source_time_s"],
                             "pixel_center": node["pixel_center"],
                             "ground_position_m_conditional": node["ground_position_m"]}
                            for node in path],
            }
        if pid == "S96":
            if item["screen_decision"] != s96["screen_status"] or pid not in accepted:
                raise ValueError("S96 review does not match integrated screen")
            item["event_status"] = "source_reviewed_false_positive"
            item["source_review"] = s96
        board = by_board.get(pid)
        if board:
            if pid not in accepted or board["crossing_time_s"] != item["passage_time_s"]:
                raise ValueError(f"Board time or screen differs for {pid}")
            summary = board_summary(board)
            if pid in added:
                item["post_event_board"] = summary
            elif item["post_event_board"] != summary:
                raise ValueError(f"Frozen board summary differs for {pid}")
        if item["complete_game_state"] or item["simulation_ready"]:
            raise ValueError("Partial observation promoted game state")
        output_rows.append(item)
    if len(output_rows) != len(old["timeline"]) or (
            {item["candidate_id"] for item in output_rows if item["post_event_board"] is not None}
            != accepted):
        raise ValueError("Timeline candidate or board coverage differs")
    output = {**old,
              "status": "postscore_147_raw_candidates_91_partial_board_attempts_not_game_states",
              "parent_timeline_sha256": digest(args.frozen_timeline),
              "screen_sha256": digest(args.integrated_screen),
              "boards_sha256": digest(args.boards),
              "motion_sha256": digest(args.motion),
              "s96_source_review_sha256": digest(args.s96_review),
              "integration_runner_sha256": digest(Path(__file__)),
              "event_status_counts": dict(Counter(row["event_status"] for row in output_rows)),
              "board_status_counts": boards["board_status_counts"],
              "timeline": output_rows,
              "limitations": old["limitations"] + [
                  "The added 12 paths and boards are development observations, not independently verified physical throws.",
                  "S96 and S143 are agent-source-reviewed false paths still accepted by the candidate screen.",
                  "All 91 post-event boards are partial and camera-local; none is simulation ready.",
              ]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(len(output_rows), "raw candidates", output["event_status_counts"])


if __name__ == "__main__":
    main()
