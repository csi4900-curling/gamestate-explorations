"""Merge complete rebased motion shards, retaining the local anchor provenance."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_scan_shards import merge_candidate_motion  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--partition-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Merged rebased scan already exists")
    shards = sorted(a.partition_dir.glob("candidates-*.json"))
    scans = [
        a.partition_dir / shard.name.replace("candidates-", "rebased-motion-v2-")
        for shard in shards
    ]
    if not shards or any(not path.exists() for path in scans):
        p.error("Missing partition or rebased scan")
    parent = json.loads(a.candidates.read_text())
    parts = [json.loads(path.read_text()) for path in shards]
    outputs = [json.loads(path.read_text()) for path in scans]
    if any(
        row["right_reference_anchor_time_s"] != outputs[0]["right_reference_anchor_time_s"]
        or row["rebase_code_sha256"] != outputs[0]["rebase_code_sha256"]
        or row["conditional_camera_prior"] != outputs[0]["conditional_camera_prior"]
        for row in outputs[1:]
    ):
        p.error("Rebased reference settings differ across partitions")
    merged = merge_candidate_motion(
        parent, file_sha256(a.candidates), parts, outputs, [file_sha256(path) for path in shards]
    )
    for key in (
        "right_reference_anchor_time_s",
        "right_reference_anchor_registration",
        "rebase_code_sha256",
        "conditional_camera_prior",
    ):
        merged[key] = outputs[0][key]
    merged["partition_provenance"] = [
        {
            "candidate_partition_sha256": file_sha256(shard),
            "rebased_motion_sha256": file_sha256(scan),
        }
        for shard, scan in zip(shards, scans)
    ]
    merged["merge_code_sha256"] = file_sha256(ROOT / "prototype" / "candidate_scan_shards.py")
    merged["merge_runner_sha256"] = file_sha256(Path(__file__))
    merged["status"] = "postscore_development_rebased_motion_merged_not_transfer_validation"
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(merged, indent=2) + "\n")
    print(merged["candidate_count"], merged["selection_status_counts"])


if __name__ == "__main__":
    main()
