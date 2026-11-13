import pytest
from prototype.learned_event_aggregate import assemble


def inputs():
    e={'events':[{'id':'L1','track_id':7,'crossing_point_normalized':[.25,.2]}],
       'sample_step_frames':3,'source_interval_s':[0,1],'source_sha256':'source'}
    raw=[];boards=[]
    for frame in [0,3,9]:
        point=[160.,72.];obs={'track_id':7,'pixel':point,'point_normalized':[.25,.2],'confidence':.9}
        raw.append({'frame_index':frame,'time_s':frame/30,'tracked_observations':[obs]})
        b={'stones':[{'tracker_id':7,'pixel':point,'ice_plane_local_m':[0,1],'height_adjusted_local_m':[0,1]}],
           'registration':{'status':'fixture'},'homography_normalized_pixels_to_local_metres':[[1,0,0],[0,1,0],[0,0,1]]}
        boards.append({'frame_index':frame,'time_s':frame/30,'boards':{'left':b,'right':{'stones':[]}}})
    return e,raw,boards


def test_bridge_retains_typed_points_gaps_and_unknown_handoff():
    e,raw,boards=inputs();r=assemble(e,raw,boards,[640,360],camera_roles={'left':'departure'})
    event=r['events'][0];s=event['segments'][0]
    assert s['point_kind']=='body_box_center'
    assert len(s['pixel_points'])==3
    assert s['detection_gaps']==[{'after_s':.1,'before_s':.3}]
    assert s['role']=='departure' and s['colour'] is None
    assert event['cross_view_links']==[] and not s['physical_identity_verified']


def test_timestamp_mismatch_cannot_project_wrong_frame():
    e,raw,boards=inputs();boards[1]['frame_index']=4
    with pytest.raises(ValueError,match='share source frames'):assemble(e,raw,boards,[640,360])


def test_missing_primary_is_preserved_as_empty_candidate():
    e,raw,boards=inputs();e['events'][0]['track_id']=99
    r=assemble(e,raw,boards,[640,360])
    assert len(r['events'])==1 and r['events'][0]['segments'][0]['pixel_points']==[]
