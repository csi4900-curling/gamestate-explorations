from types import SimpleNamespace
import numpy as np
from prototype import split_camera_geometry as module


def test_registered_anchor_is_reused_and_registration_gap_does_not_refit(monkeypatch):
    g=module.SplitCameraGeometry.__new__(module.SplitCameraGeometry)
    calls={'fit':0,'register':0}
    def native(frame):
        assert frame.shape==(1080,1920,3)
        calls['register']+=1
        return np.eye(3),{'status':'registered'}
    g.left=SimpleNamespace(register=native,H=np.eye(3));g.calibration={'right':{'refined_H':np.eye(3)}}
    g.right_reference_ellipse={};g.right_reference_ellipse['valid']=True
    g.anchors={};g.initialization_attempts={'left':0,'right':0};g.registration_attempts={'left':0,'right':0}
    g.source_house_fit_attempts=0;g.wall_seconds=0.;g.stage_wall_seconds={}
    monkeypatch.setattr(module,'fit_house_ellipse',lambda frame:{'valid':True})
    def fit(*args):calls['fit']+=1;return np.eye(3),{'status':'fixture_fit'}
    monkeypatch.setattr(module,'fit_source_house',fit)
    monkeypatch.setattr(module,'features',lambda *args:('fixture',None))
    monkeypatch.setattr(module,'transported_reference_camera',lambda *args:None)
    monkeypatch.setattr(module,'transfer',lambda *args,**kwargs:(None,{'status':'insufficient_registration_matches'}))
    frame=np.zeros((360,640,3),np.uint8)
    first=g.observe(frame,0);second=g.observe(frame,10);third=g.observe(frame,20)
    assert first['right'][0] is not None
    assert second['right'][0] is None and third['right'][0] is None
    assert calls=={'fit':1,'register':3}
    assert g.provenance()['source_house_fit_attempts']==1
    assert g.provenance()['registration_attempts']=={'left':3,'right':2}
    timings=g.provenance()['stage_wall_seconds']
    assert set(timings)=={'left:native_reference_registration','right:house_initialization','right:anchor_registration'}
    assert timings['right:house_initialization']==first['right'][1]['runtime']['wall_seconds']
    assert timings['right:anchor_registration']==sum(r['right'][1]['runtime']['wall_seconds'] for r in [second,third])
    assert all(t>=0 for t in timings.values())
