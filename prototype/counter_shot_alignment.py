"""Associate delayed broadcast counter decrements with candidate delivery shots.

Counter updates are weak event evidence: they do not identify release time and
can be absent around edits or graphics. Ambiguous associations are abstentions.
"""


def align_counter_events(shots, counter_events, motion_channels, *, max_lag_s=45.0,
                         min_probability_ratio=2.0):
    """Return evidence-preserving, one-to-one counter/shot associations.

    The shot origin probability ranks plausible shots but cannot itself create
    an association. Same-colour motion must exist in the shot and the next
    broadcast shot in at least one proposal channel. Labels are never read.
    """
    if not motion_channels:
        raise ValueError("At least one motion channel is required")
    shot_ids = [row["shot_id"] for row in shots]
    if len(shot_ids) != len(set(shot_ids)):
        raise ValueError("Duplicate shot ID")
    indexed_channels = []
    for channel, rows in motion_channels.items():
        indexed = {row["shot_id"]: row for row in rows}
        if len(indexed) != len(rows) or set(indexed) != set(shot_ids):
            raise ValueError(f"Shot ID mismatch in {channel} motion audit")
        indexed_channels.append((channel, indexed))

    used_shots = set()
    output = []
    for event in sorted(counter_events, key=lambda row: row["crossing_time_s"]):
        update = event["crossing_time_s"]
        earliest_end = update - max_lag_s
        options = []
        for shot in shots:
            start, end = shot["interval_s"]
            if (shot["shot_id"] in used_shots or not shot["phase_supported"]
                    or start > update or end < earliest_end):
                continue
            support = []
            for channel, indexed in indexed_channels:
                motion = indexed[shot["shot_id"]]
                same = {row["colour"] for row in motion["same_shot_candidates"]}
                following = {row["colour"] for row in motion["following_shot_candidates"]}
                if event["colour"] in same & following:
                    support.append(channel)
            if support:
                options.append({"shot_id": shot["shot_id"],
                                "interval_s": shot["interval_s"],
                                "origin_probability": shot["probability"],
                                "motion_channels": support})
        options.sort(key=lambda row: (-row["origin_probability"],
                                      -len(row["motion_channels"]), row["shot_id"]))
        chosen = None
        if options and options[0]["origin_probability"] > 0 and (
                        len(options) == 1 or
                        options[0]["origin_probability"] >=
                        min_probability_ratio * options[1]["origin_probability"]):
            chosen = options[0]["shot_id"]
            used_shots.add(chosen)
        output.append({"counter_id": event["id"], "colour": event["colour"],
                       "counter_evidence_interval_s": event["evidence_interval_s"],
                       "counter_update_s": update, "shot_id": chosen,
                       "status": "associated" if chosen else "abstained",
                       "association_route": "same_and_following_motion" if chosen else None,
                       "candidate_shots": options})
    return output


def rescue_following_only(alignments, shots, motion_channels, *, max_lag_s=45.0,
                          min_origin_probability=0.8,
                          max_motion_start_after_cut_s=1.5,
                          min_probability_ratio=2.0):
    """Rescue counter changes when the delivery shot cuts before track onset.

    Only a strong origin shot with two proposal channels observing the counter
    colour immediately in the next shot is eligible. Existing associations
    retain priority; uncertain choices abstain.
    """
    if len(motion_channels) < 2:
        raise ValueError("Following-only rescue requires two motion channels")
    indexed = []
    shot_ids = {row["shot_id"] for row in shots}
    for channel, rows in motion_channels.items():
        by_id = {row["shot_id"]: row for row in rows}
        if len(by_id) != len(rows) or set(by_id) != shot_ids:
            raise ValueError(f"Shot ID mismatch in {channel} motion audit")
        indexed.append((channel, by_id))
    used = {row["shot_id"] for row in alignments if row["shot_id"] is not None}
    result = []
    for alignment in alignments:
        row = dict(alignment)
        row["following_only_candidates"] = []
        if row["shot_id"] is not None:
            result.append(row)
            continue
        update = row["counter_update_s"]
        colour = row["colour"]
        for shot in shots:
            start, end = shot["interval_s"]
            if (shot["shot_id"] in used or not shot["phase_supported"]
                    or shot["probability"] < min_origin_probability
                    or start > update or end < update - max_lag_s):
                continue
            channels = []
            for channel, by_id in indexed:
                following = by_id[shot["shot_id"]]["following_shot_candidates"]
                if any(candidate["colour"] == colour and
                       0 <= candidate["interval_s"][0] - end <=
                       max_motion_start_after_cut_s for candidate in following):
                    channels.append(channel)
            if len(channels) >= 2:
                row["following_only_candidates"].append({
                    "shot_id": shot["shot_id"], "interval_s": shot["interval_s"],
                    "origin_probability": shot["probability"],
                    "motion_channels": channels})
        options = row["following_only_candidates"]
        options.sort(key=lambda item: (-item["origin_probability"], item["shot_id"]))
        if options and (len(options) == 1 or options[0]["origin_probability"] >=
                        min_probability_ratio * options[1]["origin_probability"]):
            row["shot_id"] = options[0]["shot_id"]
            row["status"] = "associated"
            row["association_route"] = "strong_origin_and_immediate_following_motion"
            used.add(row["shot_id"])
        result.append(row)
    return result


def link_existing_visual_candidates(alignments, origins, origin_events,
                                    motion_channels, *, max_lag_s=45.0,
                                    max_motion_start_after_cut_s=1.5):
    """Attach a counter to an existing visual candidate across a colour conflict.

    This does not create a new event. It prevents the same likely throw from
    being counted once as a wrong-colour origin and again as travel-only.
    """
    if len(motion_channels) < 2:
        raise ValueError("Two motion channels are required")
    indexed_shots = {row["shot_id"]: row for row in origins}
    indexed_motion = {}
    for channel, rows in motion_channels.items():
        by_id = {row["shot_id"]: row for row in rows}
        if len(by_id) != len(rows) or set(by_id) != set(indexed_shots):
            raise ValueError(f"Shot ID mismatch in {channel} motion audit")
        indexed_motion[channel] = by_id
    visual_only = {row["shot_id"] for row in origin_events
                   if row["counter_id"] is None}
    used = {row["shot_id"] for row in alignments if row["shot_id"] is not None}
    result = []
    for alignment in alignments:
        row = dict(alignment)
        row["existing_visual_candidates"] = []
        if row["shot_id"] is not None:
            result.append(row)
            continue
        update = row["counter_update_s"]
        colour = row["colour"]
        for shot_id in sorted(visual_only - used):
            shot = indexed_shots[shot_id]
            start, end = shot["interval_s"]
            if start > update or end < update - max_lag_s:
                continue
            channels = []
            for channel, by_id in indexed_motion.items():
                tracks = by_id[shot_id]["following_shot_candidates"]
                if any(track["colour"] == colour and
                       0 <= track["interval_s"][0] - end <=
                       max_motion_start_after_cut_s for track in tracks):
                    channels.append(channel)
            if len(channels) >= 2:
                row["existing_visual_candidates"].append({
                    "shot_id": shot_id, "interval_s": shot["interval_s"],
                    "visual_probability": shot["probability"],
                    "motion_channels": channels})
        if len(row["existing_visual_candidates"]) == 1:
            row["shot_id"] = row["existing_visual_candidates"][0]["shot_id"]
            row["status"] = "associated"
            row["association_route"] = "existing_visual_candidate_and_following_motion"
            used.add(row["shot_id"])
        result.append(row)
    return result
