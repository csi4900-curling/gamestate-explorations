"""Repair the old motion-oriented common-rink reflection without rerunning detection.

Preserves every camera-local homography, source point and review label. Archives
original outputs and records the exact correction code and changed segments.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'prototype'))
from cache_contract import file_sha256
from integrated_trajectory import orient_image_aligned_samples


def correct(path):
    data = json.loads(path.read_text())
    changed = []
    for event in data['events']:
        for segment in event['segments']:
            if segment.get('orientation_status') != 'provisional_from_camera_role_and_observed_longitudinal_motion':
                continue
            segment['orientation_status'] = orient_image_aligned_samples(segment['geometry_samples'], segment['role'])
            changed.append(segment['segment_id'])
    if not changed:
        return
    archive = path.with_name('aggregate-before-orientation-fix.json')
    if archive.exists():
        raise ValueError('Archive exists; refusing to overwrite')
    archive.write_bytes(path.read_bytes())
    data['context']['orientation_correction'] = {
        'upstream_sha256': file_sha256(archive),
        'upstream_file': archive.name,
        'code_sha256': {str(p.relative_to(ROOT)): file_sha256(p) for p in [Path(__file__).resolve(), ROOT/'prototype/integrated_trajectory.py']},
        'changed_segments': changed,
        'reason': 'Reverse lateral axis together with longitudinal display rotation; previous mapping mirrored image-aligned 2022 geometry.',
        'unchanged': 'Event decisions, pixel tracks, camera-local homographies and source-point review labels.',
    }
    path.write_text(json.dumps(data, indent=2) + '\n')
    print(f'{path}: corrected {len(changed)} segment orientations')


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        correct(Path(arg).resolve())
