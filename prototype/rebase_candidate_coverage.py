"""Apply a source-reviewed coverage overlay without changing event evidence."""

from copy import deepcopy


def rebase_candidate_coverage(sequence, overlay):
    if sequence["source_sha256"] != overlay["source_sha256"]:
        raise ValueError("Source fingerprints differ")
    old = {row["id"]: row["interval_s"] for row in sequence["supported_runs"]}
    new = {
        row["id"]: row["interval_s"]
        for row in overlay["supported_runs"]
        if row["layout"] == "split_2024"
    }
    if len(old) != len(sequence["supported_runs"]) or old.keys() != new.keys():
        raise ValueError("Supported run IDs differ")
    for run_id, (start, stop) in old.items():
        new_start, new_stop = new[run_id]
        if start != new_start or new_stop > stop or new_stop <= start:
            raise ValueError("Coverage overlay is not a conservative shortening")
    for row in sequence["rows"]:
        if row["observation_kind"] == "left_tracked_passage":
            run_id = row["left_event_id"].split("-", 1)[0]
        elif row["observation_kind"] == "right_observed_motion_passage":
            run_id = row["candidate_id"].split(":", 2)[1]
        else:
            raise ValueError("Unknown candidate observation kind")
        start, stop = new[run_id]
        if not start <= row["observation_time_s"] < stop:
            raise ValueError("Candidate leaves refined supported coverage")
    for right in sequence["right_proposals"]:
        start, stop = new[right["run_id"]]
        if not start <= right["passage_time_s"] < stop:
            raise ValueError("Right proposal leaves refined supported coverage")
    result = deepcopy(sequence)
    result["supported_runs"] = [{"id": run_id, "interval_s": new[run_id]} for run_id in old]
    result["coverage_gaps_s"] = deepcopy(overlay["coverage_gaps_s"])
    result["routed_coverage_status"] = (
        "source_reviewed_terminal_cut_overlay_other_gaps_still_uncertain"
    )
    result["complete_throw_sequence_verified"] = False
    return result
