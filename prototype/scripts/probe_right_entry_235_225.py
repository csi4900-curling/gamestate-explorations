"""Replay one postreview right-entry threshold variant on preserved raw tracks."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_view_entry_triage import crossing, triage_tracks


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def variant(tracks):
    proposals = []
    for track in tracks:
        points = track["points"]
        first = points[0]
        width, height = first["bbox"][2:4]
        if first["pixel"][1] < 235 or first["cap_area_px2"] < 12 or width < height:
            continue
        early = [point for point in points if point["time_s"] <= first["time_s"] + 20]
        reached = next(
            (
                i
                for i, point in enumerate(early[1:], 1)
                if point["pixel"][1] <= 225 and first["pixel"][1] - point["pixel"][1] >= 60
            ),
            None,
        )
        if reached is None:
            continue
        prefix = early[: reached + 1]
        entry = crossing(prefix, 235)
        if entry is None:
            continue
        proposals.append(
            {
                "raw_track_id": track["track_id"],
                "colour_claim": track["colour"],
                "entry_line_y_px": 235,
                "entry_crossing": entry,
                "confirmation_time_s": prefix[-1]["time_s"],
                "observed_prefix_interval_s": [prefix[0]["time_s"], prefix[-1]["time_s"]],
                "observed_prefix_points": prefix,
                "physical_throw_identity_verified": False,
                "simulation_ready": False,
            }
        )
    return sorted(proposals, key=lambda row: (row["entry_crossing"]["time_s"], row["raw_track_id"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transfer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    transfer = json.loads(args.transfer.read_text())
    tracks = transfer["raw_tracks"]
    frozen_ids = [row["raw_track_id"] for row in transfer["entry_review_proposals"]]
    if [row["raw_track_id"] for row in triage_tracks(tracks)] != frozen_ids:
        parser.error("Frozen baseline no longer reproduces")
    proposals = variant(tracks)
    ids = {row["raw_track_id"] for row in proposals}
    added = [row["raw_track_id"] for row in proposals if row["raw_track_id"] not in frozen_ids]
    result = {
        "status": "postreview_threshold_probe_not_accepted_event_rule",
        "source_id": transfer["source_id"],
        "source_sha256": transfer["source_sha256"],
        "source_interval_s": transfer["source_interval_s"],
        "source_transfer_sha256": digest(args.transfer),
        "baseline_code_sha256": digest(ROOT / "prototype/right_view_entry_triage.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": {
            "first_and_crossing_line_y_px": 235,
            "confirmation_y_at_most_px": 225,
            "minimum_upward_displacement_px": 60,
            "maximum_confirmation_delay_s": 20,
            "minimum_first_cap_area_px2": 12,
            "first_bbox_width_at_least_height": True,
        },
        "baseline_ids": frozen_ids,
        "baseline_ids_lost": [id for id in frozen_ids if id not in ids],
        "new_ids": added,
        "entry_review_proposals": proposals,
        "limitations": [
            "Thresholds selected after inspecting missed windows on these recordings.",
            "New prefixes are review proposals, not verified delivered stones.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "baseline": len(frozen_ids),
                "variant": len(proposals),
                "new_ids": added,
                "lost": result["baseline_ids_lost"],
            }
        )
    )


if __name__ == "__main__":
    main()
