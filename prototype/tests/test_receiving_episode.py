import cv2
import numpy as np
import pytest
from prototype.spin.episodes import receiving_episode_interval, receiving_scene_seeds


def fixture():
    e={'candidate_id':'a','event_prediction':{'observed_track_points':[{'time_s':10}]}}
    s={'pixel_points':[{'time_s':15},{'time_s':25}],'camera_cut_times_s':[]}
    a={'source_interval_s':[0,100],'events':[e]}
    return a,e,s


def test_episode_does_not_end_with_old_track_or_contact():
    a,e,s=fixture();interval,d=receiving_episode_interval(a,e,s,100)
    assert interval==[15,50] and d['legacy_track_end_s']==25
    assert not d['physical_stop_detected']


def test_camera_cut_bounds_episode():
    a,e,s=fixture();s['camera_cut_times_s']=[12,32,55]
    assert receiving_episode_interval(a,e,s,100)[0]==[15,32]


def test_next_delivery_bounds_episode():
    a,e,s=fixture();a['events'].append({'candidate_id':'b','event_prediction':{'observed_track_points':[{'time_s':40}]}})
    assert receiving_episode_interval(a,e,s,100)[0]==[15,40]


def test_source_boundary_is_not_a_physical_stop():
    a,e,s=fixture();a['source_interval_s'][1]=30
    interval,d=receiving_episode_interval(a,e,s,100)
    assert interval==[15,30] and d['end_reason']=='requested_source_end' and not d['physical_stop_detected']


def test_missing_event_timing_fails_instead_of_collision_specific_window():
    a,e,s=fixture();e['event_prediction']={}
    with pytest.raises(ValueError,match='event timing'):receiving_episode_interval(a,e,s,100)


def test_scene_seeds_both_colours_and_excludes_only_delivered_box(tmp_path,monkeypatch):
    import prototype.spin.episodes as ep
    path=tmp_path/'clip.avi';w=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),10,(1280,720))
    assert w.isOpened()
    for _ in range(3):w.write(np.zeros((720,1280,3),np.uint8))
    w.release()
    calls=[]
    def detector(frame):
        calls.append(frame.shape)
        return {'red':[{'pixel':[400,180],'bbox':[396,176,8,8]}],
                'yellow':[{'pixel':[500,180],'bbox':[496,176,8,8]},
                          {'pixel':[520,180],'bbox':[516,176,8,8]}]}
    monkeypatch.setattr(ep,'right_large_cap_proposals',detector)
    seeds,diag=receiving_scene_seeds(path,.1,[1000,360],'yellow')
    assert calls==[(360,640,3)]
    assert [s['colour'] for s in seeds]==['red','yellow']
    assert [s['pixel'] for s in seeds]==[[800,360],[1040,360]]
    assert sum(p['overlaps_delivered_seed'] for p in diag['proposals'])==1
    assert not diag['thresholds_changed']
