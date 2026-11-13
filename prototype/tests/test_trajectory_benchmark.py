"""Synthetic reference fixtures test scoring, not real-world accuracy."""
from copy import deepcopy
import pytest
from prototype.trajectory_benchmark import evaluate


def fixture():
    ref={'schema_version':'metric-trajectory-reference-v1','source_sha256':'source',
         'source_interval_s':[0.,2.],'coordinate_system':'delivery_tee_origin_receiving_positive_y_metres',
         'event_matching_tolerance_s':.2,'exhaustive_events':True,'exhaustive_observable_samples':True,
         'provenance':{'independent':True,'operator_kind':'instrument','prediction_visible':False,
                       'position_error_bound_m':0.,  # Exact synthetic coordinates only.
                       'reference_kind':'surveyed_metric_trajectory','evidence':['synthetic-test-fixture']},
         'events':[{'id':'reference','crossing_time_s':1.,'stone_id':'stone-A','samples':[]}]}
    agg={'source_interval_s':[0.,2.],'context':{'source_sha256':'source'},'events':[
        {'candidate_id':'candidate','event_prediction':{'crossing_time_s':1.},'segments':[],
         'cross_view_links':[{'departure_segment':'left','receiving_segment':'right'}]}]}
    for panel,pixel in [('left',[100,200]),('right',[500,200])]:
        agg['events'][0]['segments'].append({'segment_id':panel,'rink_panel':panel,'geometry_samples':[
            {'time_s':1.,'pixel':pixel,'rink_position_m':[.2,15.]}]})
        x,y=pixel[0]*3,pixel[1]*3
        ref['events'][0]['samples'].append({'panel':panel,'frame_index':10,'time_s':1.,
            'target_visible':True,'rink_position_m':[.2,15.],
            'visible_stones':[{'stone_id':'stone-A','bbox_source_px_xyxy':[x-3,y-3,x+3,y+3]}]})
    return ref,agg


def score(ref,agg):
    return evaluate(ref,agg,source_size=[1920,1080],source_fps=10.)


def test_exact_external_positions_and_identities_pass_synthetic_fixture():
    ref,agg=fixture();before=deepcopy(agg)
    r=score(ref,agg)
    assert r['accepted'] and r['metrics']['median_position_error_m']==0
    assert agg==before


def test_wrong_identity_fails_even_with_zero_position_error():
    ref,agg=fixture();ref['events'][0]['samples'][1]['visible_stones'][0]['stone_id']='stone-B'
    r=score(ref,agg)
    assert r['metrics']['median_position_error_m']==0
    assert r['metrics']['wrong_stone_samples']==1
    assert not r['accepted'] and 'physical_identity_failed' in r['failure_reasons']


def test_missing_camera_and_geometry_remain_in_reference_denominator():
    ref,agg=fixture();agg['events'][0]['segments'][0]['geometry_samples'][0]['rink_position_m']=None
    r=score(ref,agg)
    assert r['metrics']['expected_observable_samples']==2
    assert r['metrics']['missing_samples']==1
    assert r['metrics']['observable_sample_coverage']==.5
    assert not r['accepted']
    agg['events'][0]['segments']=[]
    r=score(ref,agg)
    assert r['metrics']['observable_sample_coverage']==0
    assert not r['accepted']


def test_empty_pipeline_cannot_omit_missed_events():
    ref,agg=fixture();agg['events']=[]
    r=score(ref,agg)
    assert r['metrics']['event_false_negatives']==1
    assert r['metrics']['expected_observable_samples']==2
    assert r['metrics']['observable_sample_coverage']==0


def test_false_candidate_and_ambiguous_camera_link_fail():
    ref,agg=fixture();agg['events'][0]['cross_view_links']=[]
    extra=deepcopy(agg['events'][0]);extra['candidate_id']='false-positive';extra['event_prediction']['crossing_time_s']=1.8
    agg['events'].append(extra)
    r=score(ref,agg)
    assert r['metrics']['event_false_positives']==1
    assert 'camera_handoff_missing_or_ambiguous' in r['failure_reasons']
    assert not r['accepted']


def test_errors_use_metric_reference_not_cross_camera_agreement():
    ref,agg=fixture()
    for s in agg['events'][0]['segments']:s['geometry_samples'][0]['rink_position_m']=[.2,17.]
    r=score(ref,agg)
    assert r['metrics']['median_position_error_m']==2.
    assert 'position_error_target_failed' in r['failure_reasons']


def test_agent_review_cannot_become_independent_metric_ground_truth():
    ref,agg=fixture();ref['provenance']['operator_kind']='agent'
    r=score(ref,agg)
    assert not r['accepted'] and 'independent_physical_reference_required' in r['failure_reasons']


def test_reference_must_cover_actual_source_interval_and_frame_timestamps():
    ref,agg=fixture();ref['source_interval_s']=[0.,1.]
    with pytest.raises(ValueError,match='complete requested'):score(ref,agg)
    ref,agg=fixture();ref['events'][0]['samples'][0]['time_s']=1.1
    with pytest.raises(ValueError,match='timestamp'):score(ref,agg)


def test_partial_reference_cannot_pass_complete_pipeline_acceptance():
    ref,agg=fixture();ref['exhaustive_observable_samples']=False
    assert not score(ref,agg)['accepted']


def test_reference_uncertainty_cannot_be_ignored_when_certifying_accuracy():
    ref,agg=fixture();ref['provenance'].pop('position_error_bound_m')
    r=score(ref,agg)
    assert not r['accepted'] and 'reference_position_uncertainty_required' in r['failure_reasons']
    ref['provenance']['position_error_bound_m']=.11
    r=score(ref,agg)
    assert r['metrics']['median_position_error_m']==0.
    assert r['metrics']['conservative_median_position_error_m']==.11
    assert not r['accepted'] and 'position_target_not_established_with_reference_uncertainty' in r['failure_reasons']
    for invalid in [True,-.1,float('nan')]:
        ref['provenance']['position_error_bound_m']=invalid
        assert 'reference_position_uncertainty_required' in score(ref,agg)['failure_reasons']
