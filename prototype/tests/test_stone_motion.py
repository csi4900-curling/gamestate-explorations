import numpy as np
import pytest
from prototype.stone_motion import sequences,fit_panel


def row(frame,x,visible=True):
    return {'frame_index':frame,'time_s':frame/30,'tracked_observations':[
        {'track_id':7,'pixel':[x,30],'point_normalized':[.2,.2],
         'bbox_xyxy':[x-5,20,x+5,40]}] if visible else []}


def test_motion_uses_observed_scale_and_breaks_at_visibility_gaps():
    s=sequences([row(0,10),row(3,12),row(6,0,False),row(9,50),row(12,50)],3)
    assert len(s)==2
    assert s[0]['samples']==[(3,.1,2.)]
    assert s[1]['samples'][0][2]==0
    assert all(p[0]!=9 for x in s for p in x['samples'])


def test_upstream_model_separates_synthetic_motion_then_rest():
    pytest.importorskip('hmmlearn')
    rng=np.random.default_rng(2);items=[]
    for k in range(5):
        speed=np.r_[rng.uniform(2,3,40),rng.uniform(0,.03,40)]
        items.append({'track_id':k,'samples':[(i,i/10,float(v)) for i,v in enumerate(speed)]})
    samples,info=fit_panel(items)
    stationary=np.array([r[4] for r in samples]).reshape(5,80)
    assert not stationary[:,:40].any()
    assert stationary[:,40:].all()
    assert info['backend']=='hmmlearn.hmm.GaussianHMM'


def test_flat_data_does_not_establish_two_motion_states():
    pytest.importorskip('hmmlearn')
    with pytest.raises(ValueError,match='not identifiable'):
        fit_panel([{'track_id':1,'samples':[(0,0.,0.),(1,.1,0.)]}])


def test_unidentifiable_panel_does_not_abort_unrelated_board_export(tmp_path):
    import json
    from prototype.stone_motion import run
    pytest.importorskip('hmmlearn')
    public=tmp_path/'public';public.mkdir()
    (public/'protocol.json').write_text(json.dumps({'source_sha256':'synthetic-source','sample_step_frames':3}))
    (public/'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in [row(0,10),row(3,10)]))
    result=run(public,tmp_path/'motion')
    for panel in ['left','right']:
        assert result['panels'][panel]['status']=='unidentifiable'
        assert result['panels'][panel]['stationary_hypothesis'] is None
        with np.load(tmp_path/'motion'/f'{panel}.npz') as data:
            assert len(data['stationary'])==0
