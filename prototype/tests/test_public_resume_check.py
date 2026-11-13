import json

import pytest

from prototype.public_resume_check import compare_outputs


def outputs(root, *, offset=8, different_track=False):
    for name in ['resumed', 'continuous']:
        folder = root/name/'two-view-tracking'
        folder.mkdir(parents=True)
        (folder/'result.json').write_text(json.dumps({'events': [{'segments': [{
            'status': 'tracked', 'segment_id': 'stone', 'result': 'segment.json'
        }]}]}))
        (folder/'segment.json').write_text(json.dumps({
            'frame_indices': [1, 2], 'times_s': [.1, .2],
            'tracks_px': [[[1, 2]], [[3, 5 if different_track and name == 'resumed' else 4]]],
            'point_visible': [[True], [True]],
            'model': {'progress_checkpoint': {'resumed_window_offset': offset if name == 'resumed' else 0}},
        }))


def test_exact_output_without_actual_resume_cannot_pass(tmp_path):
    outputs(tmp_path, offset=0)
    with pytest.raises(ValueError, match='comparison failed'):
        compare_outputs(tmp_path, 'test')
    assert not json.loads((tmp_path/'output-comparison.json').read_text())['all_checks_passed']


def test_changed_prediction_is_preserved_and_fails(tmp_path):
    outputs(tmp_path, different_track=True)
    with pytest.raises(ValueError, match='comparison failed'):
        compare_outputs(tmp_path, 'test')
    saved = json.loads((tmp_path/'output-comparison.json').read_text())
    assert saved['checkpoint_actually_resumed']
    assert not saved['segments'][0]['tracks_bitwise_equal']


def test_exact_resumed_output_passes_only_narrow_scope(tmp_path):
    outputs(tmp_path)
    result = compare_outputs(tmp_path, 'two test frames')
    assert result['all_checks_passed']
    assert result['full_match_complete'] is False
