"""Merge exhaustive early Latvia red-body shards and link image paths."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import link_paths

BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
LEDGER = BASE / "full-candidate-display-context-development.json"
OUT = BASE / "early-highres-red-full-transfer-development.json"
START_S, STOP_S = 1650, 2760


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first full transfer")
    paths = sorted(BASE.glob("early-highres-red-full-shard-*.json"))
    shards = [json.loads(path.read_text()) for path in paths]
    if len(shards) != 15:
        raise ValueError("Expected 15 bounded source shards")
    for key in (
        "source_video_sha256",
        "red_template_audit_sha256",
        "runner_sha256",
        "body_code_sha256",
        "handle_code_sha256",
    ):
        if len({s[key] for s in shards}) != 1:
            raise ValueError(f"Shard provenance differs: {key}")
    covered, rows = set(), {}
    for path, shard in zip(paths, shards):
        start, stop = shard["source_interval_s"]
        span = set(range(start, stop))
        if not START_S <= start < stop <= STOP_S or covered & span:
            raise ValueError(f"Invalid or overlapping shard: {path}")
        covered |= span
        for row in shard["samples_with_body_proposals"]:
            if row["time_s"] not in span or row["time_s"] in rows:
                raise ValueError(f"Invalid or duplicated sample: {path}")
            rows[row["time_s"]] = row
        if shard["body_proposal_count"] != sum(
            len(r["body_proposals"]) for r in shard["samples_with_body_proposals"]
        ):
            raise ValueError(f"Shard count mismatch: {path}")
    if covered != set(range(START_S, STOP_S)):
        raise ValueError("Full source excerpt is not covered")
    samples = [rows.get(t, {"time_s": t, "body_proposals": []}) for t in range(START_S, STOP_S)]
    screened = [
        {
            "time_s": r["time_s"],
            "body_proposals": [p for p in r["body_proposals"] if p["red_handle_supported"]],
        }
        for r in samples
    ]
    linked = link_paths(screened)
    ledger = json.loads(LEDGER.read_text())
    candidates = [
        r
        for r in ledger["candidates"]
        if START_S <= r["crossing_time_s"] < STOP_S
        and r["observation_kind"] == "left_provisional_passage"
        and r["colour_claim"] == "red"
    ]
    context = []
    for candidate in candidates:
        t = candidate["crossing_time_s"]
        ids = [
            p["diagnostic_path_id"]
            for p in linked
            if p["direction"] == "upward" and t <= p["first_observed_s"] <= t + 25
        ]
        context.append(
            {
                "candidate_id": candidate["candidate_id"],
                "crossing_time_s": t,
                "upward_path_ids_started_within_25s": ids,
                "physical_throw_verified": False,
            }
        )
    associated = {item for row in context for item in row["upward_path_ids_started_within_25s"]}
    result = {
        "status": "full_early_excerpt_red_body_handle_development_not_event_validation",
        "source_interval_s": [START_S, STOP_S],
        "sample_period_s": 1,
        "source_video_sha256": shards[0]["source_video_sha256"],
        "red_template_audit_sha256": shards[0]["red_template_audit_sha256"],
        "candidate_ledger_sha256": digest(LEDGER),
        "joiner_sha256": digest(Path(__file__)),
        "linker_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "shards": [
            {
                "path": str(p.relative_to(ROOT)),
                "sha256": digest(p),
                "interval_s": s["source_interval_s"],
            }
            for p, s in zip(paths, shards)
        ],
        "body_proposal_count": sum(len(r["body_proposals"]) for r in samples),
        "red_handle_supported_count": sum(len(r["body_proposals"]) for r in screened),
        "supported_path_direction_counts": dict(Counter(p["direction"] for p in linked)),
        "supported_image_paths": linked,
        "candidate_context": context,
        "red_candidate_count": len(context),
        "red_candidates_with_upward_path_count": sum(
            bool(r["upward_path_ids_started_within_25s"]) for r in context
        ),
        "unassociated_upward_path_ids": [
            p["diagnostic_path_id"]
            for p in linked
            if p["direction"] == "upward" and p["diagnostic_path_id"] not in associated
        ],
        "limitations": [
            "The red template and thresholds were developed on source-visible shots in this same excerpt.",
            "Temporal proximity to a provisional candidate is not independent event validation.",
            "Unassociated upward image paths require source review before being counted as false alarms or missed throws.",
            "Greedy image links may switch from delivered to parked stones and cannot establish settled board identities.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "seconds": len(covered),
                "body": result["body_proposal_count"],
                "red_handle": result["red_handle_supported_count"],
                "paths": result["supported_path_direction_counts"],
                "red_candidate_support": result["red_candidates_with_upward_path_count"],
                "red_candidates": len(context),
                "unassociated_upward": len(result["unassociated_upward_path_ids"]),
            }
        )
    )


if __name__ == "__main__":
    main()
