from prototype.camera_motion_role import recover_missing_role
from prototype.directional_handoff import metric_crossings, resolve_short_receiving_approaches
from prototype.throw_effect import DEFAULTS, effect, in_play, quiet_interval


def test_empty_house_quiet_interval_resolves_only_when_camera_registered():
    # Delivered stone enters and exits play by t=5.0s; no other stones remain in play.
    tracks = {10: [(1.0, [0.0, 5.0]), (2.0, [0.0, 2.0]), (3.0, [0.0, -1.0]), (4.0, [0.0, -2.5])]}
    region = lambda p: in_play(p, 6.401, half_width_m=2.375, house_radius_m=1.829, stone_radius_m=0.139)

    # Without registered_times, empty house has no supporting stone.
    assert quiet_interval(tracks, 10, 1.0, 15.0, region, DEFAULTS) is None

    # With camera registration confirming an empty house from t=5..12s, quiet interval resolves.
    reg_times = [round(t * 0.2, 1) for t in range(25, 65)]
    q = quiet_interval(tracks, 10, 1.0, 15.0, region, DEFAULTS, registered_times=reg_times)
    assert q is not None and q[0] >= 4.0 and q[1] - q[0] == DEFAULTS['quiet_window_s']

    # If camera registration is missing (gap), empty house MUST stay unresolved.
    assert quiet_interval(tracks, 10, 1.0, 15.0, region, DEFAULTS, registered_times=[1.0, 2.0]) is None


def test_metric_crossings_bridges_brief_geometry_gap_only_when_image_track_continuous():
    def row(t, stones):
        return {'time_s': t, 'boards': {'left': {'stones': []}, 'right': {'stones': stones}}}

    def stone(tid, xy):
        return {'tracker_id': tid, 'height_adjusted_local_m': xy, 'pixel': [1400.0, 650.0], 'confidence': 0.9}

    # Continuous image track (tid=7 present every frame) with 0.4s geometry gap over y=6.401.
    continuous_rows = [
        row(10.0, [stone(7, [0.0, 7.0])]),
        row(10.2, [stone(7, None)]),
        row(10.4, [stone(7, None)]),
        row(10.6, [stone(7, [0.0, 5.8])]),
    ]
    found = metric_crossings(continuous_rows, hog_y_by_panel={'left': -6.401, 'right': 6.401})
    assert len(found) == 1
    assert found[0]['track_id'] == 7
    assert found[0]['role'] == 'receiving'
    assert found[0]['geometry_gap_bridged_on_continuous_track'] is True

    # Real detection dropout (tid=7 absent at t=10.2s): MUST NOT bridge!
    dropout_rows = [
        row(10.0, [stone(7, [0.0, 7.0])]),
        row(10.2, []),
        row(10.6, [stone(7, [0.0, 5.8])]),
    ]
    assert metric_crossings(dropout_rows, hog_y_by_panel={'left': -6.401, 'right': 6.401}) == []


def test_short_receiving_approach_resolves_unique_hogged_stone_only():
    events = [{'id': 'L00001', 'crossing_time_s': 10.0, 'track_id': 1}]
    handoffs = {
        'L00001': {
            'status': 'unresolved',
            'role_evidence': {'role': 'departure', 'panel': 'left'},
            'interval_s': [10.0, 40.0],
            'candidates': [],
        }
    }

    def make_rows(tids):
        rows = []
        for i, y in enumerate([16.0, 14.0, 12.0, 10.0, 8.0, 6.7]):
            stones = [{'tracker_id': tid, 'height_adjusted_local_m': [0.2 * k, y],
                       'pixel': [1400.0, 700.0 - i * 10], 'confidence': 0.9} for k, tid in enumerate(tids)]
            rows.append({'time_s': 12.0 + i * 1.0, 'boards': {'left': {'stones': []}, 'right': {'stones': stones}}})
        return rows

    added = resolve_short_receiving_approaches(
        events, handoffs, make_rows([42]), hog_y_by_panel={'left': -6.401, 'right': 6.401}
    )
    assert len(added) == 1
    assert handoffs['L00001']['status'] == 'provisional_unique_receiving_approach_short_of_hog'
    assert handoffs['L00001']['candidates'][0]['track_id'] == 42

    # Two competing approaches must stay unresolved.
    handoffs_amb = {
        'L00001': {
            'status': 'unresolved',
            'role_evidence': {'role': 'departure', 'panel': 'left'},
            'interval_s': [10.0, 40.0],
            'candidates': [],
        }
    }
    assert resolve_short_receiving_approaches(
        events, handoffs_amb, make_rows([42, 43]), hog_y_by_panel={'left': -6.401, 'right': 6.401}
    ) == []
    assert handoffs_amb['L00001']['status'] == 'unresolved'


