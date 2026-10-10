"""Provisional stone events from adjacent cap motion when origin routing abstains.

The rule uses source-only camera shots and stone-cap tracks. It does not
identify a physical release instant or establish cross-cut stone identity.
"""


def qualified_colours(tracks):
    return {
        track["colour"] for track in tracks if track["point_count"] >= 10 and track["span_px"] >= 70
    }


def rescue_nonorigin_shots(shots, origins, interval_s):
    """Return candidates in one interval without counters or official shots."""
    output = []
    last_origin_end = None
    for index, shot in enumerate(shots):
        start, stop = shot["interval_s"]
        if not interval_s[0] <= (start + stop) / 2 < interval_s[1]:
            continue
        origin = origins[shot["shot_id"]]
        if origin["predicted"]:
            last_origin_end = stop
            continue
        if (
            origin["probability"] < 0.2
            or last_origin_end is None
            or start - last_origin_end < 30
            or index + 1 >= len(shots)
        ):
            continue
        next_shot = shots[index + 1]
        if origins[next_shot["shot_id"]]["predicted"] or next_shot["interval_s"][0] != stop:
            continue
        own = qualified_colours(shot["same_shot_candidates"])
        following = qualified_colours(next_shot["same_shot_candidates"])
        shared = own & following
        if len(shared) != 1:
            continue
        colour = next(iter(shared))
        tracks = [
            track
            for track in shot["same_shot_candidates"]
            if track["colour"] == colour and track["point_count"] >= 10 and track["span_px"] >= 70
        ]
        output.append(
            {
                "shot_id": shot["shot_id"],
                "interval_s": shot["interval_s"],
                "colour": colour,
                "origin_probability": origin["probability"],
                "following_shot_id": next_shot["shot_id"],
                "first_track_s": min(track["interval_s"][0] for track in tracks),
                "route": "nonorigin_adjacent_same_colour_cap_motion",
                "identity_status": "provisional_same_colour_not_proven_same_stone",
            }
        )
    return output
