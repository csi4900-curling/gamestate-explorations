"""Compare raw crossing geometry with source-reviewed pixels (development only)."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
INPUTS = {
    "raw_left": BASE / "layout-router/full-2024-coverage/latvia24-full-v1/run-02/events.json",
    "earlier_review": BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/source-pixel-review-ledger.json",
    "accepted_no_right_review": BASE
    / "canada-latvia-2024/accepted-no-right-source-audit/manifest.json",
    "withheld_cross_view_review": BASE
    / "canada-latvia-2024/withheld-cross-view-source-audit/manifest.json",
}
OUTPUT = BASE / "canada-latvia-2024/crossing-shape-source-audit-development.json"
TRANSFER_INPUTS = {
    "italy24": BASE / "layout-router/full-2024-coverage/new-preflight-italy24/run-02/events.json",
    "estonia24": BASE
    / "layout-router/full-2024-coverage/new-preflight-estonia24/run-02/events.json",
    "china24": BASE / "layout-router/full-2024-coverage/new-preflight-china24/run-02/events.json",
    "scotland24": BASE
    / "layout-router/full-2024-coverage/scotland24-bridged-development/run-01/events.json",
}


def source_class(value):
    if value.startswith("stone_body"):
        return "stone_shaped_pixels"
    if value.startswith("person_"):
        return "person_pixels"
    if value.startswith("ambiguous_"):
        return "ambiguous_pixels"
    raise ValueError(f"Unrecognized source class: {value}")


def main():
    data = {key: json.loads(path.read_text()) for key, path in INPUTS.items()}
    raw = data["raw_left"]
    for name in ("earlier_review", "accepted_no_right_review", "withheld_cross_view_review"):
        reviewed_source = data[name].get("source_sha256") or data[name].get("source_video_sha256")
        if reviewed_source != raw["source_sha256"]:
            raise ValueError(f"Review source fingerprint differs from raw left run: {name}")
    raw_rows = {row["id"]: row for row in raw["events"] + raw["withheld_events"]}
    reviews = {}

    def add(candidate_id, pixel_class, review_source):
        if candidate_id not in raw_rows:
            raise ValueError(f"Review has no raw left crossing: {candidate_id}")
        category = source_class(pixel_class)
        old = reviews.get(candidate_id)
        if old and old["source_category"] != category:
            raise ValueError(f"Contradictory source reviews: {candidate_id}")
        if old:
            old["review_sources"].append(review_source)
        else:
            reviews[candidate_id] = {
                "source_category": category,
                "source_pixel_class": pixel_class,
                "review_sources": [review_source],
            }

    for review in data["earlier_review"]["reviews"]:
        add(review["candidate_id"].split("-")[-1], review["source_pixel_class"], "earlier_review")
    for review in data["accepted_no_right_review"]["rows"]:
        add(review["left_candidate_id"], review["source_pixel_class"], "accepted_no_right_review")
    for review in data["withheld_cross_view_review"]["marked_pixels"]:
        if review["camera"] == "left":
            add(review["candidate_id"], review["source_pixel_class"], "withheld_cross_view_review")

    rows = []
    for candidate_id, review in sorted(reviews.items(), key=lambda pair: int(pair[0][1:])):
        event = raw_rows[candidate_id]
        width = event["median_candidate_bbox_width_px"]
        height = event["median_candidate_bbox_height_px"]
        rows.append(
            {
                "candidate_id": candidate_id,
                "raw_decision": "accepted" if event in raw["events"] else "withheld",
                **review,
                "mean_body_support": event["mean_body_support"],
                "median_candidate_bbox_width_px": width,
                "median_candidate_bbox_height_px": height,
                "height_to_width_ratio": round(height / width, 4),
                "recent_track_duration_s": event["recent_track_duration_s"],
                "observed_span_px": event["observed_span_px"],
                "direction_consistency": event["direction_consistency"],
            }
        )

    stones = [row for row in rows if row["source_category"] == "stone_shaped_pixels"]
    people = [row for row in rows if row["source_category"] == "person_pixels"]
    ambiguous = [row for row in rows if row["source_category"] == "ambiguous_pixels"]
    if not stones or not people:
        raise ValueError("Both clear source classes are required")
    max_stone_ratio = max(row["height_to_width_ratio"] for row in stones)
    min_stone_body = min(row["mean_body_support"] for row in stones)
    # Raw durations are binary floats from saved timestamps; compare on a
    # millisecond grid so values displayed as 1.8 s share the same boundary.
    max_stone_duration = max(round(row["recent_track_duration_s"], 3) for row in stones)
    # These boundaries are derived from this reviewed set. They are diagnostic,
    # not a rule to transfer or a measurement of throw-event precision/recall.
    flagged_people = [
        row["candidate_id"]
        for row in people
        if row["height_to_width_ratio"] > max_stone_ratio
        or row["mean_body_support"] < min_stone_body
    ]
    surviving_people = [
        row["candidate_id"] for row in people if row["candidate_id"] not in flagged_people
    ]
    flagged_with_duration = [
        row["candidate_id"]
        for row in people
        if row["candidate_id"] in flagged_people
        or round(row["recent_track_duration_s"], 3) > max_stone_duration
    ]
    surviving_with_duration = [
        row["candidate_id"] for row in people if row["candidate_id"] not in flagged_with_duration
    ]

    def would_flag(event):
        return (
            event["median_candidate_bbox_height_px"] / event["median_candidate_bbox_width_px"]
            > max_stone_ratio
            or event["mean_body_support"] < min_stone_body
            or round(event["recent_track_duration_s"], 3) > max_stone_duration
        )

    transfer = {}
    for name, path in TRANSFER_INPUTS.items():
        candidate_data = json.loads(path.read_text())
        transfer[name] = {
            "input_sha256": sha256(path.read_bytes()).hexdigest(),
            "source_sha256": candidate_data["source_sha256"],
            "candidate_counts_only_no_source_truth": {
                key: {
                    "total": len(candidate_data[key]),
                    "would_flag": sum(would_flag(event) for event in candidate_data[key]),
                }
                for key in ("events", "withheld_events")
            },
        }
    result = {
        "status": "same_agent_source_pixel_development_audit_not_event_validation",
        "input_sha256": {
            key: sha256(path.read_bytes()).hexdigest() for key, path in INPUTS.items()
        },
        "runner_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "reviewed_unique_left_crossings": len(rows),
        "source_category_counts": {
            "stone_shaped_pixels": len(stones),
            "person_pixels": len(people),
            "ambiguous_pixels": len(ambiguous),
        },
        "stone_preserving_in_sample_boundaries": {
            "maximum_stone_height_to_width_ratio": max_stone_ratio,
            "minimum_stone_mean_body_support": min_stone_body,
            "person_pixel_ids_flagged_by_either_boundary": flagged_people,
            "person_pixel_ids_surviving_both_boundaries": surviving_people,
        },
        "additional_in_sample_duration_check": {
            "maximum_stone_recent_track_duration_s": max_stone_duration,
            "person_pixel_ids_flagged_by_shape_body_or_duration": flagged_with_duration,
            "person_pixel_ids_surviving_all_three_boundaries": surviving_with_duration,
        },
        "cross_recording_proposal_distribution": transfer,
        "rows": rows,
        "limitations": [
            "Source classes were reviewed by the same agent after seeing candidate proposals.",
            "A stone-shaped pixel at a crossing is not a verified throw event.",
            "The boundaries were chosen from the reviewed Latvia examples and have no held-out validity.",
            "Source-pixel outcomes for unreviewed candidates and other recordings are not evaluated here.",
            "Transfer counts are candidate distributions only, without source-class or throw-event labels.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        f"{len(rows)} reviewed left crossings; {len(stones)} stone pixels, "
        f"{len(people)} people, {len(ambiguous)} ambiguous"
    )
    print(f"In-sample stone-safe boundaries flag {len(flagged_people)}/{len(people)} people")
    print(f"Adding in-sample duration flags {len(flagged_with_duration)}/{len(people)} people")


if __name__ == "__main__":
    main()
