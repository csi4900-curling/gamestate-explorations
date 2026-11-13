"""Describe saved public-run output and runtime without treating coverage as accuracy."""
import hashlib
import json
from pathlib import Path


def profile(directory):
    directory = Path(directory)
    evidence = {}

    def read(name):
        path = directory / name
        data = path.read_bytes()
        evidence[name] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    events = read('events.json')
    boards = read('match-observation-summary.json')
    dense = read('two-view-tracking/result.json')
    if events['source_sha256'] != dense['source_sha256']:
        raise ValueError('Event and dense reports refer to different sources')
    segments = []
    fresh_model_s = reused_original_model_s = decode_s = projection_s = 0.0
    for event in dense['events']:
        for segment in event['segments']:
            row = {key: segment.get(key) for key in ('segment_id', 'camera', 'role', 'status', 'reason')}
            row['candidate_id'] = event['candidate_id']
            segments.append(row)
            if segment['status'] != 'tracked':
                continue
            result = read('two-view-tracking/' + segment['result'])
            if result['provenance']['source_sha256'] != events['source_sha256']:
                raise ValueError('Segment source differs from public run')
            model = result['model']
            reused = 'reused_result_sha256' in model
            seconds = model['model_load_wall_s'] + model['inference_wall_s']
            if reused:
                reused_original_model_s += seconds
            else:
                fresh_model_s += seconds
            decode_s += result['provenance']['decode_and_preparation_wall_s']
            projection = result.get('projection') or {}
            projection_s += projection.get('wall_seconds', 0)
            visible = result['point_visible']
            samples = projection.get('samples', [])
            row.update(sampled_frames=len(result['times_s']),
                       primary_model_visible_frames=sum(bool(v and v[0]) for v in visible),
                       primary_raw_projected_samples=sum(bool(s.get('points_camera_local_m') and s['points_camera_local_m'][0] is not None) for s in samples),
                       primary_height_projected_samples=sum(bool(s.get('height_adjusted_points_camera_local_m') and s['height_adjusted_points_camera_local_m'][0] is not None) for s in samples),
                       reused_model_predictions=reused,
                       new_geometry_fits=projection.get('new_calibration_fits'),
                       registration_attempts=projection.get('camera_registration_attempts'))
    path = directory / 'match-observations.jsonl'
    digest = hashlib.sha256()
    counts = {'board_samples': 0, 'samples_with_end_number': 0,
              'samples_with_current_points': 0, 'stone_observations': 0,
              'stones_with_team': 0, 'stones_with_physical_identity': 0,
              'stones_with_height_projection': 0}
    confidence_count = 0
    confidence_sum = 0.0
    confidence_min = confidence_max = None
    with path.open('rb') as stream:
        for line in stream:
            digest.update(line)
            state = json.loads(line)
            counts['board_samples'] += 1
            counts['samples_with_end_number'] += state.get('current_end') is not None
            counts['samples_with_current_points'] += state.get('current_points_from_stones') is not None
            for board in state['boards'].values():
                for stone in board['stones']:
                    counts['stone_observations'] += 1
                    counts['stones_with_team'] += stone.get('team') is not None
                    counts['stones_with_physical_identity'] += stone.get('physical_identity') is not None
                    counts['stones_with_height_projection'] += stone.get('height_adjusted_local_m') is not None
                    value = stone.get('confidence')
                    if value is not None:
                        confidence_count += 1
                        confidence_sum += value
                        confidence_min = value if confidence_min is None else min(value, confidence_min)
                        confidence_max = value if confidence_max is None else max(value, confidence_max)
    evidence['match-observations.jsonl'] = digest.hexdigest()
    snapshot_counts={'snapshot_entries':0,'observed_snapshots':0,'source_crops_with_colour_ranking':0,
                     'saved_board_boxes_with_colour_ranking':0,'unknown_or_invalid_colour_crops':0}
    colour_prediction_s=0.
    if (directory/'two-view-tracking/end-views.json').exists():
        for snapshot in read('two-view-tracking/end-views.json'):
            snapshot_counts['snapshot_entries']+=1
            snapshot_counts['observed_snapshots']+=snapshot.get('status')=='observed'
            source_rows=(snapshot.get('colour_observations') or {}).get('predictions',[])
            snapshot_boards=(snapshot.get('both_panel_observations') or {}).get('boards',{})
            board_rows=[s['colour_evidence'] for b in snapshot_boards.values() for s in b['stones'] if s.get('colour_evidence')]
            for key,rows in [('source_crops_with_colour_ranking',source_rows),('saved_board_boxes_with_colour_ranking',board_rows)]:
                snapshot_counts[key]+=sum(r.get('prediction') is not None for r in rows)
                snapshot_counts['unknown_or_invalid_colour_crops']+=sum(r.get('prediction') is None for r in rows)
                colour_prediction_s+=sum(r.get('wall_seconds',0.) for r in rows)
    return {
        'end_snapshot_colour_availability':snapshot_counts,
        'colour_semantics':'Crop rankings are not unique stone counts, verified colours, teams, or calibrated probabilities. Source and saved-board crop sets can differ and are counted separately.',
        'source_sha256': events['source_sha256'], 'source_interval_s': events['source_interval_s'],
        'scope': 'Saved-output availability and recorded timers; not event, identity, geometry or state accuracy',
        'event_candidates': len(events['events']), 'dense_summary': dense['summary'], 'segments': segments,
        'state_availability': counts,
        'stone_detector_confidence': {'count': confidence_count, 'mean': confidence_sum/confidence_count if confidence_count else None,
                                      'min': confidence_min, 'max': confidence_max, 'calibrated_probability': False},
        'runtime_seconds': {'event_board_scan_wall': events['wall_seconds'],
            'scan_nested_detector_fresh': events['detector_seconds'],
            'scan_nested_association': events['association_seconds'],
            'scan_nested_geometry': boards['geometry_seconds'], 'scan_nested_OCR': boards['ocr_seconds'],
            'dense_wall_before_final_viewer_and_board_export': dense['wall_seconds'],
            'dense_nested_model_fresh': fresh_model_s, 'dense_nested_decode_and_preparation': decode_s,
            'dense_nested_projection': projection_s,
            'dense_nested_colour_model_load_and_text_encoding': (dense.get('stone_colour_model') or {}).get('load_and_text_encoding_wall_s',0.),
            'final_snapshot_colour_prediction_outside_dense_timer': colour_prediction_s,
            'historical_detector_time_for_replayed_frames_not_current_runtime': events.get('prior_detector_seconds_for_reused_frames', 0),
            'historical_model_time_for_replayed_tracks_not_current_runtime': reused_original_model_s},
        'runtime_note': 'Nested timers overlap stage wall time; do not sum them. Stage timers omit launcher, bridge and final viewer/board export overhead. Failed-segment work may be absent from nested totals. Whole-process duration requires the external launcher/service clock.',
        'reused_detector_frames': events.get('reused_detector_frames', 0),
        'geometry': boards.get('geometry', {}), 'evidence_sha256': evidence,
        'profiler_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Preserve previous profile')
    result = profile(args.run)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
