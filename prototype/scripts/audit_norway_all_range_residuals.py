"""Countercheck selected end-eight range bias against other comparable boards."""

from collections import defaultdict
from hashlib import sha256
import json
from math import dist
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
SCAN = BASE / "norway-full-candidate-post-counter-long-window-boards-v4.json"
SCORE = BASE / "norway-full-post-counter-long-window-board-postscore-v4.json"
OFFICIAL = BASE / "pwg2022-canada-norway-official-boards.json"
FOCUSED = BASE / "norway-end8-far-house-residual-audit-first.json"
OUTPUT = BASE / "norway-all-range-residual-countercheck-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def earliest(score):
    selected = {}
    for row in score["groups"]:
        key = row["video_candidate_shot_id"]
        if key not in selected or row["source_observation_interval_s"][0] < selected[key]["source_observation_interval_s"][0]:
            selected[key] = row
    return selected


def summarize(pairs):
    return {"pair_count": len(pairs),
            "mean_absolute_longitudinal_delta_house_radii": round(
                sum(abs(row["delta_y_house_radii"]) for row in pairs) / len(pairs), 4)
            if pairs else None,
            "mean_signed_longitudinal_delta_house_radii": round(
                sum(row["delta_y_house_radii"] for row in pairs) / len(pairs), 4)
            if pairs else None}


def main():
    if OUTPUT.exists():
        raise SystemExit("First all-range countercheck already exists")
    scan = json.loads(SCAN.read_text())
    score = json.loads(SCORE.read_text())
    official = json.loads(OFFICIAL.read_text())
    focused = json.loads(FOCUSED.read_text())
    if score["input_sha256"]["source_scan"] != digest(SCAN) or \
            focused["input_sha256"]["source_scan"] != digest(SCAN):
        raise SystemExit("Source scan hash conflict")
    by_candidate = {row["shot_id"]: row for row in scan["rows"]}
    by_official = {shot["official_shot_id"]: shot for end in official["ends"]
                   for shot in end["shots"]}
    rows = []
    excluded = defaultdict(int)
    for scored in earliest(score).values():
        camera = next(group for group in by_candidate[scored["video_candidate_shot_id"]]["camera_shot_boards"]
                      if group["camera_shot_id"] == scored["post_camera_shot_id"])
        shot = by_official[scored["official_shot_id"]]
        if shot["house_center_px"][1] != 440 or camera["detected_delivery_side"] != "top":
            excluded["unsupported_orientation"] += 1
            continue
        if any(sum(stone["colour"] == colour for stone in camera["stable_image_relative_stones"]) !=
               sum(stone["colour"] == colour for stone in shot["stones"])
               for colour in ("red", "yellow")):
            excluded["unequal_per_colour_counts"] += 1
            continue
        pairs = []
        for colour in ("red", "yellow"):
            video = [stone["image_house_radius_coordinates"] for stone in
                     camera["stable_image_relative_stones"] if stone["colour"] == colour]
            reference = [stone["house_radius_coordinates"] for stone in shot["stones"]
                         if stone["colour"] == colour]
            if not video:
                continue
            costs = np.asarray([[dist(a, b) for b in reference] for a in video])
            indices = linear_sum_assignment(costs)
            for vi, oi in zip(*indices):
                a, b = video[int(vi)], reference[int(oi)]
                pairs.append({"colour": colour,
                              "diagram_y_house_radii": b[1],
                              "delta_y_house_radii": round(a[1] - b[1], 4),
                              "range_band": "far_above_house" if b[1] < -1.5 else
                                            "near_house" if abs(b[1]) <= 1.25 else "intermediate"})
        rows.append({"official_shot_id": scored["official_shot_id"],
                     "candidate_id": scored["video_candidate_shot_id"],
                     "post_camera_shot_id": scored["post_camera_shot_id"],
                     "pair_count": len(pairs), "pairs": pairs})
    near = [pair for row in rows for pair in row["pairs"] if pair["range_band"] == "near_house"]
    far = [pair for row in rows for pair in row["pairs"] if pair["range_band"] == "far_above_house"]
    result = {
        "status": "retrospective_comparable_board_range_countercheck_not_general_accuracy",
        "input_sha256": {"source_scan": digest(SCAN), "postscore": digest(SCORE),
                         "official_diagrams": digest(OFFICIAL), "focused_end8_audit": digest(FOCUSED)},
        "runner_sha256": digest(Path(__file__)),
        "selection": "Earliest scoreable camera group by source time; retain only top-layout groups with equal per-colour video/PDF counts; no result-based stone threshold used for pairing.",
        "included_candidate_count": len(rows),
        "excluded_candidate_counts": dict(excluded),
        "near_band": summarize(near),
        "far_band": summarize(far),
        "rows": rows,
        "limitations": [
            "Equal per-colour counts select a favourable subset and do not validate all video detections.",
            "Same-colour assignment is diagnostic, not verified physical stone identity.",
            "Repeated stones across shots are dependent; pair counts are not independent accuracy samples.",
            "The four selected end-eight discrepant boards can still differ materially from this aggregate.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(result["included_candidate_count"], result["near_band"], result["far_band"])


if __name__ == "__main__":
    main()
