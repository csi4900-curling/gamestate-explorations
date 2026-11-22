import json
import pytest
from prototype.tests.test_workbench import app


def completed_scan(app):
    asset=app.register_video(app.root/'video.mp4')
    id=app.prepare({'video_id':asset['id'],'start_s':0.,'end_s':1.})
    folder=app.data/'jobs'/id/'observations';folder.mkdir()
    rows=[{'frame_index':i,'time_s':i/30,'detections':[],'tracked_observations':[]} for i in range(0,30,6)]
    (folder/'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (folder/'events.json').write_text(json.dumps({'status':'development_complete_event_stage','source_sha256':asset['source_sha256'],'source_fps':30,'source_interval_s':[0.,1.],'sample_step_frames':6,'sampled_frames':5}))
    (folder/'config.json').write_text('{}');(folder/'protocol.json').write_text('{}')
    app.update(id,state='done')
    return asset,id,folder


def test_detection_reuse_pins_complete_source_inputs_and_recomputes_geometry(app):
    asset,old,folder=completed_scan(app)
    id=app.prepare({'video_id':asset['id'],'start_s':0.,'end_s':1.,'detection_cache_job_id':old})
    spec=json.load(open(app.data/'jobs'/id/'spec.json'))
    assert spec['detection_cache']['job_id']==old
    assert spec['detection_cache']['scan_verification']['verified_sampled_frames']==5
    assert set(spec['detection_cache']['sha256'])=={'events.json','protocol.json','config.json','observations.jsonl'}
    assert 'reused_observations_from' not in spec
    assert not (app.data/'jobs'/id/'observations').exists()
    assert app.job(old)['has_completed_detector_scan']


def test_incomplete_or_different_interval_cache_is_rejected(app):
    asset,id,folder=completed_scan(app)
    with pytest.raises(ValueError,match='exact analysis interval'):
        app.prepare({'video_id':asset['id'],'start_s':.1,'end_s':.9,'detection_cache_job_id':id})
    lines=(folder/'observations.jsonl').read_text().splitlines()
    (folder/'observations.jsonl').write_text('\n'.join(lines[:-1])+'\n')
    with pytest.raises(ValueError,match='Incomplete scan'):
        app.prepare({'video_id':asset['id'],'start_s':0.,'end_s':1.,'detection_cache_job_id':id})


def test_interrupted_committed_prefix_is_explicit_and_preserves_failure(app):
    asset,old,folder=completed_scan(app)
    events=json.loads((folder/'events.json').read_text())
    (folder/'events.json').unlink()
    (folder/'protocol.json').write_text(json.dumps(events))
    (folder/'progress.json').write_text(json.dumps({'samples':3,'source_time_s':.4}))
    # Invalid/uncommitted tail must never enter the tracker replay.
    rows=(folder/'observations.jsonl').read_text().splitlines()[:3]
    (folder/'observations.jsonl').write_text('\n'.join(rows)+'\n{"unfinished":')
    app.update(old,state='interrupted')
    assert app.job(old)['committed_detector_prefix']['verified_sampled_frames']==3
    id=app.prepare({'video_id':asset['id'],'start_s':0.,'end_s':1.,'detection_cache_job_id':old})
    spec=json.loads((app.data/'jobs'/id/'spec.json').read_text())
    assert spec['detection_cache']['prefix_samples']==3
    assert not spec['detection_cache']['scan_verification']['complete_requested_scan']
    assert 'progress.json' in spec['detection_cache']['sha256']
    assert app.job(old)['state']=='interrupted'
    assert not (folder/'events.json').exists()
    with pytest.raises(ValueError,match='start on the saved grid'):
        app.prepare({'video_id':asset['id'],'start_s':.1,'end_s':1.,'detection_cache_job_id':old})
    app.update(old,state='running')
    with pytest.raises(ValueError,match='no verified committed prefix'):
        app.prepare({'video_id':asset['id'],'start_s':0.,'end_s':1.,'detection_cache_job_id':old})
