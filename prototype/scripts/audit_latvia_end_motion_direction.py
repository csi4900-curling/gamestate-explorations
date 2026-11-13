"""Audit candidate image directions against repeated Latvia broadcast end markers."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.end_marker_temporal import stable_marker_evidence

BASE = ROOT / "validation/throw-event-benchmark"
RUN = BASE / "layout-router/latvia24-1650-2760-raw-context-v1"
RAW = RUN / "raw.json"
EVENTS = RUN / "events.json"
MARKERS = BASE / "canada-latvia-2024/end-marker-full-2d-development.json"
TEMPORAL = ROOT / "prototype/end_marker_temporal.py"
OUT = RUN / "end-conditioned-motion-direction-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def marker_location(time_s, runs):
    for run in runs:
        if run["first_hit_s"] <= time_s <= run["last_hit_s"]:
            return "stable_marker_run", run["end"]
    return "outside_stable_marker_run", None


def main():
    if OUT.exists():
        raise ValueError("Latvia direction audit already exists")
    raw, events, markers = (json.loads(p.read_text()) for p in (RAW, EVENTS, MARKERS))
    if not (raw["source_sha256"] == events["source_sha256"] == markers["video_sha256"]):
        raise ValueError("Input sources do not match")
    raw_by_id = {row["id"]: row for row in raw["events"]}
    confirmed = {row["id"] for row in events["events"]}
    if len(raw_by_id) != len(raw["events"]) or not confirmed <= raw_by_id.keys():
        raise ValueError("Confirmed candidates are not a unique raw subset")
    temporal = stable_marker_evidence(markers["samples"])
    rows = []
    for end in (2, 3):
        run = next(row for row in temporal["stable_runs"] if row["end"] == end)
        members = [
            row
            for row in raw["events"]
            if marker_location(row["crossing_time_s"], [run])[0] == "stable_marker_run"
        ]
        confirmed_members = [row for row in members if row["id"] in confirmed]
        rows.append(
            {
                "broadcast_end_marker": end,
                "stable_marker_hit_interval_s": [run["first_hit_s"], run["last_hit_s"]],
                "marker_hit_count": run["hit_count"],
                "raw_direction_counts": dict(Counter(row["view_motion"] for row in members)),
                "context_confirmed_direction_counts": dict(
                    Counter(row["view_motion"] for row in confirmed_members)
                ),
                "context_confirmed_candidate_ids": [row["id"] for row in confirmed_members],
            }
        )
    transition = next(
        row
        for row in temporal["stable_marker_changes"]
        if row["from_end"] == 2 and row["to_end"] == 3
    )
    unassigned = [
        row["id"]
        for row in raw["events"]
        if marker_location(row["crossing_time_s"], temporal["stable_runs"])[0]
        != "stable_marker_run"
    ]
    OUT.write_text(
        json.dumps(
            {
                "status": "development_marker_conditioned_direction_audit_not_throw_classification",
                "source_sha256": raw["source_sha256"],
                "source_interval_s": raw["source_interval_s"],
                "input_sha256": {
                    "raw": digest(RAW),
                    "events": digest(EVENTS),
                    "markers": digest(MARKERS),
                    "temporal": digest(TEMPORAL),
                },
                "runner_sha256": digest(Path(__file__)),
                "marker_transition": transition,
                "rows": rows,
                "raw_candidates_outside_stable_marker_runs": unassigned,
                "limitations": [
                    "These are context-confirmed candidates, not independently labeled physical throws.",
                    "The broadcast marker is intermittent and its transition does not time a physical delivery.",
                    "Direction is in image coordinates and can change with camera layout or orientation.",
                    "This exposed Latvia interval is a transfer audit, not a held-out accuracy estimate or automatic veto.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"rows": rows, "transition": transition, "outside_stable_runs": unassigned}))


if __name__ == "__main__":
    main()
