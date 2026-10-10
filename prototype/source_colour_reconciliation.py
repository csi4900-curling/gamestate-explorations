"""Reconcile a provisional event colour with two agreeing source-video cues."""


def reconcile_event_colour(event_colour, release_cue, receiving_view):
    """Use agreeing release and receiving colours; preserve the prior value.

    This is a video-evidence correction to a provisional event label. It does
    not establish persistent physical stone identity across the camera cut.
    """
    if event_colour not in (None, "red", "yellow"):
        raise ValueError("Unsupported event colour")
    release_colour = release_cue.get("colour")
    receiving_colour = receiving_view.get("colour")
    supported = (
        release_cue.get("time_s") is not None
        and release_cue.get("status") == "unique_passage"
        and receiving_view.get("status") == "source_colour_concordant_identity_unverified"
        and release_colour in ("red", "yellow")
        and release_colour == receiving_colour
    )
    if not supported:
        return {
            "colour": event_colour,
            "status": "unchanged",
            "original_colour": event_colour,
            "source_cue_colour": None,
        }
    if event_colour == release_colour:
        status = "two_view_concordant_no_revision"
    elif event_colour is None:
        status = "source_two_view_colour_filled"
    else:
        status = "source_two_view_colour_corrected"
    return {
        "colour": release_colour,
        "status": status,
        "original_colour": event_colour,
        "source_cue_colour": release_colour,
        "physical_stone_identity_verified": False,
    }
