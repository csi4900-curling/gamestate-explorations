#!/usr/bin/env python3
"""Compare source-selected adjacent video boards with official diagram deltas."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_board_transitions import stable_symbol_pairs  # noqa: E402

SOURCE = (
    ROOT / "validation/official-shot-sequence/norway-full-match-evidence-state-handoff-first.json"
)
TARGET = ROOT / "validation/official-shot-sequence/norway-adjacent-video-board-changes-first.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparable_group(slot):
    # The first qualifying group is chosen without consulting official symbols.
    return next(
        (
            group
            for group in slot["video_post_shot_state"]["camera_groups"]
            if group["layout_side_proxy"] == "top"
        ),
        None,
    )


def normalized(stones, key):
    return [{"colour": stone["colour"], "house_radius_coordinates": stone[key]} for stone in stones]


def signature(previous, current, delta):
    return {
        colour: {
            "coordinate_stable": sum(
                pair["colour"] == colour for pair in delta["coordinate_stable_pairs"]
            ),
            "unresolved_previous": sum(
                previous[i]["colour"] == colour for i in delta["unresolved_previous_symbol_indices"]
            ),
            "unresolved_current": sum(
                current[j]["colour"] == colour for j in delta["unresolved_current_symbol_indices"]
            ),
        }
        for colour in ("red", "yellow")
    }


def main():
    source = json.loads(SOURCE.read_text())
    slots = source["slots"]
    rows = []
    for first, second in zip(slots, slots[1:]):
        if first["end"] != second["end"] or second["shot_number"] != first["shot_number"] + 1:
            continue
        a, b = comparable_group(first), comparable_group(second)
        if a is None or b is None:
            continue
        video_before = normalized(
            a["stable_image_relative_stones"], "image_house_radius_coordinates"
        )
        video_after = normalized(
            b["stable_image_relative_stones"], "image_house_radius_coordinates"
        )
        # Coordinate tolerance allows small independent camera registration drift.
        video_delta = stable_symbol_pairs(video_before, video_after, 0.10)
        official_before = first["official_reference"]["post_shot_diagram_stones"]
        official_after = second["official_reference"]["post_shot_diagram_stones"]
        official_delta = stable_symbol_pairs(official_before, official_after, 0.05)
        video_signature = signature(video_before, video_after, video_delta)
        official_signature = signature(official_before, official_after, official_delta)
        rows.append(
            {
                "end": first["end"],
                "from_official_shot_id": first["official_shot_id"],
                "to_official_shot_id": second["official_shot_id"],
                "from_camera_shot_id": a["camera_shot_id"],
                "to_camera_shot_id": b["camera_shot_id"],
                "video_observation_intervals_s": [
                    a["observation_interval_s"],
                    b["observation_interval_s"],
                ],
                "video_stones": {"before": video_before, "after": video_after},
                "video_coordinate_delta": video_delta,
                "video_colour_change_signature": video_signature,
                "official_colour_change_signature": official_signature,
                "colour_change_signature_agreement": video_signature == official_signature,
                "video_post_shot_complete_state_verified": False,
                "physical_stone_identity_verified": False,
            }
        )
    result = {
        "status": "retrospective_development_comparison_not_complete_video_state_accuracy",
        "source_handoff_sha256": sha256(SOURCE),
        "matching_code_sha256": sha256(ROOT / "prototype/official_board_transitions.py"),
        "runner_sha256": sha256(Path(__file__)),
        "selection": "Consecutive slots in one end, each with a stable video board in a camera group whose source-derived layout_side_proxy is top; choose the first such group in each slot.",
        "video_coordinate_tolerance_house_radii": 0.10,
        "official_coordinate_tolerance_house_radii": 0.05,
        "selected_adjacent_pair_count": len(rows),
        "colour_change_signature_agreement_count": sum(
            row["colour_change_signature_agreement"] for row in rows
        ),
        "rows": rows,
        "limitations": [
            "The selected pairs are a development subset of 120 within-end adjacent official-shot transitions.",
            "The official slot-to-video candidate links are provisional, not independently verified physical throw identities.",
            "Image-relative house coordinates are comparable only within a compatible camera orientation; no metric calibration is claimed.",
            "Equal colour-change signatures do not prove stone identities, complete boards, collision paths, or accurate event segmentation.",
        ],
    }
    TARGET.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(TARGET),
                "selected_pairs": len(rows),
                "signature_agreements": result["colour_change_signature_agreement_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
