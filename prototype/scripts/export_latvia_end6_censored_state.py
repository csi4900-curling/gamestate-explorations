"""Export a source-fingerprinted, camera-censored Latvia event/state handoff."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from censored_event_state_handoff import build_censored_event_state_handoff


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "body-links",
        "partial-state",
        "boundary",
        "lowres-video",
        "highres-video",
        "output",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    links, partial, boundary = (
        json.loads(path.read_text())
        for path in (args.body_links, args.partial_state, args.boundary)
    )
    if (
        digest(args.lowres_video) != links["lowres_source_sha256"]
        or digest(args.highres_video) != links["highres_source_sha256"]
        or digest(args.body_links) != boundary["body_links_sha256"]
    ):
        raise ValueError("Video or boundary lineage differs")
    rows = build_censored_event_state_handoff(links, partial, boundary)
    output = {
        "status": "camera_censored_partial_observation_not_game_state_or_simulation",
        "source_video_sha256": {
            "lowres": links["lowres_source_sha256"],
            "highres": links["highres_source_sha256"],
        },
        "source_interval_s": links["source_interval_s"],
        "input_sha256": {
            "body_links": digest(args.body_links),
            "partial_state": digest(args.partial_state),
            "boundary": digest(args.boundary),
        },
        "model_code_sha256": digest(ROOT / "prototype/censored_event_state_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(rows),
        "source_reviewed_moving_stone_pixel_count": sum(
            row["source_prefix_class"] == "moving_stone_pixels" for row in rows
        ),
        "unique_next_second_colour_component_count": sum(
            row["terminal_visibility"] is not None
            and row["terminal_visibility"]["next_second_colour_screen"]["status"]
            == "unique_colour_component_provisional"
            for row in rows
        ),
        "following_partial_image_board_count": sum(
            row["following_partial_image_board"] is not None for row in rows
        ),
        "physical_settle_verified_count": 0,
        "simulation_ready_count": 0,
        "events": rows,
        "limitations": [
            "All source classes and one-second tail rules are same-match development evidence, not independent throw labels.",
            "Colour components after the saved body path are provisional pixel continuations, not verified same-stone identity.",
            "The selected A401 frame-boundary witness does not prove a terminal cause for every path.",
            "Later partial boards are neither complete nor linked to the earlier moving stone by physical identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidates": len(rows),
                "stone_pixels": output["source_reviewed_moving_stone_pixel_count"],
                "colour_tails": output["unique_next_second_colour_component_count"],
                "partial_boards": output["following_partial_image_board_count"],
                "simulation_ready": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
