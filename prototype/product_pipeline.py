"""Shared workbench assembly stages; compose existing algorithms without replacements."""

import argparse
import json
import re
from pathlib import Path

from prototype.detection_cache import digest


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def attach_event_colours(aggregate, *, track_colours_path, event_colours_path=None):
    """Attach OpenCLIP track-level stone colours to every event (primary or promoted)."""
    from collections import Counter

    track_doc = (
        json.loads(Path(track_colours_path).read_text())
        if track_colours_path and Path(track_colours_path).exists()
        else None
    )
    event_doc = (
        json.loads(Path(event_colours_path).read_text())
        if event_colours_path and Path(event_colours_path).exists()
        else None
    )
    by_id = {row["event_id"]: row for row in (event_doc or {}).get("events", [])}
    attached = 0
    for event in aggregate.get("events", []):
        colour = None
        status = None
        if track_doc is not None:
            # Prefer receiving segment colour (clean unobstructed stone view), then departure.
            ordered_segs = sorted(
                event.get("segments", []),
                key=lambda s: 0 if s.get("role") == "receiving" else 1,
            )
            for seg in ordered_segs:
                panel = seg.get("rink_panel") or (
                    "left" if seg.get("camera") == "left_split" else "right"
                )
                tid = seg.get("tracker_id")
                if tid is None:
                    continue
                colour = track_doc.get("tracks", {}).get(panel, {}).get(str(tid))
                if colour is None:
                    samps = [
                        r.get("prediction")
                        for r in track_doc.get("evidence", {}).get(panel, {}).get(str(tid), {}).get("samples", [])
                        if r.get("prediction")
                    ]
                    if samps:
                        colour = Counter(samps).most_common(1)[0][0]
                if colour is not None:
                    status = "track_colour_openclip"
                    break
        if colour is None and event["candidate_id"] in by_id:
            row = by_id[event["candidate_id"]]
            colour = row.get("colour")
            status = row.get("colour_status")
            event["colour_observations"] = row.get("observations")
        if colour is not None:
            event["colour"] = colour
            event["colour_status"] = status
            for seg in event.get("segments", []):
                if seg.get("role") == "departure":
                    seg["colour"] = colour
            attached += 1
    aggregate["event_colour"] = {
        "summary": (track_doc or event_doc or {}).get("summary"),
        "provenance": (track_doc or event_doc or {}).get("provenance"),
        "attached_events": attached,
        "physical_identity_verified": False,
        "team_mapping_established": False,
    }
    return aggregate


