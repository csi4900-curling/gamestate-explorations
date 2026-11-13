"""Order all routed left proposals and right-entry reviews without asserting throws."""

from collections import Counter


def build_candidate_review_union(timeline, left_by_run, fusion):
    if fusion["source_sha256"] != timeline["source_sha256"]:
        raise ValueError("Candidate review sources differ")
    confirmed = {row["id"]: row for row in timeline["observed_events"]}
    if len(confirmed) != len(timeline["observed_events"]):
        raise ValueError("Duplicate confirmed timeline ID")
    rows = []
    seen = set()
    for run in timeline["supported_runs"]:
        run_id = run["id"]
        if run["layout"] == "split_2024":
            proposals = left_by_run[run_id]
        else:
            proposals = [
                dict(
                    row,
                    id=row["source_event_id"],
                    disposition="auto_confirmed_candidate",
                    stage_evidence=[],
                )
                for row in timeline["observed_events"]
                if row["source_run_id"] == run_id
            ]
        for proposal in proposals:
            candidate_id = f"{run_id}-{proposal['id']}"
            if candidate_id in seen:
                raise ValueError("Duplicate left proposal ID")
            seen.add(candidate_id)
            accepted = confirmed.get(candidate_id)
            if (proposal["disposition"] == "auto_confirmed_candidate") != (accepted is not None):
                raise ValueError(f"Left triage and accepted timeline disagree: {candidate_id}")
            if accepted and (
                accepted["colour"] != proposal["colour"]
                or accepted["crossing_time_s"] != proposal["crossing_time_s"]
            ):
                raise ValueError(f"Left triage event attributes differ: {candidate_id}")
            split = run["layout"] == "split_2024"
            observed = proposal.get("observed_motion_interval_s") if split else None
            if observed is not None and not (
                len(observed) == 2 and observed[0] <= proposal["crossing_time_s"] <= observed[1]
            ):
                raise ValueError(f"Left observed interval excludes crossing: {candidate_id}")
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "source_time_s": proposal["crossing_time_s"],
                    "observed_motion_interval_s": observed,
                    "observed_time_semantics": (
                        "first_to_confirmation_observations_not_physical_throw_segment"
                        if observed is not None
                        else "counter_or_adapter_time_only"
                    ),
                    "colour_claim": proposal["colour"],
                    "origin": "left_routed_proposal" if split else "beijing_adapter_observation",
                    "review_status": (
                        (
                            "left_context_confirmed_candidate"
                            if accepted
                            else "left_context_withheld_review"
                        )
                        if split
                        else "beijing_adapter_candidate"
                    ),
                    "source_run_id": run_id,
                    "source_candidate_id": proposal["id"],
                    "left_stage_evidence": proposal.get("stage_evidence", []),
                    "right_entry_ids": [],
                    "corroborating_right_motion_intervals_s": [],
                    "physical_throw_verified": False,
                    "release_time_s": None,
                    "physical_settle_time_s": None,
                    "complete_game_state": False,
                    "simulation_ready": False,
                }
            )
    if {row["candidate_id"] for row in rows if row["candidate_id"] in confirmed} != set(confirmed):
        raise ValueError("Some confirmed timeline events lack a left proposal")
    by_id = {row["candidate_id"]: row for row in rows}
    for right in fusion["right_entries"]:
        linked = right["conditional_left_candidate_id"]
        if linked is not None:
            if linked not in by_id:
                raise ValueError(f"Right entry links unknown left candidate: {linked}")
            by_id[linked]["right_entry_ids"].append(right["right_entry_id"])
            by_id[linked]["corroborating_right_motion_intervals_s"].append(
                right.get("right_observed_prefix_interval_s")
            )
            continue
        candidate_id = f"RIGHT-{right['right_entry_id']}"
        if candidate_id in by_id:
            raise ValueError("Duplicate right review ID")
        observed = right.get("right_observed_prefix_interval_s")
        if observed is not None and not (
            len(observed) == 2 and observed[0] <= right["right_entry_time_s"] <= observed[1]
        ):
            raise ValueError(f"Right observed prefix excludes entry: {candidate_id}")
        row = {
            "candidate_id": candidate_id,
            "source_time_s": right["right_entry_time_s"],
            "observed_motion_interval_s": observed,
            "observed_time_semantics": (
                "short_right_entry_prefix_not_physical_throw_segment"
                if observed is not None
                else "entry_time_only"
            ),
            "colour_claim": right["right_colour_claim"],
            "origin": "right_entry_review",
            "review_status": right["fusion_status"],
            "source_run_id": None,
            "source_candidate_id": right["right_raw_track_id"],
            "left_stage_evidence": [],
            "right_entry_ids": [right["right_entry_id"]],
            "corroborating_right_motion_intervals_s": [],
            "physical_throw_verified": False,
            "release_time_s": None,
            "physical_settle_time_s": None,
            "complete_game_state": False,
            "simulation_ready": False,
        }
        rows.append(row)
        by_id[candidate_id] = row
    rows.sort(key=lambda row: (row["source_time_s"], row["candidate_id"]))
    return {
        "status": "ordered_high_recall_candidate_review_not_physical_throw_timeline",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": timeline["source_interval_s"],
        "candidate_count": len(rows),
        "review_status_counts": dict(Counter(row["review_status"] for row in rows)),
        "candidates": rows,
        "limitations": [
            "Raw left and right review proposals may include people, equipment, duplicates and displaced stones.",
            "Image crossing time is not a physical release, settle or event boundary.",
            "No candidate here is independently verified as a physical throw.",
            "The ledger cannot establish complete game state or simulation readiness.",
        ],
    }
