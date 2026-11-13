"""Compare saved ByteTrack identities with CoTracker queries on common frames.

Initial point containment links components only when exactly one tracked box
contains the point. This is a comparison, not a new physical identity rule.
"""
import argparse
import hashlib
import json
from pathlib import Path


def comparable_event_inputs(left, right, left_config, right_config):
    """Require a paired head experiment, not confounded backend/settings changes."""
    for field in ['source_sha256', 'source_interval_s', 'source_fps', 'source_size_px',
                  'sample_step_frames', 'tracker_config', 'tracker_sha256', 'ultralytics',
                  'opencv_build_sha256']:
        if left[field] != right[field]:
            raise ValueError(f'Comparison inputs differ: {field}')
    # Relocation may change the filename; recorded tracker bytes must match above.
    configs = [{k: v for k, v in c.items() if k != 'tracker_config'} for c in [left_config, right_config]]
    if configs[0] != configs[1]:
        raise ValueError('Detector/line configuration differs')
    for field in ['backend', 'device', 'threads', 'checkpoint_sha256', 'imgsz', 'torch', 'ultralytics']:
        if left['model'][field] != right['model'][field]:
            raise ValueError(f'Detector comparison inputs differ: {field}')
    modes = [r['model'].get('experimental_upstream_end2end') for r in [left, right]]
    if modes != [True, False]:
        raise ValueError('Expected recorded end-to-end then conventional head')
    return {'paired_inputs_verified': True, 'changed_factor': 'upstream YOLO head',
            'tracker_path_relocation_allowed_only_with_equal_content_hash': True}


def evaluate_event_pair(left_run, right_run, reference_run, reference_path, output):
    from prototype.public_event_audit import verify_scan, verified_candidate_precision
    from prototype.throw_event_benchmark import evaluate_events
    paths = [Path(left_run), Path(right_run)]
    output = Path(output)
    if output.exists():
        raise ValueError('Preserve previous comparison')
    records = [json.loads((p/'events.json').read_text()) for p in paths]
    configs = [json.loads((p/'config.json').read_text()) for p in paths]
    check = comparable_event_inputs(*records, *configs)
    reference_run, reference_path = Path(reference_run), Path(reference_path)
    baseline = json.loads((reference_run/'events.json').read_text())
    references = json.loads(reference_path.read_text())
    if baseline['config_sha256'] != references['line_config_sha256']:
        raise ValueError('Reference line provenance differs')
    baseline_config = json.loads((reference_run/'config.json').read_text())
    if baseline_config['lines'] != configs[0]['lines']:
        raise ValueError('Evaluated line differs from source annotations')
    if references['source_sha256'] != records[0]['source_sha256']:
        raise ValueError('Reference source differs')
    lo, hi = records[0]['source_interval_s']
    selected = [r for r in references['events'] if lo <= r['delivery_interval_s'][0] and r['delivery_interval_s'][1] <= hi]
    rows = []
    for path, events in zip(paths, records):
        with (path/'observations.jsonl').open() as stream:
            coverage = verify_scan(events, (json.loads(line) for line in stream))
        scored = evaluate_events(events['events'], selected, (lo, hi), tolerance_s=0, evaluate_colour=False)
        rows.append({'run': str(path), 'coverage': coverage,
                     'predictions': len(events['events']), 'matched_known_throws': scored['true_positives'],
                     'missed_reference_ids': scored['missed_reference_ids'],
                     'unmatched_predictions_requiring_review': scored['extra_prediction_ids'],
                     'matches': scored['matches'],
                     'reviewed_candidate_precision': verified_candidate_precision(scored, selected),
                     'event_scan_wall_seconds': events['wall_seconds'],
                     'detector_seconds': events['detector_seconds'],
                     'association_seconds': events['association_seconds']})
    result = {'scope': 'Paired development event-stage comparison. Source reference completeness and trajectory identities are not certified.',
              'input_checks': check, 'known_references': len(selected), 'rows': rows,
              'reference_reviewer': references.get('reviewer'), 'input_hashes': {}}
    files = [reference_path, reference_run/'config.json', reference_run/'events.json', Path(__file__)]
    files += [p/name for p in paths for name in ['events.json', 'observations.jsonl', 'config.json']]
    for p in files:
        with p.open('rb') as stream:
            result['input_hashes'][str(p.resolve())] = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.write_text(json.dumps(result, indent=2))
    return result


