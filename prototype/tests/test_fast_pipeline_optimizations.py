import numpy as np
import pytest

from prototype.calibrated_camera_geometry import CalibratedCameraGeometry, panel_features
from prototype.tests.test_rink_calibration import bundle


def test_fast_half_scale_registration_skips_foreground_when_accepted(tmp_path, monkeypatch):
    from prototype import camera_foreground

    class FakeForeground:
        def __init__(self, *args, **kwargs):
            self.frames = 0
            self.seconds = 0.0
            self.provenance = {'backend': 'synthetic test stub'}

        def mask(self, image):
            self.frames += 1
            return np.zeros(image.shape[:2], np.uint8)

    monkeypatch.setattr(camera_foreground, 'CameraForeground', FakeForeground)
    path, _, image = bundle(tmp_path)
    g = CalibratedCameraGeometry(
        path,
        alignment='static_feature_similarity',
        foreground_checkpoint='test-stub',
        foreground_sha256='stub',
        fast_scale=0.5,
        fast_nfeatures=1200,
        parallel_panels=True,
    )
    try:
        # Reference frame still runs foreground once during init.
        assert g.foreground.frames == 1
        result = g.observe(image, 1.0)
        assert all(v[0] is not None for v in result.values())
        assert all(v[1].get('registration_tier') == 'fast_scale_0.5' for v in result.values())
        # Accepted on fast path: no current-frame foreground mask needed.
        assert g.foreground.frames == 1
        prov = g.provenance()
        assert prov['fast_accepted'] == 2
        assert prov['fallback_attempts'] == 0
        assert prov['fast_scale'] == 0.5
        assert prov['parallel_panels'] is True
    finally:
        g.close()


def test_fast_half_scale_falls_back_to_full_res_and_abstains_on_blank_frame(tmp_path, monkeypatch):
    from prototype import camera_foreground

    class FakeForeground:
        def __init__(self, *args, **kwargs):
            self.frames = 0
            self.seconds = 0.0
            self.provenance = {'backend': 'synthetic test stub'}

        def mask(self, image):
            self.frames += 1
            return np.zeros(image.shape[:2], np.uint8)

    monkeypatch.setattr(camera_foreground, 'CameraForeground', FakeForeground)
    path, _, _ = bundle(tmp_path)
    g = CalibratedCameraGeometry(
        path,
        alignment='static_feature_similarity',
        foreground_checkpoint='test-stub',
        foreground_sha256='stub',
        fast_scale=0.5,
        fast_nfeatures=1200,
        parallel_panels=True,
    )
    try:
        blank = np.zeros((1080, 1920, 3), dtype=np.uint8)
        result = g.observe(blank, 1.0)
        assert all(v[0] is None for v in result.values())
        assert all(v[1].get('registration_tier') == 'full_res_fallback' for v in result.values())
        # Blank frame triggers one shared foreground mask during fallback, not two.
        assert g.foreground.frames == 2
        assert g.provenance()['fallback_attempts'] == 2
        assert g.provenance()['fast_accepted'] == 0
    finally:
        g.close()


def test_panel_features_scaled_maps_keypoints_back_to_1080p():
    rng = np.random.default_rng(7)
    image = rng.integers(120, 255, (1080, 1920, 3), np.uint8)
    pts_left, desc_left = panel_features(image, 'left', scale=0.5, nfeatures=400)
    pts_right, desc_right = panel_features(image, 'right', scale=0.5, nfeatures=400)
    assert len(pts_left) > 0 and desc_left is not None
    assert len(pts_right) > 0 and desc_right is not None
    assert float(pts_left[:, 0].max()) <= 960.5
    assert float(pts_right[:, 0].min()) >= 959.5
    assert float(pts_right[:, 0].max()) <= 1920.5


def test_fast_scale_rejects_invalid_values(tmp_path):
    path, _, _ = bundle(tmp_path)
    with pytest.raises(ValueError, match='fast_scale'):
        CalibratedCameraGeometry(path, alignment='static_feature_similarity', fast_scale=1.0)
    with pytest.raises(ValueError, match='fast_scale'):
        CalibratedCameraGeometry(path, alignment='static_feature_similarity', fast_scale=0.05)


