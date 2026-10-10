"""Separate off-camera official symbols from visible misses in v2 transfer."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_visibility import official_visibility

TRANSFER = ROOT / "validation/official-shot-sequence/pwg2022-video-board-transfer-v2.json"
DIAGRAMS = ROOT / "validation/official-shot-sequence/pwg2022-official-board-diagrams.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-video-board-visibility.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first visibility audit")
    transfer = json.loads(TRANSFER.read_text())
    diagrams = json.loads(DIAGRAMS.read_text())
    shots = {
        shot["official_shot_id"]: shot
        for game in diagrams["games"]
        for end in game["ends"]
        for shot in end["shots"]
    }
    rows = []
    for row in transfer["rows"]:
        if row["status"] != "compared":
            continue
        official = shots[row["official_shot_id"]]
        visibility = official_visibility(
            official["stones"],
            official_house_center_y=official["house_center_px"][1],
            video_house=row["house"],
        )
        visible_indices = {item["official_index"] for item in visibility["in_frame"]}
        matched = row["comparison"]["matches"]
        colour_global_indices = {
            colour: [
                index for index, stone in enumerate(official["stones"]) if stone["colour"] == colour
            ]
            for colour in ("red", "yellow")
        }
        matched_indices = {
            colour_global_indices[item["colour"]][item["official_index"]] for item in matched
        }
        rows.append(
            {
                "official_shot_id": row["official_shot_id"],
                "video_time_s": row["video_time_s"],
                "video_stone_count": row["comparison"]["video_stone_count"],
                "official_symbol_count": len(official["stones"]),
                "matched_total": len(matched),
                "in_frame_official_count": visibility["in_frame_count"],
                "outside_or_edge_official_count": visibility["outside_or_edge_count"],
                "matched_in_frame_count": len(matched_indices & visible_indices),
                "unmatched_in_frame_count": len(visible_indices - matched_indices),
                "visibility": visibility,
            }
        )
    output = {
        "status": "projected_field_of_view_diagnostic_not_board_recall_or_throw_f1",
        "transfer_sha256": digest(TRANSFER),
        "official_diagrams_sha256": digest(DIAGRAMS),
        "visibility_code_sha256": digest(ROOT / "prototype/board_visibility.py"),
        "runner_sha256": digest(Path(__file__)),
        "stone_margin_px": 10,
        "compared_count": len(rows),
        "official_symbols_compared": sum(row["official_symbol_count"] for row in rows),
        "outside_or_edge_official_count": sum(
            row["outside_or_edge_official_count"] for row in rows
        ),
        "unmatched_in_frame_count": sum(row["unmatched_in_frame_count"] for row in rows),
        "rows": rows,
        "limitations": [
            "Projected visibility assumes a circular house and no perspective distortion; near-edge classification is approximate.",
            "In-frame unmatched symbols may be occluded, absent because of timing, or missed by the detector.",
            "Official PDF positions and counter-linked shots are development references, not independent video event labels.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            key: output[key]
            for key in (
                "compared_count",
                "official_symbols_compared",
                "outside_or_edge_official_count",
                "unmatched_in_frame_count",
            )
        }
    )


if __name__ == "__main__":
    main()