def contains(box, point):
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def box_boundary_contacts(box, bounds):
    """Exact image/crop boundary contact, not a tuned visibility threshold.

    Interior boxes can still be occluded. Contact does not establish the true
    feature height or justify discarding a track.
    """
    return [side for side, touched in zip(
        ['left', 'top', 'right', 'bottom'],
        [box[0] <= bounds[0], box[1] <= bounds[1],
         box[2] >= bounds[2], box[3] >= bounds[3]]) if touched]


def sampled_runs(records, predicate):
    """Consecutive compared samples only; never fill an unobserved interval."""
    runs = []
    active = None
    for row in records:
        if predicate(row):
            if active is None:
                active = {'first_sample_s': row['time_s'], 'last_sample_s': row['time_s'],
                          'sample_count': 0}
                runs.append(active)
            active['last_sample_s'] = row['time_s']
            active['sample_count'] += 1
        else:
            active = None
    return runs


def compare(result, observations):
    lookup = {f: i for i, f in enumerate(result['frame_indices'])}
    rows = [r for r in observations if r['frame_index'] in lookup]
    if not rows or rows[0]['frame_index'] != result['frame_indices'][0]:
        raise ValueError('Shared initial frame required; do not reseed on later evidence')
    initial = rows[0]['tracked_observations']
    links = []
    for q, point in enumerate(result['tracks_px'][0]):
        ids = sorted({d['track_id'] for d in initial if contains(d['bbox_xyxy'], point)})
        links.append({'query_index': q, 'initial_candidate_track_ids': ids,
                      'track_id': ids[0] if len(ids) == 1 else None,
                      'initial_candidate_box_boundary_contacts': [
                          {'track_id': d['track_id'],
                           'tracking_crop_sides': box_boundary_contacts(d['bbox_xyxy'], result['crop_px'])}
                          for d in initial if d['track_id'] in ids] if result.get('crop_px') else None,
                      'status': 'unique_initial_box' if len(ids) == 1 else 'ambiguous_or_missing'})
    records = []
    for row in rows:
        i = lookup[row['frame_index']]
        if abs(row['time_s'] - result['times_s'][i]) > 1e-6:
            raise ValueError('Frame timestamps differ')
        by_id = {d['track_id']: d for d in row['tracked_observations']}
        if len(by_id) != len(row['tracked_observations']):
            raise ValueError('Duplicate detector tracker ID in one frame')
        comparisons = []
        for link in links:
            q = link['query_index']; detector = by_id.get(link['track_id'])
            visible = result['point_visible'][i][q]
            point = result['tracks_px'][i][q]
            comparisons.append({'query_index': q, 'track_id': link['track_id'],
                                'point_model_visible': visible, 'point_px': point,
                                'detector_observation': detector,
                                'point_in_same_initial_track_box':
                                    contains(detector['bbox_xyxy'], point) if visible and detector else None})
        records.append({'frame_index': row['frame_index'], 'time_s': row['time_s'], 'comparisons': comparisons})
    summary = []
    for link in links:
        samples = [r['comparisons'][link['query_index']] for r in records]
        summary.append({**link, 'common_frames': len(samples),
                        'detector_track_present': sum(s['detector_observation'] is not None for s in samples),
                        'both_visible': sum(s['point_in_same_initial_track_box'] is not None for s in samples),
                        'point_outside_original_track_box': sum(s['point_in_same_initial_track_box'] is False for s in samples)})
        q = link['query_index']
        summary[-1]['detector_missing_sample_runs'] = (sampled_runs(
            records, lambda r: r['comparisons'][q]['detector_observation'] is None)
            if link['track_id'] is not None else None)
        summary[-1]['detector_availability_status'] = ('compared_to_unique_initial_track'
            if link['track_id'] is not None else 'initial_association_unresolved_not_detector_absence')
        summary[-1]['point_hidden_sample_runs'] = sampled_runs(
            records, lambda r: not r['comparisons'][q]['point_model_visible'])
        summary[-1]['point_disagreement_sample_runs'] = sampled_runs(
            records, lambda r: r['comparisons'][q]['point_in_same_initial_track_box'] is False)
        summary[-1]['run_semantics'] = 'Consecutive compared samples, not continuously observed time or physical identity switches'
    return {'development': True, 'predictions_modified': False, 'summary': summary, 'frames': records,
            'scope': 'Component agreement, not physical identity accuracy. A box can be wrong, duplicated or cover multiple stones. Missing observations remain missing.',
            'automatic_reassignment': False}


