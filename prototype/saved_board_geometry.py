"""Replay recorded camera geometry on alternative detections of the same frame.

No calibration fit, camera registration, temporal propagation or identity rule.
Conditional camera centre and feature height must already be recorded. Missing
height geometry remains missing. Reuses the existing projection implementation.
"""
import numpy as np
import argparse
import hashlib
import json
from pathlib import Path
import time


def render_review(projected_run, detector_run, video, output):
    """Render projected observations with complete bounds and retained history."""
    import shutil
    from prototype.match_observation_report import render
    projected_run, detector_run, output = map(Path, (projected_run, detector_run, output))
    if output.exists():
        raise ValueError('Preserve previous viewer output')
    summary = json.loads((projected_run/'summary.json').read_text())
    events = json.loads((detector_run/'events.json').read_text())
    if summary['source_sha256'] != events['source_sha256']:
        raise ValueError('Projection/event source mismatch')
    with Path(video).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != events['source_sha256']:
            raise ValueError('Viewer source video differs')
    output.mkdir(parents=True)
    shutil.copyfile(projected_run/'match-observations.jsonl', output/'match-observations.jsonl')
    shutil.copyfile(detector_run/'events.json', output/'events.json')
    shutil.copyfile(projected_run/'summary.json', output/'match-observation-summary.json')
    (output/'match-observation-protocol.json').write_text(json.dumps({
        'development': True, 'projection': summary, 'detector_events': events,
        'presentation_only_change': 'Complete chunk bounds at equal metric scales; retain history without current detections',
        'physical_identity_verified': False}, indent=2))
    render(output, video, events['events'])
    asset = Path(__file__).with_name('match_board_plot.js')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Development tracking review</title><a href="match-observations.html">Source video, projected observations and tracker histories</a>')
    (output/'presentation-protocol.json').write_text(json.dumps({
        'source_sha256': events['source_sha256'], 'prediction_changes': False,
        'renderer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'plot_asset_sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
        'shared_public_plot_renderer': True,
        'layout_scope': 'One-minute data chunk; future observations affect bounds only, not displayed path'}, indent=2))
    return output/'match-observations.html'

from prototype.match_observation import project
from prototype.body_localization import height_correct


def replay(board, pixels, source_size, *, height_m):
    width, height = source_size
    if width <= 0 or height <= 0 or not np.isfinite(height_m) or height_m < 0:
        raise ValueError('Invalid source dimensions or feature height')
    H = board.get('homography_normalized_pixels_to_local_metres')
    if H is None:
        return [{'ice_plane_local_m': None, 'height_adjusted_local_m': None,
                 'status': 'missing_saved_homography'} for _ in pixels]
    H = np.asarray(H, dtype=float)
    centres = [s.get('height_correction', {}).get('camera', {}).get('camera_centre_m')
               for s in board['stones']]
    centres = [c for c in centres if c is not None]
    if any(c != centres[0] for c in centres[1:]):
        raise ValueError('Conflicting recorded camera priors in one board')
    camera = None
    if centres:
        centre = np.asarray(centres[0], dtype=float)
        if not np.isfinite(centre).all() or centre[2] <= 0:
            raise ValueError('Invalid recorded camera centre')
        plane = np.linalg.inv(H)
        # Camera projection annihilates its own centre: M[Cx,Cy,1] + Cz*v = 0.
        # Recover the existing vertical projection column, not a new camera fit.
        vertical = -(plane @ np.array([centre[0], centre[1], 1.])) / centre[2]
        camera = {'plane': plane, 'vertical': vertical}
    rows = []
    for pixel in pixels:
        normalized = np.asarray(pixel, dtype=float) * [640/width, 360/height]
        raw = project(H, [normalized])[0]
        adjusted = height_correct(camera, normalized, height_m) if camera is not None else None
        if not np.isfinite(raw).all() or (adjusted is not None and not np.isfinite(adjusted).all()):
            raise ValueError('Undefined projection for alternative detection')
        rows.append({'ice_plane_local_m': raw.tolist(),
                     'height_adjusted_local_m': adjusted.tolist() if adjusted is not None else None,
                     'status': 'replayed_conditional_camera' if camera is not None else 'missing_recorded_height_camera',
                     'height_m': height_m, 'physical_accuracy_verified': False,
                     'sensitivity_m': None})
    return rows


