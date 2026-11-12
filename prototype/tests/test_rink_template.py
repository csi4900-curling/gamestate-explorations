import copy
import numpy as np
import pytest
from prototype.rink_template import template_panel
from prototype.rink_calibration import project, verify_sealed_panel
from prototype.tests.test_calibration_store import confirm
from prototype.tests.test_workbench import app


def controls(panel):
    return {'camera_x_m':0,'distance_m':15 if panel=='left' else 60,'height_m':5 if panel=='left' else 7,
            'focal_px':2000 if panel=='left' else 5000,'yaw_deg':0,'pitch_deg':0,'roll_deg':0}


@pytest.mark.parametrize('panel',['left','right'])
def test_template_has_one_consistent_plane_and_height_camera_without_fake_checks(panel):
    r=template_panel(controls(panel),panel);verify_sealed_panel(r)
    assert r['fit_points']==r['check_points']==r['checks']==[]
    assert r['maximum_check_error_m'] is None
    assert r['check_status']=='operator_visual_alignment_only'
    P=np.array(r['camera_model']['projection_xyz_up_to_normalized_source'])
    H=np.array(r['H_normalized_source_to_local_m'])
    for xyz in [[.3,1.,0.],[-.4,-3.,.068]]:
        q=P@[*xyz,1.];pixel=q[:2]/q[2]
        elevated=P[:,[0,1,3]].copy();elevated[:,2]+=xyz[2]*P[:,2]
        np.testing.assert_allclose(project(np.linalg.inv(elevated),[pixel])[0],xyz[:2],atol=1e-10)
    np.testing.assert_allclose(H@P[:,[0,1,3]],np.eye(3),atol=1e-10)
    changed=copy.deepcopy(r);changed['template_parameters']['height_m']+=1
    with pytest.raises(ValueError,match='evidence changed'):verify_sealed_panel(changed)


def test_template_rejects_invalid_placement_and_controls():
    for key,value in [('height_m',0),('focal_px',float('nan')),('roll_deg',True)]:
        p=controls('left');p[key]=value
        with pytest.raises(ValueError):template_panel(p,'left')
    p=controls('left');p['yaw_deg']=40
    with pytest.raises(ValueError,match='inside'):template_panel(p,'left')


def test_template_actual_store_preview_confirm_snapshot_and_load(app):
    from prototype.rink_calibration import load_bundle
    video,frame,_,_=confirm(app)
    request={'video_id':video['id'],'valid_interval_s':[0,1],
        'panels':{panel:{'frame_id':frame['id'],'template_parameters':controls(panel)} for panel in ['left','right']}}
    preview=app.calibrations.preview(request)
    assert preview['status']=='checks_passed',preview
    saved=app.calibrations.confirm({'preview_id':preview['id'],'confirmed':True,'reviewer':'Synthetic template UI test','operator_kind':'agent'})
    assert all(p['reference_pose_support']['status']=='source_calibration_registered' for p in saved['panels'].values())
    folder=app.data/'template-snapshot';folder.mkdir()
    path=app.calibrations.snapshot([saved],folder,video['source_sha256'],[0,1])
    bundle=load_bundle(path)
    assert all(p['calibration_method']=='operator_template_alignment_v1' and p['checks']==[] for p in bundle['calibrations'][0]['panels'].values())
