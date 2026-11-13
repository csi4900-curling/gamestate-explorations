"""Check the final deliverable's completeness from artifacts.

This is an evidence checklist, not an accuracy certificate. It reports whether
the observation stage covered the references, whether dense covered every event,
whether runtime is recorded and whether the viewer browser check passed. It
always keeps physical identity, metric trajectory accuracy and complete board
accuracy outside the completion claim.
"""

import argparse
import json
from pathlib import Path


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-dir", type=Path, required=True)
    parser.add_argument("--skip-dense", action="store_true",
                        help="owner decision: dense removed from scope; record as skipped, not passed")
    args = parser.parse_args()
    out = args.final_dir.resolve()
    evaluation = load(out / "evaluation.json")
    complete = load(out / "pipeline-complete.json")
    browser = load(out / "viewer/browser-verification.json")
    report = (out / "report.md").read_text() if (out / "report.md").exists() else ""
    checks = []
    blockers = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
        if not passed:
            blockers.append(f"{name}: {detail}")

    check("pipeline-complete marker", complete is not None,
          "pipeline-complete.json present" if complete else "missing")
    events = (evaluation or {}).get("events") or {}
    observation_complete = (
        events.get("status") == "evaluated"
        and events.get("references_beyond_coverage") == 0)
    check("full observation coverage", observation_complete,
          f"{events.get('matched')}/{events.get('predictions')} events; "
          f"references beyond coverage {events.get('references_beyond_coverage')}")
    check("no unmatched predictions", events.get("unmatched_predictions") == 0,
          f"unmatched predictions {events.get('unmatched_predictions')}")
    dense = (evaluation or {}).get("dense") or {}
    dense_summary = dense.get("summary") or {}
    dense_complete = (
        dense.get("status") == "evaluated"
        and dense_summary.get("segments_failed", 0) == 0
        and dense.get("dense_events") == events.get("predictions"))
    if args.skip_dense:
        check("dense on every event", True,
              "not run by owner decision 2026-10-25; all-events dense removed from scope")
    else:
        check("dense on every event", dense_complete,
              f"{dense.get('dense_events')} dense events / "
              f"{events.get('predictions')} predictions; "
              f"failed segments {dense_summary.get('segments_failed')}")
    runtime = (evaluation or {}).get("runtime") or {}
    event_stage = runtime.get("event_stage") or {}
    check("event runtime recorded", event_stage.get("wall_seconds") is not None,
          f"event wall {event_stage.get('wall_seconds')}")
    if args.skip_dense:
        check("dense runtime recorded", True,
              "not applicable; dense skipped by owner decision")
    else:
        check("dense runtime recorded",
              (runtime.get("dense_stage") or {}).get("wall_seconds") is not None,
              f"dense wall {(runtime.get('dense_stage') or {}).get('wall_seconds')}")
    check("viewer browser check", bool(browser) and not (browser or {}).get("errors"),
          "browser-verification.json present with no errors"
          if browser else "missing browser-verification.json")
    check("report status table", "Deliverable status" in report,
          "report.md contains the status table" if "Deliverable status" in report
          else "missing status table")
    colour = ((evaluation or {}).get("colour") or {}).get("summary") or {}
    handoff = ((evaluation or {}).get("handoff_colour") or {}).get("summary") or {}
    end = (evaluation or {}).get("end_inference") or {}
    result = {
        "final_dir": str(out),
        "checks": checks,
        "blocking_issues": blockers,
        "ready_for_owner_review": not blockers,
        "quality_acceptance_verified": False,
        "dense_skipped_by_owner_decision": bool(args.skip_dense),
        "scope_amendments": (["CoTracker/dense removed by owner decision 2026-10-25; all-events dense not run; the original dense requirement is not met"]
                             if args.skip_dense else []),
        "measured_evidence": {
            "events_matched": events.get("matched"),
            "events_predictions": events.get("predictions"),
            "event_timing_median_s": (events.get("timing_abs_error_s") or {}).get("median"),
            "dense_events": dense.get("dense_events"),
            "dense_segments_failed": dense_summary.get("segments_failed"),
            "colour_events": colour.get("events"),
            "colour_agreements": colour.get("two_observation_agreement"),
            "handoff_agree": handoff.get("agree"),
            "handoff_disagree": handoff.get("disagree"),
            "end_inference_correct": end.get("correct"),
            "end_inference_covered": end.get("references_in_coverage"),
        },
        "unmeasured": [
            "physical stone identity, including same-colour discrimination",
            "metric trajectory accuracy against independent annotations",
            "complete per-end board accuracy against independent annotations",
        ],
        "note": ("ready_for_owner_review covers the observation/aggregate deliverable; "
                 "the original all-events dense requirement was not run by owner decision; "
                 "unmeasured dimensions remain unvalidated." if args.skip_dense else
                 "ready_for_owner_review means the artifacts are complete, not that the unmeasured dimensions are validated."),
    }
    print(json.dumps(result, indent=2))
    (out / "delivery-check.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
