"""Conservative directed path through far receiving-view stone proposals."""

from math import dist


def _can_start(departure, node):
    dt = node["time_s"] - departure["time_s"]
    dx = node["world_m"][0] - departure["world_m"][0]
    dy = node["world_m"][1] - departure["world_m"][1]
    return 0 <= dt <= 2.0 and -0.5 <= dy <= 2.5 + 4.0 * dt and abs(dx) <= 0.75 + 0.5 * dt


def _can_follow(a, b):
    dt = b["time_s"] - a["time_s"]
    dx = b["world_m"][0] - a["world_m"][0]
    dy = b["world_m"][1] - a["world_m"][1]
    return 0 < dt <= 2.0 and -0.25 <= dy <= 4.0 * dt + 0.25 and abs(dx) <= 0.4 + 0.5 * dt


def select_far_receiving_path(row):
    """Select only a unique maximum-coverage path ending at the known arrival.

    The feasibility bounds are loose development values. They reject gross
    temporal/position jumps without claiming a calibrated physical identity.
    """
    departure = {
        "time_s": row["departure_last"]["time_s"],
        "world_m": row["departure_last"]["world_m"],
    }
    arrival = row["arrival_first"]
    nodes = [
        {
            "time_s": sample["source_time_s"],
            "world_m": candidate["world_m"],
            "pixel": candidate["pixel"],
            "sample_candidate_count": sample["corridor_candidate_count"],
        }
        for sample in row["samples"]
        for candidate in sample["corridor_candidates"]
    ]
    if any(a["time_s"] > b["time_s"] for a, b in zip(nodes, nodes[1:])):
        raise ValueError("Candidate nodes must be ordered by time")
    scores = [0] * len(nodes)
    counts = [0] * len(nodes)
    predecessors = [None] * len(nodes)
    for i, node in enumerate(nodes):
        if _can_start(departure, node):
            scores[i], counts[i] = 1, 1
        for j in range(i):
            if not scores[j] or not _can_follow(nodes[j], node):
                continue
            candidate_score = scores[j] + 1
            if candidate_score > scores[i]:
                scores[i], counts[i], predecessors[i] = (candidate_score, counts[j], j)
            elif candidate_score == scores[i]:
                counts[i] = min(2, counts[i] + counts[j])
                predecessors[i] = None
    terminals = [
        i
        for i, node in enumerate(nodes)
        if scores[i]
        and node["time_s"] == arrival["time_s"]
        and dist(node["world_m"], arrival["world_m"]) <= 0.4
    ]
    if not terminals:
        return {
            "status": "no_endpoint_reaching_path",
            "path": [],
            "path_count_capped_at_two": 0,
            "observed_candidate_count": len(nodes),
        }
    best = max(scores[i] for i in terminals)
    winners = [i for i in terminals if scores[i] == best]
    count = min(2, sum(counts[i] for i in winners))
    if count != 1:
        return {
            "status": "multiple_maximum_coverage_paths",
            "path": [],
            "path_count_capped_at_two": count,
            "best_path_sample_count": best,
            "observed_candidate_count": len(nodes),
        }
    path = []
    index = winners[0]
    while index is not None:
        path.append(nodes[index])
        index = predecessors[index]
    path.reverse()
    return {
        "status": "unique_maximum_coverage_path_provisional",
        "path": path,
        "path_count_capped_at_two": 1,
        "best_path_sample_count": best,
        "observed_candidate_count": len(nodes),
        "discarded_candidate_count": len(nodes) - len(path),
        "first_receiving_time_s": path[0]["time_s"],
        "last_receiving_time_s": path[-1]["time_s"],
        "first_cross_view_position_difference_m": round(
            dist(departure["world_m"], path[0]["world_m"]), 4
        ),
        "independently_verified_stone_identity": False,
        "metric_accuracy_verified": False,
    }
