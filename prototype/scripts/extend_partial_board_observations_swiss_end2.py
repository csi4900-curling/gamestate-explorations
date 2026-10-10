"""Extend video board export with two adjacent Swiss end-two snapshots."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.game_state_observation import partial_board_observation

BASE = ROOT / "validation/official-shot-sequence"
ORIGINAL = BASE / "pwg2022-video-partial-board-observations.json"
ADJACENT = BASE / "swiss-end2-adjacent-video-boards-first.json"
OUTPUT = BASE / "pwg2022-video-partial-board-observations-v2.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first extended export")
    original, adjacent = (json.loads(path.read_text()) for path in (ORIGINAL, ADJACENT))
    source_hash = adjacent["source_sha256"]
    old_by_id = {row["observation_id"]: row for row in original["observations"]}
    added = []
    for row in adjacent["rows"]:
        adapted = {
            "official_game_code": "PREL000101",
            "official_shot_id": row["shot_id"],
            "counter_time_s": row["counter_anchor_s"],
            "stable_partial_board": row["stable_partial_board"],
        }
        observation = partial_board_observation(adapted, source_hash)
        if observation is None:
            continue
        old = old_by_id.get(observation["observation_id"])
        if old is not None:
            if old != observation:
                raise ValueError("Previously exported board changed")
        else:
            added.append(observation)
    if sorted(row["observation_id"].split("-")[-1] for row in added) != ["S13", "S14"]:
        raise ValueError("Expected exactly Swiss end-two shots 13 and 14")
    observations = original["observations"] + added
    output = {
        "status": "extended_partial_video_board_export_not_complete_game_state",
        "original_export_sha256": digest(ORIGINAL),
        "adjacent_source_scan_sha256": digest(ADJACENT),
        "export_code_sha256": digest(ROOT / "prototype/game_state_observation.py"),
        "runner_sha256": digest(Path(__file__)),
        "original_observation_count": len(original["observations"]),
        "added_observation_count": len(added),
        "observation_count": len(observations),
        "stone_observation_count": sum(len(row["stones"]) for row in observations),
        "observations": observations,
        "limitations": [
            "All observations remain partial/unknown from video and not simulation-ready.",
            "The new adjacent shots were selected around an earlier successful development board.",
            "No official diagram positions are exported or used to create these boards.",
            "Local stone IDs do not establish persistent physical identities.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            "observations": output["observation_count"],
            "new": output["added_observation_count"],
            "stones": output["stone_observation_count"],
        }
    )


if __name__ == "__main__":
    main()
