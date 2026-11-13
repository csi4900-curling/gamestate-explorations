"""Development calibration from source rink boundaries and native painted lines.

Uses upstream OpenCV LSD/fitLine/SIFT and SciPy least_squares. No stone tracks,
match IDs, temporal offsets, or manually supplied new calibration enter fitting.
"""
import time
from pathlib import Path
import sys
import cv2
import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prototype.vision_core import project
from prototype.rectification_core import RADII, ring_edges, ring_summary, validate_rings
from prototype.body_localization import transported_reference_camera
from prototype.camera_geometry import features, transfer
from prototype.split_camera_geometry import SplitCameraGeometry

def parallel_boundaries(panel):
    started = time.perf_counter()
    gray = cv2.cvtColor(panel, cv2.COLOR_BGR2GRAY).astype(np.float32)
    detected = cv2.createLineSegmentDetector(cv2.LSD_REFINE_ADV).detect(gray.astype(np.uint8))[0]
    candidates = {'left': [], 'right': []}
    if detected is None:
        return None, {'status': 'no_lines'}
    height, width = gray.shape
    for segment in detected.reshape(-1, 4):
        a, b = segment.reshape(2, 2).astype(float)
        delta = b - a
        length = float(np.linalg.norm(delta))
        if abs(delta[1]) <= abs(delta[0]):
            continue
        centre = (a + b) / 2
        side = 'left' if centre[0] < width / 2 else 'right'
        # Rink boundaries diverge away from their shared longitudinal vanishing point.
        if (delta[0] / delta[1] < 0) != (side == 'left'):
            continue
        normal = np.array([-delta[1], delta[0]]) / length
        if normal[0] * (width / 2 - centre[0]) < 0:
            normal *= -1
        along = np.linspace(.05, .95, 40)
        locations = a + along[:, None] * delta
        offsets = np.linspace(1.5, 21, 20)
        inside = locations[:, None] + offsets[None, :, None] * normal
        outside = locations[:, None] - offsets[None, :, None] * normal
        valid = ((outside[:, :, 0] >= 0) & (outside[:, :, 0] < width - 1) &
                 (inside[:, :, 0] >= 0) & (inside[:, :, 0] < width - 1) &
                 (outside[:, :, 1] >= 0) & (outside[:, :, 1] < height - 1) &
                 (inside[:, :, 1] >= 0) & (inside[:, :, 1] < height - 1)).all(axis=1)
        if not valid.any():
            continue
        def sample(points):
            return cv2.remap(gray, points[:, :, 0].astype('float32'), points[:, :, 1].astype('float32'), cv2.INTER_LINEAR)
        contrast = float(np.median((sample(inside)[valid] - sample(outside)[valid]).mean(axis=1)))
        if contrast <= 0:
            continue
        line = np.cross([*a, 1], [*b, 1])
        line /= np.linalg.norm(line[:2])
        candidates[side].append({'segment': segment.tolist(), 'length_px': length,
                                  'contrast': contrast, 'score': contrast * length * float(valid.mean()),
                                  'line': line.tolist()})
    for side in candidates:
        candidates[side].sort(key=lambda row: row['score'], reverse=True)
    if not all(candidates.values()):
        return None, {'status': 'missing_boundary', 'candidates': candidates}
    selected = {side: candidates[side][0] for side in candidates}
    vp = np.cross(selected['left']['line'], selected['right']['line'])
    if abs(vp[2]) < 1e-10:
        return None, {'status': 'unidentifiable_parallel_image_lines', 'candidates': candidates}
    vp /= vp[2]
    return vp, {'status': 'candidate_not_validated', 'vanishing_point_px': vp.tolist(),
                'selected': selected, 'candidates': candidates, 'wall_s': time.perf_counter() - started}


