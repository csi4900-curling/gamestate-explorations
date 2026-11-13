import json
from prototype.spin.evaluate_handle_probe import evaluate


def test_missing_predictions_are_counted_and_ambiguous_references_excluded(tmp_path):
    (tmp_path/'result.json').write_text(json.dumps({'source_sha256':'source'}))
    (tmp_path/'observations.json').write_text(json.dumps([
        {'time_s':0,'axis_endpoints_source_px':[[0,0],[10,0]]},
        {'time_s':1,'axis_endpoints_source_px':None}]))
    reference = tmp_path/'reference.json'
    reference.write_text(json.dumps({'source_sha256':'source','samples':[
        {'time_s':0,'axis_endpoints_source_px':[[0,0],[10,0]]},
        {'time_s':1,'axis_endpoints_source_px':[[0,0],[10,0]]},
        {'time_s':2,'axis_endpoints_source_px':None}]}))
    result = evaluate(tmp_path,reference,tmp_path/'comparison.json')
    assert result['reference_axes_available'] == 2
    assert result['missing_predictions_on_labeled_frames'] == 1
    assert result['answer_coverage'] == .5
    assert result['image_axis_mae_deg_among_answered'] == 0
    assert result['physical_revolution_accuracy'] is None


def test_correct_angle_on_wrong_object_is_visible_as_localization_error(tmp_path):
    (tmp_path/'result.json').write_text(json.dumps({'source_sha256':'source'}))
    (tmp_path/'observations.json').write_text(json.dumps([{
        'time_s':0,'axis_endpoints_source_px':[[0,10],[10,10]],
        'crop_source_bounds':[0,0,20,20],
        'chosen_handle':{'corners_crop_px':[[0,8],[10,8],[10,12],[0,12]]}}]))
    reference = tmp_path/'reference.json'
    reference.write_text(json.dumps({'source_sha256':'source','samples':[
        {'time_s':0,'axis_endpoints_source_px':[[0,0],[10,0]]}]}))
    result = evaluate(tmp_path,reference,tmp_path/'comparison.json')
    row = result['comparisons'][0]
    assert row['absolute_axial_error_deg'] == 0
    assert row['axis_midpoint_distance_px'] == 10
    assert row['reference_midpoint_signed_distance_to_predicted_box_px'] == -8
