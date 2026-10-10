"""Acceptance gate for a complete-recording throw-event benchmark.

This gate is intentionally stricter than scoring a convenient excerpt. The
caller must supply the measured hash and duration of the actual source video.
It cannot independently verify that human labels are exhaustive.
"""

from math import isfinite

from throw_event_benchmark import evaluate_events


def assess_recording(
    prediction,
    reference,
    *,
    measured_source_sha256=None,
    measured_source_duration_s=None,
    min_precision=0.95,
    min_recall=0.95,
):
    """Score exhaustive events and state whether the result supports the target.

    The prediction must explicitly declare complete video coverage. A partial
    routed timeline is rejected even if its observed events happen to score well.
    """
    if not 0 < min_precision <= 1 or not 0 < min_recall <= 1:
        raise ValueError("Targets must be in (0, 1]")
    if not reference.get("source_sha256") or prediction.get("source_sha256") != reference.get(
        "source_sha256"
    ):
        raise ValueError("Prediction and reference source fingerprints differ")
    if measured_source_sha256 != reference["source_sha256"]:
        return {
            "accepted": False,
            "reason": "unverified_source_video_fingerprint",
            "score": None,
        }
    interval = reference["source_interval_s"]
    if prediction.get("source_interval_s") != interval:
        raise ValueError("Prediction and reference intervals differ")
    duration = reference.get("source_duration_s")
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not isfinite(duration)
        or duration <= 0
        or prediction.get("source_duration_s") != duration
        or reference.get("source_duration_verified") is not True
        or isinstance(measured_source_duration_s, bool)
        or not isinstance(measured_source_duration_s, (int, float))
        or not isfinite(measured_source_duration_s)
        or abs(measured_source_duration_s - duration) > 0.1
        or interval != [0, duration]
    ):
        return {
            "accepted": False,
            "reason": "unverified_full_recording_scope",
            "score": None,
        }
    if prediction.get("coverage_gaps_s") != [] or prediction.get("coverage_verified") is not True:
        return {
            "accepted": False,
            "reason": "incomplete_coverage",
            "score": None,
        }
    if "events" not in prediction or "observed_events" in prediction:
        return {
            "accepted": False,
            "reason": "non_exhaustive_predictions",
            "score": None,
        }
    if not reference.get("exhaustive", False):
        return {
            "accepted": False,
            "reason": "non_exhaustive_reference",
            "score": None,
        }
    score = evaluate_events(prediction["events"], reference["events"], interval)
    if reference.get("reference_method") not in ("human_independent", "publisher_independent"):
        return {
            "accepted": False,
            "reason": "non_independent_reference",
            "score": score,
        }
    accepted = score["precision"] >= min_precision and score["recall"] >= min_recall
    return {
        "accepted": accepted,
        "reason": "target_met" if accepted else "below_precision_or_recall_target",
        "score": score,
        "min_precision": min_precision,
        "min_recall": min_recall,
    }
