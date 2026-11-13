from prototype.camera_motion_role import crossing_role, role_for_event


def evidence(panel,y,t=0,track=7):
    return {'panel':panel,'local_m':[.2,y],'time_s':t,'track_id':track}


def test_roles_follow_motion_not_panel_or_coordinate_sign():
    for panel in ['left','right']:
        for sign in [-1,1]:
            a=evidence(panel,sign*6);b=evidence(panel,sign*7,1)
            assert crossing_role(a,b)['role']=='departure'
            assert crossing_role({**b,'time_s':0},{**a,'time_s':1})['role']=='receiving'


def test_unobservable_or_ambiguous_motion_is_not_assigned():
    a=evidence('left',-6)
    assert crossing_role(a,evidence('right',-7,1))['role']=='unassigned'
    assert crossing_role(a,evidence('left',-7,1,track=8))['role']=='unassigned'
    assert crossing_role(a,evidence('left',6,1))['role']=='unassigned'
    assert crossing_role(a,{**evidence('left',-7,1),'local_m':None})['role']=='unassigned'


def test_event_join_requires_exact_track_and_pixel_evidence():
    event={'track_id':7,'observations':[{'time_s':0,'pixel':[100,200]},{'time_s':1,'pixel':[100,210]}]}
    rows=[{'time_s':t,'boards':{'left':{'stones':[{'tracker_id':7,'pixel':[100,200+t*10],
        'height_adjusted_local_m':[.2,-7+t]}]}}} for t in [0,1]]
    assert role_for_event(event,rows,1920)['role']=='receiving'
    rows[1]['boards']['left']['stones'][0]['pixel']=[101,210]
    assert role_for_event(event,rows,1920)['role']=='unassigned'
