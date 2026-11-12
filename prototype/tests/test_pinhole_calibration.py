import copy
import cv2
import numpy as np
import pytest
from prototype.rink_calibration import fit_panel,landmarks,project,verify_sealed_panel
from prototype.pinhole_calibration import refine_camera


def physical_fixture(panel):
    cx=480 if panel=='left' else 1440
    d,h,f=(15.,5.,2000.) if panel=='left' else (60.,7.,5000.)
    c,e=d/np.hypot(d,h),h/np.hypot(d,h)
    R=np.array([[1,0,0],[0,e,-c],[0,-c,-e]])
    C=np.array([0.,d,h]);K=np.array([[f,0,cx],[0,f,540.],[0,0,1.]])
    P=K@np.column_stack([R,-R@C]);G=P[:,[0,1,3]]
    world={p['id']:p['xy_m'] for p in landmarks(panel)}
    def marks(ids):return [{'landmark_id':i,'pixel_normalized':(project(G,[world[i]])[0]/[1920,1080]).tolist()} for i in ids]
    fit=marks(['tee','outer_left','outer_right','outer_play','outer_behind','hog_centre'])
    check=marks(['middle_left','middle_right','middle_play','hog_left'])
    ys=[-6.,0.] if panel=='left' else [0.,14.]
    guides=[(project(G,[[x,y] for y in ys])/[1920,1080]).tolist() for x in [-.457,.457]]
    spec={'fit_points':fit,'check_points':check,'parallel_lines':guides}
    return spec,P,K,C


@pytest.mark.parametrize('panel',['left','right'])
def test_same_physical_camera_recovers_plane_and_elevated_stone_points(panel):
    spec,P,K,C=physical_fixture(panel)
    result=refine_camera(fit_panel(spec,panel))
    assert result['status']=='checks_passed',result['reasons']
    assert result['camera_model']['orthogonality_residual']<1e-12
    np.testing.assert_allclose(result['camera_model']['camera_centre_m'],C,atol=1e-4)
    assert result['camera_model']['focal_native_px']==pytest.approx(K[0,0],rel=1e-5)
    fitted=np.array(result['camera_model']['projection_xyz_up_to_normalized_source'])
    for xy in [[.2,-10.],[.5,1.]]:
        actual=P@[*xy,.068,1.];pixel=actual[:2]/actual[2]/3.
        height_plane=fitted[:,[0,1,3]].copy();height_plane[:,2]+=.068*fitted[:,2]
        recovered=project(np.linalg.inv(height_plane),[pixel])[0]
        np.testing.assert_allclose(recovered,xy,atol=1e-4)
    verify_sealed_panel(result)


def test_changed_physical_camera_is_caught_by_the_calibration_seal():
    spec,_,_,_=physical_fixture('left');r=refine_camera(fit_panel(spec,'left'))
    r['camera_model']['projection_xyz_up_to_normalized_source'][0][2]+=.01
    with pytest.raises(ValueError,match='evidence changed'):verify_sealed_panel(r)


def test_withheld_landmark_does_not_change_camera_optimisation():
    spec,_,_,_=physical_fixture('left')
    result=refine_camera(fit_panel(spec,'left'))
    changed=copy.deepcopy(spec);changed['check_points'][0]['pixel_normalized'][0]+=.03
    failed=refine_camera(fit_panel(changed,'left'))
    assert failed['status']=='rejected'
    np.testing.assert_allclose(failed['camera_model']['projection_xyz_up_to_normalized_source'],
                               result['camera_model']['projection_xyz_up_to_normalized_source'])
