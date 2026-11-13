"""Postscore test of naive ellipse normalization, without exporting a state."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations

BASE = ROOT / "validation/official-shot-sequence"
INPUT = BASE / "china-end2-wide-perspective-cap-evidence-development.json"
DIAGRAMS = BASE / "pwg2022-official-board-diagrams.json"
OUTPUT = BASE / "china-end2-wide-affine-projection-diagnostic.json"
SHOT_ID = "PREL000102-E02-S12"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first projection diagnostic")
    wide, diagrams = (json.loads(path.read_text()) for path in (INPUT, DIAGRAMS))
    official = next(
        shot
        for game in diagrams["games"]
        for end in game["ends"]
        for shot in end["shots"]
        if shot["official_shot_id"] == SHOT_ID
    )
    if len(wide["stable_image_caps"]) != 3:
        raise ValueError("Wide source-only evidence changed")
    ellipse = wide["frames"][0]["ellipse"]
    cx, cy = ellipse["center_px"]
    rx = max(ellipse["axis_lengths_px"]) / 2
    ry = min(ellipse["axis_lengths_px"]) / 2
    alternatives = []
    for lateral_sign in (-1, 1):
        for longitudinal_sign in (-1, 1):
            transformed = [
                {
                    "colour": stone["colour"],
                    "canonical_lateral_house_radii": round(
                        lateral_sign * (stone["pixel_center"][0] - cx) / rx, 4
                    ),
                    "longitudinal_house_radii": round(
                        longitudinal_sign * (stone["pixel_center"][1] - cy) / ry, 4
                    ),
                }
                for stone in wide["stable_image_caps"]
            ]
            strict = compare_board_observations(
                transformed,
                official["stones"],
                official_house_center_y=official["house_center_px"][1],
            )
            forced = compare_board_observations(
                transformed,
                official["stones"],
                official_house_center_y=official["house_center_px"][1],
                max_match_distance=10,
            )
            alternatives.append(
                {
                    "lateral_sign": lateral_sign,
                    "longitudinal_sign": longitudinal_sign,
                    "naive_ellipse_coordinates": transformed,
                    "matched_within_0_25_house_radii": strict["matched_count"],
                    "forced_mean_error_house_radii": forced["mean_matched_distance_house_radii"],
                    "forced_max_error_house_radii": forced["max_matched_distance_house_radii"],
                }
            )
    output = {
        "status": "postscore_naive_wide_ellipse_projection_failure_not_calibration",
        "source_sha256": wide["source_sha256"],
        "wide_image_evidence_sha256": digest(INPUT),
        "official_diagrams_sha256": digest(DIAGRAMS),
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "shot_id": SHOT_ID,
        "ellipse_frame_time_s": wide["frames"][0]["time_s"],
        "formula": "x=sign_x*(pixel_x-cx)/major_radius; y=sign_y*(pixel_y-cy)/minor_radius",
        "match_tolerance_house_radii": 0.25,
        "alternatives": alternatives,
        "limitations": [
            "Official positions are used only to score these four naive postscore alternatives.",
            "Selecting the best sign from the official diagram would leak reference data.",
            "A single fitted ellipse does not provide a validated planar homography.",
            "No transformed coordinate is exported as video-derived game state.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        [
            (
                row["lateral_sign"],
                row["longitudinal_sign"],
                row["matched_within_0_25_house_radii"],
                row["forced_mean_error_house_radii"],
            )
            for row in alternatives
        ]
    )


if __name__ == "__main__":
    main()
