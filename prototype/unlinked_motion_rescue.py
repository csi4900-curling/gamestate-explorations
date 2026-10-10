"""Propose missing or colour-conflicted events from unlinked global motion."""


def find_adjacent_origin_proposals(
    episode_links,
    episodes,
    origin_rows,
    camera_shots,
    candidate_rows,
    *,
    min_origin_probability=0.9,
    min_origin_duration_s=5.0,
    max_receiving_onset_delay_s=1.0,
):
    """Return source-review proposals; never certify a physical throw."""
    episode_by_id = {row["episode_id"]: row for row in episodes}
    if len(episode_by_id) != len(episodes):
        raise ValueError("Duplicate catalog episode ID")
    origin_by_shot = {row["shot_id"]: row for row in origin_rows}
    candidate_by_shot = {row["shot_id"]: row for row in candidate_rows}
    shot_index = {shot["id"]: i for i, shot in enumerate(camera_shots)}
    proposals = []
    for link in episode_links:
        if link["candidate_ids"]:
            continue
        episode = episode_by_id[link["episode_id"]]
        index = shot_index[episode["camera_shot_id"]]
        if index == 0:
            continue
        receiving = camera_shots[index]
        origin_shot = camera_shots[index - 1]
        origin = origin_by_shot.get(origin_shot["id"])
        if origin is None:
            continue
        origin_start, origin_end = origin_shot["interval_s"]
        if origin["interval_s"] != origin_shot["interval_s"]:
            raise ValueError(f"Origin interval disagrees: {origin_shot['id']}")
        if origin["probability"] < min_origin_probability or (
            origin_end - origin_start < min_origin_duration_s
        ):
            continue
        delay = episode["interval_s"][0] - receiving["interval_s"][0]
        if not 0 <= delay <= max_receiving_onset_delay_s:
            continue
        candidate = candidate_by_shot.get(origin_shot["id"])
        if candidate is None:
            status = "origin_absent_from_candidate_ledger"
        elif candidate["candidate_colour"] != episode["colour"] and (
            candidate["candidate_colour"] is not None
        ):
            status = "existing_candidate_colour_conflict"
        else:
            continue
        proposals.append(
            {
                "origin_shot_id": origin_shot["id"],
                "origin_interval_s": origin_shot["interval_s"],
                "origin_model_probability": origin["probability"],
                "origin_model_predicted": origin["predicted"],
                "receiving_shot_id": receiving["id"],
                "receiving_episode_id": episode["episode_id"],
                "receiving_colour": episode["colour"],
                "receiving_motion_interval_s": episode["interval_s"],
                "receiving_span_px": episode["span_px"],
                "receiving_point_count": episode["point_count"],
                "onset_after_camera_cut_s": round(delay, 3),
                "candidate_status": status,
                "existing_candidate_colour": candidate["candidate_colour"] if candidate else None,
                "existing_counter_id": candidate["counter_id"] if candidate else None,
                "physical_throw_verified": False,
            }
        )
    return sorted(proposals, key=lambda row: row["origin_interval_s"][0])