def replay_observations(observations, boards, source_size, height_m):
    """Join exact source frames; never borrow calibration from a nearby frame."""
    boards = iter(boards)
    current = next(boards, None)
    previous_frame = -1
    for row in observations:
        frame = row['frame_index']
        if frame <= previous_frame:
            raise ValueError('Detection frames must be strictly increasing')
        previous_frame = frame
        while current is not None and current['frame_index'] < frame:
            following = next(boards, None)
            if following is not None and following['frame_index'] <= current['frame_index']:
                raise ValueError('Geometry frames must be strictly increasing')
            current = following
        if current is None or current['frame_index'] != frame or current['time_s'] != row['time_s']:
            raise ValueError('No exact source-frame geometry record')
        result = dict(current)
        result['boards'] = {}
        for panel in ['left', 'right']:
            original = current['boards'][panel]
            selected = [(i, d) for i, d in enumerate(row['detections'])
                        if (d['pixel'][0] < source_size[0]/2) == (panel == 'left')]
            projected = replay(original, [d['pixel'] for _, d in selected], source_size, height_m=height_m)
            stones = []
            for (index, detection), projection in zip(selected, projected):
                ids = [t['track_id'] for t in row['tracked_observations'] if t['detection_index'] == index]
                stones.append({**detection, **projection,
                               'tracker_id': ids[0] if len(ids) == 1 else None,
                               'physical_identity': None, 'team': None,
                               'height_correction': {'status': projection['status'], 'height_m': height_m,
                                                     'sensitivity_m': None}})
            result['boards'][panel] = {**original, 'stones': stones, 'complete_board_verified': False}
        result['geometry_replayed_from_exact_frame'] = True
        result['physical_identity_verified'] = False
        yield result


def run(detector_run, geometry_run, output):
    detector_run, geometry_run, output = map(Path, (detector_run, geometry_run, output))
    detections = json.loads((detector_run/'events.json').read_text())
    geometry = json.loads((geometry_run/'events.json').read_text())
    if detections['status'] != 'development_complete_event_stage' or geometry['status'] != 'development_complete_event_stage':
        raise ValueError('Finished event scans required')
    if detections['source_sha256'] != geometry['source_sha256'] or detections['source_size_px'] != geometry['source_size_px']:
        raise ValueError('Source identity or dimensions differ')
    if output.exists():
        raise ValueError('Preserve previous projection output')
    from prototype.public_event_audit import verify_scan
    for directory, events in [(detector_run, detections), (geometry_run, geometry)]:
        with (directory/'observations.jsonl').open() as stream:
            verify_scan(events, (json.loads(line) for line in stream))
    config = json.loads((geometry_run/'match-observation-protocol.json').read_text())['config']
    height_m = config['feature_heights_m']['body_box_center']
    output.mkdir(parents=True)
    started = time.perf_counter()
    count = projected = 0
    with (detector_run/'observations.jsonl').open() as ds, (geometry_run/'match-observations.jsonl').open() as gs, (output/'match-observations.jsonl').open('w') as target:
        for row in replay_observations((json.loads(x) for x in ds), (json.loads(x) for x in gs), detections['source_size_px'], height_m):
            target.write(json.dumps(row, allow_nan=False)+'\n')
            count += 1
            projected += sum(s['height_adjusted_local_m'] is not None for b in row['boards'].values() for s in b['stones'])
    if count != detections['sampled_frames']:
        raise ValueError('Incomplete detection observations')
    summary = {'development': True, 'source_sha256': detections['source_sha256'],
               'frames': count, 'height_projected_observations': projected,
               'wall_seconds': time.perf_counter()-started,
               'new_calibration_fits': 0, 'new_image_registrations': 0,
               'physical_identity_verified': False, 'physical_geometry_accuracy_verified': False,
               'scope': 'Saved per-frame camera geometry applied to alternative detections; source score evidence retained. No physical-end identity, stone identity or in-play inference.',
               'inputs': {}}
    for path in [detector_run/'events.json', detector_run/'observations.jsonl', geometry_run/'events.json', geometry_run/'match-observations.jsonl', geometry_run/'match-observation-protocol.json', Path(__file__)]:
        with path.open('rb') as stream:
            summary['inputs'][str(path.resolve())] = hashlib.file_digest(stream, 'sha256').hexdigest()
    (output/'summary.json').write_text(json.dumps(summary, indent=2))
    (output/'adapter.py').write_bytes(Path(__file__).read_bytes())
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--detections', required=True)
    p.add_argument('--geometry', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    print(json.dumps(run(args.detections, args.geometry, args.output)))
