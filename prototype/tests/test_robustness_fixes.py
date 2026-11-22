import json

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

    # Stale departure >35s before an unrelated stone approach MUST NOT link.
    handoffs_late = {
        'L00001': {
            'status': 'unresolved',
            'role_evidence': {'role': 'departure', 'panel': 'left'},
            'interval_s': [10.0, 90.0],
            'candidates': [],
        }
    }
    late_rows = []
    for i, y in enumerate([16.0, 14.0, 12.0, 10.0, 8.0, 6.7]):
        late_rows.append({'time_s': 58.0 + i * 1.0, 'boards': {'left': {'stones': []}, 'right': {'stones': [
            {'tracker_id': 99, 'height_adjusted_local_m': [0.0, y], 'pixel': [1400.0, 700.0 - i * 10], 'confidence': 0.9}
        ]}}})
    assert resolve_short_receiving_approaches(
        events, handoffs_late, late_rows, hog_y_by_panel={'left': -6.401, 'right': 6.401}
    ) == []
    assert handoffs_late['L00001']['status'] == 'unresolved'


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


def test_pre_hog_registered_before_window_recovers_resting_stones_when_pre_arrival_unregistered():
    # Delivered stone 20 appears far beyond hog line at t=10.0 (geometry skipped until t=11.0),
    # crosses hog line (y=6.401) around t=15.0, and settles at t=20.0.
    # Resting red stone 10 sits on button (0.1, 0.1) throughout, with a late noisy yellow sample at t=60.0.
    t_reg = [round(11.0 + i * 0.2, 1) for i in range(65)]  # 11.0 .. 23.8 (registered)
    t_del = [(round(10.0 + i * 0.2, 1), None) for i in range(5)] + [
        (t, [0.5, max(0.5, 12.0 - (t - 11.0) * 1.4)]) for t in t_reg
    ]
    t10 = [(t, [0.1, 0.1]) for t in t_reg]
    colours = {
        '10': {'samples': [{'time_s': 8.0, 'prediction': 'red'}, {'time_s': 60.0, 'prediction': 'yellow'}]},
        '20': {'samples': [{'time_s': 15.0, 'prediction': 'yellow'}]},
    }
    rec = {'event_id': 'M1', 'crossing_time_s': 15.0,
           'proposal': {'time_s': 20.0, 'panel': 'right', 'receiving_tracker_id': 20}}
    res = effect(
        rec, {'right': {10: t10, 20: t_del}}, house_radius_m=1.829, stone_radius_m=0.139,
        hog_y_by_panel={'right': 6.401}, settings=DEFAULTS, search_end_s=23.8,
        colours=colours, groups=['red', 'yellow'], registered_times=t_reg,
    )
    assert res['before_window_basis'] == 'registered_pre_hog_fallback'
    assert res['in_play']['before'] == 1
    row10 = next(s for s in res['stones'] if s['after_tracker_id'] == 10)
    assert row10['before_tracker_id'] == 10 and row10['change'] == 'unchanged'
    assert row10['colour'] == 'red'  # pre-impact not_after=True, not late noisy t=60s yellow!
    assert res['points_lying_after']['conditional_points_by_group'] == {'red': 1, 'yellow': 0}


def test_post_settle_stationary_occlusion_recovers_resting_stone_not_knockout():
    # Resting red stone 10 at (0.15, 0.40) is occluded by a player during settle (~18-20s)
    # and reappears as track 11 stationary at (0.16, 0.40) from 22.0-26.0s.
    # Resting red stone 12 at (-1.5, 0.0) is genuinely knocked out and never reappears.
    t_pre = [round(10.0 + i * 0.2, 1) for i in range(15)]
    t_all = [round(10.0 + i * 0.2, 1) for i in range(85)]  # 10.0 .. 26.8
    t10 = [(t, [0.15, 0.40]) for t in t_pre]
    t11 = [(t, [0.16, 0.40]) for t in t_all if 22.0 <= t <= 26.0]
    t12 = [(t, [-1.50, 0.00]) for t in t_pre]
    t_del = [(t, [-1.20, max(-0.20, 5.0 - (t - 13.0) * 1.2)]) for t in t_all if t >= 13.0]
    colours = {
        '10': {'samples': [{'time_s': 11.0, 'prediction': 'red'}]},
        '11': {'samples': [{'time_s': 24.0, 'prediction': 'red'}]},
        '12': {'samples': [{'time_s': 11.0, 'prediction': 'red'}]},
        '20': {'samples': [{'time_s': 14.0, 'prediction': 'yellow'}]},
    }
    rec = {'event_id': 'L54', 'crossing_time_s': 12.0,
           'proposal': {'time_s': 19.0, 'panel': 'left', 'receiving_tracker_id': 20}}
    res = effect(
        rec, {'left': {10: t10, 11: t11, 12: t12, 20: t_del}}, house_radius_m=1.829, stone_radius_m=0.139,
        hog_y_by_panel={'left': -6.401}, settings=DEFAULTS, search_end_s=28.0,
        colours=colours, groups=['red', 'yellow'],
    )
    row10 = next(s for s in res['stones'] if s['before_tracker_id'] == 10)
    assert row10['after_tracker_id'] == 11
    assert row10['link'] == 'reappeared_after_settle_occlusion'
    assert row10['change'] == 'unchanged'
    assert row10['colour'] == 'red'
    row12 = next(s for s in res['stones'] if s['before_tracker_id'] == 12)
    assert row12['change'] == 'left_view_or_lost'
    assert len(res['occluded_stones_recovered']) == 1
    assert res['points_lying_after']['conditional_points_by_group'] == {'red': 1, 'yellow': 0}


