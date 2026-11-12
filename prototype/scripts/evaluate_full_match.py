"""Evaluate one full-match directional development run.

Produces a machine-readable result and a Markdown summary. It separates what
the available references support (event matching/timing, targeted score
readings, coverage, runtime) from what they do not (independent physical
identity, metric trajectory accuracy, complete per-end board accuracy).
"""

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def load_json(path):
    if path is None or not Path(path).exists():
        return None
    return json.loads(Path(path).read_text())


def interval_distance(t, interval):
    lo, hi = interval
    if lo <= t <= hi:
        return 0.0
    return min(abs(t - lo), abs(t - hi))


def match_events(predictions, references, max_cost=2.0):
    """Global greedy one-to-one matching by distance to the reference bracket."""
    pairs = []
    for ri, ref in enumerate(references):
        for pi, pred in enumerate(predictions):
            cost = interval_distance(pred["crossing_time_s"],
                                     ref["delivery_interval_s"])
            if cost <= max_cost:
                pairs.append((cost, ri, pi))
    pairs.sort()
    used_ref, used_pred, matched = set(), set(), []
    for cost, ri, pi in pairs:
        if ri in used_ref or pi in used_pred:
            continue
        used_ref.add(ri)
        used_pred.add(pi)
        matched.append((ri, pi, cost))
    matched.sort(key=lambda row: references[row[0]]["delivery_interval_s"][0])
    return matched, used_ref, used_pred


def evaluate_events(events_path, reference_path, max_cost=2.0):
    events = load_json(events_path)
    references = load_json(reference_path)
    if events is None:
        return {"status": "missing_events"}
    if references is None:
        return {"status": "missing_reference"}
    preds = events.get("events") or []
    all_refs = references.get("events") or []
    interval = events.get("source_interval_s") or [0.0, None]
    sampled = events.get("sampled_frames")
    hz = events.get("effective_sample_hz")
    if sampled and hz:
        covered_end = float(interval[0]) + sampled / hz
        if interval[1] is not None:
            covered_end = min(float(interval[1]), covered_end)
    else:
        covered_end = interval[1]
    refs = [r for r in all_refs
            if covered_end is None or r["delivery_interval_s"][0] <= covered_end]
    refs_beyond = [r for r in all_refs if r not in refs]
    matched, used_ref, used_pred = match_events(preds, refs, max_cost=max_cost)
    rows = []
    by_end = defaultdict(lambda: {"references": 0, "predictions": 0,
                                  "matched": 0, "unmatched_predictions": 0,
                                  "unmatched_references": 0})
    for ref in refs:
        by_end[ref["id"].split("-")[1]]["references"] += 1
    for ri, pi, cost in matched:
        ref, pred = refs[ri], preds[pi]
        mid = sum(ref["delivery_interval_s"]) / 2.0
        signed = pred["crossing_time_s"] - mid
        end = ref["id"].split("-")[1]
        by_end[end]["matched"] += 1
        rows.append({
            "reference_id": ref["id"],
            "prediction_id": pred["id"],
            "reference_colour": ref.get("colour"),
            "reference_interval_s": ref["delivery_interval_s"],
            "prediction_time_s": pred["crossing_time_s"],
            "signed_timing_error_s": signed,
            "absolute_timing_error_s": abs(signed),
            "inside_reference_bracket": interval_distance(
                pred["crossing_time_s"], ref["delivery_interval_s"]) == 0.0,
            "prediction_colour": pred.get("colour"),
            "prediction_physical_identity_verified": bool(
                pred.get("physical_identity_verified")),
        })
    unmatched_refs = [refs[i] for i in range(len(refs)) if i not in used_ref]
    unmatched_preds = [preds[i] for i in range(len(preds)) if i not in used_pred]
    for ref in unmatched_refs:
        by_end[ref["id"].split("-")[1]]["unmatched_references"] += 1
    for pred in unmatched_preds:
        # Match to the nearest reference end for display only; not an identity.
        nearest = min(refs, key=lambda r: interval_distance(
            pred["crossing_time_s"], r["delivery_interval_s"]), default=None)
        if nearest:
            by_end[nearest["id"].split("-")[1]]["unmatched_predictions"] += 1
    timing = [row["absolute_timing_error_s"] for row in rows]
    signed = [row["signed_timing_error_s"] for row in rows]
    precision_note = (
        "Unmatched predictions are reported as unreviewed candidates, not automatic "
        "false positives: the reference is not an exhaustive intervening-footage review."
    )
    return {
        "status": "evaluated",
        "covered_interval_s": [interval[0], covered_end],
        "references_in_covered_interval": len(refs),
        "references_beyond_coverage": len(refs_beyond),
        "predictions": len(preds),
        "references": len(refs),
        "matched": len(matched),
        "unmatched_predictions": len(unmatched_preds),
        "unmatched_references": len(unmatched_refs),
        "precision_if_reference_complete": (
            len(matched) / len(preds) if preds else None),
        "recall_against_covered_references": (
            len(matched) / len(refs) if refs else None),
        "recall_against_all_references": (
            len(matched) / len(all_refs) if all_refs else None),
        "timing_abs_error_s": {
            "median": statistics.median(timing) if timing else None,
            "mean": statistics.mean(timing) if timing else None,
            "max": max(timing) if timing else None,
            "signed_median": statistics.median(signed) if signed else None,
            "inside_bracket_fraction": (
                sum(row["inside_reference_bracket"] for row in rows) / len(rows)
                if rows else None),
        },
        "reference_colours": dict(Counter(ref.get("colour") for ref in refs)),
        "prediction_colour_available": sum(
            1 for pred in preds if pred.get("colour") is not None),
        "prediction_physical_identity_verified": sum(
            1 for pred in preds if pred.get("physical_identity_verified")),
        "unmatched_prediction_ids": [p["id"] for p in unmatched_preds],
        "unmatched_reference_ids": [r["id"] for r in unmatched_refs],
        "references_beyond_coverage_ids": [r["id"] for r in refs_beyond],
        "by_end": dict(sorted(by_end.items())),
        "matches": rows,
        "reference_provenance": {
            "reviewer": references.get("reviewer"),
            "independent_ground_truth": references.get("independent_ground_truth"),
            "exhaustive_intervening_footage_review": references.get(
                "exhaustive_intervening_footage_review"),
            "known_deliveries_reviewed": references.get(
                "known_deliveries_reviewed"),
            "source_sha256": references.get("source_sha256"),
        },
        "matching_rule": f"one-to-one global greedy; distance to reference bracket <= {max_cost} s",
        "precision_note": precision_note,
    }


