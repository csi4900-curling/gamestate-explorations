from prototype.tracking_sampling_comparison import tracking_metadata
from prototype.tracking_sampling_comparison import component_result
import pytest


def test_sampling_experiment_does_not_inherit_baseline_measurements():
    baseline={'candidate_id':'x','point_names':['stone'],'fps':30,
              'reconstruction':{'revolutions':8},'masked_evaluation':{'error':0},
              'physical_revolutions':8,'projection':{'points':[1]},
              'config':{'frame_step':1},'provenance':{'prediction_hash':'old'}}
    result=tracking_metadata(baseline)
    assert result['candidate_id']=='x' and result['point_names']==['stone']
    for field in ['reconstruction','masked_evaluation','physical_revolutions','projection']:
        assert result[field] is None
    assert 'config' not in result and 'provenance' not in result
    assert not result['physical_identity_verified']


def test_normalization_preserves_predictions_but_rejects_wrong_sample_count():
    raw={'point_names':['stone'],'times_s':[1.,1.1],'frame_indices':[30,33],
         'tracks_px':[[[1.,2.]],[[3.,4.]]],'point_visible':[[True],[False]],
         'model':{'native_frame_count':2,'checkpoint_sha256':'weights'},
         'sampling_experiment':{'frame_step':3,'model_sha256':'weights'},
         'provenance':{'source_sha256':'source'},'reconstruction':{'stale':True}}
    normalized=component_result(raw)
    assert normalized['tracks_px']==raw['tracks_px']
    assert normalized['point_visible']==raw['point_visible']
    assert normalized['reconstruction'] is None
    raw['frame_indices']=[30,31]
    with pytest.raises(ValueError,match='Sampling indices'):
        component_result(raw)