def test_batched_track_colours_matches_single_frame_calls(tmp_path, monkeypatch):
    import json
    from prototype import track_colours
    from prototype.detection_cache import digest

    video = tmp_path / 'clip.mp4'
    import cv2

    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'mp4v'), 10.0, (160, 120))
    for i in range(25):
        frame = np.full((120, 160, 3), 40 + i * 3, dtype=np.uint8)
        frame[20:60, 20:60] = (0, 0, 220)  # red-ish
        frame[20:60, 100:140] = (0, 220, 220)  # yellow-ish
        writer.write(frame)
    writer.release()

    run_dir = tmp_path / 'obs'
    run_dir.mkdir()
    (run_dir / 'protocol.json').write_text(json.dumps({'source_sha256': digest(video)}))
    with (run_dir / 'match-observations.jsonl').open('w') as f:
        for idx in range(25):
            row = {
                'frame_index': idx,
                'time_s': idx / 10.0,
                'boards': {
                    'left': {
                        'stones': [{
                            'tracker_id': 1,
                            'body_point_support': {'status': 'full_body_box'},
                            'bbox_xyxy': [20.0, 20.0, 60.0, 60.0],
                        }]
                    },
                    'right': {
                        'stones': [{
                            'tracker_id': 2,
                            'body_point_support': {'status': 'full_body_box'},
                            'bbox_xyxy': [100.0, 20.0, 140.0, 60.0],
                        }]
                    },
                },
            }
            f.write(json.dumps(row) + '\n')

    calls = []

    class FakeBatchedColourModel:
        def __init__(self, _cfg):
            self.provenance = {'backend': 'fake-batched'}

        def classify_crops(self, crops_bgr, *, batch_size=64):
            calls.append(len(crops_bgr))
            out = []
            for idx, crop in enumerate(crops_bgr):
                if crop is None or crop.size == 0:
                    out.append({'detection_index': idx, 'status': 'unavailable_invalid_crop', 'prediction': None})
                else:
                    mean_g = float(crop[:, :, 1].mean())
                    pred = 'yellow' if mean_g > 100 else 'red'
                    out.append({'detection_index': idx, 'status': 'unverified_colour_ranking',
                                'prediction': pred, 'cosine_similarity': {'red': 0.1, 'yellow': 0.9}})
            return out

    from prototype import stone_colour_model
    monkeypatch.setattr(stone_colour_model, 'StoneColourModel', FakeBatchedColourModel)
    out_path = tmp_path / 'track-colours.json'
    result = track_colours.run(
        public_run=run_dir,
        video=video,
        config_path=tmp_path / 'unused.json',
        output=out_path,
        settings={'samples_per_track': 5, 'minimum_track_observations': 20, 'batch_size': 64},
    )
    assert result['tracks'] == {'left': {'1': 'red'}, 'right': {'2': 'yellow'}}
    # 10 crops across 5 frames flushed in a single batch call!
    assert calls == [10]


def test_stone_history_allows_scheduled_inactive_skips_between_throws_but_not_real_gaps():
    from prototype.stone_history import histories

    def make_event(eid, arrival, settled, change):
        stone = dict(in_play_before=change != 'delivered', in_play_after=True, before_m=[0, 0], after_m=[0, 0],
                     before_tracker_id=4, after_tracker_id=4, change=change, colour='red',
                     colour_differs_along_track=False)
        return dict(event_id=eid, crossing_time_s=arrival, arrival_time_s=arrival, settle_interval_s=settled,
                    panel='right', stones=[stone])

    events = [make_event('A', 1, [3, 4], 'delivered'), make_event('B', 7, [9, 10], 'unchanged')]
    frames = []
    for i in range(4, 11):
        if i in (5, 6):
            # Inactive interval between throws: scheduled skip is allowed.
            board = {'registration': {'status': 'geometry_skipped_inactive_interval'},
                     'stones': [dict(tracker_id=4, height_adjusted_local_m=None)]}
        else:
            board = {'registration': {'status': 'source_calibration_registered'},
                     'stones': [dict(tracker_id=4, height_adjusted_local_m=[0, 0])]}
        frames.append(dict(time_s=i, frame_index=i, current_end=1, boards={'right': board}))

    res = histories({'events': events}, frames, 0.139, 1, 1)
    assert res['membership']['B/0'] == 'A/0'
    assert not res['stops']

    # Real alignment_unverified gap between throws MUST still break continuity!
    frames[1]['boards']['right']['registration']['status'] = 'alignment_unverified'
    res_gap = histories({'events': events}, frames, 0.139, 1, 1)
    assert res_gap['membership']['B/0'] == 'B/0'
    assert 'A/0' in res_gap['stops']


def test_window_merging_and_membership():
    from prototype.learned_event_pipeline import _merge_windows, _in_windows

    w = _merge_windows([(-5, 10), (8, 20), (30, 50), (45, 70)], 0.0, 60.0)
    assert w == [(0.0, 20.0), (30.0, 60.0)]
    assert _in_windows(0.0, w)
    assert _in_windows(15.0, w)
    assert not _in_windows(25.0, w)
    assert _in_windows(60.0, w)

