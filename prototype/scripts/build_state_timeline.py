"""Build an explicit observed/inferred/unknown state timeline from saved evidence.

The scoreboard's active-end marker is often unreadable. This module does not
pretend otherwise: it carries a recent past observed marker when available.
Event counts supply only a relative hypothesis; they do not identify the first
end of a partial recording. House stone counts are detections, not a score, and team/colour is
unknown.

No later observation is used as an earlier state. No state is filled across a
missing board sample.
"""

import argparse
import json
import math
from bisect import bisect_left, bisect_right
from pathlib import Path

HOUSE_RADIUS_M = 1.829
END_SIZE = 16


def infer_end(event_times, time_s, end_size=END_SIZE):
    """End containing the latest detected delivery at ``time_s``.

    Assumes a fixed 16-delivery end and that the event list has no misses or
    extras. This is an inference, not an observed game state.
    """
    if not isinstance(end_size, int) or end_size <= 0:
        raise ValueError('Positive integer deliveries per end required')
    before = bisect_left(event_times, time_s)
    return {
        "current_end": max(bisect_right(event_times, time_s) - 1, 0) // end_size + 1,
        "deliveries_before": before,
        "status": "inferred_from_delivery_sequence",
        "assumptions": [
            f"{end_size} deliveries per end",
            "no missing or extra line-crossing events",
            "the event list is chronological",
            "sequence index is relative; the first event need not be in game end 1",
        ],
    }


def observed_end(score_rows, time_s, tolerance_s=6.0):
    past=[row for row in score_rows if row['time_s']<=time_s]
    if not past:
        return None
    best = max(past, key=lambda row: row['time_s'])
    if abs(best["time_s"] - time_s) > tolerance_s:
        return None
    if best.get("current_end") is None:
        return None
    return {
        "current_end": best["current_end"],
        "status": "observed_scoreboard_active_end_marker",
        "observation_time_s": best["time_s"],
        "age_s": time_s - best["time_s"],
        "marker_status": best.get("current_end_status"),
    }


def parse_end_evidence(score_rows, team_labels=("CAN", "SWE")):
    """Parse readable per-end cells once; empty results stay unknown."""
    try:
        from prototype.score_grid import parse_end_cells
    except ImportError:
        return []
    evidence = []
    for row in score_rows:
        parsed = parse_end_cells(row.get("tokens") or [], list(team_labels))
        readable = {end: cells for end, cells in parsed["end_score_cells"].items()
                    if any((cells.get(team) or {}).get("value") is not None
                           for team in team_labels)}
        if parsed.get("current_end") is not None or readable:
            evidence.append({
                "time_s": row["time_s"],
                "current_end": parsed.get("current_end"),
                "current_end_status": parsed.get("current_end_status"),
                "readable_end_cells": readable,
            })
    return evidence


def role_timeline(events):
    rows = []
    for event in events:
        t = event["event_prediction"]["crossing_time_s"]
        for segment in event["segments"]:
            role = segment.get("role")
            panel = segment.get("rink_panel") or (
                "left" if str(segment.get("camera", "")).startswith("left") else "right")
            if role in ("departure", "receiving"):
                rows.append((t, panel, role))
    rows.sort()
    by_panel = {"left": [], "right": []}
    for t, panel, role in rows:
        history = by_panel[panel]
        if history and history[-1][1] == role:
            continue
        history.append((t, role))
    return by_panel


def role_at(timeline, panel, time_s):
    history = timeline.get(panel) or []
    if not history:
        return None
    chosen = None
    for t, role in history:
        if t <= time_s:
            chosen = role
        else:
            break
    return chosen


def house_count(row, panel):
    board = (row.get("boards") or {}).get(panel) or {}
    positions = [stone.get("height_adjusted_local_m")
                 for stone in board.get("stones", [])]
    positions = [p for p in positions if p is not None]
    in_house = [p for p in positions if math.hypot(p[0], p[1]) <= HOUSE_RADIUS_M]
    return {
        "panel": panel,
        "projected_stones": len(positions),
        "detected_stones_in_house": len(in_house),
        "team_breakdown": None,
        "colour_breakdown": None,
        "status": "detected_stones_not_a_score",
        "limitations": [
            "Body-box centres, not verified stone centres.",
            "Occluded or missed stones are absent.",
            "Team and colour are not inferred.",
        ],
    }


