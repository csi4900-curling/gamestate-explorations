from prototype.learned_handoff import receiving_crossings,temporal_candidates


def test_metric_crossing_respects_missing_projection():
    def row(t,y):return {'time_s':t,'boards':{'right':{'stones':[{'tracker_id':1,'height_adjusted_local_m':None if y is None else [0,y],'pixel':[10,10],'confidence':.9}]}}}
    assert receiving_crossings([row(0,7),row(1,None),row(2,6)])==[]
    e=receiving_crossings([row(0,7),row(1,6)])[0]
    assert e['track_id']==1 and not e['physical_identity_verified']
    assert abs(e['crossing_time_s']-.599)<1e-8


def test_multiple_incoming_stones_remain_ambiguous():
    e=[{'id':'A','crossing_time_s':1},{'id':'B','crossing_time_s':10}]
    incoming=[{'crossing_time_s':2},{'crossing_time_s':3},{'crossing_time_s':11}]
    r=temporal_candidates(e,incoming,20)
    assert r['A']['status']=='ambiguous' and len(r['A']['candidates'])==2
    assert r['B']['status']=='provisional_unique_temporal_hog_crossing'
    assert r['B']['interval_s']==[10,20]
