import sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from camera_geometry import transfer, calibrate_sequence
from vision_core import project


def test_transfer_matches_known_planar_image_motion_and_rejects_blank():
    rng = np.random.default_rng(123)
    image = np.full((360, 640, 3), 230, np.uint8)
    for _ in range(120):
        x, y = rng.integers([40, 90], [600, 330])
        c = int(rng.integers(120, 200))
        cv2.circle(image, (int(x), int(y)), int(rng.integers(2, 8)), (c, c, c), -1)
    A = np.array([[1.02, 0.01, 5], [-0.005, 1.01, 3], [0.00001, 0.00001, 1.0]])
    current = cv2.warpPerspective(image, A, (640, 360), borderValue=(230, 230, 230))
    H = np.array([[0.01, 0, -3], [0, 0.01, -2], [0, 0, 1.0]])
    got, diag = transfer(image, current, H, (0, 70, 640, 360))
    assert got is not None, diag
    points = [[100, 150], [300, 200], [500, 300]]
    assert (
        np.max(np.linalg.norm(project(got, project(A, points)) - project(H, points), axis=1)) < 0.01
    )
    assert transfer(image, np.full_like(image, 230), H, (0, 70, 640, 360))[0] is None


def test_sequence_does_not_transfer_across_camera_cut(monkeypatch):
    import camera_geometry as module

    a = np.zeros((360, 640, 3), np.uint8)
    b = np.ones_like(a)
    monkeypatch.setattr(
        module,
        "calibrate_house",
        lambda frame, region: (np.eye(3), {}) if not frame.any() else (None, {}),
    )
    monkeypatch.setattr(module, "features", lambda *args: ([], None))
    monkeypatch.setattr(module, "transfer", lambda *args: (np.eye(3), {"status": "accepted"}))
    assert calibrate_sequence({0: a, 1: b}, (0, 70, 640, 360))[1][0] is not None
    assert calibrate_sequence({0: a, 1: b}, (0, 70, 640, 360), cut_times=[0.5])[1][0] is None


def test_reflected_registration_reports_geometry_evidence(monkeypatch):
    points=[(50,100),(100,100),(50,200),(100,200),(75,150)]
    keys=[cv2.KeyPoint(float(x),float(y),1) for x,y in points]
    descriptors=np.eye(5,dtype=np.float32)
    reflection=np.array([[-1.,0.,640.],[0.,1.,0.],[0.,0.,1.]])
    monkeypatch.setattr(cv2,'findHomography',lambda *args,**kwargs:(reflection,np.ones((5,1),np.uint8)))
    frame=np.zeros((360,640,3),np.uint8)
    H,diagnostic=transfer(frame,frame,np.eye(3),(0,0,640,360),
                          (keys,descriptors),(keys,descriptors))
    assert H is None
    assert diagnostic['reason']=='nonpositive_warped_panel_area'
    assert diagnostic['warped_area_px2']==-640*360
    assert diagnostic['inliers']==5
    assert diagnostic['reference_to_current']==reflection.tolist()


def test_large_ring_residual_is_diagnostic_not_rejection(monkeypatch):
    import camera_geometry as module
    points = [(50,100),(100,100),(50,200),(100,200),(75,150)]
    keys = [cv2.KeyPoint(float(x),float(y),1) for x,y in points]
    descriptors = np.eye(5,dtype=np.float32)
    # Exact matches provide a valid registration, while the ring diagnostic is poor.
    monkeypatch.setattr(module,'ring_edges',lambda *args,**kw: [{}]*12)
    monkeypatch.setattr(module,'ring_summary',lambda *args:{'p95_abs_radial_error_m':2.})
    frame = np.zeros((360,640,3),np.uint8)
    H, diagnostic = transfer(frame,frame,np.eye(3),(0,0,640,360),
                              (keys,descriptors),(keys,descriptors))
    assert H is not None
    assert diagnostic['inliers'] == 5
    assert diagnostic['partial_ring_check']['p95_abs_radial_error_m'] == 2.
    assert diagnostic['quality_rejection_applied'] is False


def test_registration_tracks_camera_across_resolution_and_exposure():
    rng = np.random.default_rng(14)
    original = rng.integers(0,256,(240,320,3),dtype=np.uint8)
    original = cv2.GaussianBlur(original,(3,3),0)
    for scale in (.75,1.,2.):
        frame = cv2.resize(original,None,fx=scale,fy=scale)
        h,w = frame.shape[:2]
        A = np.array([[1.,.01,3*scale],[-.01,1.,2*scale],[0.,0.,1.]])
        current = cv2.warpPerspective(frame,A,(w,h))
        current = cv2.convertScaleAbs(current,alpha=.7,beta=30)
        H = np.array([[1/scale,0,0],[0,1/scale,0],[0,0,1.]])
        estimated,diag = transfer(frame,current,H,(0,0,w,h),strategy="adaptive_lmeds")
        assert estimated is not None,diag
        sample = np.array([[60,70],[120,140],[200,180]])*scale
        error = np.linalg.norm(project(estimated,project(A,sample))-project(H,sample),axis=1)
        assert error.max()<.5, (scale,error,diag)
        assert diag['registration_method']=='opencv_lmeds_mutual_sift'


def test_stable_camera_anchor_has_no_implicit_age_expiry(monkeypatch):
    import camera_geometry as module
    a = np.zeros((30,40,3),np.uint8)
    b = np.ones_like(a)
    monkeypatch.setattr(module,'calibrate_house',lambda frame,region:(np.eye(3),{}) if not frame.any() else (None,{}))
    monkeypatch.setattr(module,'features',lambda *args:([],None))
    monkeypatch.setattr(module,'transfer',lambda *args:(np.eye(3),{'status':'registered'}))
    assert calibrate_sequence({0:a,60:b},(0,0,40,30))[60][0] is not None
    assert calibrate_sequence({0:a,60:b},(0,0,40,30),cut_times=[30])[60][0] is None
    assert calibrate_sequence({0:a,60:b},(0,0,40,30),max_anchor_age_s=3)[60][0] is None


def test_similarity_registration_preserves_far_field_under_known_camera_motion():
    rng = np.random.default_rng(42)
    image = rng.integers(120, 255, (360, 640, 3), dtype=np.uint8)
    image = cv2.GaussianBlur(image, (3, 3), 0)
    motion = np.vstack([cv2.getRotationMatrix2D((320, 180), .3, 1.002), [0., 0., 1.]])
    motion[:2, 2] += [2., -1.]
    current = cv2.warpPerspective(image, motion, (640, 360))
    H = np.array([[.03, 0., -9.6], [0., .09, -19.], [0., .004, 1.]])
    fitted, diagnostic = transfer(image, current, H, (0, 0, 640, 360), model='similarity')
    assert fitted is not None, diagnostic
    points = np.array([[100., 25.], [320., 120.], [500., 300.]])
    errors = np.linalg.norm(project(fitted, project(motion, points)) - project(H, points), axis=1)
    assert errors.max() < .01
    assert diagnostic['motion_model'] == 'similarity'
    assert transfer(image, np.zeros_like(image), H, (0, 0, 640, 360), model='similarity')[0] is None
