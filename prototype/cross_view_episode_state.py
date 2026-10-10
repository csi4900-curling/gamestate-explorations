"""Attach existing partial boards to cross-view episodes without inferring truth."""

from copy import deepcopy


def attach_episode_partial_states(episodes, interval_candidates, reconciliation,
                                  full_states):
    source = episodes["source_sha256"]
    if (interval_candidates["source_sha256"] != source or
            full_states["source_sha256"] != source):
        raise ValueError("Episode, interval and full-state sources differ")
    interval = {row["id"]: row for row in interval_candidates["events"]}
    if len(interval) != len(interval_candidates["events"]):
        raise ValueError("Duplicate interval candidate ID")
    links = {row["interval_id"]: row for row in reconciliation["rows"]}
    if len(links) != len(reconciliation["rows"]) or not set(interval) <= set(links):
        raise ValueError("Incomplete interval-to-full reconciliation")
    states = {row["candidate_id"]: row for row in full_states["events"]}
    if len(states) != len(full_states["events"]):
        raise ValueError("Duplicate full-state event ID")
    covered = [left_id for ep in episodes["episodes"]
               for left_id in ep["member_left_candidate_ids"]]
    if len(covered) != len(interval) or set(covered) != set(interval):
        raise ValueError("Cross-view episodes do not cover interval candidates")
    rows = []
    for episode in episodes["episodes"]:
        members = []
        accepted = []
        for left_id in episode["member_left_candidate_ids"]:
            link = links[left_id]
            event = interval[left_id]
            full_id = link["full_id"]
            full_state = states.get(full_id)
            if (link["full_accepted"] != link["interval_accepted"] or
                    link["full_accepted"] != (full_state is not None)):
                raise ValueError(f"Accepted state differs: {left_id}")
            if full_state and (full_state["passage_time_s"] != event["crossing_time_s"]
                               or full_state["candidate_colour"] != event["colour"]):
                raise ValueError(f"Interval and full-state event differ: {left_id}")
            members.append({"interval_candidate_id": left_id,
                            "full_match_candidate_id": full_id,
                            "screen_accepted": link["full_accepted"],
                            "screen_status": link["full_status"]})
            if full_state:
                accepted.append(full_state)
        observation = deepcopy(accepted[0]["post_event_observation"]) \
            if len(accepted) == 1 else None
        status = ("no_accepted_event_member" if not accepted else
                  "multiple_accepted_members_ambiguous" if len(accepted) > 1 else
                  "partial_board_observed" if observation["stones"] else
                  "accepted_event_without_stable_board")
        blockers = ["physical_throw_identity_unverified",
                    "cross_view_stone_identity_unverified",
                    "complete_board_unverified",
                    "metric_geometry_unvalidated",
                    "persistent_stone_identity_unverified",
                    "release_and_settle_times_unverified",
                    "episode_to_physical_throw_count_unknown"]
        if observation is None or not observation["stones"]:
            blockers.append("no_stable_post_episode_board")
        if len(accepted) > 1:
            blockers.append("multiple_accepted_candidates_in_episode")
        rows.append({
            "episode_id": episode["episode_id"],
            "episode_kind": episode["episode_kind"],
            "observation_time_s": episode["observation_time_s"],
            "observation_time_semantics": episode["observation_time_semantics"],
            "colour_claim": episode["colour_claim"],
            "left_members": members,
            "right_proposal_ids": episode["right_proposal_ids"],
            "state_status": status,
            "post_event_partial_board": observation,
            "source_board_candidate_id": accepted[0]["candidate_id"]
            if len(accepted) == 1 else None,
            "complete_game_state": False,
            "physical_throw_count_verified": False,
            "cross_view_identity_verified": False,
            "transition_from_previous_episode_verified": False,
            "simulation_ready": False,
            "simulation_blockers": blockers,
        })
    return rows
