import json
import pytest
from prototype.public_run_profile import profile


def fixture_run(path, *, reused):
    def save(name, data):
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data))
    save('events.json', {'source_sha256': 'source', 'source_interval_s': [0, 2],
                        'events': [{'id': 'a'}], 'wall_seconds': 10,
                        'detector_seconds': 0, 'association_seconds': 1,
                        'reused_detector_frames': 2, 'prior_detector_seconds_for_reused_frames': 99})
    save('match-observation-summary.json', {'geometry_seconds': 5, 'ocr_seconds': 2})
    save('two-view-tracking/result.json', {'source_sha256': 'source', 'wall_seconds': 20,
         'summary': {'segments_failed': 1, 'segments_tracked': 1},
         'events': [{'candidate_id': 'a', 'segments': [
             {'segment_id': 'left', 'status': 'tracked', 'result': 'segment/result.json'},
             {'segment_id': 'right', 'status': 'failed', 'reason': 'missing geometry'}]}]})
    model = {'model_load_wall_s': 3, 'inference_wall_s': 7}
    if reused:
        model['reused_result_sha256'] = 'previous-result'
    save('two-view-tracking/segment/result.json', {
         'provenance': {'source_sha256': 'source', 'decode_and_preparation_wall_s': 2},
         'model': model, 'times_s': [0, 1], 'point_visible': [[True], [False]],
         'projection': {'wall_seconds': 4, 'samples': [
             {'points_camera_local_m': [[0, 0]], 'height_adjusted_points_camera_local_m': [None]},
             {'points_camera_local_m': [None], 'height_adjusted_points_camera_local_m': [None]}]}})
    state = {'current_end': None, 'current_points_from_stones': None,
             'boards': {'left': {'stones': [{'confidence': .9, 'height_adjusted_local_m': [0, 0],
                                           'physical_identity': None, 'team': None}]},
                        'right': {'stones': []}}}
    (path / 'match-observations.jsonl').write_text(json.dumps(state) + '\n')


@pytest.mark.parametrize('reused', [False, True])
def test_replayed_runtime_and_output_availability_are_not_accuracy(tmp_path, reused):
    fixture_run(tmp_path, reused=reused)
    result = profile(tmp_path)
    runtime = result['runtime_seconds']
    assert runtime['dense_nested_model_fresh'] == (0 if reused else 10)
    assert runtime['historical_model_time_for_replayed_tracks_not_current_runtime'] == (10 if reused else 0)
    assert runtime['event_board_scan_wall'] == 10
    assert runtime['historical_detector_time_for_replayed_frames_not_current_runtime'] == 99
    assert result['segments'][1]['status'] == 'failed'
    assert result['segments'][0]['primary_height_projected_samples'] == 0
    assert result['state_availability']['samples_with_current_points'] == 0
    assert result['state_availability']['stones_with_physical_identity'] == 0
    assert result['stone_detector_confidence']['calibrated_probability'] is False


def test_mixed_source_reports_are_rejected(tmp_path):
    fixture_run(tmp_path, reused=False)
    p = tmp_path / 'two-view-tracking/result.json'
    data = json.loads(p.read_text())
    data['source_sha256'] = 'different-source'
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='different sources'):
        profile(tmp_path)


def test_snapshot_colour_calls_are_separate_from_dense_stage_and_verified_state(tmp_path):
    fixture_run(tmp_path,reused=False)
    p=tmp_path/'two-view-tracking/result.json';d=json.loads(p.read_text())
    d['stone_colour_model']={'load_and_text_encoding_wall_s':3.5};p.write_text(json.dumps(d))
    snapshots=[{'status':'observed','colour_observations':{'predictions':[{'prediction':'yellow','wall_seconds':.2},{'prediction':None}]},
                'both_panel_observations':{'boards':{'left':{'stones':[{'colour_evidence':{'prediction':'red','wall_seconds':.3}}]},'right':{'stones':[]}}}}]
    (tmp_path/'two-view-tracking/end-views.json').write_text(json.dumps(snapshots))
    r=profile(tmp_path)
    assert r['end_snapshot_colour_availability']=={'snapshot_entries':1,'observed_snapshots':1,'source_crops_with_colour_ranking':1,'saved_board_boxes_with_colour_ranking':1,'unknown_or_invalid_colour_crops':1}
    assert r['runtime_seconds']['final_snapshot_colour_prediction_outside_dense_timer']==.5
    assert r['runtime_seconds']['dense_nested_colour_model_load_and_text_encoding']==3.5
    assert r['state_availability']['stones_with_team']==0
