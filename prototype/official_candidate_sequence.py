"""Conservative optimal-sequence audit against independent official shot order."""


SKIP_CANDIDATE_COST = 2
SKIP_OFFICIAL_COST = 2
UNKNOWN_COLOUR_MATCH_COST = 1
WRONG_COLOUR_MATCH_COST = 5


def align_official_sequence(candidates, official_shots, team_colours, fixed_links):
    """Find matches shared by every minimum-cost monotonic alignment.

    Fixed links come from clean counter/official correspondences. This is an
    audit that reads official shots, never a runtime throw detector.
    """
    n, m = len(candidates), len(official_shots)
    candidate_ids = [row["candidate_id"] for row in candidates]
    shot_ids = [row["official_shot_id"] for row in official_shots]
    if len(set(candidate_ids)) != n or len(set(shot_ids)) != m:
        raise ValueError("Duplicate candidate or official shot ID")
    if not set(fixed_links).issubset(candidate_ids) or not set(fixed_links.values()).issubset(shot_ids):
        raise ValueError("Fixed link refers outside this end")
    if len(set(fixed_links.values())) != len(fixed_links):
        raise ValueError("Several candidates fixed to one official shot")
    fixed_candidate_for_shot = {shot: candidate for candidate, shot in fixed_links.items()}
    infinity = 10**9

    def edges(i, j):
        if i < n and candidate_ids[i] not in fixed_links:
            yield i + 1, j, SKIP_CANDIDATE_COST, None
        if j < m and shot_ids[j] not in fixed_candidate_for_shot:
            yield i, j + 1, SKIP_OFFICIAL_COST, None
        if i < n and j < m:
            candidate_id, shot_id = candidate_ids[i], shot_ids[j]
            if candidate_id in fixed_links and fixed_links[candidate_id] != shot_id:
                return
            if shot_id in fixed_candidate_for_shot and fixed_candidate_for_shot[shot_id] != candidate_id:
                return
            expected = team_colours[official_shots[j]["team"]]
            observed = candidates[i]["colour"]
            cost = (0 if candidate_id in fixed_links or observed == expected else
                    UNKNOWN_COLOUR_MATCH_COST if observed is None else
                    WRONG_COLOUR_MATCH_COST)
            yield i + 1, j + 1, cost, (candidate_id, shot_id)

    forward = [[infinity] * (m + 1) for _ in range(n + 1)]
    forward_ways = [[0] * (m + 1) for _ in range(n + 1)]
    forward[0][0] = 0
    forward_ways[0][0] = 1
    for i in range(n + 1):
        for j in range(m + 1):
            if forward_ways[i][j] == 0:
                continue
            for ni, nj, cost, _ in edges(i, j):
                proposal = forward[i][j] + cost
                if proposal < forward[ni][nj]:
                    forward[ni][nj] = proposal
                    forward_ways[ni][nj] = forward_ways[i][j]
                elif proposal == forward[ni][nj]:
                    forward_ways[ni][nj] += forward_ways[i][j]
    if forward_ways[n][m] == 0:
        raise ValueError("Fixed links violate candidate/official chronology")

    suffix = [[infinity] * (m + 1) for _ in range(n + 1)]
    suffix_ways = [[0] * (m + 1) for _ in range(n + 1)]
    suffix[n][m] = 0
    suffix_ways[n][m] = 1
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            if i == n and j == m:
                continue
            for ni, nj, cost, _ in edges(i, j):
                if suffix_ways[ni][nj] == 0:
                    continue
                proposal = cost + suffix[ni][nj]
                if proposal < suffix[i][j]:
                    suffix[i][j] = proposal
                    suffix_ways[i][j] = suffix_ways[ni][nj]
                elif proposal == suffix[i][j]:
                    suffix_ways[i][j] += suffix_ways[ni][nj]
    if suffix[0][0] != forward[n][m] or suffix_ways[0][0] != forward_ways[n][m]:
        raise AssertionError("Forward/backward optimal path disagreement")

    match_paths = {}
    for i in range(n + 1):
        for j in range(m + 1):
            if forward_ways[i][j] == 0:
                continue
            for ni, nj, cost, pair in edges(i, j):
                if pair and suffix_ways[ni][nj] and (
                        forward[i][j] + cost + suffix[ni][nj] == forward[n][m]):
                    match_paths[pair] = (match_paths.get(pair, 0)
                                         + forward_ways[i][j] * suffix_ways[ni][nj])
    total_paths = forward_ways[n][m]
    candidate_rows = []
    for candidate in candidates:
        identifier = candidate["candidate_id"]
        options = [{"official_shot_id": shot_id, "optimal_path_count": count}
                   for (candidate_id, shot_id), count in match_paths.items()
                   if candidate_id == identifier]
        options.sort(key=lambda row: shot_ids.index(row["official_shot_id"]))
        if not options:
            status, unique_shot = "skipped_in_every_optimum", None
        elif len(options) == 1 and options[0]["optimal_path_count"] == total_paths:
            status, unique_shot = "same_match_in_every_optimum", options[0]["official_shot_id"]
        else:
            status, unique_shot = "ambiguous_optimal_alignment", None
        candidate_rows.append({"candidate_id": identifier, "colour": candidate["colour"],
                               "status": status, "unique_official_shot_id": unique_shot,
                               "optimal_match_options": options})
    official_rows = []
    for shot in official_shots:
        identifier = shot["official_shot_id"]
        options = [(candidate_id, count) for (candidate_id, shot_id), count
                   in match_paths.items() if shot_id == identifier]
        if not options:
            status, unique_candidate = "unmatched_in_every_optimum", None
        elif len(options) == 1 and options[0][1] == total_paths:
            status, unique_candidate = "same_match_in_every_optimum", options[0][0]
        else:
            status, unique_candidate = "ambiguous_optimal_alignment", None
        official_rows.append({"official_shot_id": identifier, "status": status,
                              "unique_candidate_id": unique_candidate})
    return {"minimum_cost": forward[n][m], "optimal_path_count": total_paths,
            "candidate_rows": candidate_rows, "official_rows": official_rows}
