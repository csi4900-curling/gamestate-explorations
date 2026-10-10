"""Postscore source-only adjacent boards against official diagram observations."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations

BASE = ROOT / "validation/official-shot-sequence"
BOARDS = BASE / "china-end2-adjacent-video-boards-first.json"
TRANSITIONS = BASE / "china-end2-partial-board-transitions-first.json"
DIAGRAMS = BASE / "pwg2022-official-board-diagrams.json"
LEDGER = ROOT / "validation/curlobserver-learned-probe/china-full-transfer/candidate-throw-event-ledger-after-link.json"
OUTPUT = BASE / "china-end2-adjacent-board-comparison-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first postscore comparison")
    board, transition, diagrams, ledger = (json.loads(path.read_text()) for path in
                                           (BOARDS, TRANSITIONS, DIAGRAMS, LEDGER))
    if (transition["board_scan_sha256"] != digest(BOARDS) or
            board["source_sha256"] != transition["source_sha256"] or
            board["source_sha256"] != ledger["source_sha256"]):
        raise ValueError("Frozen source-only results or source mismatch")
    official = {shot["official_shot_id"]: shot
                for game in diagrams["games"] for end in game["ends"]
                for shot in end["shots"]}
    rows = []
    for item in board["rows"]:
        diagram = official[item["shot_id"]]
        comparison = compare_board_observations(
            item["stable_partial_board"], diagram["stones"],
            official_house_center_y=diagram["house_center_px"][1])
        counter_events = [event for event in ledger["events"]
                          if event.get("broadcast_counter") is not None
                          and event["broadcast_counter"]["update_s"] ==
                          item["counter_anchor_s"]]
        complete = (comparison["matched_count"] ==
                    comparison["video_stone_count"] ==
                    comparison["official_symbol_count"])
        rows.append({
            "shot_id": item["shot_id"],
            "counter_anchor_s": item["counter_anchor_s"],
            "video_stone_count": len(item["stable_partial_board"]),
            "official_stone_count": len(diagram["stones"]),
            "matched_video_stones": comparison["matched_count"],
            "complete_diagram_match": complete,
            "comparison": comparison,
            "counter_linked_candidates": [{"candidate_id": event["candidate_id"],
                                           "colour": event["colour"],
                                           "colour_status": event["colour_status"]}
                                          for event in counter_events],
        })
    output = {
        "status": "postscore_adjacent_video_board_first_crossrecording_comparison",
        "source_sha256": board["source_sha256"],
        "board_scan_sha256": digest(BOARDS),
        "source_only_transition_sha256": digest(TRANSITIONS),
        "diagram_sha256": digest(DIAGRAMS),
        "event_ledger_sha256": digest(LEDGER),
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "scanned_shot_count": len(rows),
        "boards_with_stones": sum(row["video_stone_count"] > 0 for row in rows),
        "complete_diagram_match_count": sum(row["complete_diagram_match"]
                                            for row in rows),
        "rows": rows,
        "limitations": [
            "These adjacent shots were selected around a prior successful development board.",
            "Official diagrams evaluate after source-only detection; they are not video input.",
            "Diagram agreement does not establish persistent stone identity or exact settle time.",
            "This is not a cross-recording board rate or physical throw-event F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"scanned": output["scanned_shot_count"],
           "with_stones": output["boards_with_stones"],
           "complete_diagram_matches": output["complete_diagram_match_count"]})


if __name__ == "__main__":
    main()
