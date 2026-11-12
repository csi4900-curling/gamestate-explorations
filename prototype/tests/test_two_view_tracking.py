import json
import pytest
from prototype.spin.throws import association, handoff_observations, visibility_intervals, run_throws


def event(links=None):
    return {'candidate_id':'x','segments':[{'segment_id':'a','role':'departure','camera':'left_split'},
                                         {'segment_id':'b','role':'receiving','camera':'right_split'}],
            'cross_view_links':links or []}


def test_no_link_is_not_identity():
    assert association(event())['status']=='unresolved'


def test_existing_link_stays_provisional():
    link={'departure_segment':'a','receiving_segment':'b'}
    a=association(event([link]));assert a['status']=='provisional'
    assert a['links']==[link] and not a['physical_identity_verified']


def test_conflicting_receivers_are_ambiguous():
    e=event([{'departure_segment':'a','receiving_segment':'b'},
             {'departure_segment':'a','receiving_segment':'c'}])
    e['segments'].append({'segment_id':'c','role':'receiving'})
    assert association(e)['status']=='ambiguous'
    assert 'multiple_links_claim_same_segment' in association(e)['issues']


def test_missing_link_target_not_silently_accepted():
    assert association(event([{'departure_segment':'a','receiving_segment':'missing'}]))['status']=='ambiguous'


def test_gap_uses_visible_endpoints_without_filling():
    a={'links':[{'departure_segment':'a','receiving_segment':'b'}]}
    r={'a':{'times_s':[1,2,3],'point_visible':[[True],[True],[False]]},
       'b':{'times_s':[4,5,6],'point_visible':[[False],[True],[True]]}}
    h=handoff_observations(a,r)[0];assert h['interval_s']==[2,5] and h['gap_s']==3
    assert not h['interpolated'] and not h['physical_identity_verified']
    assert handoff_observations(a,{'a':r['a']})[0]['status']=='missing_dense_endpoint'


def test_overlap_not_negative_gap():
    a={'links':[{'departure_segment':'a','receiving_segment':'b'}]}
    r={'a':{'times_s':[1,4],'point_visible':[[True],[True]]},
       'b':{'times_s':[3,5],'point_visible':[[True],[True]]}}
    h=handoff_observations(a,r)[0];assert h['gap_s']==0 and h['overlap_s']==1


def test_visibility_keeps_internal_loss():
    r={'times_s':[1,2,3,4],'point_visible':[[True],[False],[False],[True]]}
    runs=visibility_intervals(r);assert [r['samples'] for r in runs]==[1,2,1]
    assert [r['model_visible'] for r in runs]==[True,False,True]


def test_missing_segments_and_empty_event_remain_visible(tmp_path,monkeypatch):
    import prototype.spin.throws as t
    monkeypatch.setattr(t,'digest',lambda p:'hash')
    monkeypatch.setattr(t,'write_report',lambda *a:None)
    a=tmp_path/'aggregate.json';a.write_text(json.dumps({'context':{'source_sha256':'hash'},'events':[event(),{'candidate_id':'empty','segments':[]}]}))
    r=run_throws('unused',a,tmp_path/'out','unused')
    assert len(r['events'])==2
    assert r['summary']['segments_tracked']==0
    assert r['events'][1]['missing_roles']==['departure','receiving']
    assert all(s['status']=='unavailable' for s in r['events'][0]['segments'])


def test_unknown_candidate_rejected_before_output(tmp_path,monkeypatch):
    import prototype.spin.throws as t
    monkeypatch.setattr(t,'digest',lambda p:'hash')
    a=tmp_path/'aggregate.json';a.write_text(json.dumps({'context':{'source_sha256':'hash'},'events':[]}))
    with pytest.raises(ValueError,match='Unknown'):run_throws('unused',a,tmp_path/'out','unused',candidate_ids=['missing'])
    assert not (tmp_path/'out').exists()


