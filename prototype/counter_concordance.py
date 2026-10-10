"""One-to-one visual/counter matching for overlapping weak timing windows."""


def maximum_matches(candidates, counter_events, *, require_colour=False):
    """Return deterministic maximum-cardinality candidate/reference matches."""
    candidates = sorted(candidates, key=lambda row: (row["crossing_time_s"], row["id"]))
    counter_events = sorted(counter_events, key=lambda row: (row["counter_update_s"], row["id"]))
    options = []
    for candidate in candidates:
        neighbours = [
            index for index, reference in enumerate(counter_events)
            if reference["delivery_interval_s"][0]
            <= candidate["crossing_time_s"]
            <= reference["delivery_interval_s"][1]
            and (not require_colour or candidate["colour"] == reference["colour"])
        ]
        options.append(neighbours)
    owner = {}

    def augment(candidate_index, seen):
        for reference_index in options[candidate_index]:
            if reference_index in seen:
                continue
            seen.add(reference_index)
            if reference_index not in owner or augment(owner[reference_index], seen):
                owner[reference_index] = candidate_index
                return True
        return False

    for candidate_index in range(len(candidates)):
        augment(candidate_index, set())
    return [
        {
            "counter_id": counter_events[reference_index]["id"],
            "candidate_id": candidates[candidate_index]["id"],
            "counter_colour": counter_events[reference_index]["colour"],
            "candidate_colour": candidates[candidate_index]["colour"],
            "candidate_time_s": candidates[candidate_index]["crossing_time_s"],
        }
        for reference_index, candidate_index in sorted(owner.items())
    ]


def concordance(candidates, counter_events):
    temporal = maximum_matches(candidates, counter_events)
    colour = maximum_matches(candidates, counter_events, require_colour=True)
    temporal_candidates = {row["candidate_id"] for row in temporal}
    temporal_refs = {row["counter_id"] for row in temporal}
    colour_candidates = {row["candidate_id"] for row in colour}
    colour_refs = {row["counter_id"] for row in colour}
    return {
        "counter_count": len(counter_events),
        "candidate_count": len(candidates),
        "temporal_match_count": len(temporal),
        "colour_match_count": len(colour),
        "temporal_matches": temporal,
        "colour_matches": colour,
        "counter_unmatched_temporally": [row["id"] for row in counter_events
                                         if row["id"] not in temporal_refs],
        "candidate_unmatched_temporally": [row["id"] for row in candidates
                                           if row["id"] not in temporal_candidates],
        "counter_unmatched_with_colour": [row["id"] for row in counter_events
                                          if row["id"] not in colour_refs],
        "candidate_unmatched_with_colour": [row["id"] for row in candidates
                                            if row["id"] not in colour_candidates],
    }