def stream_boards(path):
    if path is None or not Path(path).exists():
        return {"status": "missing"}
    panels = {"left": Counter(), "right": Counter()}
    samples = 0
    stones = {"left": 0, "right": 0}
    projected = {"left": 0, "right": 0}
    both_projected = 0
    both_geometry_status = 0
    score_totals = 0
    current_end_non_null = 0
    current_points_non_null = 0
    identity_verified = 0
    complete_board_verified = 0
    end_identity_non_null = 0
    parse_errors = 0
    last_time = None
    with Path(path).open() as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            samples += 1
            last_time = row.get("time_s")
            has = {"left": 0, "right": 0}
            for panel in ("left", "right"):
                board = (row.get("boards") or {}).get(panel) or {}
                status = ((board.get("registration") or {}).get("status")
                          or "missing")
                panels[panel][status] += 1
                if board.get("stones"):
                    has[panel] = sum(
                        1 for s in board["stones"]
                        if s.get("height_adjusted_local_m") is not None)
                stones[panel] += len(board.get("stones") or [])
                projected[panel] += has[panel]
                if board.get("complete_board_verified"):
                    complete_board_verified += 1
                if board.get("end_identity") is not None:
                    end_identity_non_null += 1
            if has["left"] and has["right"]:
                both_projected += 1
            if all(((row.get("boards") or {}).get(p, {}).get("registration")
                    or {}).get("status") for p in ("left", "right")):
                both_geometry_status += 1
            if row.get("last_observed_totals"):
                score_totals += 1
            if row.get("current_end") is not None:
                current_end_non_null += 1
            if row.get("current_points_from_stones") is not None:
                current_points_non_null += 1
            if row.get("physical_identity_verified"):
                identity_verified += 1
    return {
        "status": "evaluated",
        "samples": samples,
        "last_time_s": last_time,
        "parse_errors": parse_errors,
        "panel_status_counts": {p: dict(c) for p, c in panels.items()},
        "stones": stones,
        "projected_stones": projected,
        "mean_projected_stones_per_sample": {
            p: (projected[p] / samples if samples else None)
            for p in ("left", "right")},
        "samples_with_both_panels_projected": both_projected,
        "fraction_both_panels_projected": both_projected / samples if samples else None,
        "samples_with_both_geometry_statuses": both_geometry_status,
        "samples_with_last_observed_score_totals": score_totals,
        "samples_with_current_end": current_end_non_null,
        "samples_with_current_points": current_points_non_null,
        "samples_with_physical_identity_verified": identity_verified,
        "complete_board_verified_samples": complete_board_verified,
        "end_identity_non_null_samples": end_identity_non_null,
        "measured_against_independent_board_reference": False,
        "limitations": [
            "No independent per-end stone reference; precision/recall/position error are unmeasured.",
            "Both panels are observed, but panel is not a permanent physical-end identifier.",
            "Colour and team are not inferred by this run.",
        ],
    }


