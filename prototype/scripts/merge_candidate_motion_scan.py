"""Merge complete candidate motion partitions with coverage and hash guards."""

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
    p.add_argument("--scan-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Merged scan already exists")
    shard_paths = sorted(a.partition_dir.glob("candidates-*.json"))
    scan_paths = [a.scan_dir / path.name.replace("candidates-", "motion-")
                  for path in shard_paths]
    if not shard_paths or any(not path.exists() for path in scan_paths):
        p.error("Missing partition or scan output")
    parent = json.loads(a.candidates.read_text())
    shards = [json.loads(path.read_text()) for path in shard_paths]
    scans = [json.loads(path.read_text()) for path in scan_paths]
    merged = merge_candidate_motion(
        parent, file_sha256(a.candidates), shards, scans,
        [file_sha256(path) for path in shard_paths])
    merged["partition_provenance"] = [
        {"candidate_partition_sha256": file_sha256(shard),
         "motion_scan_sha256": file_sha256(scan),
         "candidate_ids": [row["id"] for row in part["events"]]}
        for shard, scan, part in zip(shard_paths, scan_paths, shards)]
    merged["merge_code_sha256"] = file_sha256(ROOT / "prototype" /
                                             "candidate_scan_shards.py")
    merged["merge_runner_sha256"] = file_sha256(Path(__file__))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(merged, indent=2) + "\n")
    print(merged["candidate_count"], merged["selection_status_counts"])


if __name__ == "__main__":
    main()
