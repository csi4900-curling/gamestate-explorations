from prototype.camera_motion_role import recover_missing_role
from prototype.directional_handoff import metric_crossings, resolve_short_receiving_approaches
from prototype.throw_effect import DEFAULTS, in_play, quiet_interval


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
