"""Choose a provisional throw colour from an origin-view early-ice gate.

The gate is layout-specific and returns an observation anchor, not a physical
release timestamp. A tie or absent evidence is an abstention.
"""


def decide_gate_colour(row):
    """Use coherent cap passage first, then a unique count of gate samples."""
    colours = ("red", "yellow")
    tracks = row["transits"]
    with_motion = [colour for colour in colours if tracks[colour]]
    if len(with_motion) == 1:
        colour = with_motion[0]
        route = "coherent_early_gate_transit"
    elif len(with_motion) == 2:
        rank = {
            colour: (tracks[colour][0]["point_count"], tracks[colour][0]["displacement_px"])
            for colour in colours
        }
        best, other = sorted(colours, key=lambda value: rank[value], reverse=True)
        if rank[best][0] - rank[other][0] < 2:
            return {"colour": None, "route": "ambiguous_competing_transits", "anchor_s": None}
        colour, route = best, "dominant_early_gate_transit"
    else:
        counts = row["gate_counts"]
        if counts["red"] == counts["yellow"]:
            return {"colour": None, "route": "missing_or_tied_gate_samples", "anchor_s": None}
        colour = max(colours, key=lambda value: counts[value])
        route = "single_or_dominant_gate_samples"
    if tracks[colour]:
        anchor = tracks[colour][0]["interval_s"][0]
    else:
        observations = [
            (candidate["patch_score"], sample["time_s"])
            for sample in row["samples"]
            for candidate in sample["gate_candidates"][colour]
        ]
        if not observations:
            raise ValueError("Selected colour has no gate evidence")
        anchor = max(observations)[1]
    return {"colour": colour, "route": route, "anchor_s": anchor}
