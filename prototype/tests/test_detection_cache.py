import json
from pathlib import Path
import pytest
from prototype.detection_cache import DetectionCache,digest


def cache(tmp_path):
    (tmp_path/'protocol.json').write_text(json.dumps({'source_sha256':'s','model':{'weights':'w'},'opencv_build_sha256':'d',
        'code_sha256':{'stone_detector.py':digest(Path(__file__).parents[1]/'stone_detector.py')}}))
    (tmp_path/'config.json').write_text(json.dumps({'detector_confidence':.1}))
    (tmp_path/'observations.jsonl').write_text(''.join(json.dumps({'frame_index':i,'detections':[{'test':i}],'detector_wall_seconds':2.})+'\n' for i in [5,8]))
    return DetectionCache(tmp_path,source_sha256='s',model={'weights':'w'},confidence=.1,decoder_sha256='d')


def test_exact_frame_lookup_and_runtime_accounting(tmp_path):
    c=cache(tmp_path)
    assert c.get(4) is None
    assert c.get(5)['detections']==[{'test':5}]
    assert c.get(6) is None
    assert c.get(8)['wall_seconds']==0
    assert c.get(9) is None
    assert c.reused==2 and c.prior_detector_seconds==4
    c.close()


def test_changed_model_is_not_reused(tmp_path):
    c=cache(tmp_path);c.close()
    with pytest.raises(ValueError,match='model/runtime mismatch'):
        DetectionCache(tmp_path,source_sha256='s',model={'weights':'other'},confidence=.1,decoder_sha256='d')


def test_cache_mutation_is_detected(tmp_path):
    c=cache(tmp_path)
    with (tmp_path/'observations.jsonl').open('a') as f:f.write('\n')
    with pytest.raises(ValueError,match='changed during run'):c.close()


def prefix(tmp_path):
    c=cache(tmp_path);c.close()
    protocol=json.loads((tmp_path/'protocol.json').read_text())
    protocol.update(source_fps=30,source_interval_s=[5/30,1.],sample_step_frames=3)
    (tmp_path/'protocol.json').write_text(json.dumps(protocol))
    rows=[{'frame_index':i,'time_s':i/30,'detections':[],'detector_wall_seconds':2.} for i in [5,8]]
    (tmp_path/'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows)+'{"uncommitted":')
    (tmp_path/'progress.json').write_text(json.dumps({'samples':2,'source_time_s':8/30}))


def test_resume_ignores_uncommitted_tail_and_falls_through_to_fresh_detection(tmp_path):
    prefix(tmp_path)
    c=DetectionCache(tmp_path,source_sha256='s',model={'weights':'w'},confidence=.1,decoder_sha256='d',prefix_samples=2)
    assert c.get(5)['reused_from_cache'] and c.get(8)['reused_from_cache']
    assert c.get(11) is None
    assert c.reused==2
    assert not c.provenance['committed_prefix']['complete_requested_scan']
    c.close()


def test_resume_rejects_changed_progress_and_missing_committed_frames(tmp_path):
    prefix(tmp_path)
    from prototype.detection_cache import verify_committed_prefix
    with pytest.raises(ValueError,match='prefix changed'):
        DetectionCache(tmp_path,source_sha256='s',model={'weights':'w'},confidence=.1,decoder_sha256='d',prefix_samples=1)
    p=tmp_path/'observations.jsonl';rows=p.read_text().splitlines();p.write_text(rows[0]+'\n')
    with pytest.raises(ValueError,match='Incomplete committed'):
        verify_committed_prefix(tmp_path)
