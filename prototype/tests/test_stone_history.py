import pytest

from prototype.stone_history import histories


def event(id, arrival, settled, change):
    stone = dict(in_play_before=change!='delivered', in_play_after=True, before_m=[0,0], after_m=[0,0],
                 before_tracker_id=4, after_tracker_id=4, change=change, colour='red',
                 colour_differs_along_track=False)
    return dict(event_id=id, crossing_time_s=arrival, arrival_time_s=arrival, settle_interval_s=settled,
                panel='right', stones=[stone])


def observations():
    return [dict(time_s=i, frame_index=i, current_end=1, boards={'right':{'stones':[
        dict(tracker_id=4, height_adjusted_local_m=[0,0])]}}) for i in range(4,11)]


def build(frames):
    events=[event('A',1,[3,4],'delivered'),event('B',7,[9,10],'unchanged')]
    return histories({'events':events},frames,.139,1,1)


def test_uninterrupted_track_across_boards():
    result=build(observations())
    assert result['membership']['B/0']=='A/0'
    assert [r['event'] for r in result['groups']['A/0']]==['A','B']
    assert not result['physical_identity_verified']


@pytest.mark.parametrize('failure', ['missing','rival','end','gap','short'])
def test_same_id_at_endpoints_does_not_bridge_conflict(failure):
    frames=observations()
    if failure=='missing':
        frames[2]['boards']['right']['stones']=[]
    elif failure=='rival':
        frames[2]['boards']['right']['stones'].append(dict(tracker_id=9,height_adjusted_local_m=[.01,.01]))
    elif failure=='end':
        frames[2]['current_end']=2
    elif failure=='gap':
        del frames[2]
    else:
        frames.pop()
    result=build(frames)
    assert result['membership']['B/0']=='B/0'
    assert result['next_events']['A/0']=='B'
    assert result['stops']['A/0']


def test_collision_swap_repair_preserves_cross_throw_stone_history():
    # Throw A repairs 3 <-> 38 at t=2.0; in raw observations, stone 38 sits at [0,0] under raw ID 3.
    a = event('A', 1, [3, 4], 'delivered')
    a['stones'][0].update(before_tracker_id=None, after_tracker_id=38)
    a['collision_swaps_repaired'] = [{'tracker_ids': [3, 38], 'swap_time_s': 2.0}]
    b = event('B', 7, [9, 10], 'unchanged')
    b['stones'][0].update(before_tracker_id=38, after_tracker_id=38)
    frames = [dict(time_s=i, frame_index=i, current_end=1, boards={'right': {'stones': [
        dict(tracker_id=3, height_adjusted_local_m=[0, 0]),
        dict(tracker_id=38, height_adjusted_local_m=[0, -3.0]),
    ]}}) for i in range(4, 11)]
    result = histories({'events': [a, b]}, frames, .139, 1, 1)
    assert result['membership']['B/0'] == 'A/0'
    assert [r['event'] for r in result['groups']['A/0']] == ['A', 'B']
    assert 'A/0' not in result['stops']