def evaluate_scores(path, reference_path=None, final_totals=None):
    if path is None or not Path(path).exists():
        return {"status": "missing"}
    rows = []
    parse_errors = 0
    with Path(path).open() as stream:
        for line in stream:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                parse_errors += 1
    values = {"CAN": [], "SWE": []}
    both = 0
    current_end = 0
    for row in rows:
        totals = row.get("totals") or {}
        seen = 0
        for team in ("CAN", "SWE"):
            value = (totals.get(team) or {}).get("value")
            if value is not None:
                values[team].append((row.get("time_s"), value))
                seen += 1
        if seen == 2:
            both += 1
        if row.get("current_end") is not None:
            current_end += 1
    summary = {
        "status": "evaluated",
        "samples": len(rows),
        "parse_errors": parse_errors,
        "samples_with_both_totals": both,
        "samples_with_all_team_totals": both,
        "fraction_both_totals": both / len(rows) if rows else None,
        "observations": {team: len(values[team]) for team in ("CAN", "SWE")},
        "distinct_values": {team: sorted({v for _, v in values[team]})
                            for team in ("CAN", "SWE")},
        "last_observed": {team: values[team][-1] if values[team] else None
                          for team in ("CAN", "SWE")},
        "nonmonotonic_transitions": {},
        "samples_with_current_end": current_end,
        "current_end_extraction_complete": False,
    }
    for team in ("CAN", "SWE"):
        seq = values[team]
        drops = [{"from": a, "to": b} for (_, a), (_, b) in zip(seq, seq[1:])
                 if b < a]
        summary["nonmonotonic_transitions"][team] = len(drops)
    if final_totals:
        summary["final_source_totals"] = final_totals
        summary["final_last_observed_match"] = {
            team: (final_totals.get(team) == summary["last_observed"][team][1]
                   if summary["last_observed"][team] else None)
            for team in ("CAN", "SWE")}
    if reference_path:
        reference = load_json(reference_path)
        samples = (reference or {}).get("samples") or []
        by_time = {}
        for row in rows:
            by_time[round(float(row.get("time_s")), 3)] = row
        fields = {team: Counter() for team in ("CAN", "SWE")}
        comparisons = []
        for sample in samples:
            time_s = round(float(sample["time_s"]), 3)
            row = by_time.get(time_s)
            if row is None:
                comparisons.append({"time_s": time_s, "status": "no_ocr_sample"})
                continue
            for team in ("CAN", "SWE"):
                ref = sample.get(team)
                pred = ((row.get("totals") or {}).get(team) or {}).get("value")
                if ref is None:
                    status = ("prediction_on_unreadable_reference"
                              if pred is not None else "both_unknown")
                elif pred is None:
                    status = "abstained"
                elif pred == ref:
                    status = "correct"
                else:
                    status = "incorrect"
                fields[team][status] += 1
                comparisons.append({"time_s": time_s, "team": team,
                                    "reference": ref, "prediction": pred,
                                    "status": status})
        summary["reference_comparison"] = {
            "reference": str(reference_path),
            "reviewer": reference.get("reviewer"),
            "independent_ground_truth": reference.get(
                "independent_ground_truth"),
            "samples": len(samples),
            "fields": {team: dict(counter) for team, counter in fields.items()},
            "comparisons": comparisons,
            "scope": "Targeted source-review timestamps, not a full-sequence independent accuracy estimate.",
        }
    return summary


