"""Postscore Norway end-two source-video partial boards against official PDF."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations

BASE = ROOT / "validation/official-shot-sequence"
INPUT = BASE / "norway-end2-source-video-partial-boards-first.json"
OFFICIAL = BASE / "pwg2022-canada-norway-official-boards.json"
OUTPUT = BASE / "norway-end2-video-board-first-score.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first comparison")
    scanned = json.loads(INPUT.read_text())
    official = json.loads(OFFICIAL.read_text())
    if (scanned["source_video_sha256"] != official["source_video_sha256"] or
            scanned["shot_count"] != 16):
        raise ValueError("Source or end-two shot count changed")
    shots = official["ends"][1]["shots"]
    if official["ends"][1]["end"] != 2 or len(shots) != 16:
        raise ValueError("Official end-two board reference changed")
    rows = []
    for scan, shot in zip(scanned["rows"], shots):
        if (scan["shot_order_in_end"] != int(shot["official_shot_id"].split("-S")[-1]) or
                scan["counter_id"] != f"B{scan['shot_order_in_end']+15:02}"):
            raise ValueError("Counter order cannot be joined to official shot order")
        comparison = compare_board_observations(
            scan["stable_partial_board"], shot["stones"],
            official_house_center_y=shot["house_center_px"][1])
        rows.append({"counter_id": scan["counter_id"],
                     "official_shot_id": shot["official_shot_id"],
                     "accepted_frame_count": scan["accepted_frame_count"],
                     "video_stone_count": len(scan["stable_partial_board"]),
                     "official_symbol_count": len(shot["stones"]),
                     "official_review_flags": shot["review_flags"],
                     "comparison": comparison})
    result = {"status": "first_postscore_norway_end2_board_transfer_diagnostic",
              "source_only_scan_sha256": digest(INPUT),
              "official_diagrams_sha256": digest(OFFICIAL),
              "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
              "runner_sha256": digest(Path(__file__)),
              "shot_count": len(rows),
              "shots_with_video_board": sum(r["video_stone_count"] > 0 for r in rows),
              "video_stone_count": sum(r["video_stone_count"] for r in rows),
              "matched_stone_count": sum(r["comparison"]["matched_count"] for r in rows),
              "complete_board_match_count": sum(r["video_stone_count"] ==
                                                r["official_symbol_count"] ==
                                                r["comparison"]["matched_count"] for r in rows),
              "rows": rows,
              "limitations": ["The 16 counter anchors are a broadcast-order proxy, not independently validated physical shot times.",
                              "This is a single selected end on a separate match, not a full-match board reconstruction rate.",
                              "No video board is promoted to a complete metric or simulation-ready game state by comparison with the PDF."]}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in ("shot_count", "shots_with_video_board",
                                       "video_stone_count", "matched_stone_count",
                                       "complete_board_match_count")})


if __name__ == "__main__":
    main()
