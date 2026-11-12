import json

from prototype.throw_effect import DEFAULTS, colour_at, effect, run

GEOMETRY = dict(house_radius_m=1.829, stone_radius_m=0.139, hog_y_by_panel={'right': 6.401},
                settings=DEFAULTS)


def still(position, start, end):
    return [(round(start+i*0.1, 1), position) for i in range(round((end-start)*10)+1)]


def record(tracker_id=9):
    return {'event_id': 'L1', 'crossing_time_s': 8.0,
            'proposal': {'time_s': 30.0, 'panel': 'right', 'receiving_tracker_id': tracker_id,
                         'stationary_interval_s': [29.0, 31.0]}}


def delivered():
    # Enters beyond the hog line, travels to the tee by 15 s, then rests.
    moving = [(round(10+i*0.1, 1), [0.0, 8.0-8.0*i/50]) for i in range(51)]
    return moving+still([0.0, 0.0], 15.1, 40.0)


def test_board_is_taken_at_first_quiet_window_not_later_handling():
    guard = still([1.0, 3.0], 0.0, 25.0)+[(round(25.1+i*0.1, 1), [1.0+i*0.05, 3.0]) for i in range(50)]
    result = effect(record(), {'right': {9: delivered(), 1: guard}}, search_end_s=40.0, **GEOMETRY)
    assert result['status'] == 'review_proposal'
    # Half-window medians can accept a window starting up to half a window before rest.
    assert 14.0 <= result['settle_interval_s'][0] <= 16.0
    assert result['counts'] == {'delivered': 1, 'moved': 0, 'unchanged': 1,
                                'left_view_or_lost': 0, 'appeared_unexplained': 0}


def test_struck_stone_is_reported_with_path_and_out_of_play_status():
    struck = still([0.0, 0.5], 0.0, 14.0)+[(round(14.1+i*0.1, 1), [0.0, 0.5-i*0.15]) for i in range(20)]
    struck += still([0.0, -2.5], 16.1, 40.0)
    result = effect(record(), {'right': {9: delivered(), 2: struck}}, search_end_s=40.0, **GEOMETRY)
    row = next(s for s in result['stones'] if s['before_tracker_id'] == 2)
    assert row['change'] == 'moved' and row['in_play_before'] and not row['in_play_after']
    assert abs(row['displacement_m']-3.0) < 0.05
    assert '2' in result['paths'] and result['in_play'] == {'before': 1, 'after': 1, 'changed': 2}


def test_resting_stone_with_new_tracker_id_is_relinked_by_position_only_when_close():
    tracks = {'right': {9: delivered(), 3: still([1.0, 1.0], 0.0, 12.0), 4: still([1.03, 1.0], 12.5, 40.0),
                        5: still([-1.0, 1.0], 0.0, 12.0), 6: still([-1.5, 1.0], 12.5, 40.0)}}
    result = effect(record(), tracks, search_end_s=40.0, **GEOMETRY)
    links = {s['before_tracker_id']: (s['after_tracker_id'], s['link'], s['change']) for s in result['stones']}
    assert links[3] == (4, 'stationary_position', 'unchanged')
    assert links[5] == (None, None, 'left_view_or_lost')
    assert result['counts']['appeared_unexplained'] == 1


def test_unobserved_delivered_stone_that_returns_blocks_the_quiet_window():
    samples = [s for s in delivered() if not 12.0 <= s[0] <= 14.0]
    result = effect(record(), {'right': {9: samples}}, search_end_s=40.0, **GEOMETRY)
    assert result['settle_interval_s'][0] >= 14.0


def test_missing_receiver_and_never_quiet_board_stay_unresolved():
    missing = {'event_id': 'L2', 'crossing_time_s': 1.0, 'proposal': {'status': 'unresolved', 'reason': 'x'}}
    assert effect(missing, {}, search_end_s=40.0, **GEOMETRY)['status'] == 'unresolved'
    result = effect(record(), {'right': {9: delivered()}}, search_end_s=14.0, **GEOMETRY)
    assert result['reason'] == 'no_quiet_board_interval_before_next_candidate'


def test_colour_uses_sample_nearest_in_time_and_flags_inconsistency():
    evidence = {'7': {'samples': [{'time_s': 10, 'prediction': 'red'}, {'time_s': 90, 'prediction': 'yellow'}]}}
    assert colour_at(evidence, 7, 20) == ('red', True)
    assert colour_at(evidence, 7, 80) == ('yellow', True)
    assert colour_at(evidence, 8, 20) == (None, None)
    # A stone already on the board keeps its colour from before the throw arrived.
    assert colour_at(evidence, 7, 80, not_after=True) == ('red', True)
    assert colour_at(evidence, 7, 5, not_after=True) == ('red', True)


def test_run_writes_viewer_and_refuses_to_overwrite(tmp_path):
    public = tmp_path/'run'; public.mkdir()
    (public/'protocol.json').write_text(json.dumps({'source_sha256': 'h', 'source_interval_s': [0, 40]}))
    tracks = {9: delivered(), 1: still([1.0, 1.0], 0.0, 40.0)}
    times = sorted({t for rows in tracks.values() for t, _ in rows})
    with (public/'match-observations.jsonl').open('w') as stream:
        for t in times:
            stones = [{'tracker_id': k, 'height_adjusted_local_m': dict(rows).get(t)}
                      for k, rows in tracks.items() if t in dict(rows)]
            stream.write(json.dumps({'time_s': t, 'boards': {'right': {'stones': stones}}})+'\n')
    for name, value in [('states.json', {'source_sha256': 'h', 'events': [record()]}),
                        ('state.json', {'house_radius_m': 1.829, 'stone_radius_m': 0.139,
                                        'group_to_team': {'red': 'A', 'yellow': 'B'}}),
                        ('match.json', {'local_hog_y_m': {'right': 6.401}})]:
        (tmp_path/name).write_text(json.dumps(value))
    arguments = dict(public_run=public, states=tmp_path/'states.json', config_path=tmp_path/'state.json',
                     match_config=tmp_path/'match.json', output=tmp_path/'throws')
    result = run(**arguments)
    assert result['summary']['with_board_change'] == 1
    assert result['events'][0]['points_lying_after']['status'] == 'unresolved'
    assert 'effects.js' in (tmp_path/'throws/index.html').read_text()
    try:
        run(**arguments)
    except ValueError:
        pass
    else:
        raise AssertionError('existing output must be preserved')
