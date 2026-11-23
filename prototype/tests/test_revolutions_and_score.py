import json
import numpy as np

from prototype.match_score_and_rocks import build, rock_pair_label, segment_ends
from prototype.throw_revolutions import estimate_period, fixed_rate_loop_sense, lag_curve


def test_segment_ends_detects_direction_reversals_and_ignores_single_glitch():
    throws = (
        [{'direction': 'left_to_right'}] * 6
        + [{'direction': 'right_to_left'}]  # isolated single-throw glitch
        + [{'direction': 'left_to_right'}] * 4
        + [{'direction': 'right_to_left'}] * 8
    )
    ends = segment_ends(throws)
    assert ends[:11] == [1] * 11
    assert ends[11:] == [2] * 8
    assert rock_pair_label(1) == '1-2 (Lead)'
    assert rock_pair_label(4) == '3-4 (Second)'
    assert rock_pair_label(7) == '7-8 (Fourth/Skip)'
    # An unresolved false-positive candidate inside a 16-throw end must not overflow into a fake end.
    with_fp = (
        [{'direction': 'left_to_right', 'board_status': 'review_proposal'}] * 8
        + [{'direction': 'left_to_right', 'board_status': 'unresolved'}]
        + [{'direction': 'left_to_right', 'board_status': 'review_proposal'}] * 8
        + [{'direction': 'right_to_left', 'board_status': 'review_proposal'}] * 6
    )
    ends_fp = segment_ends(with_fp)
    assert ends_fp[:17] == [1] * 17
    assert ends_fp[17:] == [2] * 6


def test_match_score_and_rocks_separates_provisional_board_and_ocr_unknown(tmp_path):
    agg = {
        'events': [
            {'candidate_id': 'E1', 'colour': 'red', 'segments': [{'role': 'departure', 'rink_panel': 'left'}, {'role': 'receiving', 'rink_panel': 'right', 'geometry_samples': [{'time_s': 10.0, 'rink_position_m': [0.0, 6.0]}, {'time_s': 11.0, 'rink_position_m': [0.0, 4.0]}, {'time_s': 12.0, 'rink_position_m': [0.1, 2.0]}, {'time_s': 13.0, 'rink_position_m': [0.2, 0.5]}]}]},
            {'candidate_id': 'E2', 'colour': 'yellow', 'segments': [{'role': 'departure', 'rink_panel': 'left'}, {'role': 'receiving', 'rink_panel': 'right', 'geometry_samples': []}]},
            {'candidate_id': 'E3', 'colour': 'red', 'segments': [{'role': 'departure', 'rink_panel': 'right'}, {'role': 'receiving', 'rink_panel': 'left', 'geometry_samples': []}]},
            {'candidate_id': 'E4', 'colour': 'yellow', 'segments': [{'role': 'departure', 'rink_panel': 'right'}, {'role': 'receiving', 'rink_panel': 'left', 'geometry_samples': []}]},
        ]
    }
    eff = {
        'source_sha256': 'abc',
        'events': [
            {'event_id': 'E1', 'crossing_time_s': 10.0, 'status': 'review_proposal', 'panel': 'right', 'settle_interval_s': [14.0, 16.0], 'stones': [{'change': 'delivered', 'colour': 'red', 'colour_differs_along_track': False}], 'points_lying_after': {'conditional_points_by_group': {'red': 1, 'yellow': 0}}},
            {'event_id': 'E2', 'crossing_time_s': 40.0, 'status': 'review_proposal', 'panel': 'right', 'settle_interval_s': [50.0, 52.0], 'stones': [{'change': 'delivered', 'colour': 'yellow', 'colour_differs_along_track': False}], 'points_lying_after': {'conditional_points_by_group': {'red': 0, 'yellow': 2}}},
            {'event_id': 'E3', 'crossing_time_s': 120.0, 'status': 'review_proposal', 'panel': 'left', 'settle_interval_s': [130.0, 132.0], 'stones': [{'change': 'delivered', 'colour': 'red', 'colour_differs_along_track': False}], 'points_lying_after': {'conditional_points_by_group': {'red': 1, 'yellow': 0}}},
            {'event_id': 'E4', 'crossing_time_s': 160.0, 'status': 'review_proposal', 'panel': 'left', 'settle_interval_s': [170.0, 172.0], 'stones': [{'change': 'delivered', 'colour': 'yellow', 'colour_differs_along_track': False}], 'points_lying_after': {'conditional_points_by_group': {'red': 1, 'yellow': 0}}},
        ],
    }
    state = {'group_to_team': {'red': 'CAN', 'yellow': 'SWE'}}
    agg_p = tmp_path / 'agg.json'; agg_p.write_text(json.dumps(agg))
    eff_p = tmp_path / 'eff.json'; eff_p.write_text(json.dumps(eff))
    st_p = tmp_path / 'state.json'; st_p.write_text(json.dumps(state))
    out_p = tmp_path / 'sr.json'

    res = build(aggregate=agg_p, effects=eff_p, state_config=st_p, output=out_p)
    assert res['summary']['inferred_ends'] == 2
    assert res['summary']['provisional_final_total_from_board'] == {'CAN': 1, 'SWE': 2}
    assert res['ends'][0]['ocr_running_total_observation'] is None
    assert not res['summary']['official_scoring_verified']
    assert not res['summary']['physical_rock_identity_verified']
    assert len(res['rock_pair_summary']) == 2


