"""Join saved event crossings with per-frame detector and board observations."""
from itertools import zip_longest


def make_segment(segment_id, track_id, panel, points, foreign, roles, sample_step_frames, sample_step_s=None):
    geometry = [{'time_s': s['time_s'], 'pixel': s['pixel'],
                 'top_view_m': s['stone']['ice_plane_local_m'],
                 'conditional_height_adjusted_position_m': s['stone']['height_adjusted_local_m'],
                 'homography_source_pixels_to_local_metres': s['geometry']['homography_normalized_pixels_to_local_metres'],
                 'status': s['geometry']['registration']['status'], 'calibration': s['geometry']['registration'],
                 'body_point_support': s['stone'].get('body_point_support'),
                 'localization': s['stone'].get('height_correction'),
                 'rink_position_m': None} for s in points]
    pixel_points = [{k: s[k] for k in ('time_s', 'frame_index', 'pixel', 'confidence')} for s in points]
    return {'segment_id': segment_id, 'camera': panel + '_split', 'role': roles.get(panel, 'unassigned'), 'colour': None,
            'point_kind': 'body_box_center', 'pixel_points': pixel_points, 'geometry_samples': geometry,
            'associated': False, 'physical_identity_verified': False, 'camera_cut_times_s': [],
            'tracker_id': track_id, 'point_coordinate_system': 'normalized full-source 640x360',
            'sample_step_s': sample_step_s,
            'detection_gaps': [{'after_s': a['time_s'], 'before_s': b['time_s']}
                               for a, b in zip(points, points[1:]) if b['frame_index'] - a['frame_index'] > sample_step_frames],
            'foreign_panel_observations': foreign,
            'role_status': 'Configured broadcast camera role, not physical-end identity' if panel in roles else 'Unassigned camera role; physical throwing end unverified'}


def assemble(events, observations, boards, source_size, *, camera_roles=None):
    width, height = source_size
    sample_step_s = events['sample_step_frames'] / events['source_fps'] if events.get('source_fps') else None
    roles = camera_roles or {}
    if set(roles) - {'left', 'right'} or any(v not in ('departure', 'receiving', 'unassigned') for v in roles.values()):
        raise ValueError('Invalid configured camera roles')
    wanted = {e['track_id'] for e in events['events']}
    samples = {k: [] for k in wanted}
    for raw, state in zip_longest(observations, boards):
        if raw is None or state is None or raw['frame_index'] != state['frame_index'] or raw['time_s'] != state['time_s']:
            raise ValueError('Detector/board streams do not share source frames')
        for obs in raw['tracked_observations']:
            key = obs['track_id']
            if key not in wanted:
                continue
            panel = 'left' if obs['point_normalized'][0] < .5 else 'right'
            board = state['boards'][panel]
            matching = [s for s in board['stones'] if s['tracker_id'] == key and s['pixel'] == obs['pixel']]
            if len(matching) != 1:
                raise ValueError('Tracker observation has no unique matching board observation')
            stone = matching[0]
            samples[key].append({'time_s': raw['time_s'], 'frame_index': raw['frame_index'], 'panel': panel,
                                 'pixel': [obs['pixel'][0] * 640 / width, obs['pixel'][1] * 360 / height],
                                 'confidence': obs['confidence'], 'geometry': board, 'stone': stone})
    result = []
    for e in events['events']:
        panel = 'left' if e['crossing_point_normalized'][0] < .5 else 'right'
        points = [s for s in samples[e['track_id']] if s['panel'] == panel]
        foreign = sum(s['panel'] != panel for s in samples[e['track_id']])
        segment = make_segment(e['id'] + ':primary', e['track_id'], panel, points, foreign, roles,
                               events['sample_step_frames'], sample_step_s)
        pixel_points = segment['pixel_points']
        result.append({'candidate_id': e['id'], 'event_prediction': {**e, 'observed_track_points': pixel_points},
                       'segments': [segment], 'cross_view_links': [],
                       'failure_reasons': ['cross_view_identity_unresolved'] + (
                           ['tracker_label_observed_in_both_panels'] if foreign else []),
                       'other_camera_evidence': 'Retained in match-observations.jsonl, not assigned to this stone'})
    return {'schema_version': 'learned-primary-track-bridge-v1', 'source_interval_s': events['source_interval_s'],
            'context': {'source_sha256': events['source_sha256']}, 'events': result,
            'scope': 'Typed primary crossing tracks; physical identity and metric accuracy remain unverified',
            'physical_identity_verified': False, 'handoff_development_enabled': False}
