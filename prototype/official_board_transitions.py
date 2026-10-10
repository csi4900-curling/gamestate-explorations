"""Conservative coordinate-stable transitions between official post-shot diagrams.

These diagrams cover a bounded area around the house. A symbol that vanishes
may have moved beyond the diagram; a new symbol need not be the delivered stone.
"""

from math import hypot


def stable_symbol_pairs(previous, current, tolerance=0.05):
    """Pair only uniquely colocated same-colour symbols, in house radii."""
    candidates = []
    for i, old in enumerate(previous):
        for j, new in enumerate(current):
            if old["colour"] != new["colour"]:
                continue
            ox, oy = old["house_radius_coordinates"]
            nx, ny = new["house_radius_coordinates"]
            distance = hypot(ox - nx, oy - ny)
            if distance <= tolerance:
                candidates.append((i, j, round(distance, 4)))
    old_degree = {i: 0 for i in range(len(previous))}
    new_degree = {j: 0 for j in range(len(current))}
    for i, j, _ in candidates:
        old_degree[i] += 1
        new_degree[j] += 1
    pairs = [
        (i, j, distance)
        for i, j, distance in candidates
        if old_degree[i] == 1 and new_degree[j] == 1
    ]
    matched_old = {i for i, _, _ in pairs}
    matched_new = {j for _, j, _ in pairs}
    return {
        "coordinate_stable_pairs": [
            {
                "previous_symbol_index": i,
                "current_symbol_index": j,
                "colour": previous[i]["colour"],
                "distance_house_radii": distance,
            }
            for i, j, distance in pairs
        ],
        "unresolved_previous_symbol_indices": [
            i for i in range(len(previous)) if i not in matched_old
        ],
        "unresolved_current_symbol_indices": [
            j for j in range(len(current)) if j not in matched_new
        ],
        "ambiguous_close_pair_count": sum(
            old_degree[i] != 1 or new_degree[j] != 1 for i, j, _ in candidates
        ),
    }


def build_transitions(ends, tolerance=0.05):
    rows = []
    for end in ends:
        previous = []
        for shot_number, shot in enumerate(end["shots"], start=1):
            current = shot["stones"]
            pairs = stable_symbol_pairs(previous, current, tolerance)
            rows.append(
                {
                    "official_shot_id": shot["official_shot_id"],
                    "end": end["end"],
                    "shot_number": shot_number,
                    "previous_diagram_symbol_count": len(previous),
                    "current_diagram_symbol_count": len(current),
                    "diagram_review_flags": shot["review_flags"],
                    **pairs,
                }
            )
            previous = current
    return rows
