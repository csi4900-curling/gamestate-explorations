"""Conservative colour evidence for visual-only candidates across a camera cut."""


COLOURS = {"red", "yellow"}


def reconcile_visual_only_colours(candidates, postcut_rows):
    """Keep both observations and propose a two-view colour only on agreement.

    The post-cut observation is a colour cue, never physical stone identity or
    proof that a throw occurred. Every visual-only candidate must have exactly
    one post-cut audit row so an omitted scan cannot look like abstention.
    """
    by_id = {row["candidate_id"]: row for row in postcut_rows}
    if len(by_id) != len(postcut_rows):
        raise ValueError("Duplicate post-cut candidate ID")
    selected = [row for row in candidates if row["counter_id"] is None and
                row["evidence_class"] == "origin_view_candidate"]
    ids = {row["candidate_id"] for row in selected}
    if len(ids) != len(selected) or ids != set(by_id):
        raise ValueError("Visual-only candidate and post-cut IDs differ")
    result = []
    for candidate in selected:
        sidecar = by_id[candidate["candidate_id"]]
        if (candidate["shot_id"] != sidecar["shot_id"] or
                candidate["release_window_s"] != sidecar["release_window_s"] or
                candidate["colour"] != sidecar["original_colour"]):
            raise ValueError("Post-cut row differs from candidate source")
        origin, receiving = candidate["colour"], sidecar["postcut_colour"]
        if origin not in COLOURS | {None} or receiving not in COLOURS | {None}:
            raise ValueError("Invalid candidate or receiving colour")
        if origin is not None and receiving is not None and origin == receiving:
            relation = "colour_agreement_identity_unverified"
            two_view = origin
        elif origin is not None and receiving is not None:
            relation = "colour_conflict"
            two_view = None
        elif receiving is not None:
            relation = "receiving_only"
            two_view = None
        elif origin is not None:
            relation = "origin_only"
            two_view = None
        else:
            relation = "neither_view_resolved"
            two_view = None
        result.append({
            "candidate_id": candidate["candidate_id"],
            "shot_id": candidate["shot_id"],
            "release_window_s": candidate["release_window_s"],
            "origin_colour": origin,
            "receiving_colour": receiving,
            "receiving_status": sidecar["postcut_status"],
            "relation": relation,
            "two_view_colour": two_view,
            "physical_throw_identity_verified": False,
            "camera_handoff_identity_verified": False,
            "game_state_colour_ready": False,
        })
    return result
