"""Inventory all Czech raw proposals withheld for large surrounding motion."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "validation/throw-event-benchmark/layout-router/czech24-full-camera-motion-v1"
RAW = RUN / "run-02/raw.json"
EVENTS = RUN / "run-02/events.json"
INVENTORY = RUN / "end-conditioned-candidate-inventory.json"
DIRECTION = RUN / "end-conditioned-motion-direction-development.json"
OUT = RUN / "large-surrounding-motion-rejections-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Large-motion rejection audit already exists")
    raw, events, inventory, direction = (
        json.loads(path.read_text()) for path in (RAW, EVENTS, INVENTORY, DIRECTION)
    )
    if not (
        raw["source_sha256"]
        == events["source_sha256"]
        == inventory["source_sha256"]
        == direction["source_sha256"]
    ):
        raise ValueError("Source mismatch")
    if (
        inventory["input_sha256"]["raw"] != digest(RAW)
        or inventory["input_sha256"]["events"] != digest(EVENTS)
        or direction["input_sha256"]["inventory"] != digest(INVENTORY)
    ):
        raise ValueError("Upstream artifact mismatch")
    raw_by_id = {row["id"]: row for row in raw["events"]}
    inventory_by_id = {row["candidate_id"]: row for row in inventory["rows"]}
    confirmed = {row["id"] for row in events["events"]}
    dominant = {row["end_marker"]: row["dominant_direction"] for row in direction["rows"]}
    runs = {row["end_marker"]: row for row in inventory["stable_marker_end_rows"]}
    if len(raw_by_id) != len(raw["events"]) or set(inventory_by_id) != set(raw_by_id):
        raise ValueError("Raw IDs differ from end inventory")
    rows = []
    for decision in events["decisions"]:
        if decision["reason"] != "large_surrounding_motion":
            continue
        id = decision["id"]
        if id in confirmed or decision["status"] != "unconfirmed":
            raise ValueError(f"Large-motion proposal unexpectedly confirmed: {id}")
        event = raw_by_id[id]
        placement = inventory_by_id[id]
        time_s = event["crossing_time_s"]
        end = (
            placement["possible_end_numbers"][0]
            if placement["marker_status"] == "stable_marker_run"
            else None
        )
        run = runs[end] if end is not None else None
        confirmed_times = (
            sorted(
                raw_by_id[other]["crossing_time_s"]
                for other in run["context_confirmed_candidate_ids"]
            )
            if run
            else []
        )
        before = [t for t in confirmed_times if t < time_s]
        after = [t for t in confirmed_times if t > time_s]
        edge_distance = (
            min(
                time_s - run["stable_marker_hit_interval_s"][0],
                run["stable_marker_hit_interval_s"][1] - time_s,
            )
            if run
            else None
        )
        rows.append(
            {
                "candidate_id": id,
                "passage_time_s": time_s,
                "colour_claim": event["colour"],
                "view_motion": event["view_motion"],
                "changed_px_80x80": decision["changed_px_80x80"],
                "marker_status": placement["marker_status"],
                "stable_broadcast_end_marker": end,
                "direction_matches_end_dominant": (
                    event["view_motion"] == dominant[end] if end is not None else None
                ),
                "nearest_confirmed_before_s": before[-1] if before else None,
                "nearest_confirmed_after_s": after[0] if after else None,
                "distance_to_nearest_confirmed_s": min(
                    (abs(time_s - t) for t in confirmed_times), default=None
                ),
                "distance_to_stable_marker_edge_s": edge_distance,
            }
        )
    OUT.write_text(
        json.dumps(
            {
                "status": "development_inventory_of_context_rejections_not_throw_labels",
                "source_sha256": raw["source_sha256"],
                "input_sha256": {
                    "raw": digest(RAW),
                    "events": digest(EVENTS),
                    "end_inventory": digest(INVENTORY),
                    "end_direction": digest(DIRECTION),
                },
                "runner_sha256": digest(Path(__file__)),
                "large_surrounding_motion_rejection_count": len(rows),
                "rows": rows,
                "limitations": [
                    "A large-motion rejection is a context-stage decision, not proof of a non-stone path.",
                    "The bracket times are context-confirmed candidates, not verified physical deliveries.",
                    "Image-direction agreement and marker-edge distance are review context, not classifier thresholds.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "rejected": len(rows),
                "within_stable_marker_runs": sum(
                    row["stable_broadcast_end_marker"] is not None for row in rows
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