def test_short_unconfirmed_pixel_line_flicker_is_filtered_in_aggregate(tmp_path):
    from prototype.detection_cache import digest
    from prototype.directional_event_aggregate import build
    video = tmp_path / 'v.bin'
    video.write_bytes(b'flicker fixture')
    run = tmp_path / 'run'
    run.mkdir()
    observations, boards = [], []
    # Track 99 flickers for 2 frames near left line without crossing metric hog or arriving on right.
    for i in range(6):
        t = i * 0.2
        raw = {'time_s': t, 'frame_index': i, 'tracked_observations': []}
        state = {'time_s': t, 'frame_index': i, 'boards': {
            p: {'stones': [], 'registration': {'status': 'fixture'},
                'homography_normalized_pixels_to_local_metres': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
            for p in ('left', 'right')
        }}
        if i in (1, 2):
            px = [100.0, 200.0 - 5.0 * i]
            raw['tracked_observations'].append({
                'track_id': 99, 'point_normalized': [px[0] / 640, px[1] / 360],
                'pixel': px, 'bbox_xyxy': [90, 180, 110, 210], 'confidence': 0.6,
            })
            state['boards']['left']['stones'].append({
                'tracker_id': 99, 'pixel': px, 'confidence': 0.6,
                'ice_plane_local_m': [0.0, -5.0 - 0.1 * i], 'height_adjusted_local_m': [0.0, -5.0 - 0.1 * i],
            })
        observations.append(raw)
        boards.append(state)
    flicker = {
        'id': 'L00055', 'track_id': 99, 'crossing_time_s': 0.3, 'crossing_point_normalized': [100 / 640, 192 / 360],
        'observed_bracket_s': [0.2, 0.4],
        'observations': [
            {'time_s': 0.2, 'pixel': [100.0, 195.0]},
            {'time_s': 0.4, 'pixel': [100.0, 190.0]},
        ],
    }
    (run / 'events.json').write_text(json.dumps({
        'source_sha256': digest(video), 'source_size_px': [640, 360],
        'source_interval_s': [0.0, 2.0], 'sample_step_frames': 1, 'source_fps': 5.0,
        'events': [flicker],
    }))
    for name, rows in (('observations.jsonl', observations), ('match-observations.jsonl', boards)):
        (run / name).write_text(''.join(json.dumps(r) + '\n' for r in rows))
    out = build(video, run, tmp_path / 'agg.json', hog_y_by_panel={'left': -6.401, 'right': 6.401})
    assert out['events'] == []
    dropped = out['provenance']['filtered_short_unconfirmed_pixel_line_flickers']
    assert len(dropped) == 1 and dropped[0]['event_id'] == 'L00055'


def test_state_timeline_counts_promoted_aggregate_events(tmp_path):
    from prototype.scripts.build_state_timeline import build as build_state
    (tmp_path / 'events.json').write_text(json.dumps({'events': [{'id': 'L1', 'crossing_time_s': 10.0}]}))
    (tmp_path / 'agg.json').write_text(json.dumps({'events': [
        {'candidate_id': 'L1', 'event_prediction': {'crossing_time_s': 10.0},
         'segments': [{'role': 'receiving', 'rink_panel': 'left'}]},
        {'candidate_id': 'M1', 'event_prediction': {'crossing_time_s': 20.0},
         'segments': [{'role': 'receiving', 'rink_panel': 'right'}]},
        {'candidate_id': 'M2', 'event_prediction': {'crossing_time_s': 30.0},
         'segments': [{'role': 'receiving', 'rink_panel': 'right'}]},
    ]}))
    (tmp_path / 'obs.jsonl').write_text(json.dumps({
        'time_s': 35.0, 'boards': {'left': {'stones': []}, 'right': {'stones': []}},
    }) + '\n')
    (tmp_path / 'score.jsonl').write_text('')
    res = build_state(tmp_path / 'events.json', tmp_path / 'obs.jsonl', tmp_path / 'score.jsonl',
                      aggregate_rink_path=tmp_path / 'agg.json')
    assert res['samples'][0]['deliveries_before'] == 3


def test_calibrated_hog_line_clipped_to_panel_half():
    from prototype.workbench import _clip_segment_x
    # Right-panel line bleeding across x=0.5 centerline to x=0.437 must clip cleanly to [0.5, 1.0].
    clipped = _clip_segment_x((0.437, 0.580), (1.040, 0.592), 0.5, 1.0)
    assert clipped is not None
    assert clipped[0][0] == 0.5 and clipped[1][0] == 1.0
    assert 0.580 < clipped[0][1] < clipped[1][1] < 0.592