def run(result_path, public_run, output):
    result_path, public_run, output = map(Path, (result_path, public_run, output))
    if output.exists():
        raise ValueError('Preserve previous comparison')
    result = json.loads(result_path.read_text())
    protocol = json.loads((public_run/'protocol.json').read_text())
    if result['provenance']['source_sha256'] != protocol['source_sha256']:
        raise ValueError('Source hashes differ')
    path = public_run/'observations.jsonl'
    with path.open() as stream:
        comparison = compare(result, (json.loads(line) for line in stream))
    comparison['source_sha256'] = protocol['source_sha256']
    comparison['input_hashes'] = {}
    for p in [result_path, path, Path(__file__)]:
        with p.open('rb') as stream:
            comparison['input_hashes'][str(p.resolve())] = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.write_text(json.dumps(comparison, indent=2))
    return comparison['summary']


def project_comparison(comparison, board_rows, source_size, *, height_m):
    """Use identical saved geometry for both components, without filling gaps.

    Detector box centres and tracked point features need not be the same physical
    feature. Distances between them are disagreement, never ground-truth error.
    """
    from prototype.saved_board_geometry import replay
    boards = iter(board_rows)
    current = next(boards, None)
    records = []
    for row in comparison['frames']:
        while current is not None and current['frame_index'] < row['frame_index']:
            current = next(boards, None)
        if current is None or current['frame_index'] != row['frame_index'] or current['time_s'] != row['time_s']:
            raise ValueError('Exact source-frame board geometry required')
        queries = []
        for query in row['comparisons']:
            pair = {}
            for name, pixel in [('point', query['point_px'] if query['point_model_visible'] else None),
                                ('detector', query['detector_observation']['pixel']
                                 if query['detector_observation'] else None)]:
                if pixel is None:
                    pair[name] = None
                    continue
                panel = 'left' if pixel[0] < source_size[0]/2 else 'right'
                pair[name] = {'panel': panel, **replay(current['boards'][panel], [pixel],
                                                     source_size, height_m=height_m)[0]}
            queries.append({'query_index': query['query_index'], 'track_id': query['track_id'], **pair})
        records.append({'frame_index': row['frame_index'], 'time_s': row['time_s'], 'comparisons': queries})
    return {'frames': records, 'height_m': height_m, 'predictions_modified': False,
            'physical_accuracy_verified': False,
            'method': 'Both component positions replayed through the same saved per-frame board geometry',
            'limitations': ['Detector centre and tracked point may represent different features.',
                           'Local tracker IDs do not certify physical identity.',
                           'Absent observations and unavailable geometry are retained; no interpolation.']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--result', required=True)
    p.add_argument('--run', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    print(json.dumps(run(a.result, a.run, a.output)))
