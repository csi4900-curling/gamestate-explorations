"""One split-screen trajectory path; no recording-specific dispatch or rules.

Consolidation v1 preserves departure projection and the final split receiving
algorithm. It eliminates intermediate receiving passes whose accepted outputs
were discarded. This is not yet continuous whole-rink or persistent-ID tracking.
"""
from pathlib import Path
import json
import time

from cache_contract import file_sha256
from cross_view import rink_position

VERSION = 'split-consolidated-v1'


def complete_split(video, events_path, output, *, base=None):
    from scripts.complete_throw_trajectories import complete
    from split_receiving_trajectory import complete_receiving

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    profile = {'version': VERSION, 'scope': 'Trajectory stages only; excludes routing and proposal subprocesses.', 'stages': []}

    def stage(name, operation):
        wall, cpu = time.perf_counter(), time.process_time()
        value = operation()
        profile['stages'].append({'stage': name, 'wall_seconds': time.perf_counter()-wall, 'process_cpu_seconds': time.process_time()-cpu})
        return value

    if base is None:
        base = output.parent / 'departure-evidence' / 'aggregate.json'
        stage('departure_geometry', lambda: complete(video, events_path, base, integrated=False))
    else:
        profile['base_reused'] = str(base)
    data = json.loads(Path(base).read_text())
    if data['context']['source_sha256'] != file_sha256(video) or data['context']['events_sha256'] != file_sha256(events_path):
        raise ValueError('Departure evidence does not match video/events')
    # Same left-side coordinate conversion formerly done inside complete_integrated.
    for event in data['events']:
        if 'observed_track_points' not in event['event_prediction']:
            raise ValueError('Split path requires split-screen departure observations')
        event['motion_hypotheses'] = []
        event['cross_view_links'] = []
        for index, segment in enumerate(event['segments']):
            if segment['camera'] != 'left_split':
                raise ValueError('Unexpected non-departure base segment')
            segment.update(role='departure', associated=True, segment_id=f"{event['candidate_id']}:{index}")
            for sample in segment['geometry_samples']:
                sample['rink_position_m'] = rink_position(sample['top_view_m'], 'departure') if sample['top_view_m'] is not None else None
    data['context']['split_pipeline_sha256'] = file_sha256(__file__)
    prepared = output.parent / 'split-departure.json'
    prepared.write_text(json.dumps(data, indent=2)+'\n')
    result = stage('receiving_geometry_tracking_association', lambda: complete_receiving(video, prepared, output))
    profile['source_sha256'] = data['context']['source_sha256']
    profile['output_sha256'] = file_sha256(output)
    profile['pipeline_sha256'] = file_sha256(__file__)
    (output.parent/'trajectory-stage-timing.json').write_text(json.dumps(profile, indent=2)+'\n')
    return result