def evaluate_rink(aggregate_path):
    aggregate = load_json(aggregate_path)
    if aggregate is None:
        return {"status": "missing"}
    segments = []
    links = []
    lateral_out = 0
    beyond_tee = 0
    mapped = 0
    for event in aggregate.get("events", []):
        for segment in event.get("segments", []):
            samples = [s for s in segment.get("geometry_samples", [])
                       if s.get("rink_position_m") is not None]
            mapped += len(samples)
            for sample in samples:
                x, y = sample["rink_position_m"]
                if not (-2.375 <= x <= 2.375):
                    lateral_out += 1
                if y < 0 or y > 34.747:
                    beyond_tee += 1
            times = [s["time_s"] for s in samples]
            gaps = [b - a for a, b in zip(times, times[1:]) if b - a > 0.5]
            segments.append({
                "segment_id": segment.get("segment_id"),
                "panel": segment.get("rink_panel"),
                "role": segment.get("rink_role"),
                "status": segment.get("rink_coordinate_status"),
                "samples": len(samples),
                "first_s": times[0] if times else None,
                "last_s": times[-1] if times else None,
                "gaps_over_0_5s": len(gaps),
                "max_gap_s": max(gaps) if gaps else 0.0,
                "physical_identity_verified": bool(
                    segment.get("physical_identity_verified")),
            })
        for link in event.get("cross_view_links", []):
            links.append({
                "event": event.get("candidate_id"),
                "spatial_consistency": link.get("spatial_consistency"),
                "gap_status": link.get("gap_status"),
                "speed_status": link.get("speed_status"),
                "gap_m": link.get("gap_m"),
                "gap_s": link.get("gap_s"),
                "implied_speed_m_s": link.get("implied_speed_m_s"),
                "physical_identity_verified": bool(
                    link.get("physical_identity_verified")),
            })
    gaps = [l["gap_m"] for l in links if l.get("gap_m") is not None]
    speeds = [l["implied_speed_m_s"] for l in links
              if l.get("implied_speed_m_s") is not None]
    return {
        "status": "evaluated",
        "events": len(aggregate.get("events", [])),
        "segments": len(segments),
        "mapped_geometry_samples": mapped,
        "segments_without_mapped_samples": sum(
            1 for s in segments if s["samples"] == 0),
        "segments_by_status": dict(Counter(s["status"] for s in segments)),
        "segments_by_role": dict(Counter(s["role"] for s in segments)),
        "segments_by_panel": dict(Counter(s["panel"] for s in segments)),
        "links": len(links),
        "link_status_counts": dict(Counter(
            l["spatial_consistency"] for l in links)),
        "gap_m": {"median": statistics.median(gaps) if gaps else None,
                  "max": max(gaps) if gaps else None},
        "implied_speed_m_s": {
            "median": statistics.median(speeds) if speeds else None,
            "max": max(speeds) if speeds else None},
        "links_large_gap": sum(1 for l in links
                               if l["spatial_consistency"] == "large_gap"),
        "links_implausible_gap": sum(1 for l in links
                                     if l["spatial_consistency"] == "implausible_gap"),
        "links_high_speed": sum(1 for l in links
                                if l["spatial_consistency"] == "high_speed"),
        "lateral_out_of_sheet_samples": lateral_out,
        "longitudinal_beyond_tee_samples": beyond_tee,
        "longitudinal_beyond_tee_note": "Stones can overrun either tee; this is not an error. It is reported separately from lateral out-of-sheet positions.",
        "physical_identity_verified_links": sum(
            1 for l in links if l["physical_identity_verified"]),
        "rink_transform": aggregate.get("rink_transform"),
        "trajectory_accuracy_measured": False,
        "limitations": [
            "No independent metric trajectory reference; geometry is not accuracy-validated here.",
            "Height-adjusted positions are conditional estimates, not measured stone centres.",
            "The unobserved middle is a gap and is not interpolated.",
        ],
    }


