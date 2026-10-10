"""Conservative sequence hypothesis from counter order and shared motion."""


def build_first_end_hypothesis(candidate_events, counter_events, official_shots,
                               team_colours, global_candidate_links,
                               rescue_proposal, *, first_next_end_start_s):
    """Order evidence only; no physical release or stone identity is verified."""
    end_candidates = [row for row in candidate_events
                      if row["delivery_window_s"][0] < first_next_end_start_s]
    linked_by_counter = {}
    counterless = []
    for row in end_candidates:
        counter_id = row["counter_id"]
        if counter_id is None:
            counterless.append(row)
        elif counter_id in linked_by_counter:
            raise ValueError(f"Duplicate counter assignment: {counter_id}")
        else:
            linked_by_counter[counter_id] = row
    if len(official_shots) != 16:
        raise ValueError("Expected a 16-shot first end")
    first_fifteen = counter_events[:15]
    if [row["id"] for row in first_fifteen] != [f"B{i:02}" for i in range(1, 16)]:
        raise ValueError("First 15 counter IDs are not consecutive")
    if set(linked_by_counter) != {row["id"] for row in first_fifteen}:
        raise ValueError("Counter-backed candidate set differs from B01–B15")
    by_candidate = {row["candidate_id"]: row for row in global_candidate_links["candidates"]}
    by_episode = {row["episode_id"]: row for row in global_candidate_links["episodes"]}
    duplicates = []
    for row in counterless:
        links = by_candidate[row["shot_id"]]["linked_episode_ids"]
        shared_counter_ids = sorted({
            candidate_id
            for episode_id in links
            for candidate_id in by_episode[episode_id]["candidate_ids"]
            if candidate_id != row["shot_id"] and
            by_candidate[candidate_id]["counter_id"] is not None
        })
        duplicates.append({"candidate_shot_id": row["shot_id"],
                           "shared_with_counter_backed_candidates": shared_counter_ids,
                           "shared_episode_ids": [episode_id for episode_id in links
                                                  if any(candidate_id in shared_counter_ids
                                                         for candidate_id in by_episode[episode_id]["candidate_ids"])],
                           "duplicate_throw_verified": False})
    rows = []
    for index, counter in enumerate(first_fifteen):
        official = official_shots[index]
        colour = team_colours[official["team"]]
        if counter["colour"] != colour:
            raise ValueError(f"Counter and official colour disagree at shot {index + 1}")
        candidate = linked_by_counter[counter["id"]]
        rows.append({"shot_number": index + 1,
                     "official_shot_id": official["official_shot_id"],
                     "official_team": official["team"],
                     "official_colour": colour,
                     "video_candidate_shot_id": candidate["shot_id"],
                     "provisional_delivery_window_s": candidate["delivery_window_s"],
                     "counter_id": counter["id"],
                     "counter_colour": counter["colour"],
                     "evidence_status": "counter_order_and_colour_compatible",
                     "exact_release_verified": False,
                     "physical_stone_identity_verified": False})
    final_official = official_shots[-1]
    final_colour = team_colours[final_official["team"]]
    if rescue_proposal["receiving_colour"] != final_colour:
        raise ValueError("Rescue colour disagrees with final official shot")
    if rescue_proposal["origin_interval_s"][0] <= rows[-1]["provisional_delivery_window_s"][0]:
        raise ValueError("Rescue origin is not after the fifteenth candidate")
    rows.append({"shot_number": 16,
                 "official_shot_id": final_official["official_shot_id"],
                 "official_team": final_official["team"],
                 "official_colour": final_colour,
                 "video_candidate_shot_id": rescue_proposal["origin_shot_id"],
                 "provisional_delivery_window_s": [
                     rescue_proposal["origin_interval_s"][0],
                     rescue_proposal["receiving_motion_interval_s"][1]],
                 "counter_id": None,
                 "counter_colour": None,
                 "receiving_episode_id": rescue_proposal["receiving_episode_id"],
                 "evidence_status": "source_origin_travel_and_official_order_compatible",
                 "exact_release_verified": False,
                 "physical_stone_identity_verified": False})
    return {"official_shot_count": len(official_shots),
            "counter_backed_candidate_count": len(first_fifteen),
            "counterless_candidate_count": len(counterless),
            "counterless_shared_motion_review": duplicates,
            "rows": rows}
