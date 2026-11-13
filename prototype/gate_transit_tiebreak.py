"""Conservative source-only tie-break for competing early-gate cap transits.

This is a colour decision within an existing origin shot, not event detection
or a claim that the gate anchor is a physical release time.
"""


def tiebreak_competing_transits(decision, gate_row):
    """Choose a clearly stronger cap transit or preserve the original abstention."""
    if decision["colour_route"] != "ambiguous_competing_transits":
        return dict(decision)
    side = decision["side"]
    if side not in ("left", "right"):
        return dict(decision)
    tracks = gate_row[side]["transits"]
    if not tracks["red"] or not tracks["yellow"]:
        return dict(decision)
    ranking = sorted(
        ("red", "yellow"),
        key=lambda colour: (
            tracks[colour][0]["displacement_px"],
            tracks[colour][0]["median_patch_score"],
        ),
        reverse=True,
    )
    best, other = (tracks[colour][0] for colour in ranking)
    if not (
        best["point_count"] >= 4
        and best["displacement_px"] >= 60
        and best["displacement_px"] >= 1.6 * other["displacement_px"]
        and best["median_patch_score"] >= 0.5
        and best["median_patch_score"] - other["median_patch_score"] >= 0.4
        and best["path_ratio"] <= 1.1
    ):
        return dict(decision)
    return {
        **decision,
        "colour": ranking[0],
        "colour_route": "stronger_competing_transit_development_rule",
        "early_gate_anchor_s": best["interval_s"][0],
    }
