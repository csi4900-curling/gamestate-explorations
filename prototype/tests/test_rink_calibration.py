import copy
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from prototype.rink_calibration import fit_panel, landmarks, project, load_bundle, validate_interval, digest, SCHEMA
from prototype.calibrated_camera_geometry import CalibratedCameraGeometry, panel_features, register


def example(panel, parallel=True):
    G = (np.array([[220., -50., 480.], [0., 70., 750.], [0., -.10, 1.]]) if panel == 'left'
         else np.array([[220., -43.8, 1460.], [0., 20., 500.], [0., -.03, 1.]]))
    world = {p['id']: p['xy_m'] for p in landmarks(panel)}
    def mark(name):
        return {'landmark_id': name, 'pixel_normalized': (project(G, [world[name]])[0]/[1920, 1080]).tolist()}
    fit = ['tee', 'outer_left', 'outer_right', 'outer_play', 'outer_behind', 'hog_centre']
    check = ['middle_left', 'middle_right', 'middle_play', 'hog_left']
    ys = [-6., 0.] if panel == 'left' else [2., 6.]
    lines = [(project(G, [[x, y] for y in ys])/[1920, 1080]).tolist() for x in [-.457, .457]]
    return {'fit_points': list(map(mark, fit)), 'check_points': list(map(mark, check)),
            'parallel_lines': lines if parallel else []}, G


@pytest.mark.parametrize('panel', ['left', 'right'])
def test_explicit_plane_recovers_known_near_and_far_coordinates(panel):
    spec, G = example(panel)
    fitted = fit_panel(spec, panel)
    assert fitted['status'] == 'checks_passed', fitted['reasons']
    assert fitted['maximum_check_error_m'] < 1e-7
    world = [[-.5, -20. if panel == 'left' else 12.], [.9, 0.], [-.457, -6.401 if panel == 'left' else 6.401]]
    H = np.array(fitted['H_normalized_source_to_local_m'])
    np.testing.assert_allclose(project(H, project(G, world)/3.), world, atol=1e-6)
    assert fitted['projection_scope'] == 'perspective_constrained'
    assert fitted['absolute_accuracy_verified'] is False


def test_withheld_bad_landmark_rejects_without_refitting_it():
    spec, _ = example('left')
    H = fit_panel(spec, 'left')['H_normalized_source_to_local_m']
    spec['check_points'][-1]['pixel_normalized'][0] += 40/1920
    failed = fit_panel(spec, 'left')
    assert failed['status'] == 'rejected'
    np.testing.assert_allclose(failed['H_normalized_source_to_local_m'], H)
    assert failed['maximum_check_error_m'] > .15


@pytest.mark.parametrize('panel',['left','right'])
def test_finite_guide_click_error_does_not_become_an_exact_vanishing_point(panel):
    spec,G=example(panel)
    spec['parallel_lines'][0][0][0]+=1/1920
    spec['parallel_lines'][1][1][0]-=1/1920
    result=fit_panel(spec,panel)
    assert result['status']=='checks_passed'
    target=np.array([[.2,-20. if panel=='left' else 12.]])
    predicted=project(result['H_normalized_source_to_local_m'],project(G,target)/3.)
    assert np.linalg.norm(predicted-target)<.02


def test_previous_policy_requires_checked_revision_instead_of_silent_reuse():
    from prototype.rink_calibration import verify_sealed_panel,evidence_digest
    result=fit_panel(example('left')[0],'left')
    result['policy']={**result['policy'],'version':'explicit-calibration-policy-v1'}
    result['evidence_sha256']=evidence_digest(result)
    with pytest.raises(ValueError,match='checks have changed'):
        verify_sealed_panel(result)


def test_duplicate_or_wrong_panel_landmarks_cannot_be_saved_as_checks():
    spec, _ = example('left'); spec['check_points'][0] = spec['fit_points'][0]
    with pytest.raises(ValueError, match='different'):
        fit_panel(spec, 'left')
    spec, _ = example('left');spec['fit_points'][0]['pixel_normalized'][0] = .8
    with pytest.raises(ValueError, match='other camera'):
        fit_panel(spec, 'left')


def test_marks_without_perspective_lines_are_explicitly_local_only():
    spec, _ = example('left', parallel=False)
    fit = fit_panel(spec, 'left')
    assert fit['status'] == 'checks_passed'
    assert fit['projection_scope'] == 'landmark_hull_only'


