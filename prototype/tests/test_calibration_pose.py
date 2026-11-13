import cv2
import numpy as np
from prototype.calibration_pose import PoseVerifier
from prototype.rink_calibration import fit_panel,project
from prototype.tests.test_rink_calibration import example


def reference():
    spec,G=example('left')
    spec['parallel_lines']=[(project(G,[[x,-6.],[x,0.]])/[1920,1080]).tolist() for x in [-1.6,1.6]]
    record=fit_panel(spec,'left')
    rng=np.random.default_rng(12)
    image=cv2.GaussianBlur(rng.integers(100,230,(1080,1920,3),dtype=np.uint8),(3,3),0)
    return image,record,PoseVerifier(image,record,'left')


def test_only_explicit_operator_pixels_are_used_not_inferred_line_interiors():
    _,record,v=reference()
    observed=[p['pixel_normalized'] for p in record['fit_points']+record['check_points']]
    observed+=sum(record['parallel_lines'],[])
    observed=np.array(observed)*[1920,1080]
    for x,y,group,patch in v.samples:
        assert np.linalg.norm(observed-[x,y],axis=1).min()<1.
    assert v.reference_counts['guide0']==2
    assert v.reference_counts['guide1']==2


def test_occluded_rings_do_not_hide_independent_boundary_and_hog_support():
    image,record,v=reference();occluded=image.copy()
    for p in record['fit_points']+record['check_points']:
        if p['landmark_id'].startswith('hog_'):continue
        x,y=np.rint(np.array(p['pixel_normalized'])*[1920,1080]).astype(int)
        cv2.rectangle(occluded,(x-11,y-11),(x+11,y+11),(220,220,220),-1)
    ok,evidence=v.check(occluded)
    assert ok,evidence
    assert evidence['evidence_paths']==['longitudinal_guides_and_hog']


def test_occluded_guide_does_not_hide_supported_ring_and_hog_pose():
    image,record,v=reference();occluded=image.copy()
    for p in sum(record['parallel_lines'],[]):
        x,y=np.rint(np.array(p)*[1920,1080]).astype(int)
        cv2.rectangle(occluded,(x-11,y-11),(x+11,y+11),(220,220,220),-1)
    ok,evidence=v.check(occluded)
    assert ok,evidence
    assert evidence['evidence_paths']==['rings_and_hog']


def test_camera_motion_and_cuts_fail_but_uniform_exposure_change_is_supported():
    image,_,v=reference()
    assert v.check(cv2.convertScaleAbs(image,alpha=.7,beta=20))[0]
    for A in [np.array([[1.,0.,8.],[0.,1.,0.],[0.,0.,1.]]),
              np.array([[1.01,.004,5.],[.003,1.,-7.],[1e-5,-1e-5,1.]])]:
        assert not v.check(cv2.warpPerspective(image,A,(1920,1080)))[0]
    assert not v.check(np.full_like(image,230))[0]


def test_longitudinal_guides_alone_do_not_establish_the_rink_pose():
    image,record,v=reference();occluded=image.copy()
    for p in record['fit_points']+record['check_points']:
        if not p['landmark_id'].startswith('hog_'):continue
        x,y=np.rint(np.array(p['pixel_normalized'])*[1920,1080]).astype(int)
        cv2.rectangle(occluded,(x-11,y-11),(x+11,y+11),(220,220,220),-1)
    assert not v.check(occluded)[0]
