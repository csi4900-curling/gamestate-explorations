"""Fuse shot-origin, adjacent motion, and delayed counter evidence.

Outputs are bounded broadcast-shot event candidates, not exact releases.
"""

from shot_transition_rescue import rescue_weak_origins


def fuse_shot_events(origins, decisions, counter_alignments, *, allow_rescue=True):
    """Return candidate events, conflicts, and unassociated counter changes.

    A counter-associated shot must already have same-colour adjacent motion
    from the alignment stage. Counter colour cannot silently override a
    contradictory unique visual colour.
    """
    shot_ids = [row["shot_id"] for row in origins]
    by_decision = {row["shot_id"]: row for row in decisions}
    if (len(shot_ids) != len(set(shot_ids)) or
            len(by_decision) != len(decisions) or set(by_decision) != set(shot_ids)):
        raise ValueError("Origin and motion decision shot IDs differ")
    matched_counter = {}
    unresolved_counter = []
    counter_ids = set()
    for row in counter_alignments:
        if row["counter_id"] in counter_ids:
            raise ValueError("Duplicate counter ID")
        counter_ids.add(row["counter_id"])
        if row["shot_id"] is None:
            unresolved_counter.append(row)
        elif row["shot_id"] in matched_counter or row["shot_id"] not in by_decision:
            raise ValueError("Duplicate or unknown counter-associated shot")
        else:
            matched_counter[row["shot_id"]] = row
    rescued = ({row["shot_id"]: row for row in
                rescue_weak_origins(origins, decisions)} if allow_rescue else {})
    events = []
    conflicts = []
    for origin in origins:
        shot_id = origin["shot_id"]
        decision = by_decision[shot_id]
        counter = matched_counter.get(shot_id)
        visual = decision["status"] == "corroborated_candidate"
        rescue = (allow_rescue and rescued[shot_id]["status"] == "rescued_candidate")
        if not (visual or rescue or counter):
            continue
        visual_colour = (decision["colour"] if decision["colour_status"] == "unique"
                         else rescued[shot_id]["rescued_colour"] if rescue else None)
        counter_colour = counter["colour"] if counter else None
        counter_routes = {
            "strong_origin_and_immediate_following_motion":
                "delayed_counter_and_immediate_following_motion",
            "existing_visual_candidate_and_following_motion":
                "delayed_counter_linked_to_existing_visual_candidate",
        }
        counter_source = counter_routes.get(
            counter.get("association_route") if counter else None,
            "delayed_counter_and_adjacent_motion")
        sources = (["visual_origin_and_adjacent_motion"] if visual else []) + (
            ["weak_origin_and_dual_motion"] if rescue else []) + (
            [counter_source] if counter else [])
        event = {"shot_id": shot_id, "delivery_window_s": origin["interval_s"],
                 "origin_probability": origin["probability"],
                 "evidence_sources": sources,
                 "counter_id": counter["counter_id"] if counter else None,
                 "colour": counter_colour or visual_colour,
                 "colour_status": "resolved" if counter_colour or visual_colour
                 else "ambiguous",
                 "status": "candidate"}
        if visual_colour and counter_colour and visual_colour != counter_colour:
            event["status"] = "candidate_with_colour_conflict"
            event["colour"] = None
            event["colour_status"] = "conflict"
            conflicts.append(event)
        events.append(event)
    return {"events": events, "conflicts": conflicts,
            "unassociated_counter_events": unresolved_counter}
