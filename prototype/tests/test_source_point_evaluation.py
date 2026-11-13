import pytest
from prototype.source_point_evaluation import evaluate_source_points


def test_exact_frame_and_visibility_no_interpolation_or_hidden_error():
    result={'provenance':{'source_sha256':'x'},'frame_indices':[10,12],'tracks_px':[[[3,4]],[[100,100]]],'point_visible':[[True],[False]]}
    ref={'source_sha256':'x','provenance':{'reviewer':'test'},'samples':[{'frame_index':i,'pixel':[0,0]} for i in [10,11,12]]}
    score=evaluate_source_points(result,ref)
    assert score['visible_prediction_count']==1
    assert score['mean_pixel_error']==5
    assert [r['status'] for r in score['samples']]==['visible_prediction','no_predicted_frame','model_not_visible']
    ref['source_sha256']='different'
    with pytest.raises(ValueError,match='sources differ'):evaluate_source_points(result,ref)
