"""Verify source and stage hashes for a fixed-grid throw-candidate transfer."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def load(path):
    return json.loads(path.read_text())


def require(actual, expected, label):
    if actual != expected:
        raise ValueError(f"{label} differs")


def ids(rows, field):
    values = [row[field] for row in rows]
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {field}")
    return values


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in (
        "full-video",
        "interval-video",
        "raw",
        "corridor",
        "anchor-selection",
        "motion",
        "hold",
        "gaps",
        "patch",
        "dedup",
        "screen",
        "model",
        "output",
    ):
        p.add_argument(f"--{name}", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Verification output already exists")
    raw, corridor, anchor, motion, hold, gaps, patch, dedup, screen = (
        load(getattr(a, name.replace("-", "_")))
        for name in (
            "raw",
            "corridor",
            "anchor_selection",
            "motion",
            "hold",
            "gaps",
            "patch",
            "dedup",
            "screen",
        )
    )
    full_sha = file_sha256(a.full_video)
    interval_sha = file_sha256(a.interval_video)
    require(raw["source_sha256"], full_sha, "Raw source video")
    require(corridor["input_sha256"], file_sha256(a.raw), "Corridor input")
    require(corridor["source_sha256"], full_sha, "Corridor source video")
    require(anchor["video_sha256"], interval_sha, "Anchor source video")
    require(anchor["view"], "right", "Anchor view")
    if anchor["selected_anchor_time_s"] is None:
        raise ValueError("No selected anchor")
    require(motion["candidates_sha256"], file_sha256(a.corridor), "Motion candidates")
    require(
        motion["anchor_selection_sha256"],
        file_sha256(a.anchor_selection),
        "Motion anchor selection",
    )
    require(motion["high_resolution_source_sha256"], interval_sha, "Motion source video")
    require(
        motion["right_reference_anchor_time_s"],
        anchor["selected_anchor_time_s"],
        "Motion anchor time",
    )
    require(hold["motion_sha256"], file_sha256(a.motion), "Hold motion")
    require(gaps["hold_sha256"], file_sha256(a.hold), "Gap hold")
    require(patch["motion_sha256"], file_sha256(a.gaps), "Patch paths")
    require(patch["hold_sha256"], file_sha256(a.hold), "Patch hold")
    require(patch["source_motion_sha256"], file_sha256(a.motion), "Patch source motion")
    require(patch["video_sha256"], interval_sha, "Patch source video")
    require(patch["model_sha256"], file_sha256(a.model), "Patch model")
    require(dedup["motion_sha256"], file_sha256(a.gaps), "Dedup paths")
    require(dedup["candidates_sha256"], file_sha256(a.corridor), "Dedup candidates")
    for field, path in (
        ("candidates_sha256", a.corridor),
        ("motion_sha256", a.gaps),
        ("patch_sha256", a.patch),
        ("dedup_sha256", a.dedup),
    ):
        require(screen[field], file_sha256(path), f"Screen {field}")
    candidate_ids = ids(corridor["events"], "id")
    for stage, rows in (
        ("motion", motion["rows"]),
        ("hold", hold["rows"]),
        ("gaps", gaps["rows"]),
        ("patch", patch["rows"]),
        ("dedup", dedup["decisions"]),
        ("screen", screen["decisions"]),
    ):
        require(ids(rows, "candidate_id"), candidate_ids, f"{stage} candidate order")
    accepted_ids = {d["candidate_id"] for d in screen["decisions"] if d["accepted"]}
    require({e["id"] for e in screen["events"]}, accepted_ids, "Screen event list")
    result = {
        "status": "verified_artifact_chain_not_physical_event_validation",
        "source_id": raw["source_id"],
        "source_interval_s": raw["source_interval_s"],
        "full_video_sha256": full_sha,
        "interval_video_sha256": interval_sha,
        "raw_candidate_count": len(raw["events"]),
        "corridor_candidate_count": len(candidate_ids),
        "anchor_grid_registered_count": anchor["registration_status_counts"].get("registered", 0),
        "anchor_grid_sample_count": anchor["sample_count"],
        "anchor_time_s": anchor["selected_anchor_time_s"],
        "motion_status_counts": dict(Counter(row["selection"]["status"] for row in motion["rows"])),
        "hold_borrowed_sample_count": hold["borrowed_sample_count"],
        "screen_status_counts": dict(Counter(row["status"] for row in screen["decisions"])),
        "accepted_candidate_ids": [e["id"] for e in screen["events"]],
        "runner_sha256": file_sha256(Path(__file__)),
        "limitations": [
            "This checks artifact integrity and candidate accounting, not whether any candidate is a physical throw.",
            "No independent reference is scored here.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        result["raw_candidate_count"],
        result["corridor_candidate_count"],
        len(result["accepted_candidate_ids"]),
    )


if __name__ == "__main__":
    main()