def evaluate_runtime(events_path, match_summary_path, dense_result_path):
    events = load_json(events_path)
    match = load_json(match_summary_path)
    dense = load_json(dense_result_path)
    result = {"status": "evaluated", "event_stage": None,
              "match_observation_stage": None, "dense_stage": None}
    if events:
        result["event_stage"] = {
            "wall_seconds": events.get("wall_seconds"),
            "detector_seconds": events.get("detector_seconds"),
            "association_seconds": events.get("association_seconds"),
            "sampled_frames": events.get("sampled_frames"),
            "reused_detector_frames": events.get("reused_detector_frames"),
            "prior_detector_seconds_for_reused_frames": events.get(
                "prior_detector_seconds_for_reused_frames"),
            "source_interval_s": events.get("source_interval_s"),
        }
    if match:
        result["match_observation_stage"] = {
            "samples": match.get("samples"),
            "geometry_seconds": match.get("geometry_seconds"),
            "ocr_seconds": match.get("ocr_seconds"),
            "new_calibration_fits": match.get("new_calibration_fits"),
        }
    if dense:
        result["dense_stage"] = {
            "wall_seconds": dense.get("wall_seconds"),
            "summary": dense.get("summary"),
        }
    result["notes"] = [
        "Event-stage wall time includes the match-observation stage; the geometry and OCR seconds are subsets.",
        "Dense wall time is from the same run and may share CPU with other work.",
        "perf_counter wall time excludes host suspend time on this platform.",
    ]
    return result


def evaluate_state(path):
    state = load_json(path)
    if state is None:
        return {"status": "missing"}
    summary = state.get("summary") or {}
    return {
        "status": "evaluated",
        "samples": summary.get("samples"),
        "observed_marker_samples": summary.get("observed_marker_samples"),
        "inferred_end_samples": summary.get("inferred_end_samples"),
        "end_transitions": summary.get("end_transitions"),
        "house_count_min": summary.get("house_count_min"),
        "house_count_max": summary.get("house_count_max"),
        "confirmed_end_scores_available": summary.get(
            "confirmed_end_scores_available"),
        "current_points_score_available": summary.get(
            "current_points_score_available"),
        "end_size_assumption": summary.get("end_size_assumption"),
        "notes": summary.get("notes"),
        "independent_end_reference": False,
    }


def evaluate_end_inference(state_path, score_reference_path, tolerance_s=1.5):
    state = load_json(state_path)
    reference = load_json(score_reference_path)
    if state is None or reference is None:
        return {"status": "missing"}
    samples = state.get("samples") or []
    if not samples:
        return {"status": "no_state_samples"}
    start, end = samples[0]["t"], samples[-1]["t"]
    rows = []
    for sample in reference.get("samples") or []:
        t = sample.get("time_s")
        expected = sample.get("displayed_active_end")
        if t is None or expected is None:
            continue
        if not (start - tolerance_s <= t <= end + tolerance_s):
            continue
        nearest = min(samples, key=lambda row: abs(row["t"] - t))
        if abs(nearest["t"] - t) > tolerance_s:
            rows.append({"time_s": t, "reference_end": expected,
                         "status": "no_state_sample_within_tolerance"})
            continue
        predicted = nearest.get("current_end")
        rows.append({
            "time_s": t,
            "reference_end": expected,
            "predicted_end": predicted,
            "prediction_time_s": nearest["t"],
            "prediction_status": nearest.get("current_end_status"),
            "status": "correct" if predicted == expected else "incorrect",
        })
    counts = Counter(row["status"] for row in rows)
    answered = counts["correct"] + counts["incorrect"]
    return {
        "status": "evaluated",
        "state_coverage_s": [start, end],
        "references_in_coverage": len(rows),
        "correct": counts["correct"],
        "incorrect": counts["incorrect"],
        "unavailable": counts["no_state_sample_within_tolerance"],
        "accuracy_among_answered": (
            counts["correct"] / answered if answered else None),
        "rows": rows,
        "reference": str(score_reference_path),
        "independent_ground_truth": False,
        "scope": "Assistant-labelled displayed active end; delivery-sequence inference only.",
    }


def evaluate_geometry(path):
    geometry = load_json(path)
    if geometry is None:
        return {"status": "missing"}
    return {
        "status": "evaluated",
        "source_time_s": geometry.get("source_time_s"),
        "method": geometry.get("method"),
        "independent_accuracy": geometry.get("independent_accuracy"),
        "stone_trajectory_accuracy_measured": geometry.get(
            "stone_trajectory_accuracy_measured"),
        "constraints": geometry.get("constraints"),
        "interpretation": geometry.get("interpretation"),
    }


