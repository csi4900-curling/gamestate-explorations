"""Build source-only partial boards from repeated overhead frames, then audit."""

import hashlib
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations
from prototype.temporal_board_state import stable_board_stones
from prototype.video_board_observation_v2 import detect_board_stones, detect_overhead_house

ALIGNMENT = ROOT / "validation/official-shot-sequence/pwg2022-official-counter-alignment.json"
DIAGRAMS = ROOT / "validation/official-shot-sequence/pwg2022-official-board-diagrams.json"
REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
SAMPLE = ROOT / "validation/official-shot-sequence/pwg2022-video-board-transfer-v2.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-temporal-partial-boards.json"
OFFSETS_S = tuple(range(4, 31, 2))
NEXT_COUNTER_BUFFER_S = 12


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def next_counter_time(counter_rows, current_time):
    return min(
        (row["counter_time_s"] for row in counter_rows if row["counter_time_s"] > current_time),
        default=None,
    )


def scan_frame(cap, fps, time_s):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
    ok, frame = cap.read()
    return cv2.resize(frame, (640, 360)) if ok else None


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first temporal-board audit")
    alignment = json.loads(ALIGNMENT.read_text())
    diagrams = json.loads(DIAGRAMS.read_text())
    reference = json.loads(REFERENCE.read_text())
    sample = json.loads(SAMPLE.read_text())
    source_paths = {
        g["official_game_code"]: ROOT / g["source_video_path"] for g in reference["games"]
    }
    official = {
        shot["official_shot_id"]: shot
        for game in diagrams["games"]
        for end in game["ends"]
        for shot in end["shots"]
    }
    counter_by_game = {g["official_game_code"]: g["counter_rows"] for g in alignment["games"]}
    selected_by_game = {
        code: [row for row in sample["rows"] if row["official_game_code"] == code]
        for code in source_paths
    }
    rows = []
    for code, path in source_paths.items():
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open {path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        scans = []
        for sample_row in selected_by_game[code]:
            anchor_time = sample_row["counter_time_s"]
            following = next_counter_time(counter_by_game[code], anchor_time)
            offsets = [
                offset
                for offset in OFFSETS_S
                if following is None or anchor_time + offset <= following - NEXT_COUNTER_BUFFER_S
            ]
            frames = []
            for offset in offsets:
                time_s = anchor_time + offset
                frame = scan_frame(cap, fps, time_s)
                if frame is None:
                    continue
                house = detect_overhead_house(frame)
                if house is not None:
                    frames.append(
                        {"time_s": time_s, "offset_s": offset, "house": house, "frame": frame}
                    )
            scans.append((sample_row, offsets, frames))
        # Source-only orientation propagation is allowed only if this
        # recording's clear views agree. Opposite views force abstention.
        known = [
            frame["house"]["delivery_side"]
            for _, _, frames in scans
            for frame in frames
            if frame["house"]["delivery_side"] != "uncertain"
        ]
        inferred_side = known[0] if len(known) >= 3 and len(set(known)) == 1 else None
        for sample_row, offsets, frames in scans:
            observations = []
            for item in frames:
                house = dict(item["house"])
                if house["delivery_side"] == "uncertain":
                    if inferred_side is None:
                        continue
                    house["delivery_side"] = inferred_side
                stones = detect_board_stones(item["frame"], house)
                observations.append(
                    {
                        "time_s": item["time_s"],
                        "offset_s": item["offset_s"],
                        "house": house,
                        "stones": stones,
                    }
                )
            stable = stable_board_stones(observations)
            shot = official[sample_row["official_shot_id"]]
            comparison = compare_board_observations(
                stable, shot["stones"], official_house_center_y=shot["house_center_px"][1]
            )
            rows.append(
                {
                    "official_game_code": code,
                    "official_shot_id": sample_row["official_shot_id"],
                    "counter_time_s": sample_row["counter_time_s"],
                    "following_counter_time_s": next_counter_time(
                        counter_by_game[code], sample_row["counter_time_s"]
                    ),
                    "sampled_offsets_s": offsets,
                    "inferred_recording_delivery_side": inferred_side,
                    "accepted_frame_count": len(observations),
                    "frame_observations": [
                        {
                            "time_s": item["time_s"],
                            "offset_s": item["offset_s"],
                            "house": item["house"],
                            "stones": item["stones"],
                        }
                        for item in observations
                    ],
                    "stable_partial_board": stable,
                    "comparison": comparison,
                    "official_symbol_count": len(shot["stones"]),
                }
            )
        cap.release()
    output = {
        "status": "source_video_temporal_partial_board_development_audit_not_throw_f1",
        "sample_sha256": digest(SAMPLE),
        "counter_alignment_sha256": digest(ALIGNMENT),
        "official_diagrams_sha256": digest(DIAGRAMS),
        "source_video_sha256_by_game": {
            g["official_game_code"]: g["source_video_sha256"] for g in reference["games"]
        },
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "stone_detector_sha256": digest(ROOT / "prototype/video_board_observation.py"),
        "temporal_cluster_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rule": "Same fifteen counter anchors as v2; +4..+30 seconds every 2 seconds, stopping 12 seconds before next counter; stable stone requires three frames spanning four seconds, within 0.10 house radii. Inferred delivery side uses unanimous known views per recording only.",
        "sample_count": len(rows),
        "rows_with_accepted_frames": sum(row["accepted_frame_count"] > 0 for row in rows),
        "rows_with_stable_stones": sum(bool(row["stable_partial_board"]) for row in rows),
        "stable_stone_count": sum(len(row["stable_partial_board"]) for row in rows),
        "stable_matched_count": sum(row["comparison"]["matched_count"] for row in rows),
        "stable_unmatched_count": sum(len(row["comparison"]["unmatched_video"]) for row in rows),
        "rows": rows,
        "limitations": [
            "The official diagram is used only after source-video frame selection and temporal clustering, but the sample is still drawn from development recordings.",
            "Counter spacing does not guarantee the next throw has not begun; board time and shot identity remain approximate.",
            "Stable static graphics or people can survive temporal clustering; cropped views cannot show off-frame stones.",
            "This is a partial 2D board observation, not physical game state, release timing, trajectory, or event F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            key: output[key]
            for key in (
                "sample_count",
                "rows_with_accepted_frames",
                "rows_with_stable_stones",
                "stable_stone_count",
                "stable_matched_count",
                "stable_unmatched_count",
            )
        }
    )


if __name__ == "__main__":
    main()
