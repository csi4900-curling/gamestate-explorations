"""Persistent, explicitly inferred match totals from saved upstream OCR.

Reuses score_sequence's maximum-support chronology. No stone counts or event
counts become match points. Future evidence selects the offline sequence, but
values are never displayed before their first supporting observation.
"""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import re

from prototype.detection_cache import digest
from prototype.score_sequence import infer


def build(observations):
    observations = Path(observations)
    rows = [json.loads(line) for line in observations.open()]
    result = infer(rows)
    statuses = {team: dict(Counter(item['status'] for item in analysis['observations']))
                for team, analysis in result['analyses'].items()}
    by_time = {row['time_s']: row for row in rows}
    for row in result['timeline']:
        row['raw_totals'] = {team: value['value'] for team, value in by_time[row['time_s']]['totals'].items()}
    changes = []
    previous = None
    for row in result['timeline']:
        values = {team: value['value'] for team, value in row['totals'].items()}
        if values != previous:
            changes.append({'time_s': row['time_s'], 'totals': values})
            previous = values
    return {
        'status': 'offline_inferred_from_scoreboard_OCR',
        'method': result['method'], 'assumption': result['assumption'],
        'limitations': result['limitations'], 'independent_score_accuracy_measured': False,
        'future_observations_used_for_sequence_selection': True,
        'source_interval_s': [rows[0]['time_s'], rows[-1]['time_s']] if rows else None,
        'source_observations_sha256': digest(observations),
        'code_sha256': {'score_tracking.py': digest(__file__),
                        'score_sequence.py': digest(Path(__file__).with_name('score_sequence.py'))},
        'observation_classifications': statuses,
        'conflicts': {team: [item for item in analysis['observations']
                             if item['status'] != 'required_by_all_maximum_support_sequences']
                      for team, analysis in result['analyses'].items()},
        'changes': changes, 'timeline': result['timeline'],
    }


def upgrade(viewer, observations, video):
    """Upgrade an existing viewer through the shared renderer; preserve old files."""
    from prototype.post_throw_state import render
    viewer, observations = Path(viewer), Path(observations)
    payload = json.loads((viewer / 'states.json').read_text())
    protocol = json.loads((observations.parent / 'protocol.json').read_text())
    if protocol['source_sha256'] != payload['source_sha256']:
        raise ValueError('Score observations and viewer must belong to the same source')
    source = re.search(r'<video\b[^>]*\bsrc="([^"]+)"', (viewer / 'index.html').read_text())
    if not source:
        raise ValueError('Viewer video URL missing')
    before = {}
    for name in ('index.html', 'states.json', 'states.js'):
        path = viewer / name
        backup = viewer / (name + '.before-score-tracking')
        if backup.exists():
            raise ValueError('Prior score upgrade exists; preserve it')
        before[name] = digest(path)
    tracking = build(observations)
    for name in before:
        (viewer / (name + '.before-score-tracking')).write_bytes((viewer / name).read_bytes())
    payload['score_tracking'] = tracking
    render(viewer, video, payload, payload.get('provenance', {}).get('config', {}),
           video_src=html.unescape(source.group(1)))
    record = {'before_sha256': before, 'after_sha256': {name: digest(viewer / name) for name in before},
              'score_observations_sha256': digest(observations),
              'detections_geometry_and_board_timeline_unchanged': True,
              'inference_rerun': False, 'score_accuracy_measured': False}
    (viewer / 'score-tracking-upgrade.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--viewer', required=True)
    parser.add_argument('--observations', required=True)
    parser.add_argument('--video', required=True)
    args = parser.parse_args()
    print(json.dumps(upgrade(args.viewer, args.observations, args.video)))
