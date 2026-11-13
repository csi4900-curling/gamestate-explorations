#!/usr/bin/env python3
"""Build the throw-by-throw full-match report from the completed final artifacts.

The report is a static page: performance dashboard, 152-event navigator, full
rink top view (shared homography frame) and end-of-throw house/state. It reuses
the final viewer's compact rink/state/board data; it does not re-run any stage.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path("/home/user/curling-project")
BASE = ROOT / "validation/full-match-development-2026-10-23"
FINAL = BASE / "final"
VIEWER = FINAL / "viewer"
RUN = BASE / "directional-full-match/attempt-0014"
OUT = FINAL / "match-report"
TEMPLATE = ROOT / "prototype/scripts/match_report_template.html"


def load(path: Path):
    return json.loads(path.read_text())


def fmt(value, digits=2):
    return "—" if value is None else f"{value:.{digits}f}"


def main() -> None:
    evaluation = load(FINAL / "evaluation.json")
    delivery = load(FINAL / "delivery-check.json")
    events = load(RUN / "events.json")["events"]
    colours = {c["event_id"]: c for c in load(FINAL / "event-colours.json")["events"]}
    ev_by_id = {e["id"]: e for e in events}

    ev = evaluation.get("events") or {}
    rink = evaluation.get("rink") or {}
    boards = evaluation.get("boards") or {}
    runtime = evaluation.get("runtime") or {}
    end_inf = evaluation.get("end_inference") or {}
    colour = (evaluation.get("colour") or {}).get("summary") or {}
    handoff = (evaluation.get("handoff_colour") or {}).get("summary") or {}
    gap = rink.get("gap_m") or {}
    gap_median = gap.get("median") if isinstance(gap, dict) else gap

    unmatched_ids = ev.get("unmatched_prediction_ids") or []
    unmatched = []
    for eid in unmatched_ids:
        e = ev_by_id.get(eid, {})
        c = colours.get(eid, {})
        unmatched.append({
            "id": eid,
            "time": e.get("crossing_time_s"),
            "colour": c.get("colour") or e.get("colour"),
        })

    event_stage = runtime.get("event_stage") or {}
    metrics = [
        {"label": "Events", "value": f"{ev.get('matched')}/{ev.get('references')}",
         "note": f"reviewed deliveries matched · {ev.get('unmatched_predictions')} unreviewed candidates in {ev.get('predictions')} total · 0 missed"},
        {"label": "Event timing", "value": f"{fmt((ev.get('timing_abs_error_s') or {}).get('median'))} s",
         "note": f"median absolute error · max {fmt((ev.get('timing_abs_error_s') or {}).get('max'))} s · "
                 f"{100 * ((ev.get('timing_abs_error_s') or {}).get('inside_bracket_fraction') or 0):.1f}% inside brackets"},
        {"label": "Event colour", "value": f"{colour.get('two_observation_agreement', 0)}/{colour.get('events', 0)}",
         "note": "two-observation agreements · 143/143 reviewed reference-correct · physical identity unverified"},
        {"label": "Handoff colour", "value": f"{handoff.get('agree', 0)} / {handoff.get('disagree', 0)}",
         "note": "agree / disagree · colour consistency is evidence, not identity"},
        {"label": "Shared rink", "value": f"{rink.get('segments', 0)} seg",
         "note": f"{rink.get('mapped_geometry_samples', 0):,} mapped samples · {rink.get('links', 0)} links "
                 f"({(rink.get('link_status_counts') or {}).get('consistent', 0)} consistent / "
                 f"{(rink.get('link_status_counts') or {}).get('high_speed', 0)} high-speed) · "
                 f"gap median {fmt(gap_median)} m"},
        {"label": "Both-end board", "value": f"{boards.get('samples', 0):,}",
         "note": f"samples · {boards.get('samples_with_both_panels_projected', 0):,} both-panel · per-stone accuracy unmeasured"},
        {"label": "State", "value": f"{end_inf.get('correct', 0)}/{end_inf.get('references_in_coverage', 0)}",
         "note": "end inference correct/covered · current end observed 0 · points/confirmed end score unavailable"},
        {"label": "Runtime", "value": f"{fmt(event_stage.get('wall_seconds'), 1)} s",
         "note": f"event stage wall · detector {fmt(event_stage.get('detector_seconds'), 1)} s"},
        {"label": "Compute", "value": "26.9 h",
         "note": "actual across attempts · ~30 h calendar · the 50–85 h dense stage was not spent"},
        {"label": "Dense", "value": "not run",
         "note": "CoTracker removed by owner decision; the original all-events dense requirement is not met"},
    ]

    status_note = (
        "<div class='note good'><b>The full match was processed.</b> The observation/aggregate pipeline covered "
        "all 10,195 s (101,950 samples at 10 Hz): 143/143 reviewed deliveries matched, 301 rink segments, "
        "135,673 mapped samples, 101,951 board samples and a 10,196-sample state timeline.</div>"
        "<div class='note bad'><b>The checklist is not ready.</b> The only blocker is that nine E09 candidates "
        "are unreviewed. The all-events CoTracker/dense stage was removed by owner decision, so the original "
        "dense requirement is not met.</div>"
        "<div class='note'><b>What this report does not claim:</b> physical stone identity, metric trajectory "
        "accuracy or complete per-end board accuracy. Colour evidence supports red/yellow but does not prove identity.</div>"
    )

    badges = [
        {"text": "Pipeline complete — amended scope", "kind": "ok"},
        {"text": "Checklist not ready — 9 E09 candidates", "kind": "bad"},
        {"text": "CoTracker/dense skipped", "kind": "warn"},
        {"text": "Identity · metric trajectory · complete board unmeasured", "kind": "warn"},
    ]

    blocker_note = (
        "The nine are unreviewed candidates, not automatic false positives. There are zero missed references. "
        "The E09 reference has 15 deliveries while the detector produced 24 candidates; the cluster at "
        "10,081–10,095 s looks like non-delivery crossings but is unconfirmed. Review those timestamps, or "
        "explicitly accept the non-exhaustive reference limitation, to close the checklist."
    )

    accomplished = [
        "Full 10,195 s match processed end-to-end at 10 Hz: 101,950 samples; no part of the video skipped.",
        "143/143 reviewed deliveries matched; 0 missed; 152 candidates with 9 unreviewed E09 candidates.",
        "Panel-aware shared-rink homography: 301 segments, 135,673 mapped samples, 141 handoffs (136 consistent, 5 high-speed), gap median 3.21 m; the unobserved middle is never interpolated.",
        "Both-end board: 101,951 samples, 78,267 with both panels observed.",
        "State timeline: 10,196 samples; end inference 9/10 covered; observed score totals and house counts with provenance and age.",
        "Event colour evidence: 152/152 two-observation agreements; handoff colour 140 agree / 1 disagree.",
        "Synchronized viewer, evaluation, browser check, delivery checklist and a durable run that recovered from reboots.",
        "Measured compute: ~26.9 h actual across attempts, ~30 h calendar; the 50–85 h dense estimate was not spent.",
    ]

    unmeasured = [
        "Physical stone identity, especially same-colour discrimination; colour evidence is not identity.",
        "Metric trajectory accuracy against independent trajectory annotations.",
        "Complete per-end board accuracy / per-stone position error against independent labels.",
        "All-events CoTracker dense: removed by owner decision; the original requirement is not met.",
        "Current end and points score: end is inferred from the delivery sequence; current-end observed 0, points score unavailable.",
        "One handoff colour disagreement; five high-speed links; two segments without mapped samples; 17,220 samples beyond a tee (overrun, not necessarily error).",
        "Event references are assistant visual judgments with coarse brackets, not exhaustive independent truth.",
    ]

    compute = (
        "<table><thead><tr><th>Attempt</th><th>Wall time</th><th>Source covered</th><th>Note</th></tr></thead><tbody>"
        "<tr><td>0004</td><td>10.13 h</td><td>3,220 s</td><td>detector 4.53 h; generated the detection cache</td></tr>"
        "<tr><td>0005</td><td>0.18 h</td><td>3,222 s</td><td>cache replay</td></tr>"
        "<tr><td>0008</td><td>0.74 h</td><td>3,532 s</td><td>13 h calendar; host slept/rebooted, no work</td></tr>"
        "<tr><td>0009</td><td>0.30 h</td><td>3,625 s</td><td>cache + new</td></tr>"
        "<tr><td>0011–0014</td><td>15.57 h</td><td>10,195 s</td><td>cache replays + live; several host reboots</td></tr>"
        "<tr><th>Measured total</th><th>~26.9 h actual</th><th>~30 h calendar</th><th>final event wall 15,581.8 s; detector 5,964.2 s</th></tr>"
        "</tbody></table>"
        "<p class='small'>The earlier “13.2 h to 41.5%” was a checkpoint, not the final total. The 50–85 h dense stage was not run. "
        "Host sleeps/reboots are calendar time, not model compute.</p>"
    )

    links = [
        {"label": "Full written report", "href": "../report.md"},
        {"label": "Evaluation summary", "href": "../evaluation.md"},
        {"label": "Machine-readable evaluation", "href": "../evaluation.json"},
        {"label": "Synchronized video viewer", "href": "../viewer/index.html"},
        {"label": "Both-end board/score observations", "href": "../directional-full-match/attempt-0014/match-observations.html"},
        {"label": "Delivery checklist", "href": "../delivery-check.json"},
        {"label": "Source video", "href": "../../source-1080p.mp4"},
    ]

    data = {
        "title": "Canada–Sweden 2024 · full-match curling report",
        "subtitle": "Public-entry observation/aggregate run · frozen models/hashes · amended scope without CoTracker/dense",
        "badges": badges,
        "statusNote": status_note,
        "metrics": metrics,
        "metricsNote": "Counts are coverage/scope statements, not independent accuracy certificates. The event references are assistant visual judgments with coarse brackets.",
        "ready": bool(delivery.get("ready_for_owner_review")),
        "blockers": delivery.get("blocking_issues") or [],
        "blockerNote": blocker_note,
        "unmatched": unmatched,
        "accomplished": accomplished,
        "unmeasured": unmeasured,
        "compute": compute,
        "links": links,
        "footer": ("Development result for Canada–Sweden 2024. Frozen baseline preserved; all-events CoTracker/dense removed by owner decision. "
                   "No identity, metric trajectory or complete board accuracy is claimed. "
                   "Source: validation/full-match-development-2026-10-23, attempt-0014."),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VIEWER / "rink-data.js", OUT / "rink-data.js")
    shutil.copy2(VIEWER / "state-data.js", OUT / "state-data.js")
    shutil.copytree(VIEWER / "board-data", OUT / "board-data", dirs_exist_ok=True)
    shutil.copy2(TEMPLATE, OUT / "index.html")
    (OUT / "report-data.js").write_text(
        "window.REPORT_DATA=" + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(OUT / "index.html"), "events": len(events),
                      "unmatched": len(unmatched), "metrics": len(metrics)}, indent=1))


if __name__ == "__main__":
    main()
