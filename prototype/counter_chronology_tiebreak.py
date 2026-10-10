"""Source-order diagnostic for ambiguous delayed-counter associations."""


def audit_counter_chronology(counter_rows, *, min_origin_probability=0.2):
    """Choose only a unique high-origin option ending after prior update."""
    ordered = sorted(counter_rows, key=lambda row: row["counter_update_s"])
    if len({row["counter_id"] for row in ordered}) != len(ordered):
        raise ValueError("Duplicate counter ID")
    if any(right["counter_update_s"] <= left["counter_update_s"]
           for left, right in zip(ordered, ordered[1:])):
        raise ValueError("Counter updates are not strictly chronological")
    ambiguous = []
    existing_link_conflicts = []
    for previous, current in zip(ordered, ordered[1:]):
        prior_time = previous["counter_update_s"]
        if current["shot_id"] is not None:
            chosen = [option for option in current["candidate_shots"]
                      if option["shot_id"] == current["shot_id"]]
            if len(chosen) == 1 and chosen[0]["interval_s"][1] < prior_time:
                existing_link_conflicts.append({
                    "counter_id": current["counter_id"],
                    "shot_id": current["shot_id"],
                    "previous_counter_id": previous["counter_id"],
                    "shot_end_before_previous_update_s": round(
                        prior_time - chosen[0]["interval_s"][1], 3),
                })
            continue
        if len(current["candidate_shots"]) < 2:
            continue
        options = []
        for candidate in current["candidate_shots"]:
            shot_end = candidate["interval_s"][1]
            qualifies = (candidate["origin_probability"] >= min_origin_probability
                         and shot_end >= prior_time)
            options.append({
                "shot_id": candidate["shot_id"],
                "interval_s": candidate["interval_s"],
                "origin_probability": candidate["origin_probability"],
                "shot_end_minus_previous_update_s": round(shot_end - prior_time, 3),
                "passes_tiebreak": qualifies,
            })
        choices = [row["shot_id"] for row in options if row["passes_tiebreak"]]
        ambiguous.append({
            "counter_id": current["counter_id"],
            "counter_colour": current["colour"],
            "previous_counter_id": previous["counter_id"],
            "previous_counter_update_s": prior_time,
            "counter_update_s": current["counter_update_s"],
            "chosen_shot_id": choices[0] if len(choices) == 1 else None,
            "status": "unique_chronological_option" if len(choices) == 1 else "abstained",
            "options": options,
        })
    return {"ambiguous_rows": ambiguous,
            "existing_link_temporal_conflicts": existing_link_conflicts}
