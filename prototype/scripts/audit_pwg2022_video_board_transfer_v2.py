"""Check source-video overhead boards against official post-shot diagrams.

Frame and house selection use only counter timing and broadcast pixels. Official
diagram positions are loaded after the frame has been selected.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations
from prototype.video_board_observation_v2 import detect_board_stones, detect_overhead_house

ALIGNMENT = ROOT / "validation/official-shot-sequence/pwg2022-official-counter-alignment.json"
DIAGRAMS = ROOT / "validation/official-shot-sequence/pwg2022-official-board-diagrams.json"
REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-video-board-transfer-v2.json"
OFFSETS_S = (6, 12, 18, 24, 30)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spread_sample(rows, count=5):
    return [rows[round(index * (len(rows) - 1) / (count - 1))] for index in range(count)]


def read_frame(cap, fps, time_s):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
    ok, frame = cap.read()
    if not ok:
        return None
    return cv2.resize(frame, (640, 360))


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first transfer audit")
    alignment = json.loads(ALIGNMENT.read_text())
    diagrams = json.loads(DIAGRAMS.read_text())
    reference = json.loads(REFERENCE.read_text())
    if alignment["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Counter alignment reference hash differs")
    shot_diagrams = {
        shot["official_shot_id"]: shot
        for game in diagrams["games"]
        for end in game["ends"]
        for shot in end["shots"]
    }
    paths = {
        game["official_game_code"]: ROOT / game["source_video_path"] for game in reference["games"]
    }
    rows = []
    for game in alignment["games"]:
        code = game["official_game_code"]
        eligible = [
            row
            for row in game["counter_rows"]
            if row["status"] == "unique_colour_concordant" and row["inferred_shot_number"] >= 5
        ]
        selected = spread_sample(eligible)
        cap = cv2.VideoCapture(str(paths[code]))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot read {paths[code]}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        for anchor in selected:
            choices = []
            for offset in OFFSETS_S:
                frame = read_frame(cap, fps, anchor["counter_time_s"] + offset)
                if frame is None:
                    continue
                house = detect_overhead_house(frame)
                if house is not None and house["delivery_side"] != "uncertain":
                    choices.append(
                        (
                            house["annulus_support"]["mean_blue_fraction"],
                            house["annulus_support"]["supported_angle_bins"],
                            -offset,
                            offset,
                            frame,
                            house,
                        )
                    )
            row = {
                "official_game_code": code,
                "official_shot_id": anchor["official_shot_id"],
                "counter_id": anchor["counter_id"],
                "counter_time_s": anchor["counter_time_s"],
                "sampled_offsets_s": list(OFFSETS_S),
            }
            if not choices:
                row["status"] = "no_confident_overhead_frame"
            else:
                _, _, _, offset, frame, house = max(choices, key=lambda x: x[:3])
                stones = detect_board_stones(frame, house)
                official = shot_diagrams[anchor["official_shot_id"]]
                comparison = compare_board_observations(
                    stones,
                    official["stones"],
                    official_house_center_y=official["house_center_px"][1],
                )
                row.update(
                    {
                        "status": "compared",
                        "video_time_s": anchor["counter_time_s"] + offset,
                        "house": house,
                        "video_stones": stones,
                        "official_stone_counts": official["stone_counts"],
                        "official_review_flags": official["review_flags"],
                        "comparison": comparison,
                    }
                )
            rows.append(row)
        cap.release()
    compared = [row for row in rows if row["status"] == "compared"]
    output = {
        "status": "development_video_board_transfer_diagnostic_not_throw_event_f1",
        "source_video_sha256_by_game": {
            g["official_game_code"]: g["source_video_sha256"] for g in reference["games"]
        },
        "counter_alignment_sha256": digest(ALIGNMENT),
        "official_diagrams_sha256": digest(DIAGRAMS),
        "video_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "stone_detector_sha256": digest(ROOT / "prototype/video_board_observation.py"),
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "Five evenly spaced unique colour-concordant counter anchors with shot number >=5 per game; sample +6,+12,+18,+24,+30 seconds; select accepted overhead with strongest blue ring, without official board positions.",
        "sample_count": len(rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "complete_board_match_count": sum(
            row["comparison"]["matched_count"]
            == row["comparison"]["video_stone_count"]
            == row["comparison"]["official_symbol_count"]
            for row in compared
        ),
        "rows": rows,
        "limitations": [
            "Counter timing and official shot links come from development-source broadcasts; this is not a held-out evaluation.",
            "A selected frame may be before a stone settles or after the next delivery; official PDF diagrams have no video timestamps.",
            "People, handles, graphics, occlusion, camera perspective and partial houses may create false or missed stone detections.",
            "Matching anonymous stones in 2D does not recover release time, motion trajectory, collision sequence or physical 3D state.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: output[key]
                for key in ("sample_count", "status_counts", "complete_board_match_count")
            }
        )
    )


if __name__ == "__main__":
    main()
