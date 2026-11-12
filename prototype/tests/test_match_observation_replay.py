import io
import json
from types import SimpleNamespace

import pytest

from prototype.match_observation_replay import MatchObservationReplay


def setup_cache(tmp_path):
    protocol = dict(source_sha256='video', source_fps=30, source_size_px=[1920,1080],
                    sample_step_frames=3, opencv_build_sha256='decoder', source_interval_s=[0,1])
    provenance = dict(config_sha256='config', code_sha256={'core':'code'},
                      ocr_versions={'ocr':'version'}, ocr_model_sha256={'model':'hash'},
                      reference_sha256={'reference':'hash'})
    row = dict(frame_index=0, time_s=0, detections=[{'pixel':[10,20]}], tracked_observations=[])
    board = dict(frame_index=0, time_s=0, boards={})
    for name, data in [('protocol.json',protocol), ('match-observation-protocol.json',provenance),
                       ('observations.jsonl',row), ('match-observations.jsonl',board)]:
        (tmp_path/name).write_text(json.dumps(data)+'\n')
    observer = SimpleNamespace(provenance=provenance,
        config={'geometry_mode':'original_split_geometry_with_anchor_reuse'},
        stream=io.StringIO(), count=0)
    return observer, protocol, row


def close_inputs(replay):
    for stream in replay.streams:
        stream.close()


def test_source_mismatch_rejected_before_replay(tmp_path):
    observer, protocol, _ = setup_cache(tmp_path)
    with pytest.raises(ValueError, match='source_sha256'):
        MatchObservationReplay(observer, tmp_path, {**protocol, 'source_sha256':'other'})


def test_changed_detection_cannot_reuse_old_projected_stones(tmp_path):
    observer, protocol, row = setup_cache(tmp_path)
    replay = MatchObservationReplay(observer, tmp_path, protocol)
    try:
        with pytest.raises(ValueError, match='prediction differs: detections'):
            replay.observe(None, {**row, 'detections':[]})
        assert observer.count == 0
        assert observer.stream.getvalue() == ''
    finally:
        close_inputs(replay)


def test_append_to_cache_is_not_silently_accepted(tmp_path):
    observer, protocol, row = setup_cache(tmp_path)
    replay = MatchObservationReplay(observer, tmp_path, protocol)
    try:
        with (tmp_path/'match-observations.jsonl').open('a') as f:
            f.write('{}\n')
        with pytest.raises(ValueError, match='cache changed'):
            replay.observe(None, row)
    finally:
        close_inputs(replay)
