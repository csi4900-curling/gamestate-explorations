"""Merge registration-hold partitions without changing their inference."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from registration_hold_shards import merge_registration_hold  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--motion", type=Path, required=True)
    p.add_argument("--partition-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Merged hold already exists")
    motion_paths = sorted(a.partition_dir.glob("motion-*.json"))
    hold_paths = [a.partition_dir / path.name.replace("motion-", "hold-") for path in motion_paths]
    if not motion_paths or any(not path.exists() for path in hold_paths):
        p.error("Missing motion or hold partition")
    motion = json.loads(a.motion.read_text())
    shards = [json.loads(path.read_text()) for path in motion_paths]
    holds = [json.loads(path.read_text()) for path in hold_paths]
    result = merge_registration_hold(
        motion, file_sha256(a.motion), shards, holds, [file_sha256(path) for path in motion_paths]
    )
    result["partition_provenance"] = [
        {"motion_sha256": file_sha256(motion_path), "hold_sha256": file_sha256(hold_path)}
        for motion_path, hold_path in zip(motion_paths, hold_paths)
    ]
    result["merge_code_sha256"] = file_sha256(ROOT / "prototype" / "registration_hold_shards.py")
    result["merge_runner_sha256"] = file_sha256(Path(__file__))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["selection_status_counts"], "borrowed", result["borrowed_sample_count"])


if __name__ == "__main__":
    main()
