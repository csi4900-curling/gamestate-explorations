"""Place Czech proposals in stable broadcast end-marker runs without inferring throws."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1"
RAW = RUN / "run-02/raw.json"
EVENTS = RUN / "run-02/events.json"
PREFLIGHT = RUN / "preflight.json"
MARKERS = BASE / "canada-czech-2024/end-marker-temporal-summary-postscore.json"
OFFICIAL = BASE / "canada-czech-2024/official-end-score-context.json"
OUT = RUN / "end-conditioned-candidate-inventory.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def classify_time(time_s, runs):
    for run in runs:
        if run["first_hit_s"] <= time_s <= run["last_hit_s"]:
            return "stable_marker_run", [run["end"]]
    if time_s < runs[0]["first_hit_s"]:
        return "before_first_marker_hit", [runs[0]["end"]]
    for left, right in zip(runs, runs[1:]):
        if left["last_hit_s"] < time_s < right["first_hit_s"]:
            return "between_marker_runs", [left["end"], right["end"]]
    if time_s > runs[-1]["last_hit_s"]:
        return "after_last_marker_hit", [runs[-1]["end"]]
    raise ValueError("Cannot locate candidate time")


def main():
    if OUT.exists():
        raise ValueError("End-conditioned inventory exists")
    raw, events, preflight, marker_doc, official = (
        json.loads(p.read_text()) for p in (RAW, EVENTS, PREFLIGHT, MARKERS, OFFICIAL)
    )
    if len(marker_doc["games"]) != 1:
        raise ValueError("Expected one marker scan")
    game = marker_doc["games"][0]
    if (
        raw["source_sha256"] != preflight["source_sha256"]
        or raw["source_sha256"] != events["source_sha256"]
        or raw["source_sha256"] != game["video_sha256"]
        or game["scan_sha256"] != digest(BASE / "canada-czech-2024/end-marker-full-postscore.json")
        or official["completed_ends"] != 6
        or official["nominal_completed_end_deliveries"] != 96
    ):
        raise ValueError("Source or official context differs")
    runs = game["stable_runs"]
    if [r["end"] for r in runs] != list(range(1, 7)):
        raise ValueError("Stable marker sequence differs")
    confirmed = {e["id"] for e in events["events"]}
    raw_ids = {e["id"] for e in raw["events"]}
    if len(raw_ids) != len(raw["events"]) or not confirmed <= raw_ids:
        raise ValueError("Confirmed candidates not a unique raw subset")
    rows = []
    for event in raw["events"]:
        marker_status, possible_ends = classify_time(event["crossing_time_s"], runs)
        rows.append(
            {
                "candidate_id": event["id"],
                "passage_time_s": event["crossing_time_s"],
                "colour_claim": event["colour"],
                "context_confirmed": event["id"] in confirmed,
                "marker_status": marker_status,
                "possible_end_numbers": possible_ends,
            }
        )
    end_rows = []
    for run in runs:
        members = [
            r
            for r in rows
            if r["marker_status"] == "stable_marker_run"
            and r["possible_end_numbers"] == [run["end"]]
        ]
        end_rows.append(
            {
                "end_marker": run["end"],
                "stable_marker_hit_interval_s": [run["first_hit_s"], run["last_hit_s"]],
                "marker_hit_count": run["hit_count"],
                "raw_candidate_ids": [r["candidate_id"] for r in members],
                "raw_candidate_count": len(members),
                "context_confirmed_candidate_ids": [
                    r["candidate_id"] for r in members if r["context_confirmed"]
                ],
                "context_confirmed_candidate_count": sum(r["context_confirmed"] for r in members),
                "nominal_deliveries_in_completed_end": 16,
            }
        )
    outside = [r for r in rows if r["marker_status"] != "stable_marker_run"]
    output = {
        "status": "broadcast_end_conditioned_candidate_inventory_not_throw_reference",
        "source_sha256": raw["source_sha256"],
        "source_interval_s": preflight["source_interval_s"],
        "supported_runs": [r for r in preflight["runs"] if r["layout"] != "unknown"],
        "coverage_gaps_s": preflight["coverage_gaps_s"],
        "input_sha256": {
            "raw": digest(RAW),
            "events": digest(EVENTS),
            "preflight": digest(PREFLIGHT),
            "markers": digest(MARKERS),
            "official_context": digest(OFFICIAL),
        },
        "runner_sha256": digest(Path(__file__)),
        "official_nominal_completed_end_deliveries": 96,
        "raw_candidate_count": len(rows),
        "context_confirmed_count": len(confirmed),
        "stable_marker_end_rows": end_rows,
        "outside_stable_marker_rows": outside,
        "rows": rows,
        "limitations": [
            "The 16-per-end number is nominal official delivery context, not a video-aligned physical throw label list.",
            "The broadcast marker is intermittently visible; times before, between and after stable runs are not forced into an end.",
            "A context-confirmed candidate can be a non-stone path; a missing candidate does not prove no throw occurred.",
            "The first 90 and last 113 source seconds are unknown-layout coverage gaps in this run.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "stable_confirmed": [r["context_confirmed_candidate_count"] for r in end_rows],
                "outside_stable_marker": len(outside),
                "outside_confirmed": sum(r["context_confirmed"] for r in outside),
            }
        )
    )


if __name__ == "__main__":
    main()