def test_one_sided_missing_role_recovery_handles_brief_gap_across_crossing():
    event = {'track_id': 9, 'observed_bracket_s': [10.0, 10.2], 'crossing_point_normalized': [0.2, 0.2]}
    primary = {'role': 'unassigned', 'status': 'unresolved', 'reason': 'missing_or_undefined_geometry'}
    # Geometry present before crossing, missing across/after crossing, continuous image track!
    samples = [
        (9.2, [0.0, -8.5]),
        (9.4, [0.0, -8.9]),
        (9.6, [0.0, -9.3]),
        (9.8, [0.0, -9.7]),
        (10.0, None),
        (10.2, None),
    ]
    recovered = recover_missing_role(event, samples, 0.2, primary)
    assert recovered['role'] == 'departure'
    assert recovered['status'] == 'one_sided_registered_track_observations'


def test_opposite_colour_collision_id_swap_is_repaired_and_preserves_caller_inputs():
    # Models a 5 Hz ByteTrack momentum-transfer swap (like NOR-CZE Throw 10):
    # Track 4 (red) rests at (0.73, 0.72); delivered Track 104 (yellow) approaches
    # from (0.66, 2.50) -> (0.66, 1.13) at t=15.8s. At t=16.0s ByteTrack swaps IDs:
    # track 4 jumps backward to (0.76, 1.05) and rolls right to (1.47, 0.92) in play,
    # while track 104 jumps forward to (0.71, 0.66) and exits past the back line (-2.46).
    t_pre = [round(10.0 + i * 0.2, 1) for i in range(30)]  # 10.0 .. 15.8
    t_post = [round(16.0 + i * 0.2, 1) for i in range(45)]  # 16.0 .. 24.8
    t4_raw = [(t, [0.73, 0.72]) for t in t_pre]
    # Swapped tail of 4: really yellow stone rolling right to [1.47, 0.92] by 18.0s
    for i, t in enumerate(t_post):
        frac = min(1.0, i / 10.0)
        t4_raw.append((t, [0.76 + 0.71 * frac, 1.05 - 0.13 * frac]))
    t104_raw = [(t, [0.66, 1.13 + (15.8 - t) * 1.4]) for t in t_pre if t >= 12.0]
    # Swapped tail of 104: really red stone shooting straight out past back line [-2.46]
    for i, t in enumerate(t_post):
        frac = min(1.0, i / 10.0)
        t104_raw.append((t, [0.71 - 0.08 * frac, 0.66 - 3.12 * frac]))
    # One stationary red stone near button so points_lying changes if yellow stays in house
    t70 = [(t, [0.35, 0.35]) for t in t_pre + t_post]

    tracks = {'right': {4: t4_raw, 104: t104_raw, 70: t70}}
    orig_t104_last = list(t104_raw[-1][1])
    colours = {
        '4': {'samples': [{'time_s': 11.0, 'prediction': 'red'}, {'time_s': 24.0, 'prediction': 'yellow'}]},
        '104': {'samples': [{'time_s': 13.0, 'prediction': 'yellow'}, {'time_s': 20.0, 'prediction': 'red'}]},
        '70': {'samples': [{'time_s': 11.0, 'prediction': 'red'}, {'time_s': 24.0, 'prediction': 'red'}]},
    }
    rec = {'event_id': 'L3', 'crossing_time_s': 11.0,
           'proposal': {'time_s': 20.0, 'panel': 'right', 'receiving_tracker_id': 104}}
    res = effect(
        rec, tracks, house_radius_m=1.829, stone_radius_m=0.139,
        hog_y_by_panel={'right': 6.401}, settings=DEFAULTS, search_end_s=24.8,
        colours=colours, groups=['red', 'yellow'],
    )
    assert res['status'] == 'review_proposal'
    assert len(res['collision_swaps_repaired']) == 1
    swap = res['collision_swaps_repaired'][0]
    assert swap['tracker_ids'] == [4, 104]
    assert swap['swap_time_s'] == 16.0
    assert swap['basis'] == 'opposite_colour_and_kinematic_collision_swap'
    assert swap['physical_identity_verified'] is False

    by_after = {s['after_tracker_id']: s for s in res['stones']}
    assert by_after[104]['colour'] == 'yellow'
    assert by_after[104]['change'] == 'delivered'
    assert by_after[104]['in_play_after'] is True
    assert abs(by_after[104]['after_m'][0] - 1.47) < 0.05
    assert by_after[4]['colour'] == 'red'
    assert by_after[4]['change'] == 'moved'
    assert by_after[4]['in_play_after'] is False
    assert res['tracks_with_inconsistent_colour'] == []
    assert res['points_lying_after']['conditional_points_by_group'] == {'red': 1, 'yellow': 0}
    # Caller inputs must not be mutated when mutate_state=False.
    assert tracks['right'][104][-1][1] == orig_t104_last
    assert colours['104']['samples'][-1]['prediction'] == 'red'


