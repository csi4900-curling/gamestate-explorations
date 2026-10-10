"""Reconcile full Czech proposal motion with the frozen raw inventory."""

from collections import Counter
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1/run-02"
PREFLIGHT = BASE / "layout-router/czech24-full-camera-motion-v1/preflight.json"
OLD = BASE / "canada-czech-2024/full-match-stage1-raw-postscore.json"
SOURCE_REVIEW = BASE / "canada-czech-2024/source-review"
RAW_S96_REVIEW = (
    BASE / "layout-router/czech24-full-camera-motion-v1/s96-raw-source-review/REVIEW.md"
)
RAW_S96_MANIFEST = RAW_S96_REVIEW.with_name("manifest.json")
OUT = BASE / "layout-router/czech24-full-camera-motion-v1/candidate-motion-audit.json"


def load(path):
    return json.loads(path.read_text())


def main():
    if OUT.exists():
        raise ValueError("Audit exists; preserve prior result")
    raw_path, side_path, events_path = (
        RUN / "raw.json",
        RUN / "candidate-camera-motion.json",
        RUN / "events.json",
    )
    raw, side, events, old, preflight = map(
        load, (raw_path, side_path, events_path, OLD, PREFLIGHT)
    )
    if (
        raw["source_sha256"] != old["source_sha256"]
        or raw["source_sha256"] != preflight["source_sha256"]
        or side["input_sha256"]
        != {"raw": file_sha256(raw_path), "preflight": file_sha256(PREFLIGHT)}
        or raw["source_interval_s"] != [90.0, 6570.0]
    ):
        raise ValueError("Source or sidecar lineage differs")
    keys = lambda rows: [(r["colour"], r["crossing_time_s"]) for r in rows]
    new_keys, old_keys = keys(raw["events"]), keys(old["events"])
    if new_keys != old_keys:
        raise ValueError("Current and frozen raw proposals differ")
    by_id = {row["id"]: row for row in side["rows"]}
    if len(by_id) != len(raw["events"]) or set(by_id) != {row["id"] for row in raw["events"]}:
        raise ValueError("Camera motion sidecar is not proposal-complete")
    residuals = [
        row["camera_residual_px"] for row in side["rows"] if row["camera_residual_px"] is not None
    ]
    confirmed = {row["id"] for row in events["events"]}
    negatives = []
    for candidate_id in ("S96", "S143"):
        review_path = SOURCE_REVIEW / f"{candidate_id.lower()}-review.json"
        review = load(review_path)
        negatives.append(
            {
                "candidate_id": candidate_id,
                "source_review_sha256": file_sha256(review_path),
                "review_status": review["review_conclusion"],
                "review_applies_to": "downstream_associated_path_not_verified_raw_trigger",
                "passage_time_s": next(
                    r["crossing_time_s"] for r in raw["events"] if r["id"] == candidate_id
                ),
                "context_confirmed": candidate_id in confirmed,
                "camera_motion": by_id[candidate_id],
            }
        )
    result = {
        "status": "full_source_development_motion_audit_not_throw_f1",
        "source_sha256": raw["source_sha256"],
        "source_interval_s": preflight["source_interval_s"],
        "supported_runs": [r for r in preflight["runs"] if r["layout"] != "unknown"],
        "coverage_gaps_s": preflight["coverage_gaps_s"],
        "input_sha256": {
            "preflight": file_sha256(PREFLIGHT),
            "raw": file_sha256(raw_path),
            "sidecar": file_sha256(side_path),
            "confirmed": file_sha256(events_path),
            "old_raw": file_sha256(OLD),
        },
        "runner_sha256": file_sha256(__file__),
        "summary": {
            "raw_proposals": len(raw["events"]),
            "exact_old_raw_colour_time_sequence_match": True,
            "context_confirmed": len(confirmed),
            "camera_registered": len(residuals),
            "camera_abstained": len(side["rows"]) - len(residuals),
            "camera_status_counts": dict(Counter(r["status"] for r in side["rows"])),
            "registered_residual_over_5_px": sum(v > 5 for v in residuals),
            "registered_residual_min_px": min(residuals),
            "registered_residual_median_px": statistics.median(residuals),
            "registered_residual_max_px": max(residuals),
        },
        "source_reviewed_downstream_non_stone_paths": negatives,
        "raw_S96_source_review": {
            "status": "agent_review_player_wheelchair_attached_feature_not_independent",
            "review_sha256": file_sha256(RAW_S96_REVIEW),
            "frame_manifest_sha256": file_sha256(RAW_S96_MANIFEST),
        },
        "limitations": [
            "The raw proposal inventory omits physical throws missed by the detector.",
            "The S96 and S143 non-stone reviews apply to associated downstream paths, not independently verified continuations of the raw trigger; the reviews were performed by the detector developer.",
            "A 5-pixel motion threshold was examined on development paths and offers no separation among registered Czech raw proposals.",
            "Coverage gaps and registration abstentions remain unresolved.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
