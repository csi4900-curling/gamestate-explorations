import json

from prototype.detection_cache import digest
from prototype.post_throw_state import build_board_viewer, suppress_duplicates


def test_upstream_suppression_preserves_evidence_and_separate_stones():
    stones = [{'tracker_id': i, 'bbox_xyxy': box, 'confidence': c}
              for i, box, c in [(1, [0, 0, 10, 10], .9), (2, [.1, 0, 10.1, 10], .8), (3, [30, 0, 40, 10], .7)]]
    board, suppressed = suppress_duplicates({'stones': stones}, .7)
    assert [s['tracker_id'] for s in board['stones']] == [1, 3]
    assert [s['tracker_id'] for s in suppressed] == [2]
    assert len(stones) == 3


def test_build_board_viewer_uses_effects_and_track_colours_without_hmm(tmp_path):
    video = tmp_path / 'v.mp4'
    video.write_bytes(b'board viewer fixture')
    sha = digest(video)
    pub = tmp_path / 'observations'
    pub.mkdir()
    (pub / 'protocol.json').write_text(json.dumps({
        'source_sha256': sha, 'source_size_px': [640, 360],
        'source_fps': 5.0, 'sample_step_frames': 1, 'source_interval_s': [0.0, 1.0],
    }))
    (pub / 'match-observations.jsonl').write_text(json.dumps({
        'time_s': 0.2, 'frame_index': 1,
        'boards': {
            'left': {'stones': [{'tracker_id': 7, 'pixel': [100.0, 150.0], 'bbox_xyxy': [90, 140, 110, 160],
                                 'confidence': 0.9, 'height_adjusted_local_m': [0.1, 0.2], 'ice_plane_local_m': [0.1, 0.2]}]},
            'right': {'stones': []},
        },
        'last_observed_totals': {},
    }) + '\n')
    eff = tmp_path / 'effects.json'
    eff.write_text(json.dumps({
        'source_sha256': sha,
        'events': [{'event_id': 'M00001', 'crossing_time_s': 0.2, 'status': 'review_proposal',
                    'panel': 'left', 'delivered_tracker_id': 7, 'settle_interval_s': [0.4, 0.8],
                    'points_lying_after': {'conditional_points_by_group': {'red': 1, 'yellow': 0},
                                           'status': 'conditional_on_supplied_observations'}}],
    }))
    tc = tmp_path / 'track-colours.json'
    tc.write_text(json.dumps({'tracks': {'left': {'7': 'red'}, 'right': {}}, 'evidence': {'left': {}, 'right': {}}}))
    cfg = tmp_path / 'state.json'
    cfg.write_text(json.dumps({'house_radius_m': 1.829, 'stone_radius_m': 0.139, 'duplicate_nms_iou': 0.7}))
    out = tmp_path / 'boards'
    payload = build_board_viewer(public_run=pub, effects=eff, config_path=cfg, video=video, output=out, track_colours=tc)
    assert payload['summary']['review_proposals'] == 1
    assert (out / 'index.html').exists() and (out / 'states.json').exists() and (out / 'board-timeline/0.js').exists()
    chunk_text = (out / 'board-timeline/0.js').read_text()
    assert '"red"' in chunk_text
