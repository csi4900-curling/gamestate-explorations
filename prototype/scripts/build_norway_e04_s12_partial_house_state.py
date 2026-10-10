"""Measure a source-only partial house state, then compare an official diagram."""

from hashlib import sha256
import json
from math import hypot
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.video_board_observation_v2 import detect_overhead_house, detect_board_stones


VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OFFICIAL = ROOT / "validation/official-shot-sequence/pwg2022-canada-norway-official-boards.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-e04-s12-partial-house-state-first.json"
TIMES = [3912.0, 3915.0, 3918.0, 3921.0]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def source_observations():
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    rows = []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, 1000 * t)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot read frame at {t}")
            house = detect_overhead_house(frame)
            if house is None:
                raise RuntimeError(f"Complete overhead house not detected at {t}")
            stones = detect_board_stones(frame, house)
            cx, cy = house["center_px"]
            radius = house["outer_radius_px"]
            normalized = [{**stone,
                           "image_house_radius_coordinates": [
                               round((stone["pixel"][0] - cx) / radius, 4),
                               round((stone["pixel"][1] - cy) / radius, 4)]}
                          for stone in stones]
            rows.append({"time_s": t, "house": house, "visible_stones": normalized})
    finally:
        cap.release()
    return rows


def main():
    if OUTPUT.exists():
        raise SystemExit("First partial house state already exists")
    rows = source_observations()
    if any(len(row["visible_stones"]) != 1 or row["visible_stones"][0]["colour"] != "red"
           for row in rows):
        raise RuntimeError("Expected one visible red stone in each sampled frame")
    if rows[2]["visible_stones"][0]["pixel"] != rows[3]["visible_stones"][0]["pixel"]:
        raise RuntimeError("Final two sampled red positions are not stable")
    state = rows[-1]["visible_stones"][0]
    official = json.loads(OFFICIAL.read_text())
    fourth = next(end for end in official["ends"] if end["end"] == 4)
    before, after = fourth["shots"][10:12]
    if after["official_shot_id"] != "PREL001501-E04-S12" or len(after["stones"]) != 1:
        raise RuntimeError("Expected official after diagram changed")
    reference = after["stones"][0]
    distance = hypot(*(a - b for a, b in zip(
        state["image_house_radius_coordinates"], reference["house_radius_coordinates"])))
    result = {
        "status": "source_only_partial_house_state_with_retrospective_official_comparison",
        "source_video_sha256": digest(VIDEO),
        "official_boards_sha256": digest(OFFICIAL),
        "detector_code_sha256": {
            "v1": digest(ROOT / "prototype/video_board_observation.py"),
            "v2": digest(ROOT / "prototype/video_board_observation_v2.py")},
        "runner_sha256": digest(Path(__file__)),
        "candidate_camera_shot_id": "S281",
        "receiving_camera_shot_id": "S282",
        "proposed_official_shot_id": "PREL001501-E04-S12",
        "source_measurements": rows,
        "observed_partial_house_state": {
            "observation_time_s": TIMES[-1],
            "scope": "Complete visible house, not complete sheet",
            "visible_stone_counts": {"red": 1, "yellow": 0},
            "red_stone_image_house_radius_coordinates": state["image_house_radius_coordinates"],
            "position_stable_at_sampled_times_s": [TIMES[-2], TIMES[-1]],
            "delivery_side_semantics": "Image coordinates: +x right, +y down. Source review shows stone arriving from image top; detector itself marks delivery side uncertain.",
            "complete_game_state": False,
            "simulation_ready": False,
        },
        "retrospective_official_comparison": {
            "before_official_shot_id": before["official_shot_id"],
            "before_house_stone_counts": before["stone_counts"],
            "after_official_shot_id": after["official_shot_id"],
            "after_house_stone_counts": after["stone_counts"],
            "after_red_house_radius_coordinates": reference["house_radius_coordinates"],
            "source_to_diagram_distance_house_radii": round(distance, 4),
            "interpretation": "Agreement with an extracted PDF diagram, not independent physical-position accuracy.",
        },
        "limitations": [
            "The observed state covers the visible house only; out-of-house stones are not inventoried.",
            "No independently calibrated rink coordinates or 3D physical stone identity are provided.",
            "The source-to-official comparison is retrospective and cannot establish independent validation accuracy.",
            "Stable sampled positions are not an exact settle time.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(result["observed_partial_house_state"],
          result["retrospective_official_comparison"]["source_to_diagram_distance_house_radii"])


if __name__ == "__main__":
    main()