def evaluate_identity(review_path, conflicts_path):
    review = load_json(review_path)
    conflicts = load_json(conflicts_path)
    if review is None and conflicts is None:
        return {"status": "missing"}
    return {
        "status": "evaluated",
        "targeted_review": review,
        "minimum_observed_wrong_stone_query_assignments": (
            (review or {}).get("minimum_observed_wrong_stone_query_assignments")),
        "verified_physical_identity_over_full_track": (
            (review or {}).get("verified_physical_identity_over_full_track")),
        "conflict_diagnostic": {
            k: (conflicts or {}).get(k) for k in (
                "sampled_frames_compared", "frames_with_shared_box_conflict",
                "frames_with_ambiguous_box_membership",
                "physical_identity_switch_count", "predictions_modified",
                "limitations")
        } if conflicts else None,
        "identity_switch_rate_measured": False,
    }


def evaluate_dense(result_path, tracking_dir):
    if result_path is None or not Path(result_path).exists():
        return {"status": "not_run"}
    result = load_json(result_path)
    if result is None:
        return {"status": "unreadable"}
    summary = result.get("summary") or {}
    event_dirs = sorted(Path(tracking_dir).glob("event-*")) if tracking_dir else []
    return {
        "status": "evaluated",
        "wall_seconds": result.get("wall_seconds"),
        "summary": summary,
        "event_directories": len(event_dirs),
        "physical_identity_verified": bool(
            result.get("physical_identity_verified")),
        "selection": result.get("selection"),
        "dense_events": len(result.get("events", [])),
        "dense_scope": result.get("scope"),
    }


