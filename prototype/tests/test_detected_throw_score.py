from prototype.game_board_state import BoardStateEvidence


def observer(extra=None):
    events = [{'candidate_id': name, 'event_prediction': {'crossing_time_s': t}, 'segments': [
        {'role': 'receiving', 'camera': 'right_split', 'tracker_id': track,
         'pixel_points': [{'time_s': t + .1}]}]}
        for name, t, track in [('A', 1, 7), ('B', 3, 8)]]
    if extra:
        events.append(extra)
    return BoardStateEvidence(events, [
        {'event_id': 'A', 'colour': 'red'}, {'event_id': 'B', 'colour': 'yellow'},
    ], group_to_team={'red': 'CAN', 'yellow': 'SWE'}, house_radius_m=1.829, stone_radius_m=.139)


def sample(stones, time=4):
    return {'time_s': time, 'frame_index': round(time * 30), 'boards': {'right': {'stones': [
        {'tracker_id': track, 'pixel': [100, 100], 'height_adjusted_local_m': position}
        for track, position in stones]}}}


def subset(o, stones, **kwargs):
    return o.observe(sample(stones), **kwargs)['boards']['right']['detected_throw_score']


def test_unmatched_stones_do_not_block_detected_subset_score():
    result = subset(observer(), [(7, [0, .2]), (8, [0, 1]), (99, [0, 0])])
    assert result['estimated_points'] == {'CAN': 1, 'SWE': 0}
    assert result['excluded_unmatched_tracker_ids'] == [99]
    assert {s['event_id'] for s in result['entries']} == {'A', 'B'}


def test_collision_updates_earlier_stone_and_does_not_sum_previous_points():
    o = observer()
    first = subset(o, [(7, [0, .2]), (8, [0, 1])])
    after = subset(o, [(7, [0, 4]), (8, [0, .3])])
    assert first['estimated_points'] == {'CAN': 1, 'SWE': 0}
    assert after['estimated_points'] == {'CAN': 0, 'SWE': 1}
    assert after['entries'][0]['position_m'] == [0, 4]


def test_occlusion_holds_timestamped_estimate_and_reappearance_updates_it():
    o = observer()
    memory = {'right': {7: {'time_s': 3.5, 'frame_index': 105,
                            'pixel': [100, 100], 'position_m': [0, .2]}}}
    result = subset(o, [(8, [0, 1])], track_memory=memory)
    assert result['estimated_points'] == {'CAN': 1, 'SWE': 0}
    assert result['status'] == 'estimated_with_last_known_positions'
    assert result['entries'][0]['age_s'] == .5
    assert result['observed_only_points'] == {'CAN': 0, 'SWE': 1}
    after = subset(o, [(7, [0, 4]), (8, [0, .3])], track_memory=memory)
    assert after['estimated_points'] == {'CAN': 0, 'SWE': 1}
    assert after['stale_event_ids'] == []


def test_no_observation_does_not_become_removal_or_zero():
    result = subset(observer(), [(8, [0, 1])])
    assert result['estimated_points'] is None
    assert result['entries'][0]['position_status'] == 'never_observed'


def test_same_track_claimed_by_two_events_does_not_create_two_stones():
    extra = {'candidate_id': 'C', 'event_prediction': {'crossing_time_s': 3.1}, 'segments': [
        {'role': 'receiving', 'camera': 'right_split', 'tracker_id': 7, 'pixel_points': [{'time_s': 3.2}]}]}
    result = subset(observer(extra), [(7, [0, .2]), (8, [0, 1])])
    assert result['estimated_points'] is None
    assert [s['event_id'] for s in result['entries']
            if s['position_status'] == 'ambiguous_event_track_assignment'] == ['A', 'C']


def test_missing_receiver_is_reported_not_silently_excluded_from_coverage():
    extra = {'candidate_id': 'C', 'event_prediction': {'crossing_time_s': 3.1}, 'segments': []}
    result = observer(extra).observe(sample([(7, [0, .2]), (8, [0, 1])]))
    assert result['unassigned_detected_events'][0]['event_id'] == 'C'


def test_between_crossing_and_first_receiving_observation_is_unresolved():
    result = observer().observe(sample([], time=1.05))['boards']['right']['detected_throw_score']
    assert result['entries'][0]['event_id'] == 'A'
    assert result['estimated_points'] is None


def test_empty_association_is_not_a_known_blank_end():
    result = observer().observe(sample([], time=.5))['boards']['right']['detected_throw_score']
    assert result['status'] == 'no_associated_board_state'
    assert result['estimated_points'] is None
