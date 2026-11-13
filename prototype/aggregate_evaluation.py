"""Evaluate aggregate output against event and trajectory evidence separately."""


def has_top_view(event):
    return any(
        any(
            a["top_view_m"] is not None and b["top_view_m"] is not None
            for a, b in zip(segment["geometry_samples"], segment["geometry_samples"][1:])
        )
        for segment in event["segments"]
    )


def score_event_to_top_view(aggregate, event_reviews, official_count):
    events = {row["candidate_id"]: row for row in aggregate["events"]}
    reviews = {row["candidate_id"]: row for row in event_reviews}
    if len(events) != len(aggregate["events"]) or len(reviews) != len(event_reviews):
        raise ValueError("Duplicate candidate identifiers")
    if set(events) != set(reviews):
        raise ValueError("Every candidate needs one event adjudication")
    if any(row["verdict"] not in ("TP", "FP") for row in event_reviews):
        raise ValueError("Unsupported event verdict")
    if (
        not isinstance(official_count, int)
        or isinstance(official_count, bool)
        or official_count < 0
    ):
        raise ValueError("Official count must be a nonnegative integer")
    official_ids = [row["official_shot_id"] for row in event_reviews if row["verdict"] == "TP"]
    if any(not isinstance(key, str) or not key.strip() for key in official_ids):
        raise ValueError("Every TP needs a nonempty official-shot identifier")
    if len(official_ids) != len(set(official_ids)) or len(official_ids) > official_count:
        raise ValueError("Event reference is not a one-to-one official-shot mapping")
    true_events = len(official_ids)
    emitted = [key for key, event in events.items() if has_top_view(event)]
    true_with_output = sum(reviews[key]["verdict"] == "TP" for key in emitted)
    return {
        "official_throws": official_count,
        "event_TP": true_events,
        "event_FP": len(events) - true_events,
        "event_FN": official_count - true_events,
        "true_throws_with_top_view_output": true_with_output,
        "top_view_outputs_on_event_false_positives": len(emitted) - true_with_output,
        "true_throws_without_top_view_output": official_count - true_with_output,
        "top_view_output_recall_ceiling": true_with_output / official_count
        if official_count
        else None,
        "end_to_end_trajectory_recall": 0.0 if not emitted and official_count else None,
        "end_to_end_trajectory_precision": None,
        "reason": (
            "No top-view outputs: end-to-end recall is exactly zero; precision is undefined."
            if not emitted
            else "Event agreement alone cannot certify the trajectory. This is an output-recall ceiling until tracks and geometry are adjudicated."
        ),
    }


def validate_checkpoint_review(events, selection, labels):
    """Require complete, unique labels tied to the actual confirmed samples."""
    event_ids = [event["candidate_id"] for event in events]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("Duplicate aggregate candidates")
    for rows in (selection, labels):
        ids = [row["candidate_id"] for row in rows]
        if len(set(ids)) != len(ids) or set(ids) != set(event_ids):
            raise ValueError("Checkpoint review must cover every candidate exactly once")
    selected = {row["candidate_id"]: row for row in selection}
    reviewed = {row["candidate_id"]: row for row in labels}
    for event in events:
        key = event["candidate_id"]
        points = event["event_prediction"]["observed_track_points"]
        if not points:
            raise ValueError("Checkpoint review requires observed points")
        expected = [points[i]["time_s"] for i in (0, len(points) // 2, len(points) - 1)]
        if any(row["checkpoint_times_s"] != expected for row in (selected[key], reviewed[key])):
            raise ValueError("Checkpoint timestamps differ from confirmed source samples")
        verdicts = reviewed[key]["stone_at_checkpoints"]
        if len(verdicts) != 3 or any(type(value) is not bool for value in verdicts):
            raise ValueError("Exactly three boolean checkpoint verdicts are required")
