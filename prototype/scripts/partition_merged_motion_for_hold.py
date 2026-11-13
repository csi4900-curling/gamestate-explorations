"""Partition a provenance-checked merged motion scan into singleton hold inputs."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Hold partition directory exists")
    source = json.loads(args.motion.read_text())
    rows = source["rows"]
    if len(rows) != source["candidate_count"] or len({row["candidate_id"] for row in rows}) != len(
        rows
    ):
        raise ValueError("Merged motion coverage is inconsistent")
    digest = file_sha256(args.motion)
    args.output_dir.mkdir(parents=True)
    for index, row in enumerate(rows, 1):
        part = {
            **source,
            "status": "singleton_hold_input_from_merged_motion",
            "candidate_count": 1,
            "selection_status_counts": dict(Counter([row["selection"]["status"]])),
            "rows": [row],
            "parent_motion_sha256": digest,
            "singleton_partition_index": index,
            "partition_runner_sha256": file_sha256(Path(__file__)),
        }
        (args.output_dir / f"fixed-grid-motion-{index:03d}.json").write_text(
            json.dumps(part, indent=2) + "\n"
        )
    print(len(rows), "singleton hold inputs")


if __name__ == "__main__":
    main()
