"""Evaluate saved rink homographies against explicit source-only annotations.

No calibration fitting, stone height correction, or inference changes occur.
Missing exact source frames and occluded references remain in the denominator.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def project_box(H, point, bounds, source_size, normalized_size):
    x0, y0, x1, y1 = bounds
    if not (0 <= x0 <= point[0] <= x1 < source_size[0] and
            0 <= y0 <= point[1] <= y1 < source_size[1]):
        raise ValueError('Invalid source annotation bounds')
    points = np.array([point, [x0, y0], [x0, y1], [x1, y0], [x1, y1]], dtype=float)
    points *= np.array(normalized_size)/np.array(source_size)
    homogeneous = np.column_stack([points, np.ones(len(points))]) @ np.asarray(H).T
    denominator = homogeneous[:, 2]
    if not (np.all(denominator > 0) or np.all(denominator < 0)):
        raise ValueError('Annotation crosses homography horizon')
    world = homogeneous[:, :2]/denominator[:, None]
    if not np.isfinite(world).all():
        raise ValueError('Nonfinite projected annotation')
    return world[0], world[1:].min(axis=0), world[1:].max(axis=0)


def interval_distance(value, interval):
    lo, hi = interval
    return max(lo-value, 0., value-hi)


def evaluate(references, observations):
    wanted = {f['frame_index'] for f in references['frames']}
    selected = {}
    for row in observations:
        if row['frame_index'] in wanted:
            if row['frame_index'] in selected:
                raise ValueError('Duplicate source frame in observations')
            selected[row['frame_index']] = row
    results = []
    for frame in references['frames']:
        observation = selected.get(frame['frame_index'])
        for mark in frame['landmarks']:
            entry = dict(frame_index=frame['frame_index'], panel=mark['panel'],
                         landmark=mark['landmark'], status=mark['status'])
            results.append(entry)
            if mark['status'] != 'annotated':
                continue
            if observation is None:
                entry['status'] = 'exact_source_frame_not_available'
                continue
            H = observation['boards'][mark['panel']].get('homography_normalized_pixels_to_local_metres')
            if H is None:
                entry['status'] = 'geometry_unavailable'
                continue
            try:
                point, low, high = project_box(H, mark['pixel_xy'], mark['pixel_bounds_xyxy'],
                    references['source_size_px'], references['homography_input_size_px'])
            except ValueError as exc:
                entry.update(status='invalid_projection', reason=str(exc))
                continue
            if 'target_xy_m' in mark:
                target = np.array(mark['target_xy_m'])
                error = float(np.linalg.norm(point-target))
                lower = float(np.linalg.norm(np.maximum(np.maximum(low-target, target-high), 0)))
                upper = float(np.linalg.norm(np.maximum(abs(low-target), abs(high-target))))
                metric = 'euclidean_origin_error'
            else:
                target = mark['target_y_interval_m']
                error = interval_distance(point[1], target)
                lower = max(target[0]-high[1], low[1]-target[1], 0.)
                upper = max(interval_distance(low[1], target), interval_distance(high[1], target))
                metric = 'longitudinal_distance_outside_painted_band'
            entry.update(status='evaluated', projected_xy_m=point.tolist(), metric=metric,
                         nominal_error_m=error, conservative_annotation_box_error_bounds_m=[lower, upper],
                         bounds_are_statistical_confidence=False)
    return dict(scope=references['purpose'], reviewer=references['reviewer'],
                results=results, full_trajectory_accuracy_measured=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    references = json.loads(args.references.read_text())
    protocol = json.loads((args.run/'protocol.json').read_text())
    if protocol['source_sha256'] != references['source_sha256'] or protocol['source_size_px'] != references['source_size_px']:
        raise ValueError('Reference source differs from public run')
    with (args.run/'match-observations.jsonl').open() as stream:
        result = evaluate(references, (json.loads(line) for line in stream))
    result['reference_sha256'] = hashlib.sha256(args.references.read_bytes()).hexdigest()
    result['run'] = str(args.run.resolve())
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)


if __name__ == '__main__':
    main()
