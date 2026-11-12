import numpy as np

from prototype.post_throw_state import propose_frame, suppress_duplicates


def event():
    return {'segments':[{'role':'receiving','camera':'right_split','tracker_id':7,
                         'pixel_points':[{'time_s':0}]}]}


def motion(frames, states):
    n=len(frames)
    return {'right':{'frame_index':np.array(frames),'time_s':np.array(frames)/30,
                     'track_id':np.full(n,7),'stationary':np.array(states),
                     'posterior_stationary':np.full(n,.8)}}


def test_proposal_respects_next_event_and_visibility_gaps():
    m=motion([0,3,6,9,30,33,36,39,42,45],[False,True,True,True,True,True,False,True,True,True])
    # The first low-motion run wins; disconnected frames 30/33 cannot extend it.
    r=propose_frame(event(),1.4,m,3)
    assert r['frame_index']==6
    assert r['stationary_interval_s']==[.1,.3]
    assert r['status']=='review_proposal'


def test_stationary_only_or_missing_receivers_do_not_establish_settlement():
    assert propose_frame(event(),3,motion([0,3],[True,True]),3)['status']=='unresolved'
    assert propose_frame({'segments':[]},3,{},3)['status']=='unresolved'


def test_upstream_suppression_preserves_evidence_and_separate_stones():
    stones=[{'tracker_id':i,'bbox_xyxy':box,'confidence':c}
            for i,box,c in [(1,[0,0,10,10],.9),(2,[.1,0,10.1,10],.8),(3,[30,0,40,10],.7)]]
    board,suppressed=suppress_duplicates({'stones':stones},.7)
    assert [s['tracker_id'] for s in board['stones']]==[1,3]
    assert [s['tracker_id'] for s in suppressed]==[2]
    assert len(stones)==3
