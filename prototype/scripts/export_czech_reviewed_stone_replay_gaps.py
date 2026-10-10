"""Expose missing path-to-board links for source-reviewed Czech stone prefixes."""

from collections import Counter
from hashlib import sha256
import json
from math import dist
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
HANDOFF = BASE / "full-source-diverse-episode-state-handoff-development.json"
MOTION = BASE / "full-match-motion-merged-postscore.json"
E019_AUDIT = BASE / "e019-settle-continuity-source-audit.json"
OUT = BASE / "full-reviewed-stone-replay-gaps-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Reviewed-stone replay gap artifact already exists")
    handoff, motion = (json.loads(p.read_text()) for p in (HANDOFF, MOTION))
    e019_audit = json.loads(E019_AUDIT.read_text())
    if handoff["source_video_sha256"] != motion["candidate_source_sha256"]:
        raise ValueError("Motion and handoff source differ")
    if (
        e019_audit["source_video_sha256"] != motion["high_resolution_source_sha256"]
        or e019_audit["input_sha256"]["motion"] != digest(MOTION)
        or e019_audit["episode_id"] != "E019"
        or e019_audit["simulation_ready"]
    ):
        raise ValueError("E019 dense source audit lineage differs")
    by_motion = {row["candidate_id"]: row for row in motion["rows"]}
    if len(by_motion) != len(motion["rows"]):
        raise ValueError("Duplicate left motion candidate")
    rows = []
    for episode in handoff["episodes"]:
        stone_ids = episode["source_reviewed_stone_prefix_right_ids"]
        if not stone_ids:
            continue
        if len(stone_ids) != 1:
            raise ValueError("Reviewed stone episode has multiple stone prefixes")
        rid = stone_ids[0]
        linked = [
            p
            for p in episode["cross_resolution_candidate_pair_evidence"]
            if p["right_proposal_id"] == rid and p["sampled_time_overlap_count"] >= 2
        ]
        left_ids = [r["interval_candidate_id"] for r in episode["left_members"]]
        if len({p["left_candidate_id"] for p in linked}) == 1:
            lid = linked[0]["left_candidate_id"]
            basis = "unique_exact_time_pixel_overlap"
        elif len(left_ids) == 1:
            lid = left_ids[0]
            basis = "single_temporal_left_candidate_only"
        else:
            lid = None
            basis = "ambiguous_left_motion_candidate"
        path = by_motion[lid]["selection"].get("path", []) if lid else []
        path_rows = [
            {
                "source_time_s": p["source_time_s"],
                "pixel_center_1080": p["pixel_center"],
                "ground_position_m_conditional": p.get("ground_position_m"),
            }
            for p in path
        ]
        board = episode["post_event_partial_board"]
        stable_board = episode["state_status"] == "partial_board_observed"
        stones = board["stones"] if stable_board else []
        same_colour = [s for s in stones if s["colour"] == episode["colour_claim"]]
        endpoint = path_rows[-1]["ground_position_m_conditional"] if path_rows else None
        nearest_gap = (
            min(dist(endpoint, s["position_m_conditional"]) for s in same_colour)
            if endpoint is not None and same_colour
            else None
        )
        first_same_time = min(s["first_seen_s"] for s in same_colour) if same_colour else None
        last_path_time = path_rows[-1]["source_time_s"] if path_rows else None
        if stable_board and linked:
            tier = "stone_prefix_shared_pixel_path_partial_board"
        elif stable_board:
            tier = "stone_prefix_partial_board_no_shared_pixel_path"
        else:
            tier = "stone_prefix_without_partial_board"
        blockers = [
            "physical_throw_identity_unverified",
            "settled_stone_identity_unverified",
            "complete_board_unobserved",
            "metric_accuracy_unverified",
        ]
        if not path_rows:
            blockers.append("left_motion_path_unavailable")
        if not linked:
            blockers.append("no_exact_time_cross_resolution_path_overlap")
        if not stable_board:
            blockers.append("stable_partial_board_unavailable")
        if stable_board and not same_colour:
            blockers.append("no_same_colour_stone_in_partial_board")
        rows.append(
            {
                "episode_id": episode["episode_id"],
                "reviewed_right_stone_prefix_id": rid,
                "colour_claim": episode["colour_claim"],
                "left_motion_candidate_id": lid,
                "left_assignment_basis": basis,
                "exact_time_overlap_count": max(
                    (p["sampled_time_overlap_count"] for p in linked), default=0
                ),
                "observed_left_motion_path": path_rows,
                "last_observed_motion_time_s": last_path_time,
                "last_observed_ground_position_m_conditional": endpoint,
                "post_event_board_status": episode["state_status"],
                "quiet_tail_start_s": board["quiet_tail_s"][0] if stable_board else None,
                "partial_board_local_stones": stones,
                "same_colour_local_observation_count": len(same_colour),
                "first_same_colour_local_observation_s": first_same_time,
                "path_endpoint_to_nearest_same_colour_board_observation_m_conditional": round(
                    nearest_gap, 3
                )
                if nearest_gap is not None
                else None,
                "last_path_to_first_same_colour_observation_s": (
                    round(first_same_time - last_path_time, 3)
                    if first_same_time is not None and last_path_time is not None
                    else None
                ),
                "local_source_visual_continuity": (
                    {
                        "status": e019_audit["local_red_path_to_board_visual_continuity"],
                        "source_audit_sha256": digest(E019_AUDIT),
                        "independent_identity_verification": False,
                    }
                    if episode["episode_id"] == "E019"
                    else None
                ),
                "replay_evidence_tier": tier,
                "physical_throw_identity_verified": False,
                "settled_stone_identity_verified": False,
                "simulation_ready": False,
                "simulation_blockers": blockers,
            }
        )
    tier_counts = Counter(row["replay_evidence_tier"] for row in rows)
    if (
        len(rows) != 21
        or tier_counts
        != {
            "stone_prefix_shared_pixel_path_partial_board": 7,
            "stone_prefix_partial_board_no_shared_pixel_path": 11,
            "stone_prefix_without_partial_board": 3,
        }
        or sum(not row["observed_left_motion_path"] for row in rows) != 4
        or sum(
            row["same_colour_local_observation_count"] == 0
            for row in rows
            if row["post_event_board_status"] == "partial_board_observed"
            and row["exact_time_overlap_count"] >= 2
        )
        != 2
    ):
        raise ValueError("Reviewed stone replay gap inventory changed")
    result = {
        "status": "reviewed_stone_replay_gaps_not_simulation_ready",
        "source_video_sha256": handoff["source_video_sha256"],
        "input_sha256": {
            "episode_state_handoff": digest(HANDOFF),
            "left_motion": digest(MOTION),
            "e019_dense_source_audit": digest(E019_AUDIT),
        },
        "runner_sha256": digest(Path(__file__)),
        "reviewed_stone_episode_count": len(rows),
        "replay_evidence_tier_counts": dict(tier_counts),
        "left_motion_path_missing_count": sum(not row["observed_left_motion_path"] for row in rows),
        "local_source_visual_continuity_supported_count": sum(
            bool(row["local_source_visual_continuity"]) for row in rows
        ),
        "rows": rows,
        "limitations": [
            "Nearest same-colour board distance is a descriptive gap between a last observed moving point and a camera-local board proposal, not a stone identity or tracking error.",
            "A partial board can omit the delivered colour; absence of a same-colour detection does not prove the stone is physically absent.",
            "Metric ground positions and board positions are conditional projections with unverified accuracy.",
            "Source-reviewed moving-stone pixels and cross-resolution path overlap do not independently verify physical deliveries or a complete event timeline.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "episodes": len(rows),
                "tiers": dict(tier_counts),
                "missing_motion_paths": result["left_motion_path_missing_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
