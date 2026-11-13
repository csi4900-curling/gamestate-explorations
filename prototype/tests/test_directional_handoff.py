from prototype.directional_handoff import metric_crossings,hypotheses


def row(t,left,right):
    return {'time_s':t,'boards':{panel:{'stones':[] if y is None else [{'tracker_id':k,
        'height_adjusted_local_m':[0,y],'pixel':[100*k,200],'confidence':.9}]}
        for panel,y,k in [('left',left,1),('right',right,2)]}}


def test_signed_coordinate_conventions_and_observation_gaps():
    values=metric_crossings([row(0,-7,6),row(1,-6,7)],hog_y_by_panel={'left':-6.401,'right':6.401})
    assert {(e['panel'],e['role']) for e in values}=={('left','receiving'),('right','departure')}
    assert metric_crossings([row(0,-7,6),row(1,None,None),row(2,-6,7)],hog_y_by_panel={'left':-6.401,'right':6.401})==[]


def test_arrival_primary_looks_back_for_departure():
    events=[{'id':'A','crossing_time_s':10}]
    roles={'A':{'role':'receiving','panel':'left'}}
    c=[{'id':'right-out','crossing_time_s':7,'panel':'right','role':'departure'},
       {'id':'right-in','crossing_time_s':8,'panel':'right','role':'receiving'},
       {'id':'too-late','crossing_time_s':11,'panel':'right','role':'departure'}]
    h=hypotheses(events,roles,c,[0,20])['A']
    assert h['status']=='provisional_unique_temporal_hog_crossing'
    assert [e['id'] for e in h['candidates']]==['right-out']


def test_multiple_candidates_and_unknown_roles_are_retained():
    events=[{'id':'A','crossing_time_s':10},{'id':'B','crossing_time_s':20}]
    roles={'A':{'role':'departure','panel':'left'},'B':{'role':'unassigned'}}
    c=[{'id':str(i),'crossing_time_s':i,'panel':'right','role':'receiving'} for i in [12,13]]
    h=hypotheses(events,roles,c,[0,25])
    assert h['A']['status']=='ambiguous' and len(h['A']['candidates'])==2
    assert h['B']['status']=='unresolved' and not h['B']['candidates']


def test_unmatched_and_ambiguous_receiving_observations_are_not_dropped():
    from prototype.directional_event_aggregate import retain_camera_crossings
    events=[{'id':'departure','track_id':1,'crossing_point_normalized':[.25,.2]}]
    crossings=[{'id':'out','panel':'left','role':'departure','track_id':1},
               {'id':'incoming-A','panel':'right','role':'receiving','track_id':2},
               {'id':'incoming-B','panel':'right','role':'receiving','track_id':3},
               {'id':'unmatched','panel':'right','role':'receiving','track_id':4}]
    h={'departure':{'candidates':crossings[1:3]}}
    r=retain_camera_crossings(crossings,events,h,[{'candidate_id':'departure','cross_view_links':[]}])
    assert len(r)==4
    assert r[0]['association_status']=='primary_track_observation'
    assert all(x['association_status']=='unresolved_or_ambiguous' for x in r[1:])
    assert r[1]['candidate_event_ids']==['departure'] and r[3]['candidate_event_ids']==[]
    assert all(not x['physical_delivery_verified'] for x in r)


def test_rink_enrichment_preserves_unassigned_crossings_with_no_primary_event():
    from prototype.scripts.enrich_rink_aggregate import enrich
    crossings=[{'id':'incoming','panel':'right','role':'receiving','crossing_time_s':10.,
                'association_status':'unresolved_or_ambiguous'}]
    a={'schema_version':'learned-directional-event-track-bridge-development-v1',
       'events':[],'camera_crossings':crossings,'provenance':{'local_hog_y_m':{'left':-6.401,'right':6.401}}}
    result=enrich(a)
    assert result['camera_crossings']==crossings
    assert result['events']==[] and result['summary']['events']==0


def test_unresolved_camera_track_uses_same_rink_mapping_without_an_event_link():
    import copy
    from prototype.directional_event_aggregate import camera_fragment_events
    from prototype.scripts.enrich_rink_aggregate import enrich
    crossing={'id':'incoming','panel':'right','role':'receiving','association_status':'unresolved_or_ambiguous'}
    raw={'candidate_id':'incoming','event_prediction':{'crossing_time_s':10.},'failure_reasons':['cross_view_identity_unresolved'],
         'cross_view_links':[],'segments':[{'segment_id':'incoming:primary','camera':'right_split','role':'unassigned',
             'geometry_samples':[{'time_s':10.,'top_view_m':[.3,6.5],'conditional_height_adjusted_position_m':[.3,6.4]}]}]}
    before=copy.deepcopy(raw);fragments=camera_fragment_events([crossing],{'incoming':raw})
    a={'schema_version':'learned-directional-event-track-bridge-development-v1','events':[],
       'unresolved_camera_fragments':fragments,'provenance':{'local_hog_y_m':{'left':-6.401,'right':6.401}}}
    result=enrich(a);f=result['unresolved_camera_fragments'][0]
    assert raw==before and result['events']==[]
    assert f['observation_only'] and f['cross_view_links']==[]
    assert f['segments'][0]['geometry_samples'][0]['rink_position_m'][0]==.3
    assert not f['segments'][0]['physical_identity_verified']
    assert f['segments'][0]['geometry_samples'][0]['rink_position_m'][1]==34.747-6.4
