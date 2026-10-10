"""Merge registration-hold scans with complete candidate coverage."""

from collections import Counter


def merge_registration_hold(motion, motion_sha256, motion_shards,
                            holds, motion_shard_hashes):
    if not (len(motion_shards) == len(holds) == len(motion_shard_hashes)) or not holds:
        raise ValueError("Missing registration hold partition")
    expected = [row["candidate_id"] for row in motion["rows"]]
    actual = []
    rows = []
    for shard, hold, digest in zip(motion_shards, holds, motion_shard_hashes):
        if hold["motion_sha256"] != digest:
            raise ValueError("Hold input hash differs")
        ids = [row["candidate_id"] for row in shard["rows"]]
        held_ids = [row["candidate_id"] for row in hold["rows"]]
        if ids != held_ids:
            raise ValueError("Hold partition coverage differs")
        actual.extend(ids)
        rows.extend(hold["rows"])
    if actual != expected:
        raise ValueError("Merged hold coverage differs")
    keys = ("source_video_sha256", "max_anchor_gap_s", "similarity_code_sha256",
            "runner_sha256")
    for hold in holds[1:]:
        if any(hold[key] != holds[0][key] for key in keys):
            raise ValueError("Hold settings or source differ")
    result = {key: holds[0][key] for key in keys}
    result.update({
        "status": "losslessly_merged_registration_hold_shards",
        "motion_sha256": motion_sha256,
        "selection_status_counts": dict(Counter(
            row["selection"]["status"] for row in rows)),
        "borrowed_sample_count": sum(row["borrowed_sample_count"]
                                     for row in rows),
        "rows": rows,
        "limitations": holds[0]["limitations"] + [
            "Inference was executed in bounded partitions; all inputs and hashes are retained."],
    })
    return result
