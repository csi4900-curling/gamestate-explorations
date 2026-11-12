import numpy as np
import pytest

from prototype.painted_landmark_evaluation import evaluate, project_box


def references(frame=30):
    return {'source_size_px':[1920,1080], 'homography_input_size_px':[640,360],
            'purpose':'test', 'reviewer':'test', 'frames':[{'frame_index':frame, 'landmarks':[
                {'panel':'left','landmark':'hog','status':'annotated','pixel_xy':[300,600],
                 'pixel_bounds_xyxy':[297,597,303,603], 'target_y_interval_m':[6.401,6.503]}]}]}


def test_projection_rescales_source_pixels_and_encloses_annotation():
    p, lo, hi = project_box(np.eye(3),[300,600],[297,597,303,603],[1920,1080],[640,360])
    np.testing.assert_allclose(p,[100,200])
    np.testing.assert_allclose(lo,[99,199])
    np.testing.assert_allclose(hi,[101,201])


def test_hog_uses_painted_width_and_retains_longitudinal_error():
    H=np.array([[.01,0,0],[0,.01,4.45],[0,0,1]])
    row={'frame_index':30,'boards':{'left':{'homography_normalized_pixels_to_local_metres':H.tolist()}}}
    result=evaluate(references(),[row])['results'][0]
    assert result['nominal_error_m']==0
    H[1,2]=5.45
    row['boards']['left']['homography_normalized_pixels_to_local_metres']=H.tolist()
    result=evaluate(references(),[row])['results'][0]
    assert result['nominal_error_m']==pytest.approx(.947)
    assert result['conservative_annotation_box_error_bounds_m']==pytest.approx([.937,.957])


def test_nearby_frame_cannot_substitute_for_requested_source_frame():
    r=evaluate(references(),[{'frame_index':29}])
    assert r['results'][0]['status']=='exact_source_frame_not_available'
    assert r['full_trajectory_accuracy_measured'] is False


def test_horizon_crossing_is_not_reported_as_finite_error():
    H=np.array([[1,0,0],[0,1,0],[1,0,-100]])
    with pytest.raises(ValueError,match='horizon'):
        project_box(H,[300,600],[297,597,303,603],[1920,1080],[640,360])
