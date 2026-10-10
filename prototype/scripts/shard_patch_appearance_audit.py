"""Partition candidate-local patch audits and merge their complete results.

The appearance scorer reads only the selected candidate's motion and hold row.
This wrapper changes process size, not scoring rules or source geometry.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def ids(rows):
    return [row["candidate_id"] for row in rows]


def check_unique(rows):
    values = ids(rows)
    if len(values) != len(set(values)):
        raise ValueError("Repeated candidate ID")
    return values


def partition(args):
    if args.output_dir.exists():
        raise ValueError("Partition directory already exists")
    motion, hold = read(args.motion), read(args.hold)
    motion_ids = check_unique(motion["rows"])
    if motion_ids != check_unique(hold["rows"]):
        raise ValueError("Motion and hold candidate order differs")
    if motion["hold_sha256"] != file_sha256(args.hold):
        raise ValueError("Motion and hold hashes do not chain")
    if hold["motion_sha256"] != file_sha256(args.source_motion):
        raise ValueError("Hold and source-motion hashes do not chain")
    args.output_dir.mkdir(parents=True)
    manifest = {
        "status": "candidate_local_patch_audit_partition",
        "motion_sha256": file_sha256(args.motion),
        "hold_sha256": file_sha256(args.hold),
        "source_motion_sha256": file_sha256(args.source_motion),
        "runner_sha256": file_sha256(Path(__file__)),
        "candidate_ids": motion_ids,
        "shard_size": args.shard_size,
        "shards": [],
    }
    for index, start in enumerate(range(0, len(motion_ids), args.shard_size), 1):
        stop = start + args.shard_size
        hold_part = {**hold, "rows": hold["rows"][start:stop]}
        motion_part = {**motion, "rows": motion["rows"][start:stop]}
        hold_path = args.output_dir / f"patch-input-hold-{index:03d}.json"
        motion_path = args.output_dir / f"patch-input-motion-{index:03d}.json"
        write(hold_path, hold_part)
        motion_part["hold_sha256"] = file_sha256(hold_path)
        write(motion_path, motion_part)
        manifest["shards"].append(
            {
                "index": index,
                "candidate_ids": motion_ids[start:stop],
                "hold_sha256": file_sha256(hold_path),
                "motion_sha256": file_sha256(motion_path),
            }
        )
    write(args.output_dir / "manifest.json", manifest)
    print(len(motion_ids), "candidates in", len(manifest["shards"]), "shards")


def merge(args):
    if args.output.exists():
        raise ValueError("Merged patch audit already exists")
    manifest = read(args.partition_dir / "manifest.json")
    if (
        manifest["motion_sha256"] != file_sha256(args.motion)
        or manifest["hold_sha256"] != file_sha256(args.hold)
        or manifest["source_motion_sha256"] != file_sha256(args.source_motion)
    ):
        raise ValueError("Partition manifest differs from full inputs")
    if ids(read(args.motion)["rows"]) != manifest["candidate_ids"]:
        raise ValueError("Full motion candidate order changed")
    if ids(read(args.hold)["rows"]) != manifest["candidate_ids"]:
        raise ValueError("Full hold candidate order changed")
    rows = []
    outputs = []
    shared = None
    for shard in manifest["shards"]:
        index = shard["index"]
        motion_path = args.partition_dir / f"patch-input-motion-{index:03d}.json"
        hold_path = args.partition_dir / f"patch-input-hold-{index:03d}.json"
        output_path = args.partition_dir / f"patch-result-{index:03d}.json"
        if (
            file_sha256(motion_path) != shard["motion_sha256"]
            or file_sha256(hold_path) != shard["hold_sha256"]
        ):
            raise ValueError(f"Input hash differs in shard {index}")
        if (
            ids(read(motion_path)["rows"]) != shard["candidate_ids"]
            or ids(read(hold_path)["rows"]) != shard["candidate_ids"]
        ):
            raise ValueError(f"Input candidate IDs differ in shard {index}")
        result = read(output_path)
        if (
            result["motion_sha256"] != shard["motion_sha256"]
            or result["hold_sha256"] != shard["hold_sha256"]
            or result["source_motion_sha256"] != manifest["source_motion_sha256"]
        ):
            raise ValueError(f"Result hash chain differs in shard {index}")
        if ids(result["rows"]) != shard["candidate_ids"]:
            raise ValueError(f"Result candidate IDs differ in shard {index}")
        common = {
            key: value
            for key, value in result.items()
            if key not in ("rows", "motion_sha256", "hold_sha256")
        }
        if shared is None:
            shared = common
        elif shared != common:
            raise ValueError(f"Patch configuration differs in shard {index}")
        rows.extend(result["rows"])
        outputs.append({"index": index, "patch_sha256": file_sha256(output_path)})
    if check_unique(rows) != manifest["candidate_ids"]:
        raise ValueError("Merged candidate coverage differs")
    merged = {
        **shared,
        "motion_sha256": manifest["motion_sha256"],
        "hold_sha256": manifest["hold_sha256"],
        "rows": rows,
        "partition_manifest_sha256": file_sha256(args.partition_dir / "manifest.json"),
        "partition_outputs": outputs,
        "merge_runner_sha256": file_sha256(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, merged)
    print(len(rows), "candidate patch rows merged")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    for name in ("partition", "merge"):
        command = sub.add_parser(name)
        command.add_argument("--motion", type=Path, required=True)
        command.add_argument("--hold", type=Path, required=True)
        command.add_argument("--source-motion", type=Path, required=True)
        if name == "partition":
            command.add_argument("--output-dir", type=Path, required=True)
            command.add_argument("--shard-size", type=int, default=4)
        else:
            command.add_argument("--partition-dir", type=Path, required=True)
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "partition":
        if args.shard_size < 1:
            parser.error("Shard size must be positive")
        partition(args)
    else:
        merge(args)


if __name__ == "__main__":
    main()