def test_centre_line_review_overlay_reaches_far_field_and_bottom_of_frame():
    record=fit_panel(example('left')[0],'left')
    # Rings have 181 vertices. The centre line is the first two-point overlay.
    centre=next(line for line in record['overlay_lines_normalized'] if len(line)==2)
    assert sorted(p[1] for p in centre)==pytest.approx([0.,1.])


def bundle(tmp_path, parallel=True):
    rng = np.random.default_rng(1)
    image = cv2.GaussianBlur(rng.integers(120, 255, (1080,1920,3), dtype=np.uint8), (3,3), 0)
    path = tmp_path/'anchor.png';cv2.imwrite(str(path), image)
    panels = {p: fit_panel(example(p, parallel)[0], p) for p in ['left', 'right']}
    for p in panels.values():
        p['frame']={'image_path':path.name,'image_sha256':digest(path),'time_s':1.}
    asset={'schema_version':SCHEMA,'id':'fixture','source_sha256':'source','status':'confirmed',
           'valid_interval_s':[0.,10.],'panels':panels}
    result={'schema_version':'source-calibration-bundle-v1','source_sha256':'source',
            'source_interval_s':[0.,10.],'calibrations':[asset]}
    out=tmp_path/'bundle.json';out.write_text(json.dumps(result));return out,result,image


def test_bundle_rejects_source_image_and_mapping_changes(tmp_path):
    path, spec, image = bundle(tmp_path)
    load_bundle(path, 'source', [1, 9])
    with pytest.raises(ValueError, match='another source'):
        load_bundle(path, 'different', [1, 9])
    spec['calibrations'][0]['panels']['left']['H_normalized_source_to_local_m'][0][0] += .1
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='Calibration evidence'):
        load_bundle(path)


def test_coverage_rejects_missing_intervals_and_ambiguous_poses(tmp_path):
    _, spec, _=bundle(tmp_path);a=spec['calibrations'][0]
    with pytest.raises(ValueError, match='required at source time'):
        validate_interval([a], [1,11], 'source')
    with pytest.raises(ValueError, match='overlap'):
        validate_interval([a,copy.deepcopy(a)], [1,9], 'source')


def test_camera_reuse_preserves_mapping_and_retains_blank_and_interval_gaps(tmp_path):
    path, _, image = bundle(tmp_path)
    g=CalibratedCameraGeometry(path)
    first=g.observe(image,1.)
    assert all(v[0] is not None for v in first.values()), first
    missing=g.observe(np.full_like(image, 230),2.)
    assert all(v[0] is None for v in missing.values())
    recovered=g.observe(image,3.)
    for p in ['left','right']:
        np.testing.assert_allclose(first[p][0], recovered[p][0])
    assert all(v[0] is None for v in g.observe(image,11.).values())
    assert g.provenance()['new_calibration_fits']==0


def test_local_only_mapping_does_not_project_far_field(tmp_path):
    path, _, image=bundle(tmp_path,parallel=False);g=CalibratedCameraGeometry(path)
    assert g.observe(image,1.)['left'][0] is not None
    _, G=example('left')
    assert g.point_supported('left',project(G,[[0.,0.]])[0]/3.)
    assert not g.point_supported('left',project(G,[[0.,-20.]])[0]/3.)


@pytest.mark.parametrize('mutual',[False,True])
def test_upstream_similarity_tracks_small_camera_motion_and_rejects_other_scene(mutual):
    rng=np.random.default_rng(5);image=cv2.GaussianBlur(rng.integers(120,255,(1080,1920,3),dtype=np.uint8),(3,3),0)
    A=np.vstack([cv2.getRotationMatrix2D((480,540),.2,1.003),[0.,0.,1.]])
    A[:2,2]+=[2.,-1.]
    moved=cv2.warpPerspective(image,A,(1920,1080))
    estimated,info=register(panel_features(image,'left'),panel_features(moved,'left'),mutual=mutual)
    assert estimated is not None,info
    pts=[[100.,100.],[800.,900.]]
    assert np.linalg.norm(project(estimated,pts)-project(A,pts),axis=1).max()<.3
    assert register(panel_features(image,'left'),panel_features(np.full_like(image,230),'left'),mutual=mutual)[0] is None


