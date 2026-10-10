"""Lossless union of two camera-local proposal lanes, without event merging."""


def union_right_proposals(first, second, *, first_lane, second_lane):
    if not first_lane or not second_lane or first_lane == second_lane:
        raise ValueError("Distinct nonempty lane names required")
    if (first["source_sha256"] != second["source_sha256"] or
            first["source_interval_s"] != second["source_interval_s"] or
            first.get("source_time_offset_s", 0) != second.get(
                "source_time_offset_s", 0)):
        raise ValueError("Proposal lanes must share the same source and interval")
    rows = []
    for lane, source in ((first_lane, first), (second_lane, second)):
        local_ids = set()
        for proposal in source["directional_review_proposals"]:
            raw_id = proposal["raw_track_id"]
            if raw_id in local_ids:
                raise ValueError(f"Duplicate raw track ID in {lane}")
            local_ids.add(raw_id)
            rows.append({
                "proposal_id": f"{lane}:{raw_id}",
                "lane": lane,
                "raw_track_id": raw_id,
                "colour_claim": proposal["colour_claim"],
                "passage": proposal["passage"],
                "observed_prefix_interval_s": proposal[
                    "observed_prefix_interval_s"],
                "observed_prefix_points": proposal["observed_prefix_points"],
                "physical_throw_identity_verified": False,
            })
    rows.sort(key=lambda row: (row["passage"]["time_s"], row["proposal_id"]))
    if len({row["proposal_id"] for row in rows}) != len(rows):
        raise AssertionError("Union lost unique proposal identity")
    return rows
