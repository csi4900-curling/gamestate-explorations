"""Expose candidate colour and delayed-counter identity ambiguity.

These are evidence flags, not automatic throw decisions or a deduplication rule.
"""


def audit_event_identity(events, learned_shots, *, max_counter_lag_s=45.0):
    by_shot = {row["shot_id"]: row for row in learned_shots}
    if len(by_shot) != len(learned_shots):
        raise ValueError("Duplicate learned-motion shot ID")
    by_id = {row["candidate_id"]: row for row in events}
    if len(by_id) != len(events):
        raise ValueError("Duplicate candidate ID")
    ordered = sorted(events, key=lambda row: row["observation_anchor_s"])
    rows = []
    for index, event in enumerate(ordered):
        motion = by_shot.get(event["shot_id"])
        same = (
            sorted({track["colour"] for track in motion["same_shot_candidates"]}) if motion else []
        )
        following = (
            sorted({track["colour"] for track in motion["following_shot_candidates"]})
            if motion
            else []
        )
        colour = event["colour"]
        scanned = bool(motion and motion.get("scanned"))
        same_colour_seen = colour in same if colour is not None and scanned else None
        other_following = sorted(set(following) - {colour}) if colour is not None else following
        colour_risk = bool(
            event["counter_id"] is None
            and colour is not None
            and scanned
            and not same_colour_seen
            and other_following
        )
        earliest_following_colour = None
        earliest_following_lead_s = None
        if event["counter_id"] is None and scanned and motion:
            sustained = [
                track for track in motion["following_shot_candidates"] if track["point_count"] >= 20
            ]
            first_by_colour = {
                track_colour: min(
                    track["interval_s"][0] for track in sustained if track["colour"] == track_colour
                )
                for track_colour in {track["colour"] for track in sustained}
            }
            if first_by_colour:
                earliest_following_colour = min(first_by_colour, key=first_by_colour.get)
                first_s = first_by_colour[earliest_following_colour]
                other_starts = [
                    time
                    for track_colour, time in first_by_colour.items()
                    if track_colour != earliest_following_colour
                ]
                earliest_following_lead_s = min(other_starts) - first_s if other_starts else None
                gap = first_s - event["release_window_s"][1]
                if not (
                    0 <= gap <= 3
                    and (earliest_following_lead_s is None or earliest_following_lead_s >= 3)
                ):
                    earliest_following_colour = None
        possible_delayed_links = []
        if event["counter_id"] is None and colour_risk:
            for later in ordered[index + 1 :]:
                if later["observation_anchor_s"] - event["release_window_s"][1] > max_counter_lag_s:
                    break
                counter = later["broadcast_counter"]
                if counter is None or later["colour"] not in other_following:
                    continue
                lag = counter["update_s"] - event["release_window_s"][1]
                if 0 <= lag <= max_counter_lag_s:
                    possible_delayed_links.append(
                        {
                            "candidate_id": later["candidate_id"],
                            "counter_id": later["counter_id"],
                            "colour": later["colour"],
                            "counter_update_lag_after_visual_window_s": round(lag, 3),
                        }
                    )
        rows.append(
            {
                "candidate_id": event["candidate_id"],
                "shot_id": event["shot_id"],
                "counter_id": event["counter_id"],
                "ledger_colour": colour,
                "learned_motion_scanned": scanned,
                "same_shot_learned_colours": same,
                "following_shot_learned_colours": following,
                "ledger_colour_seen_in_same_shot_learned_motion": same_colour_seen,
                "visual_only_colour_collision_risk": colour_risk,
                "earliest_following_colour_hypothesis": earliest_following_colour,
                "earliest_following_colour_lead_s": (
                    round(earliest_following_lead_s, 3)
                    if earliest_following_colour and earliest_following_lead_s is not None
                    else None
                ),
                "possible_delayed_counter_links": possible_delayed_links,
            }
        )
    return rows