def traced_example(panel):
    _,G=example(panel);fit=[];checks=[];sign=-1 if panel=='left' else 1
    for kind,r in [('outer_ring',1.829),('middle_ring',1.219)]:
        for angle in range(0,360,30):
            world=r*np.array([np.cos(np.deg2rad(angle)),np.sin(np.deg2rad(angle))])
            point={'feature_id':kind,'pixel_normalized':(project(G,[world])[0]/[1920,1080]).tolist()}
            (checks if angle%90==30 else fit).append(point)
    for x in [-1.2,-.5,.5,1.2]:
        fit.append({'feature_id':'hog_line','pixel_normalized':(project(G,[[x,sign*6.401]])[0]/[1920,1080]).tolist()})
    for x in [-.8,.8]:
        checks.append({'feature_id':'hog_line','pixel_normalized':(project(G,[[x,sign*6.401]])[0]/[1920,1080]).tolist()})
    for y in [sign*2.5,sign*4.5]:
        fit.append({'feature_id':'centre_line','pixel_normalized':(project(G,[[0,y]])[0]/[1920,1080]).tolist()})
    for y in [sign*3.,sign*5.]:
        checks.append({'feature_id':'centre_line','pixel_normalized':(project(G,[[0,y]])[0]/[1920,1080]).tolist()})
    return {'fit_points':fit,'check_points':checks,'parallel_lines':example(panel)[0]['parallel_lines']},G


@pytest.mark.parametrize('panel',['left','right'])
def test_visible_curve_calibration_recovers_occluded_tee_without_using_tee_labels(panel):
    spec,G=traced_example(panel);cal=fit_panel(spec,panel)
    assert cal['status']=='checks_passed',cal['reasons']
    assert cal['maximum_check_error_m']<1e-5
    world=[[.3,-20. if panel=='left' else 12.]]
    np.testing.assert_allclose(project(cal['H_normalized_source_to_local_m'],project(G,world)/3.),world,atol=1e-4)
    assert all(c['metric_error_kind']=='distance_to_marking' for c in cal['checks'])


def test_wrongly_marked_curve_check_is_not_silently_dropped():
    spec,_=traced_example('right')
    next(p for p in spec['check_points'] if p['feature_id']=='hog_line')['pixel_normalized'][1]+=.02
    cal=fit_panel(spec,'right')
    assert cal['status']=='rejected'


def test_single_ring_and_unlabelled_guides_cannot_certify_long_range_axis():
    spec,G=traced_example('right')
    for key in ['fit_points','check_points']:
        spec[key]=[p for p in spec[key] if p['feature_id'] in ['outer_ring','hog_line']]
    # Retain enough separate observed arc points for fit and withheld checks.
    for angle in [15,75,135,195,255,315]:
        world=1.829*np.array([np.cos(np.deg2rad(angle)),np.sin(np.deg2rad(angle))])
        spec['fit_points'].append({'feature_id':'outer_ring','pixel_normalized':(project(G,[world])[0]/[1920,1080]).tolist()})
    for angle in [45,165]:
        world=1.829*np.array([np.cos(np.deg2rad(angle)),np.sin(np.deg2rad(angle))])
        spec['check_points'].append({'feature_id':'outer_ring','pixel_normalized':(project(G,[world])[0]/[1920,1080]).tolist()})
    with pytest.raises(ValueError,match='centre-line'):
        fit_panel(spec,'right')
    spec['parallel_lines']=[]
    # Insufficient independent orientation constraints must not become a
    # long-range mapping merely because the circle and hog happen to fit.
    with pytest.raises(ValueError,match='establish the rink origin'):
        fit_panel(spec,'right')


def test_bad_withheld_axis_cannot_be_hidden_by_successful_ring_checks():
    spec,_=traced_example('left')
    for row in spec['check_points']:
        if row.get('feature_id')=='centre_line':row['pixel_normalized'][0]+=.02
    cal=fit_panel(spec,'left')
    assert cal['status']=='rejected'
    assert 'Withheld markings fail the image reprojection check' in cal['reasons']


def test_curve_axis_checks_preserve_identifiable_plane():
    spec,_=traced_example('right')
    cal=fit_panel(spec,'right')
    assert cal['status']=='checks_passed',cal['reasons']
    assert cal['fit_rank']==cal['free_parameters']


def test_loading_a_confirmed_mapping_never_calls_the_optimizer(tmp_path,monkeypatch):
    from prototype import rink_calibration as module
    path,record,_=bundle(tmp_path)
    original=record['calibrations'][0]['panels']['left']['H_normalized_source_to_local_m']
    def forbidden(*args,**kwargs):raise AssertionError('Runtime must not refit confirmed calibration')
    monkeypatch.setattr(module,'least_squares',forbidden)
    loaded=load_bundle(path)
    assert loaded['calibrations'][0]['panels']['left']['H_normalized_source_to_local_m']==original
