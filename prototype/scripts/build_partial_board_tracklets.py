"""Build camera-local observation tracklets from conservative board matches."""

import argparse
from collections import Counter
import json
from math import dist
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def build(boards, comparisons, timeline):
    rows = boards["rows"]
    edges = comparisons["comparisons"]
    if len(edges) != max(0, len(rows) - 1):
        raise ValueError("Adjacent comparison coverage differs from board order")
    states = {row["candidate_id"]: row for row in timeline["timeline"]}
    if len(states) != len(timeline["timeline"]):
        raise ValueError("Duplicate timeline candidate ID")
    nodes = {}
    node_order = []
    for row in rows:
        candidate_id = row["candidate_id"]
        state = states[candidate_id]
        if state["post_event_board"] is None or \
                state["receiving_view"] != row["receiving_view"]:
            raise ValueError(f"Timeline board does not match {candidate_id}")
        local_ids = set()
        for stone in row["board"]["stones"]:
            local_id = stone["local_observation_id"]
            if local_id in local_ids:
                raise ValueError(f"Duplicate local observation ID in {candidate_id}")
            local_ids.add(local_id)
            key = (candidate_id, local_id)
            nodes[key] = {
                "candidate_id": candidate_id,
                "local_observation_id": local_id,
                "colour": stone["colour"],
                "receiving_view": row["receiving_view"],
                "view_local_ground_position_m": stone["view_local_ground_position_m"],
                "first_seen_s": stone["first_seen_s"],
                "last_seen_s": stone["last_seen_s"],
                "supporting_frame_count": stone["supporting_frame_count"],
            }
            node_order.append(key)
    predecessor, successor = {}, {}
    for index, comparison in enumerate(edges):
        before, after = rows[index], rows[index + 1]
        if (comparison["before_candidate_id"] != before["candidate_id"] or
                comparison["after_candidate_id"] != after["candidate_id"]):
            raise ValueError("Comparison order differs from board order")
        if comparison["status"] != "view_local_partial_comparison":
            if comparison.get("matched_observations"):
                raise ValueError("Abstained comparison contains associations")
            continue
        if (before["receiving_view"] != after["receiving_view"] or
                before["board"]["status"] != "partial_stable_view_local_board" or
                after["board"]["status"] != "partial_stable_view_local_board" or
                comparison["intervening_passage_candidate_ids"]):
            raise ValueError("Invalid comparable board pair")
        for match in comparison["matched_observations"]:
            left = (before["candidate_id"], match["before_local_observation_id"])
            right = (after["candidate_id"], match["after_local_observation_id"])
            if left not in nodes or right not in nodes:
                raise ValueError("Association references missing stone observation")
            if left in successor or right in predecessor:
                raise ValueError("Association is not one-to-one")
            a, b = nodes[left], nodes[right]
            distance = dist(a["view_local_ground_position_m"],
                            b["view_local_ground_position_m"])
            if (a["colour"] != b["colour"] or
                    a["receiving_view"] != b["receiving_view"] or
                    match["colour"] != a["colour"] or
                    distance > comparisons["max_association_distance_m_conditional"] + 1e-8 or
                    abs(distance - match["distance_m_conditional"]) > 0.00011):
                raise ValueError("Association colour, view or distance differs")
            successor[left] = right
            predecessor[right] = left
    if len(successor) != comparisons["associated_observation_pair_count"]:
        raise ValueError("Association count differs from ledger")
    tracklets = []
    node_tracklet = {}
    for key in node_order:
        if key in predecessor:
            continue
        chain = []
        current = key
        while current is not None:
            if current in node_tracklet:
                raise ValueError("Cycle or reused observation in tracklets")
            chain.append(current)
            node_tracklet[current] = f"O{len(tracklets) + 1:03d}"
            current = successor.get(current)
        first = nodes[chain[0]]
        tracklets.append({
            "tracklet_id": f"O{len(tracklets) + 1:03d}",
            "colour": first["colour"],
            "receiving_view": first["receiving_view"],
            "observation_count": len(chain),
            "observations": [nodes[item] for item in chain],
            "physical_stone_identity_verified": False,
            "metric_accuracy_verified": False,
        })
    if len(node_tracklet) != len(nodes):
        raise ValueError("Unassigned or cyclic observation")
    state_rows = []
    for row in rows:
        candidate_id = row["candidate_id"]
        source_state = states[candidate_id]
        state_rows.append({
            "candidate_id": candidate_id,
            "candidate_event_status": source_state["event_status"],
            "screen_decision": source_state["screen_decision"],
            "passage_time_s": row["crossing_time_s"],
            "receiving_view": row["receiving_view"],
            "partial_board_status": row["board"]["status"],
            "observed_stones": [{
                **stone,
                "observation_tracklet_id": node_tracklet[(candidate_id,
                    stone["local_observation_id"])],
                "physical_stone_identity_verified": False,
            } for stone in row["board"]["stones"]],
            "complete_game_state": False,
            "simulation_ready": False,
        })
    return {
        "observed_stone_count": len(nodes),
        "associated_observation_pair_count": len(successor),
        "tracklet_count": len(tracklets),
        "tracklet_length_counts": dict(Counter(item["observation_count"]
                                             for item in tracklets)),
        "tracklets": tracklets,
        "candidate_states": state_rows,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--boards", type=Path, required=True)
    p.add_argument("--comparisons", type=Path, required=True)
    p.add_argument("--timeline", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Observation-tracklet output already exists")
    boards = json.loads(a.boards.read_text())
    comparisons = json.loads(a.comparisons.read_text())
    timeline = json.loads(a.timeline.read_text())
    if (comparisons["boards_sha256"] != file_sha256(a.boards) or
            timeline["boards_sha256"] != file_sha256(a.boards) or
            comparisons["source_sha256"] != timeline["source_sha256"]):
        p.error("Board, comparison, timeline provenance differs")
    result = {
        "status": "conditional_camera_local_observation_tracklets_not_physical_game_state",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "boards_sha256": file_sha256(a.boards),
        "comparisons_sha256": file_sha256(a.comparisons),
        "timeline_sha256": file_sha256(a.timeline),
        "runner_sha256": file_sha256(Path(__file__)),
        **build(boards, comparisons, timeline),
        "limitations": [
            "Tracklet IDs join uniquely nearby same-colour observations only within consecutive supported same-camera boards.",
            "A tracklet is not verified persistent stone identity, especially across unobserved action or end reset.",
            "No tracklet crosses an abstained comparison or camera change; unmatched observations do not prove appearance or removal.",
            "Positions are conditional view-local projections without independent metric error measurement.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["observed_stone_count"], "stone observations,",
          result["associated_observation_pair_count"], "associations,",
          result["tracklet_count"], "tracklets")


if __name__ == "__main__":
    main()