def test_revolutions_lag_curve_and_fixed_rate_sense_on_synthetic_rotating_blob():
    # Create 150 frames (5 seconds @ 30 fps) with a coloured blob rotating at period T=2.0s (0.5 Hz).
    fps = 30.0
    t = np.arange(150) / fps
    period_s = 2.0
    images = []
    yy, xx = np.mgrid[0:40, 0:64]
    for ti in t:
        img = np.full((40, 64, 3), 180, dtype=np.uint8)
        ang = 2 * np.pi * ti / period_s
        cx = 32 + 12 * np.cos(ang)
        cy = 14 + 5 * np.sin(ang)
        mask = ((xx - cx) ** 2 + (yy - cy) ** 2) <= 25
        img[mask] = (20, 20, 220)  # bright red handle marker
        images.append(img)
    images = np.asarray(images)
    curve = lag_curve(t, images, min_overlap_s=1.2)
    est = estimate_period(curve)
    assert est is not None and est['basis'] == 'full_turn_peak'
    assert abs(est['period_s'] - period_s) < 0.15
    sense = fixed_rate_loop_sense(t, images, est['rate_hz'])
    assert sense['screen_loop_sense'] == 'clockwise'
    assert sense['explained_fraction'] > 0.8


def test_right_to_left_departure_uses_own_hog_crossing_for_spin_window(tmp_path):
    # Right-to-left throw: primary crossing_time_s is on the LEFT receiving panel (t=100s),
    # while the RIGHT departure segment crossed its own hog line at t=82s and ended at t=88s.
    import cv2
    from prototype.throw_revolutions import run as run_revolutions

    fps = 30.0
    video_path = tmp_path / 'clip.mp4'
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (160, 120))
    yy, xx = np.mgrid[0:120, 0:160]
    for fi in range(300):  # 0..10s
        frame = np.full((120, 160, 3), 180, dtype=np.uint8)
        ti = fi / fps
        ang = 2 * np.pi * ti / 2.0  # 2.0s period
        cx = 80 + 10 * np.cos(ang)
        cy = 50 + 4 * np.sin(ang)
        frame[((xx - cx) ** 2 + (yy - cy) ** 2) <= 20] = (20, 20, 220)
        writer.write(frame)
    writer.release()

    pub = tmp_path / 'obs'; pub.mkdir()
    (pub / 'protocol.json').write_text(json.dumps({'source_sha256': 'x', 'source_fps': fps, 'sample_step_frames': 3}))
    with (pub / 'match-observations.jsonl').open('w') as f:
        for fi in range(0, 300, 3):
            f.write(json.dumps({
                'frame_index': fi, 'time_s': fi / fps,
                'boards': {'left': {'stones': []}, 'right': {'stones': [{
                    'tracker_id': 7, 'bbox_xyxy': [50.0, 30.0, 110.0, 90.0],
                    'body_point_support': {'status': 'full_body_box'},
                }]}},
            }) + '\n')

    # Primary crossing is at 25.0s (receiving left panel), way past the right departure (0..9.9s)!
    agg = {'events': [{
        'candidate_id': 'R1',
        'event_prediction': {'crossing_time_s': 25.0},
        'segments': [{
            'role': 'departure', 'rink_panel': 'right', 'camera': 'right_split', 'tracker_id': 7,
            'pixel_points': [{'time_s': 0.0}, {'time_s': 9.9}],
            'hog_crossing_evidence': {'crossing_time_s': 4.5},
        }],
    }]}
    eff = {'events': [{'event_id': 'R1', 'status': 'review_proposal', 'panel': 'left',
                       'delivered_tracker_id': 99, 'arrival_time_s': 22.0, 'settle_interval_s': [28.0, 30.0]}]}
    (tmp_path / 'agg.json').write_text(json.dumps(agg))
    (tmp_path / 'eff.json').write_text(json.dumps(eff))
    out = run_revolutions(public_run=pub, aggregate=tmp_path / 'agg.json', effects=tmp_path / 'eff.json',
                          video=video_path, output=tmp_path / 'rev.json')
    ev = out['events'][0]
    assert ev['sending']['status'] == 'observed_period_estimate'
    assert abs(ev['sending']['period_s'] - 2.0) < 0.2
    # Travel time should start at sending interval start (~4.0s, near hog release), not parked time (0.0s).
    assert ev['modeled_whole_throw_estimate'] is not None
    assert ev['modeled_whole_throw_estimate']['travel_interval_s'][0] >= 3.9


def test_estimate_period_5hz_uses_time_based_smoothing_window():
    # At 5 Hz (step=0.2s), a narrow peak around 2.6s must not be flattened by a 1.0s boxcar.
    lags = np.arange(0.2, 6.0, 0.2)
    vals = np.exp(-0.5 * ((lags - 2.6) / 0.25) ** 2) * 0.45 + 0.05 * np.cos(2 * np.pi * lags / 2.6)
    curve = np.column_stack([lags, vals])
    est = estimate_period(curve)
    assert est is not None and est['period_s'] is not None
    assert abs(est['period_s'] - 2.6) <= 0.21
