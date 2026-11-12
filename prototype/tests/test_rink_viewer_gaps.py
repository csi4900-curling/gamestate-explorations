from prototype.scripts.render_rink_viewer import compact_event


def test_viewer_keeps_calibration_failure_and_detection_gaps_visible():
    event = {'candidate_id': 'candidate', 'event_prediction': {'crossing_time_s': 1.},
             'segments': [{'segment_id': 'track', 'geometry_samples': [
                 {'time_s': 1., 'rink_position_m': [0., 1.]},
                 {'time_s': 1.1, 'rink_position_m': None},
                 {'time_s': 1.2, 'rink_position_m': [0., 1.2]},
                 {'time_s': 1.3, 'rink_position_m': [0., 1.3]},
                 {'time_s': 2., 'rink_position_m': [0., 2.]},
             ], 'pixel_points': [{'time_s': t, 'pixel': [10., 10.]} for t in [1., 1.1, 1.2, 1.3, 2.]]}]}
    segment = compact_event(event)['segments'][0]
    assert segment['times'] == [1., 1.2, 1.3, 2.]
    assert segment['missing_geometry_times'] == [1.1]
    assert segment['break_before'] == [True, True, False, True]
    assert abs(segment['sample_step_s'] - .1) < 1e-8


def test_overlapping_endpoints_are_not_presented_as_an_unobserved_gap():
    event = {'candidate_id': 'candidate', 'event_prediction': {'crossing_time_s': 1.},
             'segments': [], 'cross_view_links': [{'gap_s': -1.6, 'gap_m': 2.81}]}
    link = compact_event(event)['links'][0]
    assert link['gap_m'] == 2.81  # Preserve the raw endpoint calculation.
    assert link['temporal_relation'] == 'overlap'
    assert link['overlap_s'] == 1.6
    event['cross_view_links'][0]['gap_s'] = 2.
    assert compact_event(event)['links'][0]['temporal_relation'] == 'unobserved_gap'


def test_configured_team_labels_are_used_in_compact_state():
    from prototype.scripts.render_rink_viewer import compact_state
    result=compact_state({'team_labels':['NOR','CZE'],'samples':[{'t':1.,'last_observed_totals':{'NOR':{'value':2},'CZE':{'value':3}}}]})
    assert result['team_labels']==['NOR','CZE']
    assert result['samples'][0][5:7]==[2,3]


def test_unknown_absolute_end_is_not_presented_as_an_inferred_end_number():
    from prototype.scripts.render_rink_viewer import compact_state
    result=compact_state({'samples':[{'t':600.,'current_end':None,'current_end_status':'unknown_absolute_end'}]})
    assert result['samples'][0][1:3]==[None,'unknown']


def test_short_fragment_keeps_declared_sampling_stride_instead_of_treating_gap_as_stride():
    event={'candidate_id':'short','event_prediction':{'crossing_time_s':1.},'segments':[
        {'segment_id':'s','sample_step_s':.1,'pixel_points':[{'time_s':t,'pixel':[0,0]} for t in [1.,1.2]],
         'geometry_samples':[{'time_s':t,'rink_position_m':[0,t]} for t in [1.,1.2]]}]}
    s=compact_event(event)['segments'][0]
    assert s['sample_step_s']==.1 and s['break_before']==[True,True]


def test_board_role_is_unknown_before_first_motion_evidence():
    from prototype.scripts.render_rink_viewer import role_at
    history={'right':[(10.,'receiving')]}
    assert role_at(history,'right',9.) is None
    assert role_at(history,'right',10.)=='receiving'


def test_uncorrected_fallback_cannot_make_a_false_metric_line():
    event={'candidate_id':'e','event_prediction':{'crossing_time_s':1.},'segments':[
        {'segment_id':'e:primary','sample_step_s':.1,'geometry_samples':[
            {'time_s':1.,'rink_position_m':[0,19],'rink_position_kind':'height_adjusted_estimate'},
            {'time_s':1.1,'rink_position_m':[4,-22],'rink_position_kind':'ice_plane_unadjusted'},
            {'time_s':1.2,'rink_position_m':[0,20],'rink_position_kind':'height_adjusted_estimate'}]}]}
    s=compact_event(event)['segments'][0]
    assert s['xy']==[[0,19],[0,20]]
    assert s['missing_geometry_times']==[1.1]
    assert s['break_before']==[True,True]


def test_ambiguous_counterparts_remain_separate_from_the_event():
    event={'candidate_id':'e','event_prediction':{'crossing_time_s':1.},
           'association_issues':['multiple_or_shared_counterpart_crossings'],
           'segments':[{'segment_id':name,'associated':False,'geometry_samples':[]}
                       for name in ['e:primary','e:receiving:1','e:receiving:2']]}
    result=compact_event(event)
    assert [s['id'] for s in result['segments']]==['e:primary']
    assert result['unassigned_segment_ids']==['e:receiving:1','e:receiving:2']
    event['observation_only']=True
    assert len(compact_event(event)['segments'])==3


def test_enrichment_preserves_raw_projection_without_promoting_it_to_trajectory():
    from prototype.scripts.enrich_rink_aggregate import map_sample
    result=map_sample({'top_view_m':[4,-22]},panel='right',role='receiving',
                      hog_y_m={"right":6.401},lateral_sign=1,tee_distance=34.747)
    assert result['rink_ice_plane_m'] is not None
    assert result['rink_position_m'] is None
    assert result['rink_position_kind']=='unavailable'


def test_display_selects_only_first_receiving_crossing_strictly_after_departure():
    event={'candidate_id':'e','event_prediction':{'crossing_time_s':100.},
           'association_issues':['multiple_or_shared_counterpart_crossings'],
           'segments':[{'segment_id':'e:primary','role':'departure','geometry_samples':[]}]}
    for label,t in [('later',240.),('before',99.),('equal',100.),('first',107.)]:
        event['segments'].append({'segment_id':label,'role':'receiving','associated':False,
            'hog_crossing_evidence':{'crossing_time_s':t},'geometry_samples':[]})
    result=compact_event(event)
    assert [s['id'] for s in result['segments']]==['e:primary','first']
    assert result['display_receiving_candidate']=='first'
    assert result['links']==[]  # A display choice must never manufacture identity.
    assert event['association_issues']==['multiple_or_shared_counterpart_crossings']
    event['segments'].append({'segment_id':'tied','role':'receiving','associated':False,
        'hog_crossing_evidence':{'crossing_time_s':107.},'geometry_samples':[]})
    assert compact_event(event)['display_receiving_candidate'] is None
