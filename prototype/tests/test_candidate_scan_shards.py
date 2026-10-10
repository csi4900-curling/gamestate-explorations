"""Catch coverage holes and source changes during resumed motion scans."""

import pytest

from candidate_scan_shards import merge_candidate_motion, partition_candidates
from registration_hold_shards import merge_registration_hold


def test_merge_rejects_missing_candidate_partition():
    parent = {"events": [{"id": "A"}, {"id": "B"}, {"id": "C"}]}
    shards = partition_candidates(parent, "parent", 2)
    scan = {"rows": [{"candidate_id": "A", "selection": {"status": "x"}},
                     {"candidate_id": "B", "selection": {"status": "x"}}],
            "candidate_count": 2, "candidates_sha256": "shard"}
    with pytest.raises(ValueError, match="Merged candidate order or coverage"):
        merge_candidate_motion(parent, "parent", shards[:1], [scan], ["shard"])


def test_partition_rejects_duplicate_candidate_ids():
    with pytest.raises(ValueError, match="Duplicate"):
        partition_candidates({"events": [{"id": "A"}, {"id": "A"}]}, "x", 2)


def test_hold_merge_rejects_shard_with_wrong_input_hash():
    motion = {"rows": [{"candidate_id": "A"}]}
    shard = {"rows": [{"candidate_id": "A"}]}
    hold = {"motion_sha256": "wrong", "rows": [{"candidate_id": "A"}]}
    with pytest.raises(ValueError, match="Hold input hash"):
        merge_registration_hold(motion, "parent", [shard], [hold], ["correct"])
