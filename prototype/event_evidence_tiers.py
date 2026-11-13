"""Source-only evidence tiers for provisional full-match throw events."""


def event_evidence_tier(counter_id, release_cue, receiving_view):
    """Keep weak visual proposals while exposing independent cue support."""
    release_colour = release_cue.get("colour")
    two_view = (
        release_cue.get("status") == "unique_passage"
        and release_cue.get("time_s") is not None
        and release_colour in ("red", "yellow")
        and receiving_view.get("status") == "source_colour_concordant_identity_unverified"
        and receiving_view.get("colour") == release_colour
    )
    if counter_id is not None:
        return {
            "tier": "counter_backed_provisional",
            "counter_anchor": True,
            "two_view_colour_concordance": two_view,
            "physical_throw_verified": False,
        }
    if two_view:
        return {
            "tier": "two_view_release_without_counter",
            "counter_anchor": False,
            "two_view_colour_concordance": True,
            "physical_throw_verified": False,
        }
    return {
        "tier": "visual_window_only_unconfirmed",
        "counter_anchor": False,
        "two_view_colour_concordance": False,
        "physical_throw_verified": False,
    }
