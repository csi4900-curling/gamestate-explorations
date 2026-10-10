"""Expose path-to-board and neighboring-board gaps for Czech S04/S13."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from adjacent_partial_board import compare_adjacent_rows

BASE = ROOT / "validation/throw-event-benchmark"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1"
UNION = RUN / "candidate-state-evidence-union-development.json"
RAW = RUN / "run-02/raw.json"
MOTION = BASE / "canada-czech-2024/full-match-motion-merged-postscore.json"
EPISODES = BASE / "canada-czech-2024/full-source-diverse-episode-state-handoff-development.json"
COMPARE_CODE = ROOT / "prototype/adjacent_partial_board.py"
OUT = RUN / "rescued-stone-path-to-board-gap-development.json"
TARGETS = {"S04": "E003", "S13": "E011"}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def comparable_episode(episode):
    observed = episode.get("post_event_partial_board")
    board = {
        "status": (
            observed["status"]
            if episode["state_status"] == "partial_board_observed"
            else episode["state_status"]
        )
    }
    if episode["state_status"] == "partial_board_observed":
        board["stones"] = [
            {
                "local_observation_id": row["local_observation_id"],
                "colour": row["colour"],
                "view_local_ground_position_m": row["position_m_conditional"],
            }
            for row in observed["stones"]
        ]
    return {
        "candidate_id": episode["episode_id"],
        "crossing_time_s": episode["observation_time_s"],
        "receiving_view": observed["receiving_view"] if observed else None,
        "board": board,
    }


def main():
    if OUT.exists():
        raise ValueError("Rescued-stone board-gap audit already exists")
    union, raw, motion, handoff = (
        json.loads(path.read_text()) for path in (UNION, RAW, MOTION, EPISODES)
    )
    source = raw["source_sha256"]
    if not (
        union["source_sha256"]
        == source
        == motion["candidate_source_sha256"]
        == handoff["source_video_sha256"]
    ):
        raise ValueError("Source hash mismatch")
    if union["input_sha256"]["current_raw"] != digest(RAW) or union["input_sha256"][
        "historical_episodes"
    ] != digest(EPISODES):
        raise ValueError("Input lineage mismatch")
    raw_by_id = {row["id"]: row for row in raw["events"]}
    motion_by_id = {row["candidate_id"]: row for row in motion["rows"]}
    union_by_id = {row["candidate_id"]: row for row in union["rows"]}
    episodes = handoff["episodes"]
    indices = {row["episode_id"]: index for index, row in enumerate(episodes)}
    if len(motion_by_id) != len(motion["rows"]) or len(indices) != len(episodes):
        raise ValueError("Repeated motion or episode ID")
    rows = []
    for id, episode_id in TARGETS.items():
        proposal, path_row = raw_by_id[id], motion_by_id[id]
        event = episodes[indices[episode_id]]
        union_row = union_by_id[f"left:{id}"]
        if (
            proposal["crossing_time_s"] != path_row["crossing_time_s"]
            or proposal["colour"] != path_row["colour"]
            or union_row["historical_episode_id"] != episode_id
            or not union_row["dual_observer_supported"]
            or union_row["context_disposition"] != "needs_review"
            or event["state_status"] != "partial_board_observed"
        ):
            raise ValueError(f"Target lineage differs: {id}")
        path = path_row["selection"]["path"]
        if not path or any(
            a["source_time_s"] >= b["source_time_s"] for a, b in zip(path, path[1:])
        ):
            raise ValueError(f"Invalid selected motion path: {id}")
        board = event["post_event_partial_board"]
        same_colour = [stone for stone in board["stones"] if stone["colour"] == proposal["colour"]]
        if not same_colour:
            raise ValueError(f"No same-colour board observation: {id}")
        last_path_s = path[-1]["source_time_s"]
        earliest_same_colour_s = min(stone["first_seen_s"] for stone in same_colour)
        if earliest_same_colour_s <= last_path_s:
            raise ValueError(f"Expected positive path-to-board gap absent: {id}")
        index = indices[episode_id]
        if index == 0 or index + 1 == len(episodes):
            raise ValueError("Target lacks neighboring episodes")
        neighbors = []
        for label, first, second in (
            ("previous_to_target", episodes[index - 1], event),
            ("target_to_next", event, episodes[index + 1]),
        ):
            result = compare_adjacent_rows(
                comparable_episode(first), comparable_episode(second), raw["events"]
            )
            neighbors.append(
                {
                    "direction": label,
                    "before_episode_id": first["episode_id"],
                    "after_episode_id": second["episode_id"],
                    **result,
                }
            )
        rows.append(
            {
                "candidate_id": id,
                "passage_time_s": proposal["crossing_time_s"],
                "episode_id": episode_id,
                "selected_receiving_motion_status": path_row["selection"]["status"],
                "selected_path_first_s": path[0]["source_time_s"],
                "selected_path_last_s": last_path_s,
                "selected_path_last_ground_position_m_conditional": path[-1]["ground_position_m"],
                "same_colour_partial_board_observations": [
                    {
                        "local_observation_id": stone["local_observation_id"],
                        "first_seen_s": stone["first_seen_s"],
                        "position_m_conditional": stone["position_m_conditional"],
                        "persistent_stone_identity": stone["persistent_stone_identity"],
                    }
                    for stone in same_colour
                ],
                "minimum_unobserved_path_to_board_s": round(
                    earliest_same_colour_s - last_path_s, 3
                ),
                "neighboring_board_comparisons": neighbors,
                "delivered_stone_board_identity_verified": False,
                "physical_settle_time_verified": False,
                "simulation_ready": False,
            }
        )
    OUT.write_text(
        json.dumps(
            {
                "status": "development_rescued_stone_path_to_board_gap_not_identity_proof",
                "source_sha256": source,
                "input_sha256": {
                    "current_raw": digest(RAW),
                    "candidate_state_union": digest(UNION),
                    "historical_motion": digest(MOTION),
                    "historical_episodes": digest(EPISODES),
                },
                "code_sha256": {
                    "runner": digest(Path(__file__)),
                    "board_comparison": digest(COMPARE_CODE),
                },
                "rows": rows,
                "limitations": [
                    "The selected receiving paths and partial boards use conditional view-local projection, not validated physical coordinates.",
                    "A temporal gap between selected path and board observation prevents verified same-stone association.",
                    "Near-colour board matches or changes are partial observations, not physical addition, removal, or collision labels.",
                    "The source-selected cases are development diagnostics, not independent throw-event validation.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            [
                (
                    row["candidate_id"],
                    row["minimum_unobserved_path_to_board_s"],
                    [item["status"] for item in row["neighboring_board_comparisons"]],
                )
                for row in rows
            ]
        )
    )


if __name__ == "__main__":
    main()
