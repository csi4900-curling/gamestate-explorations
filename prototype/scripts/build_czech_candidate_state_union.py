"""Join current Czech candidate evidence to historical partial state episodes."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1"
RAW = RUN / "run-02/raw.json"
EVENTS = RUN / "run-02/events.json"
TRIAGE = RUN / "run-02/triage.json"
END_INVENTORY = RUN / "end-conditioned-candidate-inventory.json"
DUAL = RUN / "dual-observer-corroboration-development.json"
OLD_RAW = BASE / "canada-czech-2024/full-match-stage1-raw-postscore.json"
EPISODES = BASE / "canada-czech-2024/full-source-diverse-episode-state-handoff-development.json"
OUT = RUN / "candidate-state-evidence-union-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def unknown_game_state():
    return {"physical_throw_identity_verified": False,
            "physical_release_time_s": None,
            "physical_settle_time_s": None,
            "delivered_stone_identity": None,
            "complete_board": None,
            "persistent_stone_identities": None,
            "metric_trajectory": None,
            "spin_revolution_count": None,
            "simulation_ready": False}


def main():
    if OUT.exists():
        raise ValueError("Czech candidate-state union already exists")
    raw, events, triage, inventory, dual, old_raw, handoff = (
        json.loads(path.read_text()) for path in
        (RAW, EVENTS, TRIAGE, END_INVENTORY, DUAL, OLD_RAW, EPISODES))
    source = raw["source_sha256"]
    if any(value != source for value in (
            events["source_sha256"], triage["source_sha256"],
            inventory["source_sha256"], dual["source_sha256"],
            old_raw["source_sha256"], handoff["source_video_sha256"])):
        raise ValueError("Input source fingerprints differ")
    signature = lambda artifact: [(row["id"], row["crossing_time_s"],
                                   row["colour"]) for row in artifact["events"]]
    if signature(raw) != signature(old_raw):
        raise ValueError("Historical raw candidate signature differs")
    if (events["input_sha256"] != digest(RAW) or
            triage["raw_sha256"] != digest(RAW) or
            triage["confirmation_sha256"] != digest(EVENTS) or
            inventory["input_sha256"]["raw"] != digest(RAW) or
            dual["input_sha256"]["current_raw"] != digest(RAW) or
            dual["input_sha256"]["current_events"] != digest(EVENTS) or
            dual["input_sha256"]["old_handoff"] != digest(EPISODES)):
        raise ValueError("Input artifact lineage differs")
    ids = [row["id"] for row in raw["events"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate raw candidate ID")
    by_triage = {row["id"]: row for row in triage["proposals"]}
    by_end = {row["candidate_id"]: row for row in inventory["rows"]}
    by_dual = {row["candidate_id"]: row for row in dual["rows"]}
    if any(set(group) != set(ids) or len(group) != len(ids) for group in
           (by_triage, by_end, by_dual)):
        raise ValueError("Candidate sidecars do not cover raw proposals")
    confirmed = {row["id"] for row in events["events"]}
    if confirmed != {id for id, row in by_triage.items() if row[
            "disposition"] == "auto_confirmed_candidate"} or \
            confirmed != {id for id, row in by_dual.items() if row[
                "context_confirmed"]}:
        raise ValueError("Context confirmation differs between sidecars")
    episode_by_left = {}
    right_only = []
    board_episodes = set()
    for episode in handoff["episodes"]:
        if episode.get("complete_game_state") or episode.get("simulation_ready"):
            raise ValueError("Unexpected verified historical state")
        if episode["state_status"] == "partial_board_observed":
            if episode.get("post_event_partial_board") is None:
                raise ValueError("Partial board status lacks board observation")
            board_episodes.add(episode["episode_id"])
        if not episode["left_members"]:
            if episode["episode_kind"] != "right_only_candidate":
                raise ValueError("Episode without left members is not right-only")
            right_only.append(episode)
        for member in episode["left_members"]:
            id = member["full_match_candidate_id"]
            if id in episode_by_left or id not in by_triage:
                raise ValueError(f"Duplicate or unknown historical left ID: {id}")
            episode_by_left[id] = (episode, member)
    rows = []
    for proposal in raw["events"]:
        id = proposal["id"]
        old = episode_by_left.get(id)
        episode, member = old if old else (None, None)
        end = by_end[id]
        dual_row = by_dual[id]
        rows.append({
            "candidate_id": f"left:{id}",
            "candidate_origin": "current_left_raw_proposal",
            "observation_time_s": proposal["crossing_time_s"],
            "time_semantics": proposal["time_semantics"],
            "colour_claim": proposal["colour"],
            "context_disposition": by_triage[id]["disposition"],
            "context_reason": by_triage[id]["stage_evidence"][0]["reason"],
            "dual_observer_supported": dual_row["dual_observer_supported"],
            "supporting_right_proposal_ids": [item["right_proposal_id"] for item
                                              in dual_row["supporting_right_proposals"]],
            "broadcast_marker_status": end["marker_status"],
            "possible_broadcast_end_markers": end["possible_end_numbers"],
            "historical_episode_id": episode["episode_id"] if episode else None,
            "historical_episode_kind": episode["episode_kind"] if episode else None,
            "historical_screen_status": member["screen_status"] if member else None,
            "historical_state_status": episode["state_status"] if episode else None,
            "partial_board_observation_ref": ({
                "episode_id": episode["episode_id"],
                "historical_artifact_sha256": digest(EPISODES),
                "shared_with_other_left_candidates": len(episode["left_members"]) > 1,
                "conditional_coordinate_frame": True,
            } if episode and episode["state_status"] ==
                 "partial_board_observed" else None),
            "game_state_after": unknown_game_state(),
        })
    for episode in right_only:
        rows.append({
            "candidate_id": f"right-only:{episode['episode_id']}",
            "candidate_origin": "historical_right_only_proposal_episode",
            "observation_time_s": episode["observation_time_s"],
            "time_semantics": episode["observation_time_semantics"],
            "colour_claim": episode["colour_claim"],
            "context_disposition": "not_evaluated_by_left_context_gate",
            "context_reason": None,
            "dual_observer_supported": False,
            "supporting_right_proposal_ids": episode["right_proposal_ids"],
            "broadcast_marker_status": "not_assigned_in_this_union",
            "possible_broadcast_end_markers": [],
            "historical_episode_id": episode["episode_id"],
            "historical_episode_kind": episode["episode_kind"],
            "historical_screen_status": None,
            "historical_state_status": episode["state_status"],
            "partial_board_observation_ref": ({
                "episode_id": episode["episode_id"],
                "historical_artifact_sha256": digest(EPISODES),
                "shared_with_other_left_candidates": False,
                "conditional_coordinate_frame": True,
            } if episode["state_status"] == "partial_board_observed" else None),
            "game_state_after": unknown_game_state(),
        })
    rows.sort(key=lambda row: (row["observation_time_s"], row["candidate_id"]))
    candidate_ids = [row["candidate_id"] for row in rows]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Duplicate unified candidate ID")
    OUT.write_text(json.dumps({
        "status": "lossless_candidate_to_partial_board_evidence_union_not_physical_throw_sequence",
        "source_sha256": source,
        "input_sha256": {"current_raw": digest(RAW), "current_events": digest(EVENTS),
                         "current_triage": digest(TRIAGE),
                         "broadcast_end_inventory": digest(END_INVENTORY),
                         "dual_observer": digest(DUAL),
                         "historical_raw": digest(OLD_RAW),
                         "historical_episodes": digest(EPISODES)},
        "runner_sha256": digest(Path(__file__)),
        "left_raw_candidate_count": len(ids),
        "historical_left_member_count": len(episode_by_left),
        "left_candidates_without_historical_episode_count": len(ids) - len(episode_by_left),
        "historical_right_only_episode_count": len(right_only),
        "unique_historical_partial_board_episode_count": len(board_episodes),
        "candidate_row_count": len(rows),
        "candidate_origin_counts": dict(Counter(row["candidate_origin"] for row in rows)),
        "physical_throw_count_verified": None,
        "complete_throw_sequence_verified": False,
        "rows": rows,
        "limitations": [
            "The union lists proposals, not distinct physical throws; right-only and left entries may refer to the same event.",
            "Historical episode boards are view-local partial observations and may be shared across multiple candidates.",
            "Neither an episode association nor dual-observer agreement verifies physical stone identity across views.",
            "The first and last layout-unknown source spans remain coverage gaps; this union does not recover them.",
        ],
    }, indent=2) + "\n")
    print(json.dumps({"left": len(ids), "historical_left": len(episode_by_left),
                      "right_only": len(right_only), "rows": len(rows),
                      "partial_board_episodes": len(board_episodes)}))


if __name__ == "__main__":
    main()
