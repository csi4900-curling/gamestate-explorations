"""Compare frozen event roles with upstream GMC-compensated image motion.

Development diagnostic only. No new rink calibration, association, or thresholds.
Uses a single saved rink mapping after transporting the second source point into
the first camera frame. The upstream similarity camera model is an assumption.
"""
import argparse
import json
from pathlib import Path
import time
from unittest.mock import patch
from prototype.detection_cache import digest


def compare_handoffs(reference, comparison, output):
    """Replay the existing association rule with diagnostic roles, never mutate tracks."""
    from prototype.directional_handoff import metric_crossings, hypotheses
    reference, comparison, output = map(Path, (reference, comparison, output))
    if output.exists():
        raise ValueError('Preserve previous comparison')
    plan = json.loads((comparison/'plan.json').read_text())
    for name in ['events.json', 'aggregate.json', 'match-observations.jsonl']:
        path = reference/name
        if plan['inputs'].get(str(path.resolve())) != digest(path):
            raise ValueError('Role diagnostic input mismatch: '+name)
    events = json.loads((reference/'events.json').read_text())
    aggregate = json.loads((reference/'aggregate.json').read_text())
    results = json.loads((comparison/'result.json').read_text())['events']
    if len(results) != len(events['events']) or {r['event_id'] for r in results} != {e['id'] for e in events['events']}:
        raise ValueError('Role diagnostic must cover exactly the same events')
    originals = {e['candidate_id']: e for e in aggregate['events']}
    roles = {}
    for row in results:
        old = originals[row['event_id']]['segments'][0]['role_evidence']
        if old['role'] != row['frozen_role']:
            raise ValueError('Frozen role mismatch')
        roles[row['event_id']] = {
            'role': row['candidate_role'] if row['candidate_role'] in ('departure', 'receiving') else 'unassigned',
            'panel': old.get('panel'), 'physical_identity_verified': False,
            'basis': 'Development upstream GMC pair diagnostic', 'diagnostic': row}
    def boards():
        with (reference/'match-observations.jsonl').open() as stream:
            for line in stream:
                yield json.loads(line)
    crossings = metric_crossings(boards(), hog_y_by_panel=aggregate['provenance']['local_hog_y_m'])
    proposed = hypotheses(events['events'], roles, crossings, events['source_interval_s'])
    rows = []
    for event in events['events']:
        key = event['id']
        before = originals[key]['handoff_hypothesis']
        after = proposed[key]
        rows.append({'event_id': key, 'before_status': before['status'], 'after_status': after['status'],
                     'before_candidates': [c['id'] for c in before['candidates']],
                     'after_candidates': [c['id'] for c in after['candidates']], 'hypothesis': after})
    report = {'development': True, 'production_pipeline_changed': False,
              'detections_or_coordinates_modified': False, 'dense_tracking_rerun': False,
              'physical_identity_verified': False, 'events': rows,
              'inputs': {str(p.resolve()): digest(p) for p in
                         [reference/'events.json', reference/'aggregate.json', reference/'match-observations.jsonl',
                          comparison/'result.json', Path(__file__), Path(__file__).with_name('directional_handoff.py')]}}
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


