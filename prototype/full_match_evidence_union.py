"""Conserve raw triggers while joining candidate, partial-board and view evidence."""

from collections import Counter


def build_evidence_union(raw, screen, sequence, prefixes, prefix_boards,
                         right_links, right_review):
    source = raw["source_sha256"]
    for name, artifact in (("screen", screen), ("sequence", sequence),
                           ("prefix boards", prefix_boards),
                           ("right links", right_links),
                           ("right review", right_review)):
        if artifact["source_sha256"] != source:
            raise ValueError(f"{name} source fingerprint differs")
    if raw["source_id"] != sequence["source_id"]:
        raise ValueError("Source identities differ")
    raw_by_id = {row["id"]: row for row in raw["events"]}
    decisions = {row["candidate_id"]: row for row in screen["decisions"]}
    accepted = {row["candidate_id"]: row for row in sequence["events"]}
    review = {row["candidate_id"]: row for row in prefixes["proposals"]}
    boards = {row["candidate_id"]: row for row in prefix_boards["rows"]}
    if (len(raw_by_id) != len(raw["events"]) or
            len(decisions) != len(screen["decisions"]) or
            len(accepted) != len(sequence["events"]) or
            len(review) != len(prefixes["proposals"]) or
            len(boards) != len(prefix_boards["rows"])):
        raise ValueError("Duplicate candidate ID within an input")
    if set(accepted) != {id for id, row in decisions.items() if row["accepted"]}:
        raise ValueError("Screen and accepted sequence disagree")
    if set(review) != set(boards) or set(review) & set(accepted):
        raise ValueError("Prefix board coverage or candidate tiers disagree")
    if not (set(accepted) | set(review)) <= set(raw_by_id):
        raise ValueError("Selected candidate missing from raw scan")
    duplicate_to_prefix = {}
    for prefix in review.values():
        for duplicate in prefix["duplicate_candidate_ids"]:
            if (duplicate in duplicate_to_prefix or duplicate in accepted or
                    duplicate in review or duplicate not in raw_by_id):
                raise ValueError("Invalid duplicate pre-split candidate")
            duplicate_to_prefix[duplicate] = prefix["candidate_id"]
    right_review_by_id = {row["raw_track_id"]: row for row in right_review["review"]}
    if len(right_review_by_id) != len(right_review["review"]):
        raise ValueError("Duplicate right source-review ID")
    linked = {}
    unmatched = []
    for row in right_links["links"]:
        id = row["right_raw_track_id"]
        judged = right_review_by_id[id]
        if row["match_status"] == "unique_conditional_time_colour_link":
            left_id = row["left_candidate_id"]
            if left_id not in accepted or left_id in linked:
                raise ValueError("Right link is not one-to-one with accepted events")
            if (raw_by_id[left_id]["colour"] != row["right_colour_claim"] or
                    judged["sampled_prefix_class"] != "moving_stone"):
                raise ValueError("Right link colour or source class differs")
            linked[left_id] = row
        else:
            unmatched.append({"right_raw_track_id": id,
                              "entry_time_s": row["right_entry_time_s"],
                              "colour_claim": row["right_colour_claim"],
                              "match_status": row["match_status"],
                              "development_source_class": judged["sampled_prefix_class"],
                              "physical_throw_verified": False})
    if len(right_review_by_id) != len(right_links["links"]):
        raise ValueError("Right review and link ledger differ")
    rows = []
    for id, candidate in raw_by_id.items():
        screen_row = decisions.get(id)
        common = {"candidate_id": id,
                  "passage_time_s": candidate["crossing_time_s"],
                  "colour_claim": candidate["colour"],
                  "screen_status": screen_row["status"] if screen_row else "outside_screen_corridor",
                  "physical_throw_verified": False,
                  "simulation_ready": False}
        if id in accepted:
            event = accepted[id]
            board = event["post_event_observation"]
            common.update({
                "tier": "screen_provisional",
                "agent_source_review": event["agent_source_review"],
                "post_event_board_status": board["status"],
                "partial_board_observations": board.get("stones", []),
                "right_entry_link": linked.get(id),
                "release_time_s": None,
                "physical_settle_time_s": None,
                "spin_revolution_count": None,
            })
        elif id in review:
            prefix = review[id]
            board = boards[id]["board"]
            common.update({
                "tier": "pre_split_review_only",
                "shared_prefix_samples": prefix["prefix_samples"],
                "first_ambiguity_time_s": prefix["first_ambiguity_time_s"],
                "duplicate_raw_candidate_ids": prefix["duplicate_candidate_ids"],
                "post_split_identity_verified": False,
                "post_event_board_status": board["status"],
                "partial_board_observations": board["stones"],
                "right_entry_link": None,
                "release_time_s": None,
                "physical_settle_time_s": None,
                "spin_revolution_count": None,
            })
        elif id in duplicate_to_prefix:
            common.update({"tier": "duplicate_pre_split_trigger",
                           "duplicate_of_candidate_id": duplicate_to_prefix[id],
                           "post_event_board_status": None,
                           "partial_board_observations": [],
                           "right_entry_link": None})
        else:
            common.update({"tier": "not_selected_for_event_handoff",
                           "post_event_board_status": None,
                           "partial_board_observations": [],
                           "right_entry_link": None})
        rows.append(common)
    rows.sort(key=lambda row: (row["passage_time_s"], row["candidate_id"]))
    return {
        "raw_trigger_count": len(rows),
        "candidate_tier_counts": dict(Counter(row["tier"] for row in rows)),
        "partial_board_count": sum(row["post_event_board_status"] ==
                                   "partial_stable_view_local_board" for row in rows),
        "conditional_right_link_count": len(linked),
        "unmatched_right_review_count": len(unmatched),
        "raw_candidates": rows,
        "unmatched_right_entries": unmatched,
        "simulation_ready_count": 0,
    }
