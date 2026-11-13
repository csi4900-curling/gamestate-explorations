"""Verify provenance and candidate accounting for the frozen dropout transfer."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


ARTIFACTS = {
    "raw": "frozen-first-span-raw.json",
    "corridor": "frozen-first-span-corridor.json",
    "anchor": "fixed-grid-right-anchor-frozen-first.json",
    "motion": "fixed-grid-motion-merged-frozen-first.json",
    "hold": "fixed-grid-hold-merged-frozen-first.json",
    "gaps": "fixed-grid-gaps-frozen-first.json",
    "rescue": "conditional-dropout-rescue-frozen-first.json",
    "patch": "conditional-dropout-patch-frozen-first.json",
    "screen": "conditional-dropout-screen-frozen-first.json",
}


def require(actual, expected, name):
    if actual != expected:
        raise ValueError(f"{name} differs: {actual!r} != {expected!r}")


def unique_ids(rows, key):
    found = [row[key] for row in rows]
    if len(found) != len(set(found)):
        raise ValueError(f"Duplicate {key}")
    return found


def verify(directory):
    paths = {key: directory / filename for key, filename in ARTIFACTS.items()}
    data = {key: json.loads(path.read_text()) for key, path in paths.items()}
    hashes = {key: file_sha256(path) for key, path in paths.items()}
    frozen = json.loads((directory / "frozen-components.json").read_text())
    full = file_sha256(directory / "source-360p.mp4")
    interval = file_sha256(directory / "source-1080p-1650-2760.mp4")
    for key, field in (
        ("raw", "source_sha256"),
        ("corridor", "source_sha256"),
        ("screen", "source_sha256"),
    ):
        require(data[key][field], full, f"{key} full source")
        require(data[key]["source_id"], frozen["source_id"], f"{key} source ID")
        require(data[key]["source_interval_s"], frozen["source_interval_s"], f"{key} interval")
    for key, field in (
        ("anchor", "video_sha256"),
        ("motion", "high_resolution_source_sha256"),
        ("rescue", "high_resolution_source_sha256"),
        ("patch", "video_sha256"),
    ):
        require(data[key][field], interval, f"{key} interval source")
    for key, field, upstream in (
        ("corridor", "input_sha256", "raw"),
        ("motion", "candidates_sha256", "corridor"),
        ("motion", "anchor_selection_sha256", "anchor"),
        ("hold", "motion_sha256", "motion"),
        ("gaps", "hold_sha256", "hold"),
        ("rescue", "base_sha256", "gaps"),
        ("rescue", "hold_sha256", "hold"),
        ("rescue", "source_motion_sha256", "motion"),
        ("patch", "motion_sha256", "rescue"),
        ("patch", "hold_sha256", "hold"),
        ("patch", "source_motion_sha256", "motion"),
        ("screen", "candidates_sha256", "corridor"),
        ("screen", "motion_sha256", "rescue"),
        ("screen", "patch_sha256", "patch"),
    ):
        require(data[key][field], hashes[upstream], f"{key} {field}")
    require(data["anchor"]["view"], "right", "anchor view")
    anchor_time = data["anchor"]["selected_anchor_time_s"]
    if anchor_time is None:
        raise ValueError("Right anchor was not selected")
    for key in ("motion", "patch"):
        require(data[key]["right_reference_anchor_time_s"], anchor_time, f"{key} anchor time")
    model_path = (
        ROOT
        / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-china-dev.npz"
    )
    require(data["patch"]["model_sha256"], file_sha256(model_path), "patch model")
    for relpath, expected in frozen["files_sha256"].items():
        require(file_sha256(ROOT / relpath), expected, f"frozen {relpath}")

    raw_ids = unique_ids(data["raw"]["events"], "id")
    candidates = unique_ids(data["corridor"]["events"], "id")
    withheld = unique_ids(data["corridor"]["withheld_events"], "id")
    if set(candidates) & set(withheld):
        raise ValueError("Corridor and withheld IDs overlap")
    require(set(candidates) | set(withheld), set(raw_ids), "corridor partition")
    for key in ("motion", "hold", "gaps", "rescue", "patch"):
        require(unique_ids(data[key]["rows"], "candidate_id"), candidates, f"{key} candidate order")
    decisions = data["screen"]["decisions"]
    require(unique_ids(decisions, "candidate_id"), candidates, "screen candidate order")
    statuses = dict(Counter(row["status"] for row in decisions))
    require(data["screen"]["decision_status_counts"], statuses, "screen status totals")
    accepted = [row["candidate_id"] for row in decisions if row["accepted"]]
    require(unique_ids(data["screen"]["events"], "id"), accepted, "accepted event order")
    for row in data["rescue"]["rows"]:
        selection = row["selection"]
        if selection.get("path") and selection.get("simulation_ready") is not False:
            raise ValueError("Rescue path marked simulation-ready")

    return {
        "status": "verified_artifact_chain_not_physical_event_validation",
        "source_id": frozen["source_id"],
        "source_interval_s": frozen["source_interval_s"],
        "full_video_sha256": full,
        "interval_video_sha256": interval,
        "artifact_sha256": hashes,
        "raw_candidate_count": len(raw_ids),
        "corridor_candidate_count": len(candidates),
        "withheld_candidate_count": len(withheld),
        "anchor_grid_sample_count": data["anchor"]["sample_count"],
        "anchor_grid_registered_count": data["anchor"]["registration_status_counts"].get(
            "registered", 0
        ),
        "anchor_time_s": anchor_time,
        "motion_status_counts": data["motion"]["selection_status_counts"],
        "hold_borrowed_sample_count": data["hold"]["borrowed_sample_count"],
        "gap_status_counts": data["gaps"]["selection_status_counts"],
        "rescue_status_counts": data["rescue"]["rescue_status_counts"],
        "screen_status_counts": statuses,
        "accepted_candidate_ids": accepted,
        "runner_sha256": file_sha256(Path(__file__)),
        "limitations": [
            "Artifact provenance and candidate accounting do not validate physical throws.",
            "There are no exhaustive independent labels or precision, recall, and F1 estimates.",
            "Selected motion paths are provisional and not simulation-ready.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Verification output already exists")
    result = verify(args.directory)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        result["raw_candidate_count"],
        result["corridor_candidate_count"],
        len(result["accepted_candidate_ids"]),
    )


if __name__ == "__main__":
    main()
