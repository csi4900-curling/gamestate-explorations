"""Assemble the final full-match deliverable from frozen observation outputs.

Steps:
  1. build the frozen directional aggregate from events/observations/boards;
  2. add panel-aware shared-rink coordinates and handoff diagnostics;
  3. build the explicit observed/inferred state timeline;
  4. render the synchronized shared-rink viewer;
  5. evaluate events, rink coverage, board/score/state, identity evidence and runtime;
  6. write the report and a landing page.

This is post-processing. It does not rerun detection, tracking or dense
inference, and it does not establish physical identity or metric accuracy.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from prototype.scripts.build_state_timeline import build as build_state
from prototype.scripts.enrich_rink_aggregate import enrich
from prototype.scripts.evaluate_full_match import (
    evaluate_dense,
    evaluate_end_inference,
    evaluate_events,
    evaluate_geometry,
    evaluate_identity,
    evaluate_rink,
    evaluate_runtime,
    evaluate_scores,
    evaluate_state,
    stream_boards,
    write_markdown,
)
from prototype.scripts.render_rink_viewer import render as render_rink

DEV_ROOT = Path("/home/user/curling-baseline-recovery-development")


def attach_event_colours(aggregate, path):
    """Attach post-hoc OpenCLIP event colour evidence; does not alter inference."""
    document = json.loads(Path(path).read_text())
    by_id = {row["event_id"]: row for row in document.get("events", [])}
    attached = 0
    for event in aggregate.get("events", []):
        row = by_id.get(event["candidate_id"])
        if row is None:
            continue
        event["colour"] = row.get("colour")
        event["colour_status"] = row.get("colour_status")
        event["colour_observations"] = row.get("observations")
        for segment in event.get("segments", []):
            if segment.get("role") == "departure":
                segment["colour"] = row.get("colour")
        attached += 1
    aggregate["event_colour"] = {
        "summary": document.get("summary"),
        "reference_comparison": document.get("reference_comparison"),
        "provenance": document.get("provenance"),
        "attached_events": attached,
        "physical_identity_verified": False,
        "team_mapping_established": False,
    }
    return aggregate


def attach_handoff_colours(aggregate, path):
    document = json.loads(Path(path).read_text())
    by_key = {(row["event_id"], row["segment_id"]): row
              for row in document.get("handoffs", [])}
    attached = 0
    for event in aggregate.get("events", []):
        for link in event.get("cross_view_links", []):
            row = by_key.get((event["candidate_id"], link["receiving_segment"]))
            if row is None:
                continue
            link["departure_colour"] = row.get("departure_colour")
            link["receiving_colour"] = row.get("receiving_colour")
            link["colour_consistency"] = row.get("status")
            link["same_colour_ambiguity_remaining"] = True
            attached += 1
    aggregate["handoff_colour"] = {
        "summary": document.get("summary"),
        "provenance": document.get("provenance"),
        "attached_links": attached,
        "physical_identity_verified": False,
        "same_colour_ambiguity_remaining": True,
    }
    return aggregate


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def build_aggregate(video, run_dir, output, hog_y_m):
    code = (
        "import json\n"
        "from prototype.directional_event_aggregate import build\n"
        f"build({json.dumps(str(video))}, {json.dumps(str(run_dir))}, "
        f"{json.dumps(str(output))}, "
        f"hog_y_by_panel={json.dumps(hog_y_m)})\n"
    )
    env = {**os.environ,
           "PYTHONPATH": str(DEV_ROOT),
           "CURLING_PYTHON": "/home/user/curling-project/.venv-detector/bin/python"}
    wrapper = "/home/user/curling-project/feasibility/scripts/python.sh"
    subprocess.run([wrapper, "-c", code], cwd=DEV_ROOT, env=env, check=True)


def deliverable_summary(evaluation):
    events = evaluation.get("events") or {}
    rink = evaluation.get("rink") or {}
    boards = evaluation.get("boards") or {}
    scores = evaluation.get("scores") or {}
    runtime = evaluation.get("runtime") or {}
    dense = evaluation.get("dense") or {}
    state = evaluation.get("state") or {}
    colour = evaluation.get("colour") or {}
    handoff = evaluation.get("handoff_colour") or {}
    end_inference = evaluation.get("end_inference") or {}
    event_status = ("complete observation"
                    if (events.get("status") == "evaluated"
                        and events.get("references_beyond_coverage") == 0)
                    else "partial observation"
                    if events.get("status") == "evaluated" else "not run")
    dense_summary = dense.get("summary") or {}
    dense_events = dense.get("dense_events")
    if dense_events is None:
        dense_events = dense_summary.get("events")
    prediction_count = events.get("predictions")
    if dense.get("status") != "evaluated":
        dense_status = "not run"
    elif dense_summary.get("segments_failed", 0) > 0:
        dense_status = "complete with failures"
    elif prediction_count and dense_events is not None and dense_events < prediction_count:
        dense_status = "partial dense"
    else:
        dense_status = "complete"
    event_evidence = "n/a"
    if events.get("status") == "evaluated":
        timing = events.get("timing_abs_error_s") or {}
        event_evidence = (f"{events.get('matched')}/{events.get('predictions')} matched; "
                          f"unmatched preds {events.get('unmatched_predictions')}; "
                          f"timing median {timing.get('median')}")
    identity_evidence = "physical identity unverified"
    if colour.get("summary"):
        reference = colour.get("reference_comparison") or {}
        identity_evidence = (f"event colour {colour['summary'].get('two_observation_agreement')} "
                             f"agreements ({reference.get('correct', 'n/a')}/{reference.get('matched', 'n/a')} reference correct); "
                             f"handoff colour {handoff.get('summary', {}).get('agree', 'n/a')} agree; "
                             "physical identity unverified")
    rink_evidence = "n/a"
    if rink.get("status") == "evaluated":
        rink_evidence = (f"{rink.get('events')} events, {rink.get('links')} links, "
                         f"gap median {rink.get('gap_m', {}).get('median')} m; "
                         "metric accuracy unmeasured")
    board_evidence = "n/a"
    if boards.get("status") == "evaluated":
        board_evidence = (f"{boards.get('samples')} samples; both panels "
                          f"{boards.get('samples_with_both_panels_projected')}; "
                          "per-stone accuracy unmeasured")
    state_evidence = "n/a"
    if scores.get("status") == "evaluated":
        state_evidence = (f"OCR samples {scores.get('samples')}; both totals "
                          f"{scores.get('samples_with_both_totals')}; "
                          f"current_end non-null {scores.get('samples_with_current_end')}")
    if end_inference.get("status") == "evaluated":
        state_evidence += (f"; end inference {end_inference.get('correct')}/"
                           f"{end_inference.get('references_in_coverage')} covered")
    runtime_measured = bool(runtime.get("event_stage")
                            and runtime["event_stage"].get("wall_seconds") is not None)
    runtime_evidence = "event wall missing"
    if runtime_measured:
        runtime_evidence = (f"event wall {runtime['event_stage'].get('wall_seconds')} s; "
                            f"detector {runtime['event_stage'].get('detector_seconds')} s")
        if runtime.get("dense_stage"):
            runtime_evidence += f"; dense wall {runtime['dense_stage'].get('wall_seconds')} s"
    rows = [
        ("One public-entry full-match run", event_status, event_evidence),
        ("Dense CoTracker on every event", dense_status,
         (f"{dense_events}/{prediction_count} events; "
          f"tracked {dense_summary.get('segments_tracked')}; "
          f"failed {dense_summary.get('segments_failed')}"
          if dense.get("status") == "evaluated" else "no dense result")),
        ("Event TP/FP/FN + timing", "measured (development)" if events.get("status") == "evaluated" else "not measured",
         event_evidence),
        ("Physical stone identity", "unverified", identity_evidence),
        ("Shared-rink trajectories", "delivered; metric accuracy unmeasured",
         rink_evidence),
        ("Both-end board", "observed; per-stone accuracy unmeasured", board_evidence),
        ("Game/end/score state", "partial", state_evidence),
        ("Per-stage runtime", "measured" if runtime_measured else "not measured",
         runtime_evidence),
        ("Synchronized viewer", "delivered", "viewer/index.html; browser check recorded"),
    ]
    lines = ["## Deliverable status", "",
             "| Requirement | Status | Evidence |", "|---|---|---|"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    lines += ["", "Statuses are scope statements, not independent-accuracy claims. "
              "See the evidence boundary below.", ""]
    return "\n".join(lines)


def landing_page(path, *, report, viewer, dense_index, match_viewer,
                 events_viewer, evaluation):
    links = [
        ("Synchronized shared-rink viewer", viewer),
        ("Dense two-view tracks (every event)", dense_index),
        ("Both-end board and score observations", match_viewer),
        ("Learned crossing evidence", events_viewer),
        ("Machine-readable evaluation", evaluation),
    ]
    rows = "".join(f"<li><a href='{href}'>{label}</a></li>" for label, href in links
                   if href)
    path.write_text(f"""<!doctype html><meta charset="utf-8"><title>Full-match curling deliverable</title>
