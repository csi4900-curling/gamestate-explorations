"""Create bounded, hash-linked candidate inputs for the unchanged motion runner."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_scan_shards import partition_candidates  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--size", type=int, default=4)
    a = p.parse_args()
    if a.output_dir.exists():
        p.error("Partition output directory already exists")
    parent = json.loads(a.candidates.read_text())
    shards = partition_candidates(parent, file_sha256(a.candidates), a.size)
    a.output_dir.mkdir(parents=True)
    for index, shard in enumerate(shards, 1):
        (a.output_dir / f"candidates-{index:02d}.json").write_text(
            json.dumps(shard, indent=2) + "\n"
        )
    print(len(shards), [len(shard["events"]) for shard in shards])


if __name__ == "__main__":
    main()
