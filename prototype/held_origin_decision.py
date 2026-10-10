"""Use strong held/moving cap evidence to revise a provisional gate colour.

The rule may abstain; it never invents a new release timestamp or identity.
"""


def held_motion_override(evidence):
    """Return a colour only when one cap dominates held or moving evidence."""
    colours = ("red", "yellow")
    holds = {colour: (evidence[colour]["best_hold"] or {}).get("duration_s", 0)
             for colour in colours}
    held = max(colours, key=lambda colour: holds[colour])
    other = next(colour for colour in colours if colour != held)
    if holds[held] >= 3.0 and holds[held] - holds[other] >= 1.0:
        return {"colour": held, "route": "dominant_held_cap",
                "evidence_interval_s": evidence[held]["best_hold"]["interval_s"]}
    movement = {colour: (evidence[colour]["best_motion"] or {}).get(
        "displacement_px", 0) for colour in colours}
    moving = max(colours, key=lambda colour: movement[colour])
    other = next(colour for colour in colours if colour != moving)
    if movement[moving] >= 60 and movement[moving] >= 1.5 * max(1, movement[other]):
        return {"colour": moving, "route": "dominant_central_cap_motion",
                "evidence_interval_s": evidence[moving]["best_motion"]["interval_s"]}
    return {"colour": None, "route": "no_dominant_held_or_motion_cap",
            "evidence_interval_s": None}


def combine_with_gate(gate_colour, evidence):
    cue = held_motion_override(evidence)
    if cue["colour"] is None:
        return {"colour": gate_colour, "route": "gate_unmodified",
                "held_override": cue}
    return {"colour": cue["colour"],
            "route": "held_cap_confirmed_gate" if cue["colour"] == gate_colour
            else "held_cap_overrode_gate",
            "held_override": cue}
