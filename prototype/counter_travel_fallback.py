"""Travel-view evidence for counter changes without a delivery-side shot."""


def travel_only_candidates(
    counter_alignments,
    shots,
    cap_motion,
    learned_motion,
    origin_events,
    *,
    max_lag_s=45.0,
    counter_motion_tolerance_s=5.0,
):
    """Keep counter-backed dual-channel travel observations separate from origins.

    These observations indicate a possible throw when the broadcast may omit
    its release. They cannot identify the physical stone or exact release.
    """
    shot_ids = [row["shot_id"] for row in shots]
    cap = {row["shot_id"]: row for row in cap_motion}
    learned = {row["shot_id"]: row for row in learned_motion}
    if (
        len(set(shot_ids)) != len(shot_ids)
        or len(cap) != len(cap_motion)
        or len(learned) != len(learned_motion)
        or set(cap) != set(shot_ids)
        or set(learned) != set(shot_ids)
    ):
        raise ValueError("Shot IDs differ across travel evidence")
    occupied = {row["shot_id"] for row in origin_events}
    result = []
    for counter in counter_alignments:
        if counter["shot_id"] is not None:
            continue
        update = counter["counter_update_s"]
        colour = counter["colour"]
        options = []
        for shot in shots:
            shot_id = shot["shot_id"]
            start, end = shot["interval_s"]
            if (
                shot_id in occupied
                or start > update + counter_motion_tolerance_s
                or end < update - max_lag_s
            ):
                continue
            channels = []
            for channel, by_id in (("cap", cap), ("learned", learned)):
                tracks = [
                    row
                    for row in by_id[shot_id]["same_shot_candidates"]
                    if row["colour"] == colour
                    and row["interval_s"][0] >= update - max_lag_s
                    and row["interval_s"][0] <= update + counter_motion_tolerance_s
                    and row["interval_s"][1] >= update - counter_motion_tolerance_s
                ]
                if tracks:
                    channels.append({"channel": channel, "tracks": tracks})
            if len(channels) == 2:
                options.append(
                    {
                        "shot_id": shot_id,
                        "shot_interval_s": shot["interval_s"],
                        "channel_support": channels,
                    }
                )
        selected = options[0] if len(options) == 1 else None
        record = {
            "counter_id": counter["counter_id"],
            "colour": colour,
            "counter_update_s": update,
            "candidate_shots": options,
            "status": "unlocalized_travel_candidate" if selected else "abstained",
            "travel_shot_id": selected["shot_id"] if selected else None,
        }
        if selected:
            tracks = [
                track for channel in selected["channel_support"] for track in channel["tracks"]
            ]
            first_motion = min(track["interval_s"][0] for track in tracks)
            last_motion = max(track["interval_s"][1] for track in tracks)
            record["release_window_s"] = [max(0, update - max_lag_s), min(first_motion, update)]
            record["observed_travel_window_s"] = [first_motion, last_motion]
            occupied.add(selected["shot_id"])
        result.append(record)
    return result
