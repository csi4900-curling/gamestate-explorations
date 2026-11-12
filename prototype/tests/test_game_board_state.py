from prototype.game_board_state import BoardStateEvidence


def observer():
    events=[{'candidate_id':'A', 'event_prediction':{'crossing_time_s':1},'segments':[
        {'role':'receiving','camera':'right_split','tracker_id':7,'pixel_points':[{'time_s':2}]}]}]
    colours=[{'event_id':'A','colour':'red','colour_status':'two_observation_agreement'}]
    return BoardStateEvidence(events,colours,group_to_team={'red':'A','yellow':'B'},
                              house_radius_m=1.829,stone_radius_m=.139)


def sample(stones,t=3):
    return {'time_s':t,'frame_index':round(t*30),'boards':{'right':{'stones':stones}}}


def stone(track=7,position=None):
    return {'tracker_id':track,'height_adjusted_local_m':position or [0,.5],'pixel':[1400,500]}


def test_points_require_settlement_and_retain_track_provenance():
    o=observer();s=o.observe(sample([stone()]))['boards']['right']
    assert s['conditional_visible_board_points']=={'A':1,'B':0}
    assert s['post_throw_points'] is None
    s=o.observe(sample([stone()]),settlement={'status':'estimated_settled'})['boards']['right']
    assert s['post_throw_points']=={'A':1,'B':0}
    assert not s['stones'][0]['physical_identity_verified']


def test_stored_or_unknown_stone_in_house_is_not_silently_assigned():
    s=observer().observe(sample([stone(),stone(54,[1.9,0])]))['boards']['right']
    assert s['conditional_visible_board_points'] is None
    assert s['stones'][1]['in_play_status']=='unknown_no_receiving_track_evidence'


def test_hidden_previously_received_stone_does_not_become_post_throw_zero():
    s=observer().observe(sample([]),settlement={'status':'estimated_settled'})['boards']['right']
    assert s['conditional_visible_board_points']=={'A':0,'B':0}
    assert s['unobserved_previously_received_tracker_ids']==[7]
    assert s['post_throw_points'] is None


def test_future_event_evidence_is_not_applied_to_earlier_state():
    s=observer().observe(sample([stone()],t=.5))['boards']['right']
    assert s['stones'][0]['receiving_track_evidence']==[]
    assert s['conditional_visible_board_points'] is None


def test_end_epoch_does_not_accumulate_previous_end_missing_tracks():
    o=observer()
    s=o.observe(sample([],t=20),end_context={'epoch_start_s':10,'status':'inferred'})
    assert s['boards']['right']['unobserved_previously_received_tracker_ids']==[]
    assert s['end_context']['status']=='inferred'
    assert s['boards']['right']['post_throw_points'] is None


def test_unseen_stones_keep_timestamped_last_observations_without_becoming_current():
    memory={'right':{7:{'time_s':2.5,'frame_index':75,'pixel':[1400,500],'position_m':[0,.5]}}}
    result=observer().observe(sample([],t=4),track_memory=memory)['boards']['right']
    assert result['stones']==[]
    assert result['last_observed_unretained_receiving_tracks'][0]['age_s']==1.5
    assert not result['last_observed_unretained_receiving_tracks'][0]['currently_observed']
    assert result['post_throw_points'] is None
    assert memory['right'][7]['time_s']==2.5


def test_memory_cannot_use_future_or_pre_delivery_track_positions():
    for t in [1,10]:
        memory={'right':{7:{'time_s':t,'frame_index':round(t*30),'pixel':[1400,500],'position_m':[0,.5]}}}
        result=observer().observe(sample([],t=4),track_memory=memory)['boards']['right']
        assert result['last_observed_unretained_receiving_tracks']==[]


def test_suppressed_current_observation_is_not_described_as_unseen():
    memory={'right':{7:{'time_s':3,'frame_index':90,'pixel':[1400,500],'position_m':[0,.5]}}}
    result=observer().observe(sample([]),track_memory=memory)['boards']['right']
    assert result['unobserved_previously_received_tracker_ids']==[]
    assert result['observed_but_not_retained_received_tracker_ids']==[7]
    assert result['last_observed_unretained_receiving_tracks'][0]['currently_observed']
    assert result['post_throw_points'] is None
