import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest

from prototype.spin.point_tracking import pair_angles, read_clip, digest


def test_pair_visibility_and_collapse_retained_as_unknown():
    xy=np.array([[[0.,0.],[10.,0.]],[[0.,0.],[0.,10.]],[[0.,0.],[1.,0.]]])
    angle,valid=pair_angles(xy,np.array([[1,1],[1,0],[1,1]],bool),[0,1])
    assert valid.tolist()==[True,False,False]
    assert angle[0]==pytest.approx(0)


def test_orientation_uses_full_source_coordinates_and_handedness():
    xy=np.array([[[100.,200.],[110.,200.]]])
    H=np.array([[0,-1,300],[1,0,-50],[0,0,1.]])
    a,v=pair_angles(xy,np.ones((1,2),bool),[0,1],H)
    assert v[0] and a[0]==pytest.approx(np.pi/2)


def make_video(path,n=20):
    import cv2
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),10,(64,48))
    assert writer.isOpened()
    for i in range(n):writer.write(np.full((48,64,3),i*8,np.uint8))
    writer.release()


def test_decoded_interval_timestamps_and_crop(tmp_path):
    p=tmp_path/'clip.avi';make_video(p)
    frames,t,indices,fps,crop=read_clip(p,.3,1.2,[10,5,40,25])
    assert frames.shape==(9,20,30,3)
    assert indices==list(range(3,12))
    assert t==pytest.approx(np.arange(3,12)/10)
    assert frames[0].mean()==pytest.approx(24,abs=2)


def test_temporal_sampling_is_exact_subset_in_memory_and_memmap(tmp_path):
    p=tmp_path/'clip.avi';make_video(p)
    full,t,ids,fps,crop=read_clip(p,.3,1.3,[10,5,40,25])
    for storage in [None,tmp_path/'frames.npy']:
        frames,sampled,indices,source_fps,_=read_clip(p,.3,1.3,crop,frame_step=3,storage_path=storage)
        assert np.array_equal(frames,full[::3])
        assert np.array_equal(sampled,t[::3])
        assert indices==ids[::3] and source_fps==fps
        if isinstance(frames,np.memmap):frames._mmap.close()
    with pytest.raises(ValueError,match='positive integer'):
        read_clip(p,.3,1.3,frame_step=0)


@pytest.mark.parametrize('with_progress', [False, True])
def test_pipeline_no_pair_keeps_rotation_unknown_and_output_viewable(tmp_path,monkeypatch,with_progress):
    from prototype.spin import pipeline
    p=tmp_path/'clip.avi';make_video(p)
    cfg={'source_sha256':digest(p),'interval_s':[.3,1.2], 'points':[{'name':'cap','pixel':[20,20]}],
         'seed_provenance':'synthetic fixture', 'orientation_pair':None}
    if with_progress:
        cfg['tracking_progress_directory']=str(tmp_path/'progress')
    c=tmp_path/'config.json';c.write_text(json.dumps(cfg));w=tmp_path/'weights';w.write_bytes(b'fixture')
    def mock_tracker(frames,queries,checkpoint,**kwargs):
        import hashlib
        assert kwargs['progress_directory']==cfg.get('tracking_progress_directory')
        assert kwargs['decoded_sha256']==hashlib.sha256(frames).hexdigest()
        return np.tile(np.array([[[20.,20.]]]),(len(frames),1,1)),np.ones((len(frames),1),bool),{'mode':'test'}
    monkeypatch.setattr(pipeline,'track_points',mock_tracker)
    r=pipeline.run(p,c,tmp_path/'out',checkpoint=w)
    assert r['physical_revolutions'] is None
    assert r['reconstruction']['unresolved_count']==9
    assert (tmp_path/'out/index.html').exists()
    assert r['frame_indices'][0]==3
    with pytest.raises(ValueError,match='already exists'):pipeline.run(p,c,tmp_path/'out',checkpoint=w)


