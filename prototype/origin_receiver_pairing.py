"""Pair a likely delivery view with stone motion in its next camera shot.

Produces provisional events with a broad release window, never a fabricated
continuous trajectory or exact release instant.
"""


def pair_origin_receiver(shots, origins):
    """Return at most one event per frozen origin-positive camera shot.

    `shots` is an ordered list with shot_id, interval_s and ranked transits.
    `origins` maps shot_id to the frozen view decision. No counter or official
    shot fields enter this function.
    """
    events = []
    for index, shot in enumerate(shots):
        origin = origins[shot["shot_id"]]
        if not origin["predicted"]:
            continue
        own = shot["transits"]
        next_shot = shots[index + 1] if index + 1 < len(shots) else None
        following = (
            next_shot["transits"]
            if next_shot is not None and not origins[next_shot["shot_id"]]["predicted"]
            else []
        )
        own_colours = {track["colour"] for track in own}
        next_colours = {track["colour"] for track in following}
        shared = own_colours & next_colours
        if shared:
            colour = max(
                shared,
                key=lambda value: (
                    max(track["point_count"] for track in own if track["colour"] == value),
                    max(track["point_count"] for track in following if track["colour"] == value),
                    value,
                ),
            )
            route = "same_colour_across_adjacent_camera_shots"
        elif own:
            colour = own[0]["colour"]
            route = "origin_shot_visual_only"
        elif following:
            colour = following[0]["colour"]
            route = "receiving_shot_visual_only"
        else:
            continue
        own_tracks = [track for track in own if track["colour"] == colour]
        following_tracks = [track for track in following if track["colour"] == colour]
        events.append(
            {
                "candidate_id": f"{shot['shot_id']}-paired",
                "origin_shot_id": shot["shot_id"],
                "origin_probability": origin["probability"],
                "receiving_shot_id": next_shot["shot_id"] if following_tracks else None,
                "release_window_s": shot["interval_s"],
                "colour": colour,
                "evidence_route": route,
                "origin_visual_tracks": own_tracks,
                "receiving_visual_tracks": following_tracks,
                "identity_status": "provisional_same_colour_adjacent_view"
                if following_tracks
                else "unlinked_single_view",
            }
        )
    return events
