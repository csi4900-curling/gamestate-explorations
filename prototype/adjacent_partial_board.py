"""Conservative associations between adjacent, incomplete board observations."""

from math import dist


def compare_partial_boards(before, after, max_distance_m=0.25):
    """Associate only mutually unique, same-colour, nearby detections.

    Unassociated detections are observations, not claims that stones appeared or
    disappeared physically. Crowded associations remain explicitly unresolved.
    """
    if max_distance_m <= 0:
        raise ValueError("max_distance_m must be positive")
    neighbors_before = [[] for _ in before]
    neighbors_after = [[] for _ in after]
    for i, a in enumerate(before):
        for j, b in enumerate(after):
            if a["colour"] != b["colour"]:
                continue
            d = dist(a["view_local_ground_position_m"],
                     b["view_local_ground_position_m"])
            if d <= max_distance_m:
                neighbors_before[i].append((j, d))
                neighbors_after[j].append((i, d))
    matches = []
    used_before = set()
    used_after = set()
    for i, options in enumerate(neighbors_before):
        if len(options) != 1:
            continue
        j, distance = options[0]
        if len(neighbors_after[j]) != 1:
            continue
        used_before.add(i)
        used_after.add(j)
        matches.append({
            "before_local_observation_id": before[i]["local_observation_id"],
            "after_local_observation_id": after[j]["local_observation_id"],
            "colour": before[i]["colour"],
            "distance_m_conditional": round(distance, 4),
            "physical_identity_verified": False,
        })
    ambiguous_before = {i for i, options in enumerate(neighbors_before)
                        if len(options) > 1 or any(len(neighbors_after[j]) > 1
                                                   for j, _ in options)}
    ambiguous_after = {j for j, options in enumerate(neighbors_after)
                       if len(options) > 1 or any(len(neighbors_before[i]) > 1
                                                  for i, _ in options)}
    return {
        "matched_observations": matches,
        "before_only_observations": [before[i]["local_observation_id"]
                                     for i, options in enumerate(neighbors_before)
                                     if not options],
        "after_only_observations": [after[j]["local_observation_id"]
                                    for j, options in enumerate(neighbors_after)
                                    if not options],
        "ambiguous_before_observations": [before[i]["local_observation_id"]
                                          for i in sorted(ambiguous_before)],
        "ambiguous_after_observations": [after[j]["local_observation_id"]
                                         for j in sorted(ambiguous_after)],
        "physical_appearance_or_removal_inferred": False,
    }


def compare_adjacent_rows(before, after, candidate_events, max_distance_m=0.25):
    """Abstain across camera changes, missing boards, or intervening candidates."""
    result = {"before_candidate_id": before["candidate_id"],
              "after_candidate_id": after["candidate_id"],
              "before_view": before["receiving_view"],
              "after_view": after["receiving_view"],
              "elapsed_between_crossings_s": round(
                  after["crossing_time_s"] - before["crossing_time_s"], 3)}
    between = [event["id"] for event in candidate_events
               if before["crossing_time_s"] < event["crossing_time_s"] <
               after["crossing_time_s"]]
    result["intervening_passage_candidate_ids"] = between
    if before["receiving_view"] != after["receiving_view"]:
        result["status"] = "abstain_camera_change"
    elif (before["board"]["status"] != "partial_stable_view_local_board" or
          after["board"]["status"] != "partial_stable_view_local_board"):
        result["status"] = "abstain_missing_partial_board"
    elif between:
        result["status"] = "abstain_intervening_passage_candidate"
    else:
        result["status"] = "view_local_partial_comparison"
        result.update(compare_partial_boards(before["board"]["stones"],
                                             after["board"]["stones"],
                                             max_distance_m))
    result["same_end_verified"] = False
    result["complete_game_state"] = False
    result["simulation_ready"] = False
    return result
