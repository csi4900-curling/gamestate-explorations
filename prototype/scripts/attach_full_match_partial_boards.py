"""Attach conditional partial boards without claiming complete game state."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timeline", type=Path, required=True)
    p.add_argument("--boards", type=Path, required=True)
    p.add_argument("--screen", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Board-augmented timeline already exists")
    timeline = json.loads(a.timeline.read_text())
    boards = json.loads(a.boards.read_text())
    screen = json.loads(a.screen.read_text())
    screen_hash = file_sha256(a.screen)
    if (
        timeline["input_sha256"]["screen"] != screen_hash
        or boards["screen_sha256"] != screen_hash
        or boards["source_sha256"] != timeline["source_sha256"]
    ):
        p.error("Timeline, board and screen provenance differs")
    rows = boards["rows"]
    accepted = [row["candidate_id"] for row in screen["decisions"] if row["accepted"]]
    if [row["candidate_id"] for row in rows] != accepted:
        p.error("Board observations do not cover all screened candidate IDs")
    by_id = {row["candidate_id"]: row for row in rows}
    output_rows = []
    for entry in timeline["timeline"]:
        item = dict(entry)
        board = by_id.get(entry["candidate_id"])
        if board:
            if (
                entry["event_status"]
                not in ("provisional_unreviewed_candidate", "source_reviewed_false_positive")
                or board["crossing_time_s"] != entry["passage_time_s"]
                or board["receiving_view"] != entry["receiving_view"]
            ):
                p.error(f"Board does not match candidate {entry['candidate_id']}")
            item["post_event_board"] = {
                "status": board["board"]["status"],
                "tail_interval_s": [board["tail"]["start_s"], board["tail"]["stop_s"]]
                if board["tail"]["eligible"]
                else None,
                "coordinate_frame": board["coordinate_frame"],
                "stones": board["board"]["stones"],
                "registered_frame_count": board["registered_frame_count"],
                "registration_abstention_count": board["registration_abstention_count"],
                "completeness": board["completeness"],
                "settle_verified": board["post_throw_settle_verified"],
                "persistent_stone_ids_verified": board["persistent_stone_ids_verified"],
            }
        if item["simulation_ready"] or item["complete_game_state"]:
            p.error("Partial observation cannot promote game state readiness")
        output_rows.append(item)
    result = {
        **timeline,
        "status": "full_match_candidate_evidence_with_partial_boards_not_game_states",
        "parent_timeline_sha256": file_sha256(a.timeline),
        "boards_sha256": file_sha256(a.boards),
        "screen_sha256": screen_hash,
        "attachment_runner_sha256": file_sha256(Path(__file__)),
        "board_status_counts": boards["board_status_counts"],
        "timeline": output_rows,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(len(output_rows), "candidate rows;", len(rows), "partial-board attempts")


if __name__ == "__main__":
    main()
