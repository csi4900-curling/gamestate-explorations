"""Export source-linked partial video boards with explicit simulation limits."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.game_state_observation import partial_board_observation


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temporal-boards", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first state export")
    source = json.loads(args.temporal_boards.read_text())
    hashes = source["source_video_sha256_by_game"]
    observations = []
    for row in source["rows"]:
        game = row["official_game_code"]
        observation = partial_board_observation(row, hashes[game])
        if observation is not None:
            observations.append(observation)
    output = {
        "status": "partial_video_board_observation_export_not_complete_game_state",
        "temporal_board_input_sha256": digest(args.temporal_boards),
        "export_code_sha256": digest(ROOT / "prototype/game_state_observation.py"),
        "runner_sha256": digest(Path(__file__)),
        "input_sample_count": len(source["rows"]),
        "observation_count": len(observations),
        "stone_observation_count": sum(len(row["stones"]) for row in observations),
        "observations": observations,
        "limitations": [
            "These positions come from video temporal consensus; official diagram positions are not exported.",
            "A board may be incomplete even when every emitted stone is correct.",
            "Counter anchors are delayed and do not establish exact throw or settle time.",
            "The unitless image-derived frame has no validated metric or 3D transform.",
            "Stone IDs are local to each snapshot and cannot yet seed a physical trajectory simulation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print({"partial_boards": len(observations),
           "stone_observations": output["stone_observation_count"]})


if __name__ == "__main__":
    main()