def compare(reference, video, output):
    import cv2
    import numpy as np
    import ultralytics
    from ultralytics.trackers.utils.gmc import GMC
    reference, video, output = map(Path, (reference, video, output))
    if output.exists():
        raise ValueError('Preserve previous comparison')
    events = json.loads((reference/'events.json').read_text())
    aggregate = json.loads((reference/'aggregate.json').read_text())
    if digest(video) != events['source_sha256']:
        raise ValueError('Source mismatch')
    roles = {e['candidate_id']: e['segments'][0]['role'] for e in aggregate['events']}
    needed = {o['time_s'] for e in events['events'] for o in e['observations']}
    boards = {}
    with (reference/'match-observations.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['time_s'] in needed:
                boards[row['time_s']] = row
    output.mkdir(parents=True)
    code = Path(ultralytics.__file__).parent/'trackers/utils/gmc.py'
    plan = {'development': True, 'default_pipeline_changed': False,
            'method': 'Ultralytics GMC sparseOptFlow, unmodified defaults, applied separately to the event panel',
            'acceptance': 'Compare all saved event pairs, preserve missing fits and disagreements, visually review failure case; role agreement alone is not physical trajectory accuracy.',
            'inputs': {str(p.resolve()): digest(p) for p in [reference/'events.json', reference/'aggregate.json', reference/'match-observations.jsonl', code, Path(__file__)]}}
    (output/'plan.json').write_text(json.dumps(plan, indent=2))
    (output/'camera_motion_role_comparison.py').write_bytes(Path(__file__).read_bytes())
    (output/'upstream_gmc.py').write_bytes(code.read_bytes())
    cap = cv2.VideoCapture(str(video))
    width, height = events['source_size_px']
    original_fit = cv2.estimateAffinePartial2D
    results = []
    try:
        for event in events['events']:
            observations = event['observations']
            panel = 'left' if event['crossing_point_normalized'][0] < .5 else 'right'
            offset = 0 if panel == 'left' else width//2
            fits = []
            def capture_fit(a, b, *args, **kwargs):
                result = original_fit(a, b, *args, **kwargs)
                fits.append({'matched_points': len(a), 'matrix_available': result[0] is not None,
                             'inliers': int(result[1].sum()) if result[1] is not None else 0})
                return result
            tracker = GMC()
            started = time.perf_counter()
            with patch.object(cv2, 'estimateAffinePartial2D', capture_fit):
                for observation in observations:
                    index = round(observation['time_s']*events['source_fps'])
                    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = cap.read()
                    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1 != index:
                        raise ValueError('Exact source frame unavailable')
                    warp = tracker.apply(frame[:, offset:offset+width//2])
            result = {'event_id': event['id'], 'frozen_role': roles[event['id']],
                      'fits': fits, 'wall_seconds': time.perf_counter()-started,
                      'candidate_role': 'unresolved', 'physical_role_verified': False}
            mapping = boards[observations[0]['time_s']]['boards'][panel]['homography_normalized_pixels_to_local_metres']
            if fits and fits[-1]['matrix_available'] and mapping is not None:
                first = np.asarray(observations[0]['pixel'], float)
                second = np.asarray(observations[1]['pixel'], float)-[offset, 0]
                corrected = cv2.invertAffineTransform(warp)@np.r_[second, 1]+[offset, 0]
                pixels = np.asarray([first, corrected])/[width/640, height/360]
                xy = cv2.perspectiveTransform(pixels.reshape(-1, 1, 2), np.asarray(mapping)).reshape(-1, 2)
                delta = float(abs(xy[1, 1])-abs(xy[0, 1]))
                result.update(candidate_role='departure' if delta > 0 else 'receiving' if delta < 0 else 'unresolved',
                              absolute_longitudinal_distance_change_m=delta,
                              camera_warp_previous_to_current=warp.tolist(),
                              first_source_pixel=first.tolist(), second_source_pixel=observations[1]['pixel'],
                              second_pixel_in_previous_frame=corrected.tolist(),
                              point_projection='Raw body-centre ice-plane mapping; not height-adjusted physical motion accuracy')
            results.append(result)
    finally:
        cap.release()
    (output/'result.json').write_text(json.dumps({'events': results, 'pipeline_changed': False}, indent=2)+'\n')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['reference', 'video', 'output']:
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--handoff-comparison', action='store_true',
                        help='Also replay unchanged temporal association on these diagnostic roles')
    args = parser.parse_args()
    compare(args.reference, args.video, args.output)
    if args.handoff_comparison:
        compare_handoffs(args.reference, args.output, Path(args.output)/'handoff-comparison.json')