def test_optional_attachment_preserves_venv_executable_symlink(tmp_path,monkeypatch):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from scripts import run_throw_pipeline as runner
    out=tmp_path/'run';out.mkdir();(out/'aggregate.json').write_text('{}')
    cfg=tmp_path/'config.json';cfg.write_text('{}')
    env_python=tmp_path/'venv-python';env_python.symlink_to(sys.executable)
    a=SimpleNamespace(spin_config=cfg,spin_checkpoint=tmp_path/'w',spin_python=env_python,
                      spin_mode='online',output_dir=out,video=tmp_path/'v')
    calls=[]
    monkeypatch.setattr(runner.subprocess,'run',lambda *args,**kw:calls.append(kw))
    runner.attach_spin_development(a)
    assert calls[0]['env']['CURLING_PYTHON']==str(env_python.absolute())
    assert calls[0]['env']['CURLING_PYTHON']!=str(env_python.resolve())
    runner.attach_spin_development(SimpleNamespace(spin_config=None))
    assert len(calls)==1


def test_dense_attachment_passes_progress_directory(tmp_path,monkeypatch):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from scripts import run_throw_pipeline as runner
    args=SimpleNamespace(track_throws=True,video=tmp_path/'video.mp4',output_dir=tmp_path/'run',
                         spin_checkpoint=tmp_path/'weights',spin_mode='online',
                         spin_python=Path(sys.executable),tracking_progress_dir=tmp_path/'progress')
    calls=[]
    monkeypatch.setattr(runner.subprocess,'run',lambda command,**kw:calls.append(command))
    runner.attach_spin_development(args)
    command=calls[0]
    assert command[command.index('--tracking-progress-dir')+1]==str(args.tracking_progress_dir.resolve())


def test_automatic_candidate_initialization_uses_source_dimensions(tmp_path):
    from prototype.spin.pipeline import candidate_config
    p=tmp_path/'clip.avi';make_video(p)
    a=tmp_path/'aggregate.json'
    a.write_text(json.dumps({'context':{'source_sha256':digest(p)}, 'events':[{'candidate_id':'E1','segments':[{
        'segment_id':'E1:1','camera':'right_split','pixel_points':[{'time_s':.3,'pixel':[450,300]},{'time_s':1.,'pixel':[460,200]}],
        'camera_cut_times_s':[]}]}]}))
    cfg=candidate_config(p,a,'E1:1')
    assert cfg['crop_px']==[32,0,64,48]
    assert cfg['segment_to_source_scale']==pytest.approx([.1,48/360])
    assert cfg['seed_from_segment'] and cfg['orientation_pair'] is None
    assert cfg['interval_s']==pytest.approx([.3,1.1])
    with pytest.raises(ValueError,match='exactly once'):candidate_config(p,a,'missing')


def test_projection_reuses_existing_anchor_and_keeps_hidden_points_missing(tmp_path,monkeypatch):
    from prototype.spin import projection
    p=tmp_path/'clip.avi';make_video(p)
    H=np.diag([.01,.01,1.]).tolist()
    a=tmp_path/'aggregate.json'
    a.write_text(json.dumps({'context':{'source_sha256':digest(p)},'events':[{'segments':[{
        'segment_id':'E1:1','camera':'right_split','geometry_samples':[{'time_s':.3,'top_view_m':[4,1.8],
        'homography_source_pixels_to_local_metres':H}]}]}]}))
    monkeypatch.setattr(projection,'features',lambda *args:('keypoints','descriptors'))
    calls=[]
    def transfer(*args,**kwargs):
        calls.append(args)
        return np.asarray(H),{'status':'test_registered'}
    monkeypatch.setattr(projection,'transfer',transfer)
    r=projection.project_existing(p,a,'E1:1',[.3,.4],np.array([[[40,24]],[[41,24]]]),np.array([[True],[False]]))
    assert r['new_calibration_fits']==0 and len(calls)==1
    assert r['samples'][0]['points_camera_local_m'][0]==pytest.approx([4,1.8])
    assert r['samples'][1]['points_camera_local_m']==[None]
    assert r['projected_point_count']==1