def build(events_path, match_observations_path, score_observations_path,
          *, aggregate_rink_path=None, sample_hz=1.0, end_size=END_SIZE, team_labels=("CAN", "SWE")):
    events = json.loads(Path(events_path).read_text())
    event_list = events.get("events") or []
    event_times = sorted(event["crossing_time_s"] for event in event_list)
    if aggregate_rink_path is not None:
        aggregate = json.loads(Path(aggregate_rink_path).read_text())
        timeline = role_timeline(aggregate.get("events") or [])
    else:
        # Fallback only: direction is a line-crossing direction, not a
        # verified camera role. Prefer the enriched aggregate.
        fallback = []
        for event in event_list:
            fallback.append({
                "event_prediction": event,
                "segments": [{
                    "role": "departure" if event.get("direction") == "negative" else "receiving",
                    "rink_panel": "left" if event["crossing_point_normalized"][0] < 0.5 else "right",
                    "camera": "left_split" if event["crossing_point_normalized"][0] < 0.5 else "right_split",
                }],
            })
        timeline = role_timeline(fallback)
    score_rows = []
    with Path(score_observations_path).open() as stream:
        for line in stream:
            try:
                score_rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    end_evidence = parse_end_evidence(score_rows, team_labels)
    observed_markers = [row for row in score_rows if row.get("current_end") is not None]
    samples = []
    last_t = None
    previous_end = None
    transitions = []
    with Path(match_observations_path).open() as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = row["time_s"]
            if last_t is not None and t - last_t < 1.0 / sample_hz - 1e-9:
                continue
            last_t = t
            inferred = infer_end(event_times, t, end_size=end_size)
            observed = observed_end(score_rows, t)
            receiving_panel = None
            for panel in ("left", "right"):
                if role_at(timeline, panel, t) == "receiving":
                    receiving_panel = panel
            house = house_count(row, receiving_panel) if receiving_panel else {
                "panel": None, "projected_stones": None,
                "detected_stones_in_house": None, "team_breakdown": None,
                "colour_breakdown": None, "status": "no_receiving_role_at_time",
            }
            totals = row.get("last_observed_totals") or {}
            sample = {
                "t": t,
                "current_end": observed["current_end"] if observed else None,
                "current_end_status": observed["status"] if observed else 'unknown_absolute_end',
                "relative_end_hypothesis": inferred,
                "observed_marker": observed,
                "deliveries_before": inferred["deliveries_before"],
                "house": house,
                "last_observed_totals": {
                    team: {"value": payload.get("value"),
                           "age_s": payload.get("age_s"),
                           "observed_at_s": payload.get("observed_at_s")}
                    for team, payload in totals.items()},
                "confirmed_end_score": None,
                "current_points_score": None,
                "provenance": {
                    "end": "observed_marker" if observed else "unknown_sequence_origin_and_unverified_delivery_completeness",
                    "house": house.get("status"),
                    "totals": "raw OCR totals with age" if totals else "unknown",
                    "end_score": "unreadable_or_not_extracted",
                },
            }
            if previous_end is not None and sample["current_end"] != previous_end:
                transitions.append({"time_s": t,
                                    "from_end": previous_end,
                                    "to_end": sample["current_end"],
                                    "status": sample["current_end_status"]})
            previous_end = sample["current_end"]
            samples.append(sample)
    summary = {
        "samples": len(samples),
        "sample_hz": sample_hz,
        "observed_marker_samples": sum(
            1 for sample in samples
            if sample["current_end_status"].startswith("observed")),
        "inferred_end_samples": sum(
            1 for sample in samples
            if sample["current_end_status"].startswith("inferred")),
        "unknown_absolute_end_samples": sum(sample['current_end'] is None for sample in samples),
        "end_transitions": transitions,
        "interpretable_end_evidence_rows": len(end_evidence),
        "observed_markers_in_score_stream": len(observed_markers),
        "house_count_min": min(
            (sample["house"]["detected_stones_in_house"] for sample in samples
             if sample["house"].get("detected_stones_in_house") is not None),
            default=None),
        "house_count_max": max(
            (sample["house"]["detected_stones_in_house"] for sample in samples
             if sample["house"].get("detected_stones_in_house") is not None),
            default=None),
        "end_size_assumption": end_size,
        "confirmed_end_scores_available": 0,
        "current_points_score_available": 0,
        "notes": [
            "Absolute game end stays unknown without a recent past readable scoreboard marker.",
            "Relative end hypotheses assume complete delivery counts and are not promoted to absolute game state.",
            "House counts are detections, not a score; team and colour are unknown.",
        ],
    }
    return {
        "schema_version": "state-evidence-development-v1",
        "team_labels": list(team_labels),
        "source_interval_s": events.get("source_interval_s"),
        "samples": samples,
        "summary": summary,
        "provenance": {
            "events": str(Path(events_path).resolve()),
            "match_observations": str(Path(match_observations_path).resolve()),
            "score_observations": str(Path(score_observations_path).resolve()),
            "end_evidence": end_evidence,
            "physical_identity_verified": False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--match-observations", type=Path, required=True)
    parser.add_argument("--score-observations", type=Path, required=True)
    parser.add_argument("--aggregate-rink", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-hz", type=float, default=1.0)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output exists; preserve the previous run")
    result = build(args.events, args.match_observations,
                   args.score_observations,
                   aggregate_rink_path=args.aggregate_rink,
                   sample_hz=args.sample_hz)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
