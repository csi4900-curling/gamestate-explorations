"""Interpret shot-scoped release-colour cues for motion review proposals."""


def classify_release_colour(passages, receiving_colour, existing_candidate_colour=None):
    """Unique passage is colour evidence, never cross-view stone identity."""
    if len(passages) != 1:
        return {"status": "abstain_no_unique_release_cue",
                "release_colour": None,
                "receiving_colour_relation": "unknown",
                "candidate_colour_relation": "unknown"}
    colour = passages[0]["colour"]
    return {
        "status": "unique_shot_scoped_release_colour_cue",
        "release_colour": colour,
        "receiving_colour_relation": "agrees" if colour == receiving_colour else "conflicts",
        "candidate_colour_relation": (
            "unknown" if existing_candidate_colour is None else
            "agrees" if colour == existing_candidate_colour else "conflicts"),
    }