def test_cached_predictions_require_matching_hashes(tmp_path,monkeypatch):
    from prototype.spin import pipeline
    p=tmp_path/'clip.avi';make_video(p)
    cfg={'source_sha256':digest(p),'interval_s':[.3,1.2], 'points':[{'name':'cap','pixel':[20,20]}],
         'seed_provenance':'synthetic fixture', 'orientation_pair':None}
    c=tmp_path/'config.json';c.write_text(json.dumps(cfg));w=tmp_path/'weights';w.write_bytes(b'fixture')
    calls=[]
    def tracker(frames,queries,checkpoint,**kwargs):
        calls.append(1)
        return np.tile(np.array([[[20.,20.]]]),(len(frames),1,1)),np.ones((len(frames),1),bool),{'mode':'online','checkpoint_sha256':digest(checkpoint)}
    monkeypatch.setattr(pipeline,'track_points',tracker)
    pipeline.run(p,c,tmp_path/'first',checkpoint=w)
    pipeline.run(p,c,tmp_path/'reuse',checkpoint=w,reuse_result=tmp_path/'first/result.json')
    assert len(calls)==1
    w.write_bytes(b'changed')
    with pytest.raises(ValueError,match='do not match'):
        pipeline.run(p,c,tmp_path/'reject',checkpoint=w,reuse_result=tmp_path/'first/result.json')


def test_height_prior_is_constructed_once_and_raw_points_preserved(tmp_path,monkeypatch):
    from prototype.spin import projection
    p=tmp_path/'clip.avi';make_video(p)
    H=np.diag([.01,.01,1.]).tolist();a=tmp_path/'aggregate.json'
    a.write_text(json.dumps({'context':{'source_sha256':digest(p)},'events':[{'segments':[{
        'segment_id':'E1:1','camera':'right_split','geometry_samples':[{'time_s':.3,'top_view_m':[4,1.8],
        'homography_source_pixels_to_local_metres':H}]}]}]}))
    monkeypatch.setattr(projection,'features',lambda *args:('keypoints','descriptors'))
    A=np.array([[1.,0.,2.],[0.,1.,0.],[0.,0.,1.]])
    monkeypatch.setattr(projection,'transfer',lambda *args,**kw:(np.array(H),{'status':'test_registered','reference_to_current':A.tolist()}))
    constructed=[];received=[]
    def prior(*args):
        constructed.append(1)
        return {'camera':{'plane':np.eye(3),'vertical':np.array([0.,0.,1.])},'diagnostic':{'status':'test'},'alternatives':[]}
    def localize(H,xy,region,kind,camera_prior,heights_m):
        received.append(camera_prior['camera']['plane'])
        return np.array([3.,2.]),{'status':'test_height_adjusted'}
    monkeypatch.setattr(projection,'transported_reference_camera',prior)
    monkeypatch.setattr(projection,'localize',localize)
    r=projection.project_existing(p,a,'E1:1',[.3,.4],np.array([[[40,24]],[[41,24]]]),np.array([[True],[True]]))
    assert len(constructed)==1
    assert np.allclose(received[0],np.eye(3)) and np.allclose(received[1],A)
    assert r['samples'][0]['points_camera_local_m'][0]==pytest.approx([4,1.8])
    assert r['samples'][0]['height_adjusted_points_camera_local_m'][0]==[3.,2.]
    assert r['height_adjusted_point_count']==2


def test_decoder_mismatch_rejected_before_output(tmp_path):
    from prototype.spin.pipeline import run
    cfg=tmp_path/'config.json';cfg.write_text(json.dumps({'expected_decoder':{'opencv_version':'different'}}))
    with pytest.raises(ValueError,match='Decoder differs'):
        run(tmp_path/'unused-video',cfg,tmp_path/'out',checkpoint=tmp_path/'weights')
    assert not (tmp_path/'out').exists()


def test_cache_rejects_changed_decoded_pixels(tmp_path,monkeypatch):
    from prototype.spin import pipeline
    p=tmp_path/'clip.avi';make_video(p)
    cfg={'source_sha256':digest(p),'interval_s':[.3,1.2],
         'points':[{'name':'cap','pixel':[20,20]}],'seed_provenance':'synthetic fixture','orientation_pair':None}
    c=tmp_path/'config.json';c.write_text(json.dumps(cfg));w=tmp_path/'weights';w.write_bytes(b'fixture')
    calls=[]
    def tracker(frames,queries,checkpoint,**kwargs):
        calls.append(1)
        return np.tile(np.array([[[20.,20.]]]),(len(frames),1,1)),np.ones((len(frames),1),bool),{'mode':'online','checkpoint_sha256':digest(checkpoint)}
    monkeypatch.setattr(pipeline,'track_points',tracker)
    pipeline.run(p,c,tmp_path/'first',checkpoint=w)
    decode=pipeline.read_clip
    def changed_decoder(*args,**kwargs):
        frames,*rest=decode(*args,**kwargs)
        return (frames ^ np.uint8(1),*rest)
    monkeypatch.setattr(pipeline,'read_clip',changed_decoder)
    with pytest.raises(ValueError,match='do not match'):
        pipeline.run(p,c,tmp_path/'reuse',checkpoint=w,reuse_result=tmp_path/'first/result.json')
    assert len(calls)==1


