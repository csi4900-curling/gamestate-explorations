"""Shared workbench assembly stages; compose existing algorithms without replacements."""

import argparse
import json
import re
from pathlib import Path

from prototype.detection_cache import digest


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def assemble(spec):
    from prototype.directional_event_aggregate import build
    from prototype.scripts.enrich_rink_aggregate import enrich
    from prototype.scripts.build_state_timeline import build as build_state, END_SIZE
    from prototype.scripts.render_rink_viewer import render
    from prototype.scripts.finalize_full_match import attach_event_colours
    from prototype.cross_camera_consistency import annotate

    output = Path(spec["output"])
    run = output / "observations"
    result = output / "result"
    result.mkdir()
    config = json.loads(Path(spec["match_config"]).read_text())
    aggregate_path = result / "aggregate.json"
    build(spec["video"], run, aggregate_path, hog_y_by_panel=config["local_hog_y_m"])
    aggregate = json.loads(aggregate_path.read_text())
    attach_event_colours(aggregate, output / "event-colours.json")
    rink = annotate(enrich(aggregate, aggregate_path=aggregate_path))
    rink_path = result / "aggregate-rink.json"
    write(rink_path, rink)
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
        rink_path,
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
    from prototype.stone_motion import run as fit_motion
    from prototype.post_throw_state import run

    output = Path(spec["output"])
    result = output / "result"
    fit_motion(output / "observations", output / "motion-model")
    run(
        public_run=output / "observations",
        aggregate=result / "aggregate-rink.json",
        event_colours=output / "event-colours.json",
        motion_dir=output / "motion-model",
        config_path=spec["state_config"],
        video=spec["video"],
        output=result / "boards",
        state_timeline=result / "state-timeline.json",
    )


def finish(spec):
    output = Path(spec["output"])
    result = output / "result"
    events = json.loads((output / "observations/events.json").read_text())
    board = json.loads((result / "boards/manifest.json").read_text())
    aggregate = json.loads((result / "aggregate-rink.json").read_text())
    fragment_samples=[p for e in aggregate.get('unresolved_camera_fragments',[]) for s in e['segments'] for p in s.get('geometry_samples',[])]
    summary = {
        "schema_version": "curling-product-result-v1",
        "development": True,
        "source_sha256": digest(spec["video"]),
        "event_candidates": len(events["events"]),
        "post_throw_proposals": board["summary"]["review_proposals"],
        "unresolved_post_throw_candidates": len(events["events"])
        - board["summary"]["review_proposals"],
        "observed_board_frames": len(board["timeline"]["times"]),
        "trajectory_viewer": "trajectories/index.html",
        "board_viewer": "boards/index.html",
        "physical_identity_verified": False,
        "metric_geometry_accuracy_verified": False,
        "official_scoring_verified": False,
        "physical_revolutions": None,
        "rotation_status": "Unavailable: physical handle landmarks and angular tracking are not validated.",
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
<p><a href="trajectories/index.html" target="review">Trajectories</a> · <a href="boards/index.html" target="review">Stone observations</a> · <a href="summary.json">Result summary</a> · <a href="calibration/index.html">Source calibration evidence (explicit-calibration runs)</a></p>
<iframe name="review" title="Synchronized match review" src="boards/index.html"></iframe>""")
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
