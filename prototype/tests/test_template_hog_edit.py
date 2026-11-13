import numpy as np
import pytest
from prototype.rink_template import edit_hog_handle,template_panel
from prototype.rink_calibration import project,verify_sealed_panel
from prototype.tests.test_rink_template import controls


@pytest.mark.parametrize('panel',['left','right'])
def test_hog_edit_protects_all_rings_and_retains_physical_mapping(panel):
    p=controls(panel);r=template_panel(p,panel);P=np.array(r['camera_model']['projection_xyz_up_to_normalized_source'])
    sign=-1 if panel=='left' else 1
    target=project(P[:,[0,1,3]],[[0,sign*6.401]])[0]*3+[0,-10]
    # Stored image coordinates are 640x360; the editor uses canonical 1920x1080.
    result=edit_hog_handle(p,panel,target,3.)
    assert result['accepted'],result
    assert result['maximum_house_contour_error_px']<=3.001
    assert result['centre_drift_px']<=.051
    assert result['pointer_error_px']<1
    verify_sealed_panel(template_panel(result['parameters'],panel))


def test_incompatible_hog_target_is_limited_instead_of_destroying_house():
    p=controls('left');P=np.array(template_panel(p,'left')['camera_model']['projection_xyz_up_to_normalized_source'])
    target=project(P[:,[0,1,3]],[[0,-6.401]])[0]*3+[0,-150]
    result=edit_hog_handle(p,'left',target,2.)
    assert result['maximum_house_contour_error_px']<=2.001
    assert not result['target_reached']
    assert result['pointer_error_px']>1


def test_nonfinite_target_and_invalid_protection_are_rejected():
    with pytest.raises(ValueError):edit_hog_handle(controls('left'),'left',[0,float('nan')],2)
    with pytest.raises(ValueError):edit_hog_handle(controls('left'),'left',[300,300],0)