def write_markdown(result, path):
    lines = ["# Full-match directional evaluation", "",
             "Development run. Read the evidence boundary before quoting any number.", ""]
    events = result.get("events") or {}
    if events.get("status") == "evaluated":
        lines += ["## Events", "",
                  f"- Predictions: {events['predictions']}; references: {events['references']}; matched: {events['matched']}",
                  f"- Unmatched predictions (unreviewed candidates, not automatic FP): {events['unmatched_predictions']}",
                  f"- Unmatched known deliveries inside coverage (missed): {events['unmatched_references']}",
                  f"- Known deliveries beyond processed coverage: {events['references_beyond_coverage']}",
                  f"- Recall against covered references: {events['recall_against_covered_references']:.4f}" if events['recall_against_covered_references'] is not None else "- Recall: unknown",
                  f"- Recall against all references (partial-run view): {events['recall_against_all_references']:.4f}" if events['recall_against_all_references'] is not None else "- Recall (all): unknown",
                  f"- Timing abs error: median {events['timing_abs_error_s']['median']:.3f} s, max {events['timing_abs_error_s']['max']:.3f} s" if events['timing_abs_error_s']['median'] is not None else "- Timing: unknown",
                  f"- Inside reference bracket: {events['timing_abs_error_s']['inside_bracket_fraction']:.3f}" if events['timing_abs_error_s']['inside_bracket_fraction'] is not None else "- Inside bracket: unknown",
                  f"- Prediction colour available: {events['prediction_colour_available']}; independently verified physical identities: {events['prediction_physical_identity_verified']}",
                  ""]
        lines += ["| End | Refs | Matched | Unmatched preds | Unmatched refs |", "|---|---|---|---|---|"]
        for end, row in events["by_end"].items():
            lines.append(f"| {end} | {row['references']} | {row['matched']} | {row['unmatched_predictions']} | {row['unmatched_references']} |")
        lines += ["", events["precision_note"], ""]
    rink = result.get("rink") or {}
    if rink.get("status") == "evaluated":
        lines += ["## Rink trajectories", "",
                  f"- Events: {rink['events']}; segments: {rink['segments']}; mapped samples: {rink['mapped_geometry_samples']}",
                  f"- Segments without mapped samples: {rink['segments_without_mapped_samples']}",
                  f"- Links: {rink['links']} ({rink['link_status_counts']})",
                  f"- Gap median/max: {rink['gap_m']['median']} / {rink['gap_m']['max']} m",
                  f"- Lateral out-of-sheet samples: {rink['lateral_out_of_sheet_samples']}; positions beyond a tee (overrun): {rink['longitudinal_beyond_tee_samples']}",
                  "- Trajectory accuracy measured: **no independent metric reference**.", ""]
    boards = result.get("boards") or {}
    if boards.get("status") == "evaluated":
        lines += ["## Board observations", "",
                  f"- Samples: {boards['samples']}; both panels projected: {boards['samples_with_both_panels_projected']} ({boards['fraction_both_panels_projected']:.3f})" if boards['fraction_both_panels_projected'] is not None else f"- Samples: {boards['samples']}",
                  f"- Mean projected stones/sample: {boards['mean_projected_stones_per_sample']}",
                  f"- `complete_board_verified`: {boards['complete_board_verified_samples']} samples; `end_identity` non-null: {boards['end_identity_non_null_samples']}",
                  "- Independent per-end stone accuracy: **not measured**.", ""]
    scores = result.get("scores") or {}
    if scores.get("status") == "evaluated":
        lines += ["## Score observations", "",
                  f"- OCR samples: {scores['samples']}; both totals readable: {scores['samples_with_both_totals']}",
                  f"- Last observed: {scores['last_observed']}",
                  f"- Non-monotonic transitions: {scores['nonmonotonic_transitions']}",
                  f"- `current_end` non-null samples: {scores['samples_with_current_end']}", ""]
        if scores.get("reference_comparison"):
            lines += [f"- Targeted reference fields: {scores['reference_comparison']['fields']}", ""]
    state = result.get("state") or {}
    if state.get("status") == "evaluated":
        lines += ["## Game/end state evidence", "",
                  f"- State samples: {state['samples']}; observed markers: {state['observed_marker_samples']}; inferred ends: {state['inferred_end_samples']}",
                  f"- Inferred end transitions: {state['end_transitions']}",
                  f"- Detected stones in receiving house (min/max): {state['house_count_min']} / {state['house_count_max']} (detections, not a score)",
                  f"- Confirmed end scores available: {state['confirmed_end_scores_available']}; current-points score available: {state['current_points_score_available']}",
                  "- Independent end/score reference: **no**.", ""]
    geometry = result.get("geometry") or {}
    if geometry.get("status") == "evaluated":
        lines += ["## Geometry evidence", "",
                  f"- Source time: {geometry['source_time_s']} s; method: {geometry['method']}",
                  f"- Independent accuracy: {geometry['independent_accuracy']}; trajectory accuracy measured: {geometry['stone_trajectory_accuracy_measured']}",
                  f"- Constraints: {geometry['constraints']}", ""]
    identity = result.get("identity") or {}
    if identity.get("status") == "evaluated":
        lines += ["## Identity evidence", "",
                  f"- Minimum observed wrong-stone query assignments (targeted): {identity['minimum_observed_wrong_stone_query_assignments']}",
                  f"- Verified physical identity over a full track: {identity['verified_physical_identity_over_full_track']}",
                  f"- Identity-switch rate measured: {identity['identity_switch_rate_measured']}",
                  f"- Conflict diagnostic: {identity['conflict_diagnostic']}", ""]
    colour = result.get("colour") or {}
    if colour.get("summary"):
        summary = colour["summary"]
        reference = colour.get("reference_comparison") or {}
        lines += ["## Event colour (post-hoc, unverified)", "",
                  f"- Events: {summary.get('events')}; two-observation agreement: {summary.get('two_observation_agreement')}; single: {summary.get('single_observation')}; disagreement: {summary.get('disagreement')}; unavailable: {summary.get('unavailable')}",
                  f"- Colour counts: red {summary.get('red')}, yellow {summary.get('yellow')}; wall {summary.get('wall_seconds')} s",
                  f"- Reference comparison: matched {reference.get('matched')}, correct {reference.get('correct')}, incorrect {reference.get('incorrect')}, abstained {reference.get('abstained')}",
                  "- Colour is a forced-choice OpenCLIP ranking, not team or physical identity; references are assistant labels.", ""]
    end_inference = result.get("end_inference") or {}
    if end_inference.get("status") == "evaluated":
        lines += ["## End-number inference", "",
                  f"- References in state coverage: {end_inference['references_in_coverage']}; correct {end_inference['correct']}; incorrect {end_inference['incorrect']}; unavailable {end_inference['unavailable']}",
                  f"- Accuracy among answered: {end_inference['accuracy_among_answered']}",
                  "- Inference from the delivery sequence only; assistant-labelled displayed active end; not independent.", ""]
    handoff_colour = result.get("handoff_colour") or {}
    if handoff_colour.get("summary"):
        summary = handoff_colour["summary"]
        lines += ["### Handoff colour consistency", "",
                  f"- Handoffs: {summary.get('handoffs')}; agree {summary.get('agree')}; disagree {summary.get('disagree')}; unverified {summary.get('unverified')}",
                  f"- Consistency among verified: {summary.get('colour_consistency_among_verified')}",
                  "- Supporting evidence only; same-colour stones remain indistinguishable.", ""]
    runtime = result.get("runtime") or {}
    if runtime.get("status") == "evaluated":
        lines += ["## Runtime", "",
                  f"- Event stage wall: {runtime['event_stage']['wall_seconds']} s; detector: {runtime['event_stage']['detector_seconds']} s; sampled frames: {runtime['event_stage']['sampled_frames']}" if runtime.get("event_stage") else "- Event stage: missing",
                  f"- Match observation: {runtime['match_observation_stage']}" if runtime.get("match_observation_stage") else "- Match observation: missing",
                  f"- Dense stage: {runtime['dense_stage']}" if runtime.get("dense_stage") else "- Dense stage: not run",
                  ""]
    dense = result.get("dense") or {}
    lines += ["## Dense tracking", "", f"- Status: {dense.get('status')}"]
    if dense.get("status") == "evaluated":
        lines += [f"- Wall: {dense['wall_seconds']} s; summary: {dense['summary']}",
                  f"- Event directories: {dense['event_directories']}; physical identity verified: {dense['physical_identity_verified']}"]
    lines += ["", "## Evidence boundary", "",
              "- Event references are assistant visual judgments with coarse brackets and non-exhaustive intervening footage.",
              "- Identity, metric trajectory accuracy and complete per-end board accuracy have no independent references in this run.",
              "- Score comparisons are targeted development reviews, not full-sequence independent accuracy.",
              "- No number here establishes independent transfer or physical-identity correctness."]
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--references", type=Path)
    parser.add_argument("--match-observations", type=Path)
    parser.add_argument("--score-observations", type=Path)
    parser.add_argument("--score-reference", type=Path)
    parser.add_argument("--final-totals", type=Path)
    parser.add_argument("--aggregate-rink", type=Path)
    parser.add_argument("--match-summary", type=Path)
    parser.add_argument("--dense-result", type=Path)
    parser.add_argument("--tracking-dir", type=Path)
    parser.add_argument("--state-timeline", type=Path)
    parser.add_argument("--geometry-review", type=Path)
    parser.add_argument("--identity-review", type=Path)
    parser.add_argument("--identity-conflicts", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    final_totals = None
    if args.final_totals:
        payload = load_json(args.final_totals) or {}
        final_totals = payload.get("final_source_confirmed_totals")
    result = {
        "development": True,
        "events": evaluate_events(args.events, args.references) if args.events and args.references else {"status": "not_supplied"},
        "rink": evaluate_rink(args.aggregate_rink) if args.aggregate_rink else {"status": "not_supplied"},
        "boards": stream_boards(args.match_observations) if args.match_observations else {"status": "not_supplied"},
        "scores": evaluate_scores(args.score_observations, args.score_reference, final_totals) if args.score_observations else {"status": "not_supplied"},
        "runtime": evaluate_runtime(args.events, args.match_summary, args.dense_result) if args.events else {"status": "not_supplied"},
        "dense": evaluate_dense(args.dense_result, args.tracking_dir) if args.dense_result else {"status": "not_run"},
        "state": evaluate_state(args.state_timeline) if args.state_timeline else {"status": "not_supplied"},
        "geometry": evaluate_geometry(args.geometry_review) if args.geometry_review else {"status": "not_supplied"},
        "identity": evaluate_identity(args.identity_review, args.identity_conflicts) if (args.identity_review or args.identity_conflicts) else {"status": "not_supplied"},
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.markdown:
        write_markdown(result, args.markdown)
    print(json.dumps({
        "events": result["events"].get("status"),
        "rink": result["rink"].get("status"),
        "boards": result["boards"].get("status"),
        "scores": result["scores"].get("status"),
        "dense": result["dense"].get("status"),
        "state": result["state"].get("status"),
        "geometry": result["geometry"].get("status"),
        "identity": result["identity"].get("status"),
    }))


if __name__ == "__main__":
    main()
