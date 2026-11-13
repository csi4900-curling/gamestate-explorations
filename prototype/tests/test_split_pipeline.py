"""Behavioral contracts for the consolidated split path, independent of recordings."""
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cache_contract import file_sha256
from split_pipeline import complete_split


def fixture(tmp_path):
    video = tmp_path / 'video.bin'
    video.write_bytes(b'source-identity-only')
    events = tmp_path / 'events.json'
    events.write_text('{}')
    base = tmp_path / 'base.json'
    data = {'context': {'source_sha256': file_sha256(video), 'events_sha256': file_sha256(events)}, 'events': [{
        'candidate_id': 'E1', 'event_prediction': {'observed_track_points': []},
        'segments': [{'camera': 'left_split', 'pixel_points': [{'time_s': 1, 'pixel': [20, 30]}], 'geometry_samples': [
            {'time_s': 1, 'top_view_m': [0.2, -7]}, {'time_s': 2, 'top_view_m': None}]}]}]}
    base.write_text(json.dumps(data))
    return video, events, base, data


def test_single_receiving_stage_preserves_observations_and_missing_geometry(tmp_path, monkeypatch):
    import split_receiving_trajectory
    import integrated_trajectory
    import scripts.extend_registered_trajectories as extension
    video, events, base, original = fixture(tmp_path)
    calls = []

    def forbidden(*args, **kwargs):
        raise AssertionError('Discarded receiving stage must not run')

    def receiving(video_path, prepared, output):
        data = json.loads(prepared.read_text())
        calls.append(data)
        output.write_text(json.dumps(data))
        return data

    monkeypatch.setattr(integrated_trajectory, 'complete_integrated', forbidden)
    monkeypatch.setattr(extension, 'extend', forbidden)
    monkeypatch.setattr(split_receiving_trajectory, 'complete_receiving', receiving)
    output = tmp_path / 'output' / 'aggregate.json'
    result = complete_split(video, events, output, base=base)
    assert len(calls) == 1
    segment = result['events'][0]['segments'][0]
    assert segment['pixel_points'] == original['events'][0]['segments'][0]['pixel_points']
    assert segment['geometry_samples'][0]['rink_position_m'] == [0.2, 7.0]
    assert segment['geometry_samples'][1]['rink_position_m'] is None
    assert json.loads(base.read_text()) == original
    timing = json.loads((output.parent/'trajectory-stage-timing.json').read_text())
    assert timing['output_sha256'] == file_sha256(output)
    assert [x['stage'] for x in timing['stages']] == ['receiving_geometry_tracking_association']


def test_changed_video_cannot_reuse_departure_geometry(tmp_path):
    video, events, base, _ = fixture(tmp_path)
    video.write_bytes(b'another recording')
    with pytest.raises(ValueError, match='does not match'):
        complete_split(video, events, tmp_path/'out/aggregate.json', base=base)


def test_non_split_evidence_rejected_in_split_path(tmp_path):
    video, events, base, data = fixture(tmp_path)
    data['events'][0]['event_prediction'] = {'shot_id': 'S1'}
    base.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='split-screen departure'):
        complete_split(video, events, tmp_path/'out/aggregate.json', base=base)