<style>body{{font:16px system-ui;max-width:980px;margin:28px auto;color:#20323d}}h1{{font-size:26px}}.note{{border-left:4px solid #c88700;background:#fff5df;padding:12px}}li{{margin:7px 0}}</style>
<h1>Full-match left/right curling deliverable</h1>
<div class="note">Development result. Event references are assistant visual judgments; physical identity, metric trajectory accuracy and complete per-end board accuracy are not independently measured. Read the report before quoting any number.</div>
<ul>{rows}</ul>
<p><a href="report.md">Full report</a> · <a href="evaluation.md">Evaluation summary</a> · <a href="evaluation.json">Evaluation JSON</a></p>
""")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="attempt directory with events.json and observation streams")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--match-state-config", type=Path)
    parser.add_argument("--post-throw-config", type=Path,
                        help="Development state parameters; adds post-throw review proposals")
    parser.add_argument("--post-throw-motion", type=Path,
                        help="Reuse matched stone_motion output; otherwise fit once automatically")
    parser.add_argument("--post-throw-aggregate", type=Path,
                        help="Postprocess ONLY this existing aggregate; no new inference or geometry")
    parser.add_argument("--post-throw-timeline", type=Path,
                        help="Existing observed/inferred end context for postprocessing-only mode")
    parser.add_argument("--dense-dir", type=Path)
    parser.add_argument("--references", type=Path)
    parser.add_argument("--score-reference", type=Path)
    parser.add_argument("--final-totals", type=Path)
    parser.add_argument("--geometry-review", type=Path)
    parser.add_argument("--identity-review", type=Path)
    parser.add_argument("--identity-conflicts", type=Path)
    parser.add_argument("--event-colours", type=Path)
    parser.add_argument("--handoff-colours", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.post_throw_aggregate:
        if not all([args.post_throw_config, args.event_colours]):
            parser.error("Post-throw replay requires config and event colours")
        if not args.post_throw_motion:
            from prototype.stone_motion import run as fit_motion
            args.post_throw_motion = args.output_dir.with_name(args.output_dir.name + "-motion")
            print("fitting recording-level motion model: " + str(args.post_throw_motion), flush=True)
            fit_motion(args.run_dir, args.post_throw_motion)
        from prototype.post_throw_state import run
        result = run(public_run=args.run_dir, aggregate=args.post_throw_aggregate,
                     event_colours=args.event_colours, motion_dir=args.post_throw_motion,
                     config_path=args.post_throw_config, video=args.video,
                     output=args.output_dir, state_timeline=args.post_throw_timeline)
        print(json.dumps(result['summary']), flush=True)
        return
    if not args.match_state_config:
        parser.error("--match-state-config is required for normal full-match assembly")
    run_dir = args.run_dir.resolve()
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()) and not args.resume:
        raise SystemExit("Output exists; preserve the previous deliverable or use --resume")
    out.mkdir(parents=True, exist_ok=True)
    events_path = run_dir / "events.json"
    match_path = run_dir / "match-observations.jsonl"
    score_path = run_dir / "score-observations.jsonl"
    match_summary_path = run_dir / "match-observation-summary.json"
    if not events_path.exists():
        raise SystemExit("events.json is missing; observation stage is not complete")
    config = json.loads(args.match_state_config.read_text())
    hog_y_m = config["local_hog_y_m"]
    aggregate_path = out / "aggregate.json"
    if not (args.resume and aggregate_path.exists()):
        print("building frozen aggregate", flush=True)
        build_aggregate(args.video.resolve(), run_dir, aggregate_path, hog_y_m)
    aggregate = json.loads(aggregate_path.read_text())
    if args.event_colours and args.event_colours.exists():
        print("attaching post-hoc event colour evidence", flush=True)
        attach_event_colours(aggregate, args.event_colours)
    if args.handoff_colours and args.handoff_colours.exists():
        print("attaching handoff colour-consistency evidence", flush=True)
        attach_handoff_colours(aggregate, args.handoff_colours)
    rink_path = out / "aggregate-rink.json"
    if not (args.resume and rink_path.exists()):
        print("adding shared-rink coordinates", flush=True)
        rink = enrich(aggregate, aggregate_path=aggregate_path)
        write_json(rink_path, rink)
        write_json(out / "aggregate-rink.summary.json", {
            "summary": rink["summary"],
            "rink_transform": rink["rink_transform"],
            "provenance": rink["provenance"],
        })
    else:
        rink = json.loads(rink_path.read_text())
    state_path = out / "state-timeline.json"
    if not (args.resume and state_path.exists()):
        print("building state timeline", flush=True)
        state = build_state(events_path, match_path, score_path,
                            aggregate_rink_path=rink_path, sample_hz=1.0)
        write_json(state_path, state)
    else:
        state = json.loads(state_path.read_text())
    if args.post_throw_config:
        if not args.event_colours:
            parser.error("Post-throw state requires event colours")
        if not args.post_throw_motion:
            from prototype.stone_motion import run as fit_motion
            args.post_throw_motion = out / "motion-model"
            fit_motion(run_dir, args.post_throw_motion)
        from prototype.post_throw_state import run
        run(public_run=run_dir, aggregate=rink_path, event_colours=args.event_colours,
            motion_dir=args.post_throw_motion, config_path=args.post_throw_config,
            video=args.video, output=out / "post-throw-state", state_timeline=state_path)
    viewer_dir = out / "viewer"
    if not (args.resume and (viewer_dir / "index.html").exists()):
        print("rendering shared-rink viewer", flush=True)
        render_rink(rink_path, args.video, viewer_dir,
                    match_observations=match_path,
                    state_timeline=state_path, board_hz=1.0,
                    title="Synchronized shared-rink trajectory review — full match")
    print("evaluating", flush=True)
    final_totals = None
    if args.final_totals and args.final_totals.exists():
        final_totals = (json.loads(args.final_totals.read_text())
                        .get("final_source_confirmed_totals"))
    dense_result = (args.dense_dir / "result.json") if args.dense_dir else None
    evaluation = {
        "development": True,
        "events": evaluate_events(events_path, args.references) if args.references else {"status": "not_supplied"},
        "rink": evaluate_rink(rink_path),
        "boards": stream_boards(match_path),
        "scores": evaluate_scores(score_path, args.score_reference, final_totals),
        "runtime": evaluate_runtime(events_path, match_summary_path, dense_result),
        "dense": evaluate_dense(dense_result, args.dense_dir) if dense_result else {"status": "not_run"},
        "state": evaluate_state(state_path),
        "geometry": evaluate_geometry(args.geometry_review) if args.geometry_review else {"status": "not_supplied"},
        "identity": evaluate_identity(args.identity_review, args.identity_conflicts)
        if (args.identity_review or args.identity_conflicts) else {"status": "not_supplied"},
        "colour": (aggregate.get("event_colour")
                   if aggregate.get("event_colour") else {"status": "not_supplied"}),
        "handoff_colour": (aggregate.get("handoff_colour")
                           if aggregate.get("handoff_colour") else {"status": "not_supplied"}),
        "end_inference": (evaluate_end_inference(state_path, args.score_reference)
                          if (state_path and args.score_reference) else {"status": "not_supplied"}),
    }
    write_json(out / "evaluation.json", evaluation)
    write_markdown(evaluation, out / "evaluation.md")
    dense_index = None
    if args.dense_dir and (args.dense_dir / "index.html").exists():
        dense_index = os.path.relpath((args.dense_dir / "index.html").resolve(), out.resolve())
    header = f"""# Full-match left/right curling deliverable

**Run directory:** `{run_dir}`  
**Source:** `{args.video.resolve()}`  
**Frozen aggregate:** `aggregate.json`  
**Shared-rink aggregate:** `aggregate-rink.json`  
**State timeline:** `state-timeline.json`  

## Open the product

- [Synchronized shared-rink viewer](viewer/index.html)
- {('[Dense two-view tracks, every event](' + dense_index + ')') if dense_index else 'Dense two-view tracks: not run'}
- Both-end board and score observations: `{os.path.relpath((run_dir / 'match-observations.html').resolve(), out.resolve()) if (run_dir / 'match-observations.html').exists() else 'missing'}`
- Learned crossing evidence: `{os.path.relpath((run_dir / 'index.html').resolve(), out.resolve()) if (run_dir / 'index.html').exists() else 'missing'}`
- [Evaluation JSON](evaluation.json) · [Evaluation Markdown](evaluation.md)

"""
    addendum_path = out.parent / "FINAL_REPORT_ADDENDUM.md"
    addendum = addendum_path.read_text() if addendum_path.exists() else ""
    report = (header + deliverable_summary(evaluation) + "\n"
              + (out / "evaluation.md").read_text() + "\n" + addendum)
    (out / "report.md").write_text(report)
    landing_page(out / "index.html", report=out / "report.md",
                 viewer="viewer/index.html", dense_index=dense_index,
                 match_viewer=(os.path.relpath((run_dir / 'match-observations.html').resolve(), out.resolve())
                               if (run_dir / 'match-observations.html').exists() else None),
                 events_viewer=(os.path.relpath((run_dir / 'index.html').resolve(), out.resolve())
                                if (run_dir / 'index.html').exists() else None),
                 evaluation="evaluation.json")
    print(json.dumps({
        "events": evaluation["events"].get("status"),
        "dense": evaluation["dense"].get("status"),
        "output": str(out),
    }))


if __name__ == "__main__":
    main()
