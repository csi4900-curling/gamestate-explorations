"""Conserve source-reviewed disagreement classes against a temporal inventory."""

from collections import Counter


def audit(
    inventory,
    context,
    right_reviews,
    left_review,
    matched_cluttered_review,
    matched_clear_sample=None,
):
    inventory_rows = {row["proposal_id"]: row for row in inventory["rows"]}
    context_rows = {row["proposal_id"]: row for row in context["rows"]}
    if (
        len(inventory_rows) != len(inventory["rows"])
        or len(context_rows) != len(context["rows"])
        or set(inventory_rows) != set(context_rows)
    ):
        raise ValueError("Inventory and context proposal coverage differs")
    right_rows = {}
    for run_id, review in right_reviews:
        for row in review["rows"]:
            proposal_id = f"{run_id}:{row['raw_track_id']}"
            if proposal_id in right_rows:
                raise ValueError("Duplicate reviewed right proposal")
            right_rows[proposal_id] = row
    expected_right = {
        id
        for id, row in inventory_rows.items()
        if row["temporal_status"] != "one_left_time_colour_candidate"
    }
    if set(right_rows) != expected_right:
        raise ValueError("Every right temporal disagreement must be source-reviewed")
    left_rows = {row["left_event_id"]: row for row in left_review["rows"]}
    if len(left_rows) != len(left_review["rows"]) or set(left_rows) != set(
        inventory["left_events_without_any_right_time_colour_candidate"]
    ):
        raise ValueError("Every left-only event must be source-reviewed")
    matched_rows = {row["proposal_id"]: row for row in matched_cluttered_review["rows"]}
    expected_matched = {
        id
        for id, row in inventory_rows.items()
        if row["temporal_status"] == "one_left_time_colour_candidate"
        and context_rows[id]["context_tier"] == "context_cluttered_review"
    }
    if (
        len(matched_rows) != len(matched_cluttered_review["rows"])
        or set(matched_rows) != expected_matched
    ):
        raise ValueError("Every matched cluttered path must be source-reviewed")
    sample_count = 0
    sample_class_counts = {}
    if matched_clear_sample is not None:
        sample_rows = {row["proposal_id"]: row for row in matched_clear_sample["rows"]}
        if len(sample_rows) != len(matched_clear_sample["rows"]):
            raise ValueError("Duplicate matched-clear sample ID")
        eligible = {
            id
            for id, row in inventory_rows.items()
            if row["temporal_status"] == "one_left_time_colour_candidate"
            and context_rows[id]["context_tier"] == "clear_context_review"
        }
        if not set(sample_rows) <= eligible:
            raise ValueError("Sample includes ineligible path")
        sample_count = len(sample_rows)
        sample_class_counts = dict(
            Counter(row["source_prefix_class"] for row in sample_rows.values())
        )
    right_only_rows = {
        id: row
        for id, row in right_rows.items()
        if inventory_rows[id]["temporal_status"] == "no_left_time_colour_candidate"
    }
    duplicate_rows = {
        id: row
        for id, row in right_rows.items()
        if inventory_rows[id]["temporal_status"] == "multiple_right_candidates_for_left_review"
    }
    right_classes = Counter(row["source_prefix_class"] for row in right_only_rows.values())
    right_context = Counter(
        (row["source_prefix_class"], context_rows[id]["context_tier"])
        for id, row in right_only_rows.items()
    )
    return {
        "reviewed_right_disagreement_count": len(right_rows),
        "right_only_source_class_counts": dict(right_classes),
        "right_only_class_by_context": {
            cls: {
                tier: right_context[cls, tier]
                for tier in (
                    "clear_context_review",
                    "context_cluttered_review",
                    "context_unavailable_review",
                )
            }
            for cls in sorted(right_classes)
        },
        "duplicate_right_source_class_counts": dict(
            Counter(row["source_prefix_class"] for row in duplicate_rows.values())
        ),
        "duplicate_right_class_by_context": {
            cls: {
                tier: sum(
                    1
                    for id, row in duplicate_rows.items()
                    if row["source_prefix_class"] == cls
                    and context_rows[id]["context_tier"] == tier
                )
                for tier in (
                    "clear_context_review",
                    "context_cluttered_review",
                    "context_unavailable_review",
                )
            }
            for cls in sorted({row["source_prefix_class"] for row in duplicate_rows.values()})
        },
        "left_only_source_class_counts": dict(
            Counter(row["source_prefix_class"] for row in left_rows.values())
        ),
        "matched_cluttered_source_class_counts": dict(
            Counter(row["source_prefix_class"] for row in matched_rows.values())
        ),
        "matched_clear_sample_count": sample_count,
        "matched_clear_sample_class_counts": sample_class_counts,
    }
