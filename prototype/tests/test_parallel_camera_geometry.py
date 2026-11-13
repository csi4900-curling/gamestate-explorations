from types import SimpleNamespace

import cv2
import numpy as np

from prototype import parallel_camera_geometry as module
from prototype import split_camera_geometry as baseline
from prototype.vision_core import project


def test_vanishing_constraint_recovers_known_far_geometry_without_stone_fit():
    plane_to_image = np.array([[235., -48., 480.], [0., 70., 700.], [0., -.1, 1.]])
    truth = np.linalg.inv(plane_to_image)
    perturbation = np.array([[1., .005, 0.], [0., 1., 0.], [0., .003, 1.]])
    initial = perturbation @ truth
    vp = plane_to_image[:, 1]
    corrected = module.constrain_vanishing_point(initial, vp)
    world = np.array([[-1., -20.], [1., -18.], [0., -6.401], [0., 0.], [.5, 1.829]])
    pixels = project(plane_to_image, world)
    assert np.max(np.linalg.norm(project(initial, pixels) - world, axis=1)) > 1.
    np.testing.assert_allclose(project(corrected, pixels), world, atol=1e-10)
    normalized = module.constrain_vanishing_point(initial @ np.diag([3., 3., 1.]),
                                                  vp / [3., 3., 1.])
    np.testing.assert_allclose(project(normalized, pixels / 3.), world, atol=1e-10)


def test_boundary_detection_ignores_frame_border_and_interior_pole():
    image = np.full((1080, 960, 3), (120, 100, 95), np.uint8)
    # All four vertices lie on two world-parallel rink boundaries.
    def trapezoid(half_width_at_top):
        far = half_width_at_top * (1080 + 700) / 700
        return np.rint([[480 - half_width_at_top, 0], [480 + half_width_at_top, 0],
                        [480 + far, 1080], [480 - far, 1080]]).astype(np.int32)
    # A constant-width world divider changes image width with depth. A fixed
    # pixel-width stroke would introduce a second, incorrect vanishing point.
    cv2.fillConvexPoly(image, trapezoid(266), (25, 25, 25))
    cv2.fillConvexPoly(image, trapezoid(260), (245, 245, 245))
    cv2.line(image, (950, 0), (950, 1079), (255, 255, 255), 4)
    cv2.line(image, (470, 100), (510, 900), (20, 20, 160), 5)
    vp, diagnostic = module.parallel_boundaries(image)
    assert vp is not None, diagnostic
    np.testing.assert_allclose(vp[:2], [480., -700.], atol=15.)


def test_absent_markings_never_invent_calibration():
    blank = np.full((1080, 1920, 3), 240, np.uint8)
    vp, _ = module.parallel_boundaries(blank[:, :960])
    assert vp is None
    H, diagnostic = module.native_receiving_geometry(blank, np.eye(3))
    assert H is None
    assert diagnostic['status'] == 'native_markings_insufficient'


def test_both_camera_anchors_are_reused_and_failure_does_not_refit(monkeypatch):
    geometry = module.ParallelNativeGeometry.__new__(module.ParallelNativeGeometry)
    calls = {'native_left': 0, 'native_right': 0, 'transfer': 0}
    def left_register(frame):
        calls['native_left'] += 1
        return np.eye(3), {'status': 'registered'}
    geometry.left = SimpleNamespace(register=left_register, H=np.eye(3))
    geometry.calibration = {'right': {'refined_H': np.eye(3)}}
    geometry.right_reference_ellipse = {'valid': True}
    geometry.anchors = {}
    geometry.pending_right = None
    geometry.initialization_attempts = {'left': 0, 'right': 0}
    geometry.registration_attempts = {'left': 0, 'right': 0}
    geometry.source_house_fit_attempts = 0
    geometry.native_fit_attempts = geometry.boundary_attempts = 0
    geometry.wall_seconds = 0.
    geometry.stage_wall_seconds = {}
    monkeypatch.setattr(module, 'parallel_boundaries', lambda image: (np.array([0., -1., 1.]), {}))
    monkeypatch.setattr(module, 'features', lambda *args: (None, None))
    monkeypatch.setattr(module, 'transported_reference_camera', lambda *args: None)
    monkeypatch.setattr(baseline, 'transported_reference_camera', lambda *args: None)
    monkeypatch.setattr(baseline, 'features', lambda *args: (None, None))
    monkeypatch.setattr(baseline, 'fit_house_ellipse', lambda image: {'valid': True})
    monkeypatch.setattr(baseline, 'fit_source_house', lambda *args: (np.eye(3), {}))
    def native_right(*args):
        calls['native_right'] += 1
        return np.eye(3), {'status': 'native_markings_supported'}
    monkeypatch.setattr(module, 'native_receiving_geometry', native_right)
    def failed_transfer(*args, **kwargs):
        calls['transfer'] += 1
        return None, {'status': 'no_registration_features'}
    monkeypatch.setattr(module, 'transfer', failed_transfer)
    frame = np.zeros((1080, 1920, 3), np.uint8)
    first = geometry.observe(frame, 0.)
    for t in [1., 2.]:
        unavailable = geometry.observe(frame, t)
        assert all(unavailable[p][0] is None for p in ['left', 'right'])
    assert all(first[p][0] is not None for p in ['left', 'right'])
    assert calls == {'native_left': 1, 'native_right': 1, 'transfer': 4}
    assert geometry.native_fit_attempts == 1


def test_independent_boundaries_reject_a_moving_foreground_transform():
    def boundary():
        return {'selected': {
            'left': {'line': [1., 0., -100.], 'segment': [100., 0., 100., 1000.]},
            'right': {'line': [1., 0., -850.], 'segment': [850., 0., 850., 1000.]},
        }}
    reference = boundary()
    supported, result = module.boundary_motion_support(reference, boundary(), np.eye(3))
    assert supported and not result['used_to_fit_motion']
    foreground_motion = np.array([[1., 0., 8.], [0., 1., 0.], [0., 0., 1.]])
    supported, result = module.boundary_motion_support(reference, boundary(), foreground_motion)
    assert not supported
    assert result['status'] == 'boundary_motion_contradiction'
    assert module.boundary_motion_support(reference, {}, np.eye(3))[0] is False
