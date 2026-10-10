"""Check whether saved pre/post cap deltas can discriminate coarse events.

This is an exposed-data diagnostic, not a new detector score or evaluation.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.throw_event_benchmark import evaluate_events

BASE = ROOT / "validation/throw-event-benchmark"
SOURCES = {
    "estonia": (
        BASE / "canada-estonia-2024/full-match-conditional-receiving-view-state-transitions-postreview.json",
        BASE / "canada-estonia-2024/blind-reference.json"),
    "italy": (
        BASE / "canada-italy/full-match-conditional-receiving-view-state-transitions-transfer.json",
        BASE / "canada-italy/blind-reference.json"),
}
OUTPUT = BASE / "layout-router/full-2024-coverage/routed-cap-delta-event-filter-diagnostic-postreview.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first diagnostic")
    rows = []
    for name, (sequence_path, reference_path) in SOURCES.items():
        sequence = json.loads(sequence_path.read_text())
        reference = json.loads(reference_path.read_text())
        if sequence["source_sha256"] != reference["source_sha256"]:
            raise ValueError(f"Source differs: {name}")
        lo, hi = reference["source_interval_s"]
        candidates = [row for row in sequence["rows"]
                      if row["observation_kind"] == "left_tracked_passage"
                      and lo <= row["observation_time_s"] <= hi]
        predictions = [{"id": row["candidate_id"],
                        "colour": row["colour_claim"],
                        "crossing_time_s": row["observation_time_s"]}
                       for row in candidates]
        score = evaluate_events(predictions, reference["events"], [lo, hi])
        matched = {item["prediction_id"] for item in score["matches"]}
        comparison = []
        for row in candidates:
            observation = row.get("post_candidate_receiving_view_observation")
            delta = row.get("receiving_view_partial_cap_transition")
            change = delta.get("image_cap_delta") if delta else None
            comparison.append({
                "candidate_id": row["candidate_id"],
                "matches_coarse_window": row["candidate_id"] in matched,
                "conditional_receiving_view": observation["view"] if observation else None,
                "comparison_status": delta["comparison_status"] if delta else None,
                "new_image_cap_observation_count":
                    len(change["newly_observed"]) if change else None,
                "no_longer_observed_image_cap_count":
                    len(change["no_longer_observed"]) if change else None,
            })
        result = {
            "recording": name,
            "source_sha256": sequence["source_sha256"],
            "sequence_sha256": digest(sequence_path),
            "reference_sha256": digest(reference_path),
            "reference_method": reference["reference_method"],
            "source_interval_s": reference["source_interval_s"],
            "score_against_coarse_reference": {
                key: score[key] for key in (
                    "prediction_count", "reference_count", "true_positives",
                    "false_positives", "false_negatives", "f1")},
            "matched_comparison_status_counts": dict(Counter(
                row["comparison_status"] for row in comparison
                if row["matches_coarse_window"])),
            "unmatched_candidate_count": sum(
                not row["matches_coarse_window"] for row in comparison),
            "can_estimate_cap_delta_false_positive_rejection": any(
                not row["matches_coarse_window"] for row in comparison),
            "candidate_comparisons": comparison,
        }
        rows.append(result)
    output = {
        "status": "postreview_cap_delta_filter_diagnostic_no_negative_candidate_denominator",
        "runner_sha256": digest(Path(__file__)),
        "scorer_code_sha256": digest(ROOT / "prototype/throw_event_benchmark.py"),
        "rows": rows,
        "conclusion": "The saved later full-match candidate sequences have no unmatched left candidate in either fixed interval, so these data cannot test whether an image-cap delta rejects false throw proposals.",
        "limitations": [
            "The full-match sequences are later development products on exposed recordings.",
            "Agent-blind coarse windows were not independently or continuously labelled.",
            "An image-cap change can reflect movement, occlusion, handling, graphics or a real throw.",
            "The result must not be reported as a new held-out detector F1.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps([(row["recording"], row["score_against_coarse_reference"],
                       row["unmatched_candidate_count"]) for row in rows]))


if __name__ == "__main__":
    main()
