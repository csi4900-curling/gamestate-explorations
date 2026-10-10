"""Join source-reviewed 360p moving caps to 1080p body/handle paths."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cross_resolution_body_cap import compatible_body_path


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("low-segments", "red-highres", "yellow-highres", "highres-video", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    low, red, yellow = (
        json.loads(path.read_text())
        for path in (args.low_segments, args.red_highres, args.yellow_highres)
    )
    high_source_hash = digest(args.highres_video)
    if (
        red["source_video_sha256"] != high_source_hash
        or yellow["blind_video_sha256"] != high_source_hash
        or red["source_interval_s"] != [5670, 6670]
        or yellow["body_probe_sha256"] is None
    ):
        raise ValueError("High-resolution source or interval differs")
    paths = {
        "red": red["red_supported_image_paths"],
        "yellow": yellow["supported_image_paths"],
    }
    for colour, entries in paths.items():
        ids = [row["diagnostic_path_id"] for row in entries]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {colour} high-resolution path ID")
    reviewed = [row for row in low["rows"] if row["source_prefix_class"]]
    if len(reviewed) != 20 or any(not 5670 <= row["passage_time_s"] <= 6670 for row in reviewed):
        raise ValueError("Expected complete end-six source-reviewed subset")
    provisional = []
    for row in reviewed:
        source_class = row["source_prefix_class"]
        base = {
            "right_proposal_id": row["right_proposal_id"],
            "episode_id": row["episode_id"],
            "source_prefix_class": source_class,
            "colour_claim": row["colour_claim"],
            "observed_motion_onset": row["observed_motion_onset"],
            "following_partial_image_state_status": row["following_partial_image_state_status"],
        }
        if source_class != "moving_stone_pixels":
            provisional.append(
                {
                    **base,
                    "body_path_status": "not_attempted_person_or_clothing_pixels",
                    "compatible_highres_paths": [],
                }
            )
            continue
        onset = row["observed_motion_onset"]
        if onset["status"] != "observed_quiet_to_sustained_directional_motion":
            provisional.append(
                {
                    **base,
                    "body_path_status": "lowres_motion_onset_unavailable",
                    "compatible_highres_paths": [],
                }
            )
            continue
        options = []
        for high in paths[row["colour_claim"]]:
            match = compatible_body_path(onset["observed_moving_points"], high["points"])
            if match is not None:
                options.append(
                    {
                        "highres_path_id": high["diagnostic_path_id"],
                        "highres_path_first_observed_s": high["first_observed_s"],
                        "highres_path_last_observed_s": high["last_observed_s"],
                        "highres_handle_supported_moving_points": [
                            point
                            for point in high["points"]
                            if onset["first_strong_motion_time_s"]
                            <= point["time_s"]
                            <= high["last_observed_s"]
                        ],
                        **match,
                    }
                )
        provisional.append(
            {
                **base,
                "body_path_status": (
                    "unique_compatible_body_path"
                    if len(options) == 1
                    else "no_compatible_body_path"
                    if not options
                    else "ambiguous_compatible_body_paths"
                ),
                "compatible_highres_paths": options,
            }
        )
    owners = {}
    for row in provisional:
        if row["body_path_status"] != "unique_compatible_body_path":
            continue
        key = (row["colour_claim"], row["compatible_highres_paths"][0]["highres_path_id"])
        owners.setdefault(key, []).append(row)
    for linked in owners.values():
        if len(linked) > 1:
            for row in linked:
                row["body_path_status"] = "shared_compatible_body_path"
    matched = {
        (row["colour_claim"], row["compatible_highres_paths"][0]["highres_path_id"])
        for row in provisional
        if row["body_path_status"] == "unique_compatible_body_path"
    }
    output = {
        "status": "postinspection_cross_resolution_body_cap_correspondence_not_complete_trajectory",
        "lowres_source_sha256": low["source_sha256"],
        "highres_source_sha256": high_source_hash,
        "source_interval_s": [5670, 6670],
        "input_sha256": {
            "low_segments": digest(args.low_segments),
            "red_highres": digest(args.red_highres),
            "yellow_highres": digest(args.yellow_highres),
        },
        "join_code_sha256": digest(ROOT / "prototype/cross_resolution_body_cap.py"),
        "runner_sha256": digest(Path(__file__)),
        "matching_rule": {
            "scope": "source-reviewed moving-stone-pixel right-only paths only",
            "minimum_synchronous_moving_points": 2,
            "maximum_absolute_horizontal_offset_360p_px": 12,
            "body_minus_cap_vertical_offset_360p_px": [0, 16],
            "status": "postinspection_development_rule_not_independent_validation",
        },
        "reviewed_proposal_count": len(provisional),
        "body_path_status_counts": dict(Counter(row["body_path_status"] for row in provisional)),
        "unmatched_highres_path_ids": {
            colour: [
                row["diagnostic_path_id"]
                for row in entries
                if (colour, row["diagnostic_path_id"]) not in matched
            ]
            for colour, entries in paths.items()
        },
        "rows": provisional,
        "limitations": [
            "Match geometry was set after inspecting the Latvia body/cap offsets.",
            "Source classes and body/handle paths are same-match development evidence, not independent throw labels.",
            "Synchronous pixel correspondence does not prove identity across a long stationary lead-in.",
            "High-resolution paths still leave this camera; their last point is not the throw end or settled position.",
            "No metric ice calibration, complete board or simulation-ready trajectory is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "reviewed": len(provisional),
                "statuses": output["body_path_status_counts"],
                "unmatched": output["unmatched_highres_path_ids"],
            }
        )
    )


if __name__ == "__main__":
    main()
