"""Partition candidate scans without changing per-candidate inference."""

from collections import Counter
from copy import deepcopy


def partition_candidates(parent, parent_sha256, size):
    if size <= 0:
        raise ValueError("Shard size must be positive")
    events = parent["events"]
    if len({row["id"] for row in events}) != len(events):
        raise ValueError("Duplicate parent candidate ID")
    partitions = []
    for offset in range(0, len(events), size):
        shard = deepcopy(parent)
        shard["status"] = "candidate_scan_partition_of_frozen_corridor"
        shard["parent_candidates_sha256"] = parent_sha256
        shard["partition_range"] = [offset, min(offset + size, len(events))]
        shard["events"] = events[offset : offset + size]
        shard["withheld_events"] = []
        shard["screened_events"] = []
        partitions.append(shard)
    return partitions


def merge_candidate_motion(parent, parent_sha256, partitions, scans, scan_hashes):
    if not (len(partitions) == len(scans) == len(scan_hashes)) or not scans:
        raise ValueError("Missing candidate scan partition")
    expected_ids = [row["id"] for row in parent["events"]]
    observed_ids = []
    rows = []
    for shard, scan, digest in zip(partitions, scans, scan_hashes):
        if shard["parent_candidates_sha256"] != parent_sha256:
            raise ValueError("Partition has a different parent")
        ids = [row["id"] for row in shard["events"]]
        actual = [row["candidate_id"] for row in scan["rows"]]
        if actual != ids or scan["candidate_count"] != len(ids):
            raise ValueError("Partition scan coverage differs")
        if scan["candidates_sha256"] != digest:
            raise ValueError("Partition scan input hash differs")
        observed_ids.extend(ids)
        rows.extend(scan["rows"])
    if observed_ids != expected_ids:
        raise ValueError("Merged candidate order or coverage differs")
    keys = (
        "candidate_source_id",
        "candidate_source_sha256",
        "high_resolution_source_sha256",
        "source_offset_s",
        "lookahead_s",
        "sample_period_s",
        "max_corner_displacement_px",
        "vision_calibration_sha256",
        "rectification_sha256",
        "registration_code_sha256",
        "detector_code_sha256",
        "selector_sha256",
        "runner_sha256",
    )
    for scan in scans[1:]:
        if any(scan[key] != scans[0][key] for key in keys):
            raise ValueError("Scan settings or source differ across partitions")
    merged = {key: scans[0][key] for key in keys}
    merged.update(
        {
            "status": "losslessly_merged_candidate_centric_motion_shards",
            "candidates_sha256": parent_sha256,
            "candidate_count": len(rows),
            "selection_status_counts": dict(Counter(row["selection"]["status"] for row in rows)),
            "rows": rows,
            "limitations": scans[0]["limitations"]
            + [
                "Inference was executed in bounded partitions; each partition and its input hash are retained."
            ],
        }
    )
    return merged