def assemble(spec):
    from prototype.directional_event_aggregate import build
    from prototype.scripts.enrich_rink_aggregate import enrich
    from prototype.scripts.build_state_timeline import build as build_state, END_SIZE
    from prototype.scripts.render_rink_viewer import render
    from prototype.cross_camera_consistency import annotate

    output = Path(spec["output"])
    run = output / "observations"
    result = output / "result"
    result.mkdir()
    config = json.loads(Path(spec["match_config"]).read_text())
    aggregate_path = result / "aggregate.json"
    build(spec["video"], run, aggregate_path, hog_y_by_panel=config["local_hog_y_m"],
          track_colours=output / "track-colours.json")
    aggregate = json.loads(aggregate_path.read_text())
    attach_event_colours(
        aggregate,
        track_colours_path=output / "track-colours.json",
        event_colours_path=output / "event-colours.json",
    )
    rink = annotate(enrich(aggregate, aggregate_path=aggregate_path))
    rink_path = result / "aggregate-rink.json"
    # The stored aggregate keeps every tracked sample; the trajectory view stops each
    # receiving track at the throw's first quiet board instead of at tracker loss.
    from prototype.throw_effect import throw_extents
    state_config = json.loads(Path(spec["state_config"]).read_text())
    rink, throw_view = throw_extents(
        rink, run / "match-observations.jsonl", house_radius_m=state_config["house_radius_m"],
        stone_radius_m=state_config["stone_radius_m"], hog_y_by_panel=config["local_hog_y_m"])
    write(rink_path, rink)
    view_path = result / "aggregate-rink-throw-extent.json"
    write(view_path, throw_view)
    state = build_state(
        run / "events.json",
        run / "match-observations.jsonl",
        run / "score-observations.jsonl",
        aggregate_rink_path=rink_path,
        sample_hz=1.0,
        end_size=json.loads(Path(spec['state_config']).read_text()).get('deliveries_per_end', END_SIZE),
        team_labels=config['scoreboard_team_labels'],
    )
    write(result / "state-timeline.json", state)
    render(
        view_path,
        Path(spec["video"]),
        result / "trajectories",
        match_observations=run / "match-observations.jsonl",
        state_timeline=result / "state-timeline.json",
        board_hz=1.0,
        title="Trajectories — development pipeline",
    )
    fragments=rink.get('unresolved_camera_fragments',[])
    if fragments:
        fragment_path=result/'camera-fragments.json'
        fragment_aggregate={**rink,'events':fragments,'unresolved_camera_fragments':[],
            'scope':'Observed camera track fragments with unresolved event/physical identity; no cross-view link or missing trajectory is inferred.',
            'summary':{'camera_fragments':len(fragments),'physical_events_verified':False}}
        write(fragment_path,fragment_aggregate)
        render(fragment_path,Path(spec['video']),result/'camera-fragments',
               match_observations=run/'match-observations.jsonl',state_timeline=result/'state-timeline.json',
               board_hz=1.,title='Unresolved camera tracks — event identity unknown')


def observation_view(spec):
    from prototype.match_observation_report import render

    output = Path(spec["output"]) / "observations"
    events = json.loads((output / "events.json").read_text())
    render(output, Path(spec["video"]), events["events"])


def boards(spec):
    from prototype.post_throw_state import build_board_viewer
    from prototype.throw_effect import run as throw_effects
    from prototype.throw_revolutions import run as run_revolutions
    from prototype.match_score_and_rocks import build as build_score_and_rocks

    output = Path(spec["output"])
    result = output / "result"
    colours = output / "track-colours.json"
    throw_effects(
        public_run=output / "observations",
        states=None,
        config_path=spec["state_config"],
        match_config=spec["match_config"],
        output=result / "throws",
        video=spec["video"],
        aggregate=result / "aggregate-rink.json",
        track_colours=colours if colours.exists() else None,
    )
    build_board_viewer(
        public_run=output / "observations",
        effects=result / "throws/effects.json",
        config_path=spec["state_config"],
        video=spec["video"],
        output=result / "boards",
        track_colours=colours if colours.exists() else None,
    )
    rev_path = result / "throws/revolutions.json"
    rev_payload = run_revolutions(
        public_run=output / "observations",
        aggregate=result / "aggregate-rink.json",
        effects=result / "throws/effects.json",
        video=spec["video"],
        output=rev_path,
    )
    score_rocks_path = result / "score-and-rocks.json"
    score_rocks = build_score_and_rocks(
        aggregate=result / "aggregate-rink.json",
        effects=result / "throws/effects.json",
        state_config=spec["state_config"],
        score_observations=output / "observations/score-observations.jsonl",
        revolutions=rev_path,
        output=score_rocks_path,
    )
    # Attach revolutions and inferred end/rock-pair context to throws/effects.json & effects.js
    # so the Throws viewer displays them alongside the before/after board.
    effects_path = result / "throws/effects.json"
    effects_data = json.loads(effects_path.read_text())
    rev_by_id = {e["event_id"]: e for e in rev_payload.get("events", [])}
    ctx_by_id = {t["event_id"]: t for t in score_rocks.get("throws", [])}
    for ev in effects_data["events"]:
        eid = ev["event_id"]
        if eid in rev_by_id:
            ev["revolutions"] = rev_by_id[eid]
        if eid in ctx_by_id:
            c = ctx_by_id[eid]
            ev["match_context"] = {
                "end_index": c.get("end_index"),
                "throw_in_end": c.get("throw_in_end"),
                "direction": c.get("direction"),
                "team": c.get("team"),
                "colour": c.get("colour"),
                "team_slot": c.get("team_slot"),
                "rock_pair": c.get("rock_pair"),
                "kinematics": c.get("kinematics"),
                "provenance": c.get("rock_slot_provenance"),
            }
    effects_data["revolutions_summary"] = rev_payload["summary"]
    effects_data["score_and_rocks_summary"] = score_rocks["summary"]
    effects_path.write_text(json.dumps(effects_data, indent=2, allow_nan=False) + "\n")
    (result / "throws/effects.js").write_text("window.THROW_EFFECTS=" + json.dumps(effects_data, allow_nan=False) + ";\n")


