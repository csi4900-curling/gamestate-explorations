"""Monotone weak-reference score for counter-independent visual candidates."""


def score_visual_against_counters(
    visual, counters, *, max_counter_lag_s=50, max_window_overrun_s=20
):
    """Match ordered visual intervals to delayed counter updates one-to-one.

    This measures agreement with a broadcast proxy, not physical throw F1.
    """
    visual = sorted(visual, key=lambda row: row["interval_s"][0])
    counters = sorted(counters, key=lambda row: row["counter_time_s"])
    n, m = len(visual), len(counters)
    # Lexicographic objective: maximize count, then matching known colours,
    # then proximity to an illustrative 15-second counter delay.
    score = [[None] * (m + 1) for _ in range(n + 1)]
    parent = [[None] * (m + 1) for _ in range(n + 1)]
    score[0][0] = (0, 0, 0.0)

    def relax(i, j, ni, nj, proposal, action):
        if score[ni][nj] is None or proposal > score[ni][nj]:
            score[ni][nj] = proposal
            parent[ni][nj] = (i, j, action)

    for i in range(n + 1):
        for j in range(m + 1):
            current = score[i][j]
            if current is None:
                continue
            if i < n:
                relax(i, j, i + 1, j, current, "skip_visual")
            if j < m:
                relax(i, j, i, j + 1, current, "skip_counter")
            if i < n and j < m:
                start, end = visual[i]["interval_s"]
                counter_time = counters[j]["counter_time_s"]
                if (
                    start <= counter_time
                    and end <= counter_time + max_window_overrun_s
                    and counter_time - end <= max_counter_lag_s
                ):
                    colour_match = int(
                        visual[i]["colour"] is not None
                        and visual[i]["colour"] == counters[j]["counter_colour"]
                    )
                    proposal = (
                        current[0] + 1,
                        current[1] + colour_match,
                        current[2] - abs(counter_time - end - 15),
                    )
                    relax(i, j, i + 1, j + 1, proposal, "match")
    matches = []
    used_visual, used_counter = set(), set()
    i, j = n, m
    while i or j:
        pi, pj, action = parent[i][j]
        if action == "match":
            vi, cj = pi, pj
            used_visual.add(vi)
            used_counter.add(cj)
            matches.append(
                {
                    "visual_id": visual[vi]["shot_id"],
                    "official_shot_id": counters[cj]["official_shot_id"],
                    "visual_colour": visual[vi]["colour"],
                    "counter_colour": counters[cj]["counter_colour"],
                    "counter_minus_visual_end_s": round(
                        counters[cj]["counter_time_s"] - visual[vi]["interval_s"][1], 3
                    ),
                }
            )
        i, j = pi, pj
    matches.reverse()
    matched = len(matches)
    return {
        "visual_candidate_count": n,
        "clean_counter_count": m,
        "matched_count": matched,
        "unmatched_visual_ids": [
            row["shot_id"] for index, row in enumerate(visual) if index not in used_visual
        ],
        "unmatched_official_shot_ids": [
            row["official_shot_id"]
            for index, row in enumerate(counters)
            if index not in used_counter
        ],
        "matches": matches,
        "counter_proxy_precision": round(matched / n, 4) if n else None,
        "counter_proxy_recall": round(matched / m, 4) if m else None,
        "counter_proxy_f1": round(2 * matched / (n + m), 4) if n + m else None,
        "known_colour_match_count": sum(
            row["visual_colour"] == row["counter_colour"]
            for row in matches
            if row["visual_colour"] is not None
        ),
        "known_colour_conflict_count": sum(
            row["visual_colour"] != row["counter_colour"]
            for row in matches
            if row["visual_colour"] is not None
        ),
        "unknown_colour_match_count": sum(row["visual_colour"] is None for row in matches),
    }