def boundary_motion_support(reference_boundary, current_boundary, normalized_motion):
    """Check motion against source rink edges excluded from SIFT fitting.

    The tolerance is the existing 1.5 normalized-pixel registration tolerance.
    This rejects an unsupported mapping; it never adjusts the mapping to agree.
    """
    if not reference_boundary.get('selected') or not current_boundary.get('selected'):
        return False, {'status': 'boundaries_unavailable'}
    A = np.diag([3., 3., 1.]) @ normalized_motion @ np.diag([1/3, 1/3, 1.])
    errors = []
    for side in ('left', 'right'):
        line = np.linalg.inv(A).T @ np.asarray(reference_boundary['selected'][side]['line'])
        line /= np.linalg.norm(line[:2])
        points = np.asarray(current_boundary['selected'][side]['segment']).reshape(2, 2)
        errors.extend(abs(np.c_[points, np.ones(2)] @ line) / 3.)
    maximum = float(max(errors))
    return maximum <= 1.5, {'status': 'supported' if maximum <= 1.5 else 'boundary_motion_contradiction',
                            'maximum_normalized_pixel_error': maximum,
                            'tolerance_normalized_px': 1.5,
                            'used_to_fit_motion': False}

def hog_edges(image, H, region, signed_y, search_px=21):
    """Read house-facing hog edge, whose nominal distance is 6.401 m (R1b)."""
    inv = np.linalg.inv(H)
    world = np.column_stack([np.linspace(-2, 2, 25), np.full(25, signed_y)])
    pixels = project(inv, world)
    normal = project(inv, world + [0, .01]) - pixels
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    offsets = np.arange(-search_px, search_px + .125, .25)
    grid = pixels[:, None] + normal[:, None] * offsets[None, :, None]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    values = cv2.remap(gray, grid[:, :, 0].astype('float32'), grid[:, :, 1].astype('float32'),
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    gap = 6
    score = -np.sign(signed_y) * (values[:, 2 * gap:] - values[:, :-2 * gap])
    rows = []
    x0, y0, x1, y1 = region
    for i, profile in enumerate(score):
        j = int(np.argmax(profile))
        if j in (0, len(profile) - 1) or profile[j] < 10:
            continue
        point = pixels[i] + normal[i] * offsets[j + gap]
        if not (x0 + 3 < point[0] < x1 - 3 and y0 + 3 < point[1] < y1 - 3):
            continue
        sensitivity = abs(np.diff(project(H, [point - normal[i], point + normal[i]])[:, 1])[0]) / 2
        rows.append({"pixel": point.tolist(), "contrast": float(profile[j]),
                     "metres_per_normal_pixel": float(sensitivity)})
    return rows

def longitudinal_edges(image, H, world_x, signed_hog, search_px=21):
    """Probe nominal wheelchair wool lines; no longitudinal coordinate is assigned."""
    sign = np.sign(signed_hog)
    world = np.column_stack([np.full(60, world_x), sign * np.linspace(1.95, 6.25, 60)])
    pixels = project(np.linalg.inv(H), world)
    offsets = np.arange(-search_px, search_px + .125, .25)
    grid = pixels[:, None, :] + offsets[None, :, None] * np.array([1., 0.])
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    values = cv2.remap(gray, grid[:, :, 0].astype('float32'), grid[:, :, 1].astype('float32'),
                      cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    gap = 6
    scores = .5 * (values[:, 2 * gap:] + values[:, :-2 * gap]) - values[:, gap:-gap]
    rows = []
    for i, profile in enumerate(scores):
        j = int(np.argmax(profile))
        if j in (0, len(profile) - 1) or profile[j] < 10:
            continue
        point = pixels[i] + [offsets[j + gap], 0]
        if not (0 < point[0] < image.shape[1] and 0 < point[1] < image.shape[0]):
            continue
        sensitivity = abs(np.diff(project(H, [point - [1, 0], point + [1, 0]])[:, 0])[0]) / 2
        rows.append({'pixel': point.tolist(), 'world_x': world_x,
                     'contrast': float(profile[j]), 'metres_per_normal_pixel': float(sensitivity)})
    return rows


def constrain_vanishing_point(H, vanishing_point):
    """Pin the observed longitudinal vanishing point, retaining the tee origin.

    The correction is first-order identity at the tee apart from the small
    lateral shear required by the measured longitudinal direction. This avoids
    fitting unidentifiable far-field perspective from house rings alone.
    """
    H = np.asarray(H, dtype=float)
    v = H @ np.asarray(vanishing_point, dtype=float)
    if not np.isfinite(v).all() or abs(v[1]) < 1e-10:
        raise ValueError('Longitudinal vanishing point is unidentifiable')
    C = np.array([[1., -v[0] / v[1], 0], [0, 1., 0], [0, -v[2] / v[1], 1.]])
    result = C @ H
    if not np.isfinite(result).all() or abs(np.linalg.det(result)) < 1e-12:
        raise ValueError('Singular boundary-constrained homography')
    return result / result[2, 2]


def native_receiving_geometry(frame, initial_normalized):
    """Refine with native outer/middle rings, inside hog edge and wool lines.

    Inner-ring samples and the centre line are withheld. Nominal wheelchair-line
    outer edges are +/-0.457 m from the centre line (World Curling R1(c)).
    Existing image-evidence acceptance bounds are retained; they do not certify
    absolute metric accuracy. No measured stone position is an optimization input.
    """
    started = time.perf_counter()
    image = cv2.resize(frame, (1920, 1080))
    region = (960, 0, 1920, 1080)
    initial = np.asarray(initial_normalized) @ np.diag([1 / 3, 1 / 3, 1.])
    edges = [e for radius in RADII[:2] for e in ring_edges(image, initial, radius, region)]
    train = [e for e in edges if int(e['angle_deg'] // 3) % 4]
    held = [e for e in edges if not int(e['angle_deg'] // 3) % 4]
    inner = ring_edges(image, initial, RADII[2], region)
    hog = hog_edges(image, initial, region, 6.401)
    wool = [p for x in [-.457, .457] for p in longitudinal_edges(image, initial, x, 6.401)]
    centre = longitudinal_edges(image, initial, 0., 6.401)
    counts = {'training_ring': len(train), 'heldout_angles': len(held), 'inner_ring': len(inner),
              'hog': len(hog), 'centreline': len(centre),
              'wheelchair_lines': {str(x): sum(p['world_x'] == x for p in wool) for x in [-.457, .457]}}
    diagnostic = {'counts': counts, 'calibration_uses_stone_tracks': False,
                  'physical_metric_accuracy_validated': False}
    # Ring support counts are the existing receiving initializer's requirements.
    if (len(train) < 70 or len(held) < 15 or len(inner) < 40 or len(hog) < 4
            or len(centre) < 2 or any(n < 2 for n in counts['wheelchair_lines'].values())):
        return None, {**diagnostic, 'status': 'native_markings_insufficient'}
    hog_px = np.array([p['pixel'] for p in hog])
    vx, vy, x, y = cv2.fitLine(hog_px.astype(np.float32), cv2.DIST_WELSCH, 0, .01, .01).ravel()
    direction, origin = np.array([vx, vy]), np.array([x, y])
    hog_px = origin + ((hog_px - origin) @ direction)[:, None] * direction
    hog_scale = np.array([p['metres_per_normal_pixel'] for p in hog])
    wool_px = np.array([p['pixel'] for p in wool])
    wool_x = np.array([p['world_x'] for p in wool])
    wool_scale = np.array([p['metres_per_normal_pixel'] for p in wool])
    N = np.array([[1 / 1920, 0, -.5], [0, 1 / 1080, -.5], [0, 0, 1.]])
    normalized = initial @ np.linalg.inv(N)
    normalized /= normalized[2, 2]
    points = project(N, [e['pixel'] for e in train])
    radii = np.array([e['radius_m'] for e in train])
    scale = np.array([e['metres_per_normal_pixel'] for e in train])

    def unpack(p):
        return np.r_[p, 1.].reshape(3, 3)

    def residual(p):
        H = unpack(p) @ N
        ring = (np.linalg.norm(project(unpack(p), points), axis=1) - radii) / scale
        hog_residual = (project(H, hog_px)[:, 1] - 6.401) / hog_scale
        wool_residual = (project(H, wool_px)[:, 0] - wool_x) / wool_scale
        return np.r_[ring, hog_residual, wool_residual]

    opt = least_squares(residual, normalized.ravel()[:8], loss='soft_l1', f_scale=1.,
                        max_nfev=150, x_scale='jac')
    H = unpack(opt.x) @ N
    H /= H[2, 2]
    target = H @ np.diag([3., 3., 1.])
    supported, rings = validate_rings(cv2.resize(image, (640, 360)), target, (320, 0, 640, 360))
    held_summary, inner_summary = ring_summary(H, held), ring_summary(H, inner)
    centre_px = np.array([p['pixel'] for p in centre])
    centre_before = float(np.median(abs(project(initial, centre_px)[:, 0])))
    centre_after = float(np.median(abs(project(H, centre_px)[:, 0])))
    inner_before = ring_summary(initial, inner)
    hog_max = float(np.max(abs(project(H, hog_px)[:, 1] - 6.401)))
    accepted = (opt.success and np.isfinite(H).all() and supported
                and held_summary['p95_abs_radial_error_m'] < .26
                and inner_summary['p95_abs_radial_error_m'] < .25 and hog_max < .15
                and inner_summary['median_abs_radial_error_m'] <= inner_before['median_abs_radial_error_m']
                and centre_after <= centre_before)
    diagnostic.update(status='native_markings_supported' if accepted else 'native_markings_check_failed',
                      training_ring=ring_summary(H, train), heldout_angles=held_summary,
                      withheld_inner=inner_summary, withheld_inner_before=inner_before,
                      withheld_centreline_median_abs_x_before_m=centre_before,
                      withheld_centreline_median_abs_x_after_m=centre_after,
                      hog_max_residual_m=hog_max, middle_frame_ring_check=rings,
                      optimizer_evaluations=opt.nfev, initial_H_native=initial.tolist(),
                      fitted_H_native=H.tolist(), wall_s=time.perf_counter() - started,
                      feature_semantics='Native paint/wool pixels; nominal rink geometry; no stone fitting')
    return target if accepted else None, diagnostic


class ParallelNativeGeometry(SplitCameraGeometry):
    """Initialize automatically, then reuse recording-local anchors in BOTH views."""

    def __init__(self, calibration, annotations, reference_frames):
        super().__init__(calibration, annotations, reference_frames)
        self.pending_right = None
        self.native_fit_attempts = 0
        self.boundary_attempts = 0
        self.boundary_registration_checks = 0

    def _anchor(self, panel, normalized, H, time_s, diagnostic):
        region = (0, 0, 320, 360) if panel == 'left' else (320, 0, 640, 360)
        prior = transported_reference_camera(H, H, region)
        self.anchors[panel] = {'time_s': time_s, 'frame': normalized.copy(), 'H': H,
                               'features': features(normalized, region), 'prior': prior,
                               'initialization': diagnostic}
        return H, {**diagnostic, 'anchor_time_s': time_s}, prior

    def _transfer_anchor(self, anchor, normalized, panel, native_frame=None):
        region = (0, 0, 320, 360) if panel == 'left' else (320, 0, 640, 360)
        H, diagnostic = transfer(anchor['frame'], normalized, anchor['H'], region,
                                 reference_features=anchor['features'], model='similarity')
        if H is not None and panel == 'left':
            self.boundary_registration_checks += 1
            if native_frame is None:
                H, diagnostic = None, {**diagnostic, 'status': 'native_boundary_check_unavailable'}
            else:
                _, boundary = parallel_boundaries(cv2.resize(native_frame, (1920, 1080))[:, :960])
                supported, check = boundary_motion_support(anchor['initialization']['boundary'], boundary,
                                                           np.asarray(diagnostic['reference_to_current']))
                diagnostic = {**diagnostic, 'boundary_motion_check': check,
                              'quality_rejection_applied': True}
                if not supported:
                    H, diagnostic = None, {**diagnostic, 'status': check['status']}
        prior = None
        if H is not None and anchor['prior'] is not None:
            A = np.asarray(diagnostic['reference_to_current'])
            def move(camera):
                return {'plane': A @ camera['plane'], 'vertical': A @ camera['vertical']}
            prior = {'camera': move(anchor['prior']['camera']),
                     'diagnostic': anchor['prior']['diagnostic'],
                     'alternatives': [move(c) for c in anchor['prior']['alternatives']]}
        return H, {**diagnostic, 'stage': 'recording_anchor_registration',
                    'anchor_time_s': anchor['time_s'], 'no_new_calibration_fit': True}, prior

    def _panel(self, frame, normalized, time_s, panel):
        if panel in self.anchors:
            self.registration_attempts[panel] += 1
            return self._transfer_anchor(self.anchors[panel], normalized, panel, frame)
        if panel == 'left':
            self.initialization_attempts[panel] += 1
            native = cv2.resize(frame, (1920, 1080))
            H, registration = self.left.register(native)
            if H is None:
                return None, registration, None
            self.boundary_attempts += 1
            vp, boundary = parallel_boundaries(native[:, :960])
            if vp is None:
                return None, {'status': 'longitudinal_boundaries_unavailable', 'boundary': boundary}, None
            H = constrain_vanishing_point(H, vp) @ np.diag([3., 3., 1.])
            return self._anchor(panel, normalized, H, time_s,
                                {'status': 'parallel_boundaries_constrained', 'stage': 'source_boundary_initialization',
                                 'reference_registration': registration, 'boundary': boundary,
                                 'physical_metric_accuracy_validated': False})
        if self.pending_right is None:
            H, diagnostic, prior = super()._panel(frame, normalized, time_s, panel)
            if H is None:
                return H, diagnostic, prior
            self.pending_right = self.anchors.pop('right')
        else:
            H, diagnostic, prior = self._transfer_anchor(self.pending_right, normalized, panel)
            if H is None:
                return H, diagnostic, prior
        self.native_fit_attempts += 1
        target, refined = native_receiving_geometry(frame, H)
        if target is None:
            return None, {**refined, 'stage': 'native_paint_initialization',
                          'baseline_initializer': diagnostic, 'no_metric_fallback': True}, None
        return self._anchor(panel, normalized, target, time_s,
                            {**refined, 'stage': 'native_paint_initialization',
                             'baseline_initializer': diagnostic})

    def observe(self, frame, time_s):
        started = time.perf_counter()
        normalized = cv2.resize(frame, (640, 360))
        result = {}
        for panel in ('left', 'right'):
            stage = 'anchor_registration' if panel in self.anchors else 'constraint_initialization'
            stage_start = time.perf_counter()
            try:
                H, diagnostic, prior = self._panel(frame, normalized, time_s, panel)
            except (ValueError, np.linalg.LinAlgError, FloatingPointError, cv2.error) as exc:
                H, diagnostic, prior = None, {'status': 'undefined_geometry', 'reason': str(exc)}, None
            elapsed = time.perf_counter() - stage_start
            key = panel + ':' + stage
            self.stage_wall_seconds[key] = self.stage_wall_seconds.get(key, 0.) + elapsed
            result[panel] = H, {**diagnostic, 'runtime': {'stage': stage, 'wall_seconds': elapsed}}, prior
        self.wall_seconds += time.perf_counter() - started
        return result

    def provenance(self):
        result = super().provenance()
        result.update(initializer='Departure parallel-boundary VP; receiving native rings/hog/wheelchair lines',
                      version='parallel-native-similarity-development-v2', native_fit_attempts=self.native_fit_attempts,
                      new_application_quality_thresholds=True,
                      threshold_provenance='Development paint-profile contrast/support gates and boundary-motion gate are programmed, uncalibrated heuristics. Registration tolerance is inherited; no per-video tuning is permitted.',
                      boundary_attempts=self.boundary_attempts,
                      boundary_registration_checks=self.boundary_registration_checks,
                      registration_model='OpenCV SIFT/RANSAC similarity; departure source boundaries independently checked',
                      calibration_uses_stone_tracks=False, camera_feed_offset_fitted=False,
                      failure_policy='Unsupported markings/registration leave geometry missing; no metric fallback or refit after accepted recording anchors')
        return result
