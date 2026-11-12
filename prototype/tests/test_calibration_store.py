import json
import cv2
import numpy as np
from pathlib import Path
import pytest
from prototype.tests.test_workbench import app, imported
from prototype.tests.test_pinhole_calibration import physical_fixture
from prototype.rink_calibration import load_bundle


def confirm(app):
    textured=app.root/'textured.mp4'
    rng=np.random.default_rng(7);image=rng.integers(120,255,(320,640,3),dtype=np.uint8)
    writer=cv2.VideoWriter(str(textured),cv2.VideoWriter_fourcc(*'mp4v'),30,(640,320))
    for _ in range(30):writer.write(image)
    writer.release()
    video=app.register_video(textured);frame=app.calibrations.frame({'video_id':video['id'],'time_s':.2})
    panels={p:{**physical_fixture(p)[0],'frame_id':frame['id']} for p in ['left','right']}
    preview=app.calibrations.preview({'video_id':video['id'],'valid_interval_s':[0,1.],
                                     'panels':panels,'prediction_visible_during_annotation':False})
    assert preview['status']=='checks_passed'
    record=app.calibrations.confirm({'preview_id':preview['id'],'confirmed':True,'reviewer':'Synthetic test operator','operator_kind':'agent'})
    return video,frame,preview,record


def test_required_calibration_blocks_jobs_before_creating_output(app):
    app.profile['calibration_required']=True
    asset=app.register_video(app.root/'video.mp4')
    with pytest.raises(ValueError,match='Calibration required'):
        app.prepare({'video_id':asset['id'],'start_s':0,'end_s':1})
    assert not list((app.data/'jobs').iterdir())


def test_source_calibration_is_immutable_snapshotted_and_reusable(app):
    app.profile['calibration_required']=True
    video,frame,preview,record=confirm(app)
    request={'video_id':video['id'],'start_s':0.,'end_s':1.,'calibration_ids':[record['id']]}
    ids=[app.prepare(request),app.prepare(request)]
    for id in ids:
        job=app.data/'jobs'/id;config=json.load(open(job/'match.json'))
        assert config['geometry_mode']=='explicit_source_calibration_v1'
        bundle=load_bundle(config['source_calibration_bundle'],video['source_sha256'],[0,1])
        saved=bundle['calibrations'][0]
        assert saved['reviewer']=='Synthetic test operator'
        assert saved['operator_kind']=='agent'
        assert all(p['camera_model']['orthogonality_residual']<1e-12 for p in saved['panels'].values())
        assert saved['prediction_visible_during_annotation'] is False
        assert saved['panels']['left']['frame']['image_path'].startswith('calibration-frames/')
        assert saved['panels']['left']['frame']['image_sha256']==frame['image_sha256']
    assert app.calibrations.list(video['id'])[0]['id']==record['id']


def test_failed_preview_cannot_be_confirmed_or_hidden(app):
    video=app.register_video(app.root/'video.mp4');frame=app.calibrations.frame({'video_id':video['id'],'time_s':.1})
    panels={p:{**physical_fixture(p)[0],'frame_id':frame['id']} for p in ['left','right']}
    panels['right']['check_points'][0]['pixel_normalized'][1]+=.03
    preview=app.calibrations.preview({'video_id':video['id'],'valid_interval_s':[0,1],'panels':panels})
    assert preview['status']=='rejected'
    with pytest.raises(ValueError,match='failed its checks'):
        app.calibrations.confirm({'preview_id':preview['id'],'confirmed':True,'reviewer':'test'})
    assert (app.calibrations.root/'previews'/(preview['id']+'.json')).exists()
    assert app.calibrations.list(video['id'])==[]


def test_unconfirmed_and_other_source_calibration_rejected(app):
    video,frame,preview,record=confirm(app)
    with pytest.raises(ValueError,match='confirm'):
        app.calibrations.confirm({'preview_id':preview['id'],'confirmed':False,'reviewer':'test'})
    with pytest.raises(ValueError,match='another recording'):
        app.calibrations.selected([record['id']],'other source',[0,1])
    with pytest.raises(ValueError,match='inside the source'):
        app.calibrations.frame({'video_id':video['id'],'time_s':2})

