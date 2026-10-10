"""Collapse passage fragments that point to the same timed stone observations."""

from math import dist


def shared_timed_observations(a, b, position_tolerance_m=0.15):
    positions = {node["source_time_s"]: node["ground_position_m"]
                 for node in a}
    return sum(node["source_time_s"] in positions and
               dist(positions[node["source_time_s"]],
                    node["ground_position_m"]) <= position_tolerance_m
               for node in b)


def deduplicate_motion_paths(candidates, motion_rows,
                             min_shared_observations=5):
    by_id = {row["candidate_id"]: row for row in motion_rows}
    if len(by_id) != len(motion_rows):
        raise ValueError("Duplicate motion candidate ID")
    event_by_id = {event["id"]: event for event in candidates}
    if len(event_by_id) != len(candidates) or set(by_id) != set(event_by_id):
        raise ValueError("Motion and candidate IDs differ")
    parent = {pid: pid for pid in by_id}

    def root(pid):
        while parent[pid] != pid:
            pid = parent[pid]
        return pid

    pairs = []
    for i, first in enumerate(candidates):
        first_row = by_id[first["id"]]
        first_path = first_row["selection"].get("path", [])
        if not first_path:
            continue
        for second in candidates[i + 1:]:
            second_row = by_id[second["id"]]
            second_path = second_row["selection"].get("path", [])
            if not second_path or first["colour"] != second["colour"] or (
                    first_row["receiving_view"] != second_row["receiving_view"]):
                continue
            count = shared_timed_observations(first_path, second_path)
            if count < min_shared_observations:
                continue
            pairs.append({"candidate_ids": [first["id"], second["id"]],
                          "shared_timed_observation_count": count})
            parent[root(second["id"])] = root(first["id"])
    groups = {}
    for candidate in candidates:
        groups.setdefault(root(candidate["id"]), []).append(candidate["id"])
    decisions = []
    for group in groups.values():
        primary = min(group, key=lambda pid: (event_by_id[pid]["crossing_time_s"], pid))
        for pid in group:
            decisions.append({"candidate_id": pid,
                              "status": "primary_motion_path" if pid == primary else
                                        "duplicate_shared_timed_motion_path",
                              "primary_candidate_id": primary,
                              "group_size": len(group)})
    return {"pairs": pairs, "decisions": decisions,
            "retained_candidate_ids": [row["candidate_id"] for row in decisions
                                       if row["status"] == "primary_motion_path"]}
