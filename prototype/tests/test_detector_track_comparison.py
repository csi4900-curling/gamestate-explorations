import pytest

from prototype.detector_track_comparison import compare
from prototype.detector_track_comparison import comparable_event_inputs
from copy import deepcopy


def test_shared_geometry_comparison_preserves_occlusion_and_missing_projection():
    from prototype.detector_track_comparison import project_comparison
    comparison = {'frames': [{'frame_index': 3, 'time_s': .1, 'comparisons': [
        {'query_index': 0, 'track_id': 2, 'point_px': [10, 20],
         'point_model_visible': False, 'detector_observation': {'pixel': [12, 22]}}]}]}
    board = {'frame_index': 3, 'time_s': .1, 'boards': {'left': {}, 'right': {}}}
    out = project_comparison(comparison, [board], [640, 360], height_m=.068)
    q = out['frames'][0]['comparisons'][0]
    assert q['point'] is None
    assert q['detector']['ice_plane_local_m'] is None
    assert q['detector']['status'] == 'missing_saved_homography'
    board['time_s'] = .2
    with pytest.raises(ValueError, match='Exact source-frame'):
        project_comparison(comparison, [board], [640, 360], height_m=.068)


def test_boundary_contact_is_reported_without_discarding_identity_link():
    from prototype.detector_track_comparison import box_boundary_contacts
    assert box_boundary_contacts([12, 90, 30, 100], [10, 0, 50, 100]) == ['bottom']
    assert box_boundary_contacts([12, 90, 30, 99.999], [10, 0, 50, 100]) == []
    result = {'frame_indices': [0], 'times_s': [0], 'tracks_px': [[[20, 95]]],
              'point_visible': [[True]], 'crop_px': [10, 0, 50, 100]}
    rows = [{'frame_index': 0, 'time_s': 0, 'tracked_observations': [
        {'track_id': 7, 'bbox_xyxy': [12, 90, 30, 100]}]}]
    summary = compare(result, rows)['summary'][0]
    assert summary['track_id'] == 7
    assert summary['initial_candidate_box_boundary_contacts'][0]['tracking_crop_sides'] == ['bottom']


def test_collision_disagreement_and_occlusion_are_distinct():
    result = {'frame_indices': [0, 3, 6], 'times_s': [0, .1, .2],
              'tracks_px': [[[1, 1]], [[1, 1]], [[1, 1]]],
              'point_visible': [[True], [True], [False]]}
    rows = [{'frame_index': f, 'time_s': t, 'tracked_observations':
             [{'track_id': 7, 'bbox_xyxy': box}]} for f, t, box in
            [(0, 0, [0, 0, 2, 2]), (3, .1, [4, 4, 6, 6]), (6, .2, [4, 4, 6, 6])]]
    summary = compare(result, rows)['summary'][0]
    assert summary['both_visible'] == 2
    assert summary['point_outside_original_track_box'] == 1
    assert summary['detector_track_present'] == 3


def test_duplicate_initial_detections_are_not_silently_resolved():
    result = {'frame_indices': [0], 'times_s': [0], 'tracks_px': [[[1, 1]]], 'point_visible': [[True]]}
    row = {'frame_index': 0, 'time_s': 0, 'tracked_observations':
           [{'track_id': k, 'bbox_xyxy': [0, 0, 2, 2]} for k in [1, 2]]}
    summary = compare(result, [row])['summary'][0]
    assert summary['track_id'] is None
    assert summary['initial_candidate_track_ids'] == [1, 2]
    assert summary['detector_missing_sample_runs'] is None
    assert summary['detector_availability_status'] == 'initial_association_unresolved_not_detector_absence'


def test_missing_detection_and_hidden_point_runs_remain_separate():
    result = {'frame_indices': [0, 3, 6, 9], 'times_s': [0, .1, .2, .3],
              'tracks_px': [[[1, 1]]] * 4,
              'point_visible': [[True], [False], [False], [True]]}
    detection = {'track_id': 7, 'bbox_xyxy': [0, 0, 2, 2]}
    rows = [{'frame_index': f, 'time_s': t, 'tracked_observations': boxes}
            for f, t, boxes in [(0, 0, [detection]), (3, .1, []),
                                (6, .2, [detection]), (9, .3, [detection])]]
    summary = compare(result, rows)['summary'][0]
    assert summary['detector_missing_sample_runs'] == [
        {'first_sample_s': .1, 'last_sample_s': .1, 'sample_count': 1}]
    assert summary['point_hidden_sample_runs'] == [
        {'first_sample_s': .1, 'last_sample_s': .2, 'sample_count': 2}]
    assert summary['point_disagreement_sample_runs'] == []


def test_missing_initial_frame_does_not_reseed():
    result = {'frame_indices': [0, 3], 'times_s': [0, .1]}
    with pytest.raises(ValueError, match='initial frame'):
        compare(result, [{'frame_index': 3, 'time_s': .1}])


def paired_inputs():
    a = dict(source_sha256='video', source_interval_s=[0,1], source_fps=30,
             source_size_px=[1920,1080], sample_step_frames=3,
             tracker_config={'type':'bytetrack'}, tracker_sha256='tracker',
             ultralytics='version', opencv_build_sha256='decoder',
             model=dict(backend='pytorch', device='cpu', threads=1,
                        checkpoint_sha256='weights', imgsz=1280, torch='version',
                        ultralytics='version', experimental_upstream_end2end=True))
    b = deepcopy(a);b['model']['experimental_upstream_end2end'] = False
    return a,b


def test_tracker_file_relocation_is_not_an_inference_change():
    a,b = paired_inputs()
    assert comparable_event_inputs(a,b,{'tracker_config':'old.yaml','lines':[]},
                                   {'tracker_config':'new.yaml','lines':[]})['paired_inputs_verified']


@pytest.mark.parametrize('field,value', [('backend','openvino'),('threads',4),('imgsz',640)])
def test_paired_head_audit_rejects_confounded_model_changes(field,value):
    a,b = paired_inputs();b['model'][field] = value
    with pytest.raises(ValueError, match='inputs differ'):
        comparable_event_inputs(a,b,{}, {})


def test_paired_head_audit_rejects_changed_line_configuration():
    a,b = paired_inputs()
    with pytest.raises(ValueError, match='configuration differs'):
        comparable_event_inputs(a,b,{'lines':[1]}, {'lines':[2]})
