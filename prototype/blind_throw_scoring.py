"""One-to-one throw-event scoring against independent broad intervals."""


def score_throw_intervals(reference_events, predicted_events):
    """Match by source time only; uncertain intervals quarantine predictions."""
    references = sorted(reference_events,
                        key=lambda row: row["delivery_source_interval_s"][0])
    for left, right in zip(references, references[1:]):
        if left["delivery_source_interval_s"][1] >= right["delivery_source_interval_s"][0]:
            raise ValueError("Reference intervals overlap")
    predictions = sorted(predicted_events, key=lambda row: row["crossing_time_s"])
    ids = [row["id"] for row in predictions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate prediction ID")
    matched = []
    unmatched_reference = []
    uncertain_reference = []
    used = set()
    quarantined = set()
    for reference in references:
        start, end = reference["delivery_source_interval_s"]
        inside = [i for i, predicted in enumerate(predictions)
                  if start <= predicted["crossing_time_s"] <= end]
        if reference["uncertain"]:
            uncertain_reference.append(reference["id"])
            quarantined.update(inside)
            continue
        if not inside:
            unmatched_reference.append(reference["id"])
            continue
        midpoint = (start + end) / 2
        best = min(inside, key=lambda i: (abs(predictions[i]["crossing_time_s"] - midpoint), i))
        used.add(best)
        matched.append({
            "reference_id": reference["id"],
            "prediction_id": predictions[best]["id"],
            "reference_colour": reference["colour"],
            "predicted_colour": predictions[best]["colour"],
            "colour_correct": None if reference["colour"] == "unknown" else
            reference["colour"] == predictions[best]["colour"],
            "prediction_time_s": predictions[best]["crossing_time_s"],
            "delivery_interval_s": [start, end],
        })
    unmatched_prediction = [row["id"] for i, row in enumerate(predictions)
                            if i not in used and i not in quarantined]
    quarantined_prediction = [predictions[i]["id"] for i in sorted(quarantined)]
    tp, fp, fn = len(matched), len(unmatched_prediction), len(unmatched_reference)
    complete = not uncertain_reference
    precision = (tp / (tp + fp) if tp + fp else (0.0 if fn else None)) if complete else None
    recall = (tp / (tp + fn) if tp + fn else (0.0 if fp else None)) if complete else None
    f1 = (2 * tp / (2 * tp + fp + fn)
          if complete and 2 * tp + fp + fn else None)
    known_colours = [row for row in matched if row["colour_correct"] is not None]
    return {
        "status": "complete_interval_event_score" if complete else
                  "partial_score_uncertain_reference_no_f1",
        "reference_count": len(references),
        "certain_reference_count": len(references) - len(uncertain_reference),
        "prediction_count": len(predictions),
        "true_positive_certain": tp,
        "false_positive_outside_uncertain_intervals": fp,
        "false_negative_certain": fn,
        "uncertain_reference_ids": uncertain_reference,
        "quarantined_prediction_ids": quarantined_prediction,
        "matched": matched,
        "unmatched_reference_ids": unmatched_reference,
        "unmatched_prediction_ids": unmatched_prediction,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "known_colour_match_count": len(known_colours),
        "known_colour_correct_count": sum(row["colour_correct"] for row in known_colours),
        "limitations": [
            "Broad-interval matching assesses event detection, not release timing.",
            "Uncertain human intervals block a full-interval F1 claim.",
            "One interval can match only one proposal; duplicate proposals remain false positives.",
        ],
    }
