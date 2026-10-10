"""Place visual-only proposals between independently ordered counter anchors."""

from bisect import bisect_right


def audit_counter_gaps(slots, candidates, colour_rows):
    """Return temporal proposal groups without asserting physical shot identity."""
    anchor_indices = [i for i, slot in enumerate(slots) if slot["counter_id"]]
    anchor_times = [slots[i]["video_event_evidence"]["candidate_release_window_s"][0]
                    for i in anchor_indices]
    if any(a >= b for a, b in zip(anchor_times, anchor_times[1:])):
        raise ValueError("Counter anchor candidate times are not strictly ordered")
    visual = [row for row in candidates if row["counter_id"] is None and
              row["evidence_class"] == "origin_view_candidate"]
    by_colour = {row["candidate_id"]: row for row in colour_rows}
    if (len(by_colour) != len(colour_rows) or len({row["candidate_id"] for row in visual})
            != len(visual) or set(by_colour) != {row["candidate_id"] for row in visual}):
        raise ValueError("Visual candidate and colour handoff IDs differ")
    groups = {}
    for row in visual:
        time_s = row["release_window_s"][0]
        gap = bisect_right(anchor_times, time_s)
        if (gap and time_s == anchor_times[gap - 1]) or (
                gap < len(anchor_times) and time_s == anchor_times[gap]):
            raise ValueError("Visual candidate starts exactly at a counter anchor")
        groups.setdefault(gap, []).append(row)
    result = []
    for gap in range(len(anchor_indices) + 1):
        left_index = anchor_indices[gap - 1] if gap else -1
        right_index = anchor_indices[gap] if gap < len(anchor_indices) else len(slots)
        missing = slots[left_index + 1:right_index]
        proposals = sorted(groups.get(gap, []),
                           key=lambda row: row["release_window_s"][0])
        if any(slot["counter_id"] for slot in missing):
            raise ValueError("Gap contains a counter anchor")
        if not missing and not proposals:
            continue
        if not missing:
            status = "visual_proposals_without_missing_official_slot"
        elif not proposals:
            status = "missing_slots_without_visual_proposal"
        elif len(missing) == len(proposals) == 1:
            status = "single_temporal_proposal_not_identity_verified"
        elif len(proposals) > len(missing):
            status = "more_visual_proposals_than_missing_slots"
        elif len(proposals) < len(missing):
            status = "fewer_visual_proposals_than_missing_slots"
        else:
            status = "equal_multi_proposals_ambiguous_identity"
        result.append({
            "preceding_counter_id": slots[left_index]["counter_id"]
            if left_index >= 0 else None,
            "following_counter_id": slots[right_index]["counter_id"]
            if right_index < len(slots) else None,
            "missing_official_slots": [{"official_shot_id": slot["official_shot_id"],
                                        "official_colour": slot["official_colour"]}
                                       for slot in missing],
            "visual_only_candidates": [{
                "candidate_id": row["candidate_id"],
                "shot_id": row["shot_id"],
                "release_window_s": row["release_window_s"],
                "origin_colour": by_colour[row["candidate_id"]]["origin_colour"],
                "receiving_colour": by_colour[row["candidate_id"]]["receiving_colour"],
                "two_view_colour": by_colour[row["candidate_id"]]["two_view_colour"],
                "colour_relation": by_colour[row["candidate_id"]]["relation"],
            } for row in proposals],
            "status": status,
            "physical_throw_identity_verified": False,
            "official_slot_association_verified": False,
        })
    return result
