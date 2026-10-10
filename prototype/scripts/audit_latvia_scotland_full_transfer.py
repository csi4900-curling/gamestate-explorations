"""Verify the two saved full-source 2024 routed timelines and interval replay."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage"
OUTPUT = BASE / "latvia-scotland-full-transfer-audit.json"
SOURCES = (
    ("latvia", "canada-latvia-2024", 96),
    ("scotland", "canada-scotland-2024", 112),
)


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def audit(name, source_dir, nominal):
    directory = BASE / f"{name}24-full-v1"
    preflight_path = directory / "preflight.json"
    timeline_path = directory / "timeline.json"
    preflight, timeline = read(preflight_path), read(timeline_path)
    source = ROOT / "validation/throw-event-benchmark" / source_dir / "source-360p.mp4"
    assert digest(source) == preflight["source_sha256"] == timeline["source_sha256"]
    assert digest(preflight_path) == timeline["preflight_artifact_sha256"]
    assert timeline["coverage_gaps_s"] == preflight["coverage_gaps_s"]
    assert timeline["observed_event_count"] == len(timeline["observed_events"])
    assert len(timeline["supported_runs"]) == sum(
        r["layout"] != "unknown" for r in preflight["runs"]
    )
    raw = []
    review_count = 0
    for run in timeline["supported_runs"]:
        folder = directory / Path(run["adapter_artifact"]).parent
        candidates = read(folder / "raw.json")
        screen = read(folder / "events.json")
        triage = read(folder / "triage.json")
        interval = run["interval_s"]
        for artifact in (candidates, screen, triage):
            assert artifact["source_sha256"] == preflight["source_sha256"]
            assert artifact["source_interval_s"] == interval
        assert triage["raw_sha256"] == digest(folder / "raw.json")
        assert triage["confirmation_sha256"] == digest(folder / "events.json")
        assert triage["counts"]["proposed"] == len(candidates["events"])
        assert triage["counts"]["auto_confirmed"] == len(screen["events"])
        assert triage["counts"]["needs_review"] + len(screen["events"]) == len(candidates["events"])
        assert run["observed_event_count"] == len(screen["events"])
        raw.extend(candidates["events"])
        review_count += triage["counts"]["needs_review"]
    old = read(
        ROOT / "validation/throw-event-benchmark" / source_dir / "frozen-first-span-raw.json"
    )
    assert old["source_sha256"] == preflight["source_sha256"]

    # Exclude only the routed run boundaries. The old interval's right edge
    # can still change whether a near-edge track has time to be emitted.
    def eligible(t):
        return 1650 <= t < 2760 and any(
            row["layout"] != "unknown" and row["interval_s"][0] + 2 <= t < row["interval_s"][1] - 2
            for row in preflight["runs"]
        )

    earlier = [e for e in old["events"] if eligible(e["crossing_time_s"])]
    current = [e for e in raw if eligible(e["crossing_time_s"])]
    remaining = current[:]
    matched = []
    unmatched_old = []
    for event in earlier:
        same = [
            candidate
            for candidate in remaining
            if candidate["colour"] == event["colour"]
            and abs(candidate["crossing_time_s"] - event["crossing_time_s"]) <= 0.25
        ]
        if same:
            candidate = min(
                same, key=lambda row: abs(row["crossing_time_s"] - event["crossing_time_s"])
            )
            remaining.remove(candidate)
            matched.append(abs(candidate["crossing_time_s"] - event["crossing_time_s"]))
        else:
            unmatched_old.append(event)
    supported = sum(
        end - start
        for row in preflight["runs"]
        if row["layout"] != "unknown"
        for start, end in [row["interval_s"]]
    )
    return {
        "source_sha256": preflight["source_sha256"],
        "preflight_sha256": digest(preflight_path),
        "timeline_sha256": digest(timeline_path),
        "source_interval_s": preflight["source_interval_s"],
        "supported_seconds": supported,
        "coverage_gaps_s": preflight["coverage_gaps_s"],
        "raw_proposals": len(raw),
        "auto_accepted_candidates": len(timeline["observed_events"]),
        "review_proposals": review_count,
        "boundary_review_candidates": sum(
            e["boundary_review_required"] for e in timeline["observed_events"]
        ),
        "accepted_colours": {
            colour: sum(e["colour"] == colour for e in timeline["observed_events"])
            for colour in ("red", "yellow")
        },
        "nominal_completed_end_deliveries": nominal,
        "accepted_minus_nominal": len(timeline["observed_events"]) - nominal,
        "fixed_interval_raw_replay": {
            "earlier_eligible": len(earlier),
            "full_pass_eligible": len(current),
            "matched_same_colour_within_quarter_second": len(matched),
            "maximum_matched_time_delta_s": max(matched, default=None),
            "earlier_unmatched": [[e["crossing_time_s"], e["colour"]] for e in unmatched_old],
            "full_pass_unmatched": [[e["crossing_time_s"], e["colour"]] for e in remaining],
        },
    }


def main():
    result = {
        "status": "development_full_source_coverage_and_reproducibility_not_event_f1",
        "sources": {
            name: audit(name, source_dir, nominal) for name, source_dir, nominal in SOURCES
        },
        "limitations": [
            "Nominal completed-end deliveries are count constraints, not timestamped event labels.",
            "Routed support is sampled layout support, not continuous throw coverage.",
            "Raw and accepted event candidates can include false positives and miss physical deliveries.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                name: {
                    key: row[key]
                    for key in ("raw_proposals", "auto_accepted_candidates", "review_proposals")
                }
                for name, row in result["sources"].items()
            }
        )
    )


if __name__ == "__main__":
    main()
