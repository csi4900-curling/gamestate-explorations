"""Run the unchanged post-event board observer on candidate-local screen shards."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def unique_ids(rows, field):
    ids = [row[field] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate candidate ID")
    return ids


def partition(args):
    if args.output_dir.exists():
        raise ValueError("Board partition directory exists")
    screen = read(args.screen)
    accepted_ids = unique_ids(screen["events"], "id")
    decision_ids = {row["candidate_id"] for row in screen["decisions"] if row["accepted"]}
    if set(accepted_ids) != decision_ids:
        raise ValueError("Screen accepted IDs differ from event rows")
    if screen["candidates_sha256"] != file_sha256(args.candidates) or screen[
        "motion_sha256"
    ] != file_sha256(args.motion):
        raise ValueError("Screen input chain differs")
    args.output_dir.mkdir(parents=True)
    manifest = {
        "status": "candidate_local_post_event_board_partition",
        "screen_sha256": file_sha256(args.screen),
        "candidates_sha256": file_sha256(args.candidates),
        "motion_sha256": file_sha256(args.motion),
        "runner_sha256": file_sha256(Path(__file__)),
        "accepted_ids": accepted_ids,
        "shard_size": args.shard_size,
        "shards": [],
    }
    for index, start in enumerate(range(0, len(accepted_ids), args.shard_size), 1):
        part = {**screen, "events": screen["events"][start : start + args.shard_size]}
        path = args.output_dir / f"board-input-screen-{index:03d}.json"
        write(path, part)
        manifest["shards"].append(
            {
                "index": index,
                "accepted_ids": accepted_ids[start : start + args.shard_size],
                "screen_sha256": file_sha256(path),
            }
        )
    write(args.output_dir / "manifest.json", manifest)
    print(len(accepted_ids), "accepted candidates in", len(manifest["shards"]), "shards")


def merge(args):
    if args.output.exists():
        raise ValueError("Merged boards already exist")
    manifest = read(args.partition_dir / "manifest.json")
    if (
        manifest["screen_sha256"] != file_sha256(args.screen)
        or manifest["candidates_sha256"] != file_sha256(args.candidates)
        or manifest["motion_sha256"] != file_sha256(args.motion)
    ):
        raise ValueError("Full board inputs differ from partition manifest")
    if unique_ids(read(args.screen)["events"], "id") != manifest["accepted_ids"]:
        raise ValueError("Full accepted candidate order changed")
    rows, outputs, shared = [], [], None
    for shard in manifest["shards"]:
        index = shard["index"]
        screen_path = args.partition_dir / f"board-input-screen-{index:03d}.json"
        result_path = args.partition_dir / f"board-result-{index:03d}.json"
        if (
            file_sha256(screen_path) != shard["screen_sha256"]
            or unique_ids(read(screen_path)["events"], "id") != shard["accepted_ids"]
        ):
            raise ValueError(f"Board input differs in shard {index}")
        result = read(result_path)
        if (
            result["screen_sha256"] != shard["screen_sha256"]
            or result["candidates_sha256"] != manifest["candidates_sha256"]
            or result["motion_sha256"] != manifest["motion_sha256"]
            or unique_ids(result["rows"], "candidate_id") != shard["accepted_ids"]
        ):
            raise ValueError(f"Board output differs in shard {index}")
        common = {
            key: value
            for key, value in result.items()
            if key not in ("rows", "screen_sha256", "board_status_counts")
        }
        if shared is None:
            shared = common
        elif shared != common:
            raise ValueError(f"Board configuration differs in shard {index}")
        rows.extend(result["rows"])
        outputs.append({"index": index, "result_sha256": file_sha256(result_path)})
    if unique_ids(rows, "candidate_id") != manifest["accepted_ids"]:
        raise ValueError("Merged board candidate coverage differs")
    merged = {
        **shared,
        "screen_sha256": manifest["screen_sha256"],
        "board_status_counts": dict(Counter(row["board"]["status"] for row in rows)),
        "rows": rows,
        "partition_manifest_sha256": file_sha256(args.partition_dir / "manifest.json"),
        "partition_outputs": outputs,
        "merge_runner_sha256": file_sha256(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, merged)
    print(len(rows), "candidate board rows", merged["board_status_counts"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    for name in ("partition", "merge"):
        q = sub.add_parser(name)
        q.add_argument("--screen", type=Path, required=True)
        q.add_argument("--candidates", type=Path, required=True)
        q.add_argument("--motion", type=Path, required=True)
        if name == "partition":
            q.add_argument("--output-dir", type=Path, required=True)
            q.add_argument("--shard-size", type=int, default=1)
        else:
            q.add_argument("--partition-dir", type=Path, required=True)
            q.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.mode == "partition":
        if args.shard_size < 1:
            p.error("Shard size must be positive")
        partition(args)
    else:
        merge(args)


if __name__ == "__main__":
    main()