def finish(spec):
    output = Path(spec["output"])
    result = output / "result"
    events = json.loads((output / "observations/events.json").read_text())
    board = json.loads((result / "boards/manifest.json").read_text())
    aggregate = json.loads((result / "aggregate-rink.json").read_text())
    throws = json.loads((result / "throws/effects.json").read_text())
    fragment_samples=[p for e in aggregate.get('unresolved_camera_fragments',[]) for s in e['segments'] for p in s.get('geometry_samples',[])]
    total_candidates = len(aggregate["events"])
    summary = {
        "schema_version": "curling-product-result-v1",
        "development": True,
        "source_sha256": digest(spec["video"]),
        "event_candidates": total_candidates,
        "primary_pixel_line_events": len(events["events"]),
        "promoted_calibrated_receiving_events": max(0, total_candidates - len(events["events"])),
        "post_throw_proposals": board["summary"]["review_proposals"],
        "unresolved_post_throw_candidates": total_candidates
        - board["summary"]["review_proposals"],
        "observed_board_frames": len(board["timeline"]["times"]),
        "trajectory_viewer": "trajectories/index.html",
        "board_viewer": "boards/index.html",
        "throw_viewer": "throws/index.html",
        "throws_with_board_change": throws["summary"]["with_board_change"],
        "throws_without_board_change": throws["summary"]["unresolved"],
        "physical_identity_verified": False,
        "metric_geometry_accuracy_verified": False,
        "official_scoring_verified": False,
        "physical_revolutions": None,
        "rotation_status": "Development crop-period probe attached where observable; physical handle landmarks and angular counts remain unvalidated.",
        "revolutions_summary": throws.get("revolutions_summary"),
        "score_and_rocks_summary": throws.get("score_and_rocks_summary"),
        "confidence_status": "No calibrated complete-pipeline probability. Model scores/posteriors remain component evidence.",
        "measurement_scope": "Availability counts; accuracy requires timestamped source reviews.",
        "pipeline_spec_sha256": digest(output / "spec.json"),
        "camera_consistency": aggregate['summary'].get('camera_consistency'),
        "camera_crossing_observations": len(aggregate.get('camera_crossings',[])),
        "unresolved_camera_crossings": [
            {k:c.get(k) for k in ['id','panel','role','track_id','crossing_time_s','association_status','candidate_event_ids']}
            for c in aggregate.get('camera_crossings',[]) if c['association_status']=='unresolved_or_ambiguous'],
        "unresolved_camera_fragments_viewer": 'camera-fragments/index.html' if aggregate.get('unresolved_camera_fragments') else None,
        "unresolved_camera_fragment_samples":len(fragment_samples),
        "unresolved_camera_fragment_samples_without_geometry":sum(p.get('rink_position_m') is None for p in fragment_samples),
        "detection_reuse": {
            'source_job': (spec.get('detection_cache') or {}).get('job_id'),
            'reused_frames': events.get('reused_detector_frames', 0),
            'sampled_frames': events['sampled_frames'],
            'prior_detector_seconds': events.get('prior_detector_seconds_for_reused_frames', 0.),
            'scope': 'Detector predictions only; elapsed time excludes their original computation. Tracking, geometry and downstream stages reran.'},
    }
    observation_summary = json.loads((output/'observations/match-observation-summary.json').read_text())
    if observation_summary.get('manual_calibration'):
        coverage = observation_summary['calibration_coverage']
        samples = [p for e in aggregate['events'] for s in e['segments'] for p in s.get('geometry_samples', [])]
        missing_samples = sum(p.get('rink_position_m') is None for p in samples)
        incomplete_events = [e['candidate_id'] for e in aggregate['events'] if not e.get('cross_view_links')]
        gaps = any(v['registered_frames'] < v['frames'] or v['unsupported_stone_points'] for v in coverage.values())
        summary['calibration'] = {
            'status': ('no_observations' if not any(v['frames'] for v in coverage.values()) else
                       'gaps_present' if gaps else 'registered_observations_available'),
            'origin': 'explicit_operator_markings', 'camera_coverage': coverage,
            'gap_intervals': observation_summary.get('calibration_gaps', {}),
            'bundle_sha256': observation_summary['calibration_bundle_sha256'],
            'calibration_ids': spec.get('calibration_ids', []),
            'trajectory_samples': len(samples), 'trajectory_samples_without_geometry': missing_samples,
            'events_without_unique_camera_link': incomplete_events,
            'calibration_record': '../camera-calibration.json',
            'physical_accuracy_verified': False,
            'scope': 'Manual source calibration and image-registration availability. Gaps, conditional height, stone identity and feed synchronization remain separate limitations.'}
        summary['trajectory_status'] = ('incomplete' if summary['unresolved_camera_crossings'] else
                                        'no_candidates_detected' if not aggregate['events'] else
                                        'incomplete' if missing_samples or incomplete_events else
                                        'available_with_provisional_identity')
    if observation_summary.get('manual_calibration'):
        from prototype.calibration_review import render as render_calibration
        render_calibration(output/'camera-calibration.json', result/'calibration',
                           runtime=summary['calibration'], video_url=spec['video_url'])
        summary['calibration']['viewer']='calibration/index.html'
    write(result / "summary.json", summary)
    # Presentation only: a registered media route also supports sources outside
    # the project directory without copying a multi-gigabyte recording.
    for path in result.rglob("*.html"):
        text = path.read_text()
        text = re.sub(
            r'(<video\b[^>]*\bsrc=)(["\'])(.*?)\2',
            lambda m: m[1] + m[2] + spec["video_url"] + m[2],
            text,
            flags=re.DOTALL,
        )
        path.write_text(text)
    (
        result / "index.html"
    ).write_text("""<!doctype html><meta charset="utf-8"><title>Curling results</title>
<style>body{font:16px system-ui;margin:20px;color:#203641}a{color:#156777}iframe{width:100%;height:85vh;border:1px solid #d5e1e4}</style>
<h1>Match review</h1><p>Source detections and estimated trajectories. Positions depend on calibration; tracking gaps and provisional camera links remain visible.</p>
<p><a href="throws/index.html" target="review">Throws</a> · <a href="trajectories/index.html" target="review">Trajectories</a> · <a href="boards/index.html" target="review">Stone observations</a> · <a href="summary.json">Result summary</a> · <a href="calibration/index.html">Source calibration evidence (explicit-calibration runs)</a></p>
<iframe name="review" title="Synchronized match review" src="throws/index.html"></iframe>""")
    if not observation_summary.get('manual_calibration'):
        page=result/'index.html'
        page.write_text(page.read_text().replace(' · <a href="calibration/index.html">Source calibration evidence (explicit-calibration runs)</a>', ''))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", choices=["observation-view", "assemble", "boards", "finish"], required=True
    )
    parser.add_argument("--spec", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    {
        "observation-view": observation_view,
        "assemble": assemble,
        "boards": boards,
        "finish": finish,
    }[args.stage](spec)
