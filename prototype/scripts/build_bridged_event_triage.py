"""Keep recovered-gap event candidates separate from the frozen base timeline."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage"
OLD = BASE / "scotland24-full-v1/timeline.json"
BRIDGED = BASE / "scotland24-bridged-development/timeline.json"
LAYOUT = BASE / "scotland24-bridged-development/event-layout-audit.json"
OUTPUT = BASE / "scotland24-bridged-development/bridge-review-triage.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    old, bridged, layout = (json.loads(path.read_text()) for path in (OLD, BRIDGED, LAYOUT))
    assert old["source_sha256"] == bridged["source_sha256"] == layout["source_sha256"]
    assert layout["timeline_sha256"] == digest(BRIDGED)
    assert old["observed_event_count"] == len(old["observed_events"])
    assert bridged["observed_event_count"] == len(bridged["observed_events"])
    assert layout["event_count"] == len(layout["events"])
    layout_by_id = {row["event_id"]: row for row in layout["events"]}
    assert len(layout_by_id) == len(bridged["observed_events"])
    available = bridged["observed_events"][:]
    matched = []
    for original in old["observed_events"]:
        candidates = [
            row
            for row in available
            if row["colour"] == original["colour"]
            and abs(row["crossing_time_s"] - original["crossing_time_s"]) <= 0.25
        ]
        if len(candidates) != 1:
            raise ValueError(f"Old candidate did not match uniquely: {original['id']}")
        chosen = candidates[0]
        available.remove(chosen)
        if chosen["crossing_time_s"] != original["crossing_time_s"]:
            raise ValueError("Old candidate timestamp changed")
        matched.append(
            {
                "original_id": original["id"],
                "bridged_id": chosen["id"],
                "time_s": chosen["crossing_time_s"],
                "colour": chosen["colour"],
            }
        )
    gaps = [row for row in old["coverage_gaps_s"] if row not in bridged["coverage_gaps_s"]]
    recovered = []
    for row in available:
        time_s = row["crossing_time_s"]
        containing = [gap for gap in gaps if gap[0] <= time_s < gap[1]]
        if len(containing) != 1:
            raise ValueError(f"New event is outside exactly one recovered gap: {row['id']}")
        check = layout_by_id[row["id"]]
        recovered.append(
            {
                "id": row["id"],
                "candidate_time_s": time_s,
                "colour_claim": row["colour"],
                "original_unknown_gap_s": containing[0],
                "event_time_split_signature_count": check["matching_samples"],
                "event_time_sample_count": check["sample_count"],
                "layout_review_required": check["layout_review_required"],
                "review_state": "new_from_bridged_layout_needs_physical_stone_verification",
                "physical_throw_verified": False,
                "candidate_evidence": row,
            }
        )
    result = {
        "status": "additive_bridged_gap_review_not_revised_accepted_timeline",
        "source_id": old["source_id"],
        "source_sha256": old["source_sha256"],
        "baseline_timeline_sha256": digest(OLD),
        "bridged_timeline_sha256": digest(BRIDGED),
        "event_layout_audit_sha256": digest(LAYOUT),
        "original_auto_accepted_candidate_count": len(matched),
        "original_candidates_preserved": matched,
        "recovered_unknown_gaps_s": gaps,
        "remaining_unknown_gaps_s": bridged["coverage_gaps_s"],
        "new_review_candidate_count": len(recovered),
        "new_review_candidates": recovered,
        "limitations": [
            "New candidates are review proposals, not accepted physical throws.",
            "Image-layout agreement does not verify a stone; a failed signature can occur during a real delivery.",
            "The source and bridge rule are exposed development data.",
            "The original accepted timeline can itself contain false or missed throws.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "preserved": len(matched),
                "new_review": len(recovered),
                "new_layout_review": sum(row["layout_review_required"] for row in recovered),
            }
        )
    )


if __name__ == "__main__":
    main()