def test_all_camera_segments_run_and_one_failure_keeps_other(tmp_path,monkeypatch):
    import prototype.spin.throws as t
    monkeypatch.setattr(t,'digest',lambda p:'hash')
    monkeypatch.setattr(t,'write_report',lambda *a:None)
    monkeypatch.setattr(t,'candidate_config',lambda v,a,s,**kw:{'segment_id':s})
    e=event([{'departure_segment':'a','receiving_segment':'b'}])
    for s in e['segments']:s['pixel_points']=[{'time_s':1,'pixel':[10,10]}]
    a=tmp_path/'aggregate.json';a.write_text(json.dumps({'context':{'source_sha256':'hash'},'events':[e]}))
    calls=[]
    def track(v,c,out,**kwargs):
        sid=json.loads(c.read_text())['segment_id'];calls.append(sid)
        if sid=='a':raise RuntimeError('Fixture tracking failure')
        return {'times_s':[2,3],'point_visible':[[True],[True]],'tracks_px':[[[10,10]],[[11,11]]],'fps':1,'model':{'fixture':True},'point_names':['cap'],'config':{}}
    monkeypatch.setattr(t,'run',track)
    r=run_throws('unused',a,tmp_path/'out','unused')
    assert calls==['a','b']
    assert [s['status'] for s in r['events'][0]['segments']]==['failed','tracked']
    assert r['events'][0]['handoffs'][0]['status']=='missing_dense_endpoint'
    assert r['events'][0]['missing_roles']==['departure']


def test_height_configuration_reaches_segment_configs(tmp_path,monkeypatch):
    import prototype.spin.throws as t
    monkeypatch.setattr(t,'digest',lambda p:'hash')
    monkeypatch.setattr(t,'write_report',lambda *a:None)
    monkeypatch.setattr(t,'candidate_config',lambda v,a,s,**kw:{'segment_id':s})
    e=event()
    for segment in e['segments']:segment['pixel_points']=[{'time_s':1,'pixel':[10,10]}]
    a=tmp_path/'aggregate.json';a.write_text(json.dumps({'context':{'source_sha256':'hash'},'events':[e]}))
    settings=tmp_path/'heights.json';settings.write_text(json.dumps({'body_box_center':.09}))
    seen=[]
    def track(v,c,out,**kw):
        seen.append(json.loads(c.read_text())['feature_heights_m'])
        raise RuntimeError('Stop after testing settings transport')
    monkeypatch.setattr(t,'run',track)
    r=t.run_throws('unused',a,tmp_path/'out','unused',projection_config=settings)
    assert len(seen)==2 and all(h=={'body_box_center':.09,'cap_with_body_support':.136} for h in seen)
    assert r['projection_config']['feature_heights_m']==seen[0]


def test_missing_identity_audit_input_preserves_tracked_segment(tmp_path, monkeypatch):
    import prototype.spin.throws as t
    monkeypatch.setattr(t, 'digest', lambda p: 'hash')
    monkeypatch.setattr(t, 'write_report', lambda *a: None)
    monkeypatch.setattr(t, 'candidate_config', lambda *a, **kw: {})
    e = event()
    e['segments'] = [dict(e['segments'][0], pixel_points=[{'time_s': 1, 'pixel': [10, 10]}])]
    a = tmp_path/'aggregate.json'
    a.write_text(json.dumps({'context': {'source_sha256': 'hash'}, 'events': [e],
                            'provenance': {'match_observation_run': str(tmp_path/'missing-observations'),
                                           'board_observations_sha256': 'hash'}}))
    tracked = {'times_s': [1, 2], 'point_visible': [[True], [True]],
               'tracks_px': [[[10, 10]], [[11, 11]]], 'fps': 1, 'model': {},
               'point_names': ['body'], 'config': {}}
    monkeypatch.setattr(t, 'run', lambda *a, **kw: tracked)
    result = t.run_throws('unused', a, tmp_path/'out', 'unused')
    segment = result['events'][0]['segments'][0]
    assert segment['status'] == 'tracked'
    assert segment['tracks_px'] == tracked['tracks_px']
    assert segment['detector_consistency_error'].startswith('FileNotFoundError:')
    assert 'detector_consistency' not in segment
    assert 'stone_query_consistency.py' in result['code_sha256']