def test_cache_rejects_changed_automatic_query(tmp_path,monkeypatch):
    from prototype.spin import pipeline
    p=tmp_path/'clip.avi';make_video(p);a=tmp_path/'aggregate.json'
    aggregate={'context':{'source_sha256':digest(p)},'events':[{'candidate_id':'e','segments':[{'segment_id':'s','pixel_points':[{'time_s':.3,'pixel':[200,150]}]}]}]}
    a.write_text(json.dumps(aggregate))
    cfg={'source_sha256':digest(p),'interval_s':[.3,1.2],'candidate_id':'e','segment_id':'s',
         'seed_from_segment':True,'segment_to_source_scale':[.1,48/360],'orientation_pair':None}
    c=tmp_path/'config.json';c.write_text(json.dumps(cfg));w=tmp_path/'weights';w.write_bytes(b'fixture');calls=[]
    def tracker(frames,queries,checkpoint,**kwargs):
        calls.append(1)
        return np.tile(np.array([[[20.,20.]]]),(len(frames),1,1)),np.ones((len(frames),1),bool),{'mode':'online','checkpoint_sha256':digest(checkpoint)}
    monkeypatch.setattr(pipeline,'track_points',tracker);monkeypatch.setattr(pipeline,'project_existing',lambda *a,**kw:{'fixture':True})
    pipeline.run(p,c,tmp_path/'first',checkpoint=w,aggregate_path=a)
    aggregate['events'][0]['segments'][0]['pixel_points'][0]['pixel'][0]=210;a.write_text(json.dumps(aggregate))
    with pytest.raises(ValueError,match='do not match'):
        pipeline.run(p,c,tmp_path/'reuse',checkpoint=w,aggregate_path=a,reuse_result=tmp_path/'first/result.json')
    assert len(calls)==1


def test_learned_body_seed_preserves_feature_kind_through_dense_projection(tmp_path,monkeypatch):
    from prototype.spin import pipeline
    p=tmp_path/'clip.avi';make_video(p)
    a=tmp_path/'aggregate.json'
    a.write_text(json.dumps({'context':{'source_sha256':digest(p)},'events':[{'candidate_id':'L1','segments':[{
        'segment_id':'L1:left','camera':'left_split','point_kind':'body_box_center',
        'pixel_points':[{'time_s':.3,'pixel':[200,150]},{'time_s':.4,'pixel':[210,145]}]}]}]}))
    cfg=pipeline.candidate_config(p,a,'L1:left')
    assert cfg['segment_point_kind']=='body_box_center'
    c=tmp_path/'config.json';c.write_text(json.dumps(cfg));w=tmp_path/'weights';w.write_bytes(b'fixture')
    def track(frames,queries,checkpoint,**kwargs):
        return np.tile(np.array([[[20.,20.]]]),(len(frames),1,1)),np.ones((len(frames),1),bool),{'mode':'test'}
    monkeypatch.setattr(pipeline,'track_points',track)
    calls=[]
    def project(*args,**kwargs):
        calls.append(kwargs['point_kinds']);return {'status':'test'}
    monkeypatch.setattr(pipeline,'project_existing',project)
    monkeypatch.setattr(pipeline,'write_report',lambda *args:None)
    r=pipeline.run(p,c,tmp_path/'out',checkpoint=w,aggregate_path=a)
    assert calls==[['body_box_center']]
    assert r['point_names']==['candidate_body_box_center']
    assert r['physical_revolutions'] is None


def test_memmap_decode_preserves_pixels_and_timestamps(tmp_path):
    p=tmp_path/'clip.avi';make_video(p)
    memory,t,indices,fps,crop=read_clip(p,.3,1.2,[10,5,40,25])
    mapped,mt,mi,mf,mc=read_clip(p,.3,1.2,[10,5,40,25],storage_path=tmp_path/'frames.npy')
    assert isinstance(mapped,np.memmap)
    assert np.array_equal(memory,mapped)
    assert np.array_equal(t,mt) and indices==mi and fps==mf and crop==mc
    mapped._mmap.close()