def test_normal_close_collision_does_not_trigger_false_swap():
    # Delivered yellow stone hits resting red stone and does NOT swap IDs.
    t_pre = [round(10.0 + i * 0.2, 1) for i in range(30)]
    t_post = [round(16.0 + i * 0.2, 1) for i in range(45)]
    t4 = [(t, [0.0, 0.5]) for t in t_pre] + [
        (t, [0.0, 0.5 - min(1.0, i / 10.0) * 3.0]) for i, t in enumerate(t_post)
    ]
    t9 = [(t, [0.0, 0.85 + (15.8 - t) * 1.2]) for t in t_pre if t >= 12.0] + [
        (t, [0.25 * min(1.0, i / 10.0), 0.78 - 0.05 * min(1.0, i / 10.0)]) for i, t in enumerate(t_post)
    ]
    colours = {
        '4': {'samples': [{'time_s': 11.0, 'prediction': 'red'}, {'time_s': 20.0, 'prediction': 'red'}]},
        '9': {'samples': [{'time_s': 13.0, 'prediction': 'yellow'}, {'time_s': 20.0, 'prediction': 'yellow'}]},
    }
    rec = {'event_id': 'L4', 'crossing_time_s': 11.0,
           'proposal': {'time_s': 20.0, 'panel': 'right', 'receiving_tracker_id': 9}}
    res = effect(
        rec, {'right': {4: t4, 9: t9}}, house_radius_m=1.829, stone_radius_m=0.139,
        hog_y_by_panel={'right': 6.401}, settings=DEFAULTS, search_end_s=24.8,
        colours=colours, groups=['red', 'yellow'],
    )
    assert res['collision_swaps_repaired'] == []
    by_after = {s['after_tracker_id']: s for s in res['stones']}
    assert by_after[9]['colour'] == 'yellow' and by_after[9]['in_play_after'] is True
    assert by_after[4]['colour'] == 'red' and by_after[4]['in_play_after'] is False


def test_overlapping_duplicate_tracker_box_is_deduplicated_and_does_not_block_scoring():
    # Stone 10 (red) sits in house at (0.5, 0.5); a short-lived uncoloured duplicate box 99
    # overlaps within 1.5 cm at (0.51, 0.51) during the settled window.
    t_all = [round(10.0 + i * 0.2, 1) for i in range(60)]
    t10 = [(t, [0.50, 0.50]) for t in t_all]
    t99 = [(t, [0.51, 0.51]) for t in t_all if 17.0 <= t <= 20.0]
    t_del = [(t, [0.0, max(0.0, 5.0 - (t - 12.0) * 1.0)]) for t in t_all if t >= 12.0]
    colours = {
        '10': {'samples': [{'time_s': 11.0, 'prediction': 'red'}]},
        '20': {'samples': [{'time_s': 13.0, 'prediction': 'yellow'}]},
    }
    rec = {'event_id': 'L5', 'crossing_time_s': 11.0,
           'proposal': {'time_s': 19.0, 'panel': 'right', 'receiving_tracker_id': 20}}
    res = effect(
        rec, {'right': {10: t10, 99: t99, 20: t_del}}, house_radius_m=1.829, stone_radius_m=0.139,
        hog_y_by_panel={'right': 6.401}, settings=DEFAULTS, search_end_s=21.8,
        colours=colours, groups=['red', 'yellow'],
    )
    assert res['points_lying_after']['status'] == 'conditional_on_supplied_observations'
    assert res['points_lying_after']['conditional_points_by_group'] == {'red': 0, 'yellow': 1}
    assert any(m['dropped_tracker_id'] == 99 and m['kept_tracker_id'] == 10 for m in res['duplicate_tracks_merged'])


def test_stationary_linked_stone_falls_back_to_after_track_colour_when_before_missing():
    # Stone 10 (uncoloured) sits at (0.6, 0.6) before arrival, re-tracked as 11 (red) after arrival.
    t_pre = [round(10.0 + i * 0.2, 1) for i in range(15)]
    t_post = [round(15.0 + i * 0.2, 1) for i in range(30)]
    t10 = [(t, [0.60, 0.60]) for t in t_pre]
    t11 = [(t, [0.61, 0.60]) for t in t_post]
    t_del = [(t, [0.0, max(0.0, 5.0 - (t - 13.0) * 1.2)]) for t in [round(13.0 + i * 0.2, 1) for i in range(40)]]
    colours = {
        '11': {'samples': [{'time_s': 18.0, 'prediction': 'red'}]},
        '20': {'samples': [{'time_s': 14.0, 'prediction': 'yellow'}]},
    }
    rec = {'event_id': 'L6', 'crossing_time_s': 12.0,
           'proposal': {'time_s': 18.0, 'panel': 'right', 'receiving_tracker_id': 20}}
    res = effect(
        rec, {'right': {10: t10, 11: t11, 20: t_del}}, house_radius_m=1.829, stone_radius_m=0.139,
        hog_y_by_panel={'right': 6.401}, settings=DEFAULTS, search_end_s=20.8,
        colours=colours, groups=['red', 'yellow'],
    )
    row = next(s for s in res['stones'] if s['before_tracker_id'] == 10)
    assert row['after_tracker_id'] == 11 and row['colour'] == 'red'
    assert row['colour_basis'] == 'linked_after_track_sample_nearest_settled_board'
    assert res['points_lying_after']['status'] == 'conditional_on_supplied_observations'
