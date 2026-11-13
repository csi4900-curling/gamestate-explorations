import json
import pytest
from prototype.camera_motion_role_comparison import compare_handoffs
from prototype.detection_cache import digest


def fixture(tmp_path, candidate='receiving'):
    reference = tmp_path/'reference'; reference.mkdir()
    comparison = tmp_path/'comparison'; comparison.mkdir()
    (reference/'events.json').write_text(json.dumps({'events': [{'id': 'A', 'crossing_time_s': 10}],
                                                    'source_interval_s': [0, 20]}))
    aggregate = {'events': [{'candidate_id': 'A', 'segments': [{'role_evidence': {
        'role': 'departure', 'panel': 'left'}}], 'handoff_hypothesis': {
            'status': 'unresolved', 'candidates': []}}],
        'provenance': {'local_hog_y_m': {'left': -6.401, 'right': 6.401}}}
    (reference/'aggregate.json').write_text(json.dumps(aggregate))
    rows = [{'time_s': t, 'boards': {'left': {'stones': []}, 'right': {'stones': [{
        'tracker_id': 7, 'height_adjusted_local_m': [0, y], 'pixel': [500, 200], 'confidence': .9}]}}}
        for t, y in [(6, 6), (7, 7)]]
    (reference/'match-observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    hashes = {str(p.resolve()): digest(p) for p in reference.iterdir()}
    (comparison/'plan.json').write_text(json.dumps({'inputs': hashes}))
    (comparison/'result.json').write_text(json.dumps({'events': [
        {'event_id': 'A', 'frozen_role': 'departure', 'candidate_role': candidate}]}))
    return reference, comparison, hashes


def test_replays_handoff_without_changing_observations_or_claiming_identity(tmp_path):
    reference, comparison, hashes = fixture(tmp_path)
    result = compare_handoffs(reference, comparison, tmp_path/'result.json')
    row = result['events'][0]
    assert row['before_candidates'] == []
    assert row['after_status'] == 'provisional_unique_temporal_hog_crossing'
    assert not result['physical_identity_verified']
    assert all(digest(p) == sha for p, sha in hashes.items())


def test_failed_role_does_not_silently_fall_back(tmp_path):
    reference, comparison, _ = fixture(tmp_path, candidate='unresolved')
    row = compare_handoffs(reference, comparison, tmp_path/'result.json')['events'][0]
    assert row['after_status'] == 'unresolved'
    assert row['after_candidates'] == []


def test_changed_inputs_are_rejected(tmp_path):
    reference, comparison, _ = fixture(tmp_path)
    with (reference/'match-observations.jsonl').open('a') as stream:
        stream.write('\n')
    with pytest.raises(ValueError, match='input mismatch'):
        compare_handoffs(reference, comparison, tmp_path/'result.json')
