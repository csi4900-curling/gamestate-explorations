"""Reuse explicit source-bound calibration; abstain on unsupported camera motion.

Only source frames and operator calibration records initialize this component.
OpenCV normalized patch correlation checks reuse of the fixed camera pose.
An explicitly selected SIFT similarity mode verifies and aligns static source image correspondences. No reference match geometry, ring refits or trajectory alignment.
"""
from pathlib import Path
import collections
from concurrent.futures import ThreadPoolExecutor
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import time

import cv2
import numpy as np

from prototype.rink_calibration import load_bundle, project
from prototype.body_localization import transported_reference_camera
from prototype.calibration_pose import PoseVerifier, POLICY as POSE_POLICY

REGISTRATION_POLICY = {
    'version': 'source-camera-registration-v1', 'sift_features_per_panel': 1800,
    'sift_contrast_threshold': .01, 'descriptor_ratio': .7,
    'ransac_threshold_px_at_1080p': 4.5, 'max_iterations': 2000, 'confidence': .995,
    'minimum_unique_fit_inliers': 12, 'minimum_heldout_matches': 4,
    'minimum_inlier_width_fraction': .25, 'minimum_inlier_height_fraction': .12,
    'minimum_heldout_fraction_within_tolerance': .5,
    'provenance': 'Shared engineering gates; SIFT/RANSAC tolerance and spatial support adapted from the existing native registrar. Not calibrated probabilities or absolute error bounds.',
    'motion_model': 'Image rotation, uniform zoom and translation. Unsupported framing/perspective changes require another explicit calibration.',
}


def panel_features(image, panel, exclude_mask=None, *, scale=1.0, nfeatures=1800):
    # Compute separately: global nfeatures otherwise lets the textured receiving
    # view consume the departure view's entire feature budget.
    offset = 0 if panel == 'left' else 960
    crop = image[:, offset:offset+960]
    if exclude_mask is not None and exclude_mask.shape != (1080, 1920):
        raise ValueError('Foreground mask must use canonical source pixels')
    if scale != 1.0:
        nw, nh = round(960 * scale), round(1080 * scale)
        work = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_AREA)
    else:
        work = crop
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 2] > 110) & ((hsv[:, :, 1] < 110) |
            ((hsv[:, :, 0] > 85) & (hsv[:, :, 0] < 135)))).astype('uint8') * 255
    if exclude_mask is not None:
        panel_exclude = exclude_mask[:, offset:offset+960]
        if scale != 1.0:
            panel_exclude = cv2.resize(panel_exclude, (work.shape[1], work.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask[panel_exclude > 0] = 0
    kp, desc = cv2.SIFT_create(nfeatures=nfeatures, contrastThreshold=.01).detectAndCompute(
        cv2.cvtColor(work, cv2.COLOR_BGR2GRAY), mask)
    inv_scale = 1.0 / scale
    points = np.array([(k.pt[0]*inv_scale + offset, k.pt[1]*inv_scale) for k in kp], np.float32).reshape(-1, 2)
    return points, desc


def register(reference_features, current_features, *, mutual=False):
    """Shared similarity gates; reciprocal matching is an opt-in ablation only."""
    a, da = reference_features; b, db = current_features
    if da is None or db is None:
        return None, {'status': 'alignment_unverified', 'reason': 'No image descriptors'}
    pairs = cv2.BFMatcher().knnMatch(da, db, k=2)
    matches = [m for pair in pairs if len(pair) == 2 for m, n in [pair] if m.distance < .7*n.distance]
    if mutual:
        reverse=cv2.BFMatcher().knnMatch(db,da,k=2)
        reciprocal={(m.trainIdx,m.queryIdx) for pair in reverse if len(pair)==2
                    for m,n in [pair] if m.distance<.7*n.distance}
        matches=[m for m in matches if (m.queryIdx,m.trainIdx) in reciprocal]
    if not matches:
        return None, {'status': 'alignment_unverified', 'reason': 'No descriptor correspondences'}
    first = a[[m.queryIdx for m in matches]]; second = b[[m.trainIdx for m in matches]]
    # Duplicate orientations at one SIFT pixel stay together. Pixel grouping is
    # deterministic across time and does not use fitted residuals or stone paths.
    hold = np.array([(int(x*8)+int(y*8)) % 5 == 0 for x, y in first])
    evidence = {'matches': len(matches), 'heldout_matches': int(hold.sum()),
                'policy': REGISTRATION_POLICY['version'], 'calibration_refitted': False,
                'descriptor_matching':'reciprocal_ratio' if mutual else 'forward_ratio'}
    if hold.sum() < 4 or (~hold).sum() < 12:
        return None, {**evidence, 'status': 'alignment_unverified', 'reason': 'Insufficient independent image support'}
    matrix, inliers = cv2.estimateAffinePartial2D(first[~hold], second[~hold], method=cv2.RANSAC,
                    ransacReprojThreshold=4.5, maxIters=2000, confidence=.995)
    if matrix is None:
        return None, {**evidence, 'status': 'alignment_unverified', 'reason': 'Similarity registration failed'}
    A = np.vstack([matrix, [0., 0., 1.]])
    inside = inliers.ravel().astype(bool)
    unique = np.unique(np.round(first[~hold][inside], 3), axis=0)
    span = np.ptp(unique, axis=0) if len(unique) else np.zeros(2)
    errors = np.linalg.norm(project(A, first[hold]) - second[hold], axis=1)
    fraction = float(np.mean(errors <= 4.5))
    evidence.update(unique_fit_inliers=len(unique), inlier_span_px_at_1080p=span.tolist(),
                    heldout_median_error_px_at_1080p=float(np.median(errors)),
                    heldout_supported_fraction=fraction, reference_to_current=A.tolist())
    if len(unique) < 12 or span[0] < .25*960 or span[1] < .12*1080 or fraction < .5:
        return None, {**evidence, 'status': 'alignment_unverified', 'reason': 'Registration support or withheld matches fail'}
    if not np.isfinite(A).all() or np.linalg.det(A[:2, :2]) <= 0:
        return None, {**evidence, 'status': 'alignment_unverified', 'reason': 'Invalid camera motion'}
    return A, {**evidence, 'status': 'source_calibration_registered', 'physical_accuracy_verified': False}


class CalibratedCameraGeometry:
    def __init__(self, bundle_path, *, alignment='locked',foreground_checkpoint=None,foreground_sha256=None,
                 fast_scale=None, fast_nfeatures=1200, parallel_panels=False):
        if alignment not in ('locked','static_feature_similarity'):
            raise ValueError('Unknown explicit-camera alignment method')
        if fast_scale is not None:
            fast_scale = float(fast_scale)
            if not (0.1 <= fast_scale < 1.0):
                raise ValueError('fast_scale must lie in [0.1, 1.0)')
        self.alignment=alignment
        self.fast_scale = fast_scale if alignment == 'static_feature_similarity' else None
        self.fast_nfeatures = int(fast_nfeatures)
        self.parallel_panels = bool(parallel_panels)
        self._pool = ThreadPoolExecutor(max_workers=2) if (self.parallel_panels and self.alignment == 'static_feature_similarity') else None
        self.fast_accepted = 0
        self.fallback_attempts = 0
        self.bundle_path = Path(bundle_path)
        self.bundle = load_bundle(bundle_path)
        if alignment!='static_feature_similarity' and any(p.get('projection_scope')=='operator_template_alignment' for a in self.bundle['calibrations'] for p in a['panels'].values()):
            raise ValueError('Template calibration requires verified source-image registration')
        self.anchors = []
        self.counts = collections.Counter()
        self.wall_seconds = 0.
        self._current = {}
        self.foreground=None;reference_masks={}
        if foreground_checkpoint is not None:
            from prototype.camera_foreground import CameraForeground
            self.foreground=CameraForeground(foreground_checkpoint,foreground_sha256)
        for asset in self.bundle['calibrations']:
            for panel, record in asset['panels'].items():
                frame = cv2.imread(str(self.bundle_path.parent / record['frame']['image_path']))
                if frame is None:
                    raise ValueError('Cannot read explicit calibration frame')
                frame = cv2.resize(frame, (1920, 1080))
                foreground=None
                if self.foreground is not None:
                    key=record['frame']['image_sha256']
                    if key not in reference_masks:reference_masks[key]=self.foreground.mask(frame)
                    foreground=reference_masks[key]
                H = np.asarray(record['H_normalized_source_to_local_m'], float)
                region = (0, 0, 320, 360) if panel == 'left' else (320, 0, 640, 360)
                self.anchors.append({'id': asset['id'], 'panel': panel, 'record': record,
                                     'interval': asset['valid_interval_s'], 'H': H,
                                     'verifier': PoseVerifier(frame, record, panel),
                                     'features':panel_features(frame,panel,foreground) if alignment=='static_feature_similarity' else None,
                                     'fast_features':panel_features(frame,panel,foreground,scale=self.fast_scale,nfeatures=self.fast_nfeatures) if self.fast_scale is not None else None,
                                     'prior': self.camera_prior(record,H,H,region,np.eye(3))})

    def close(self):
        if self._pool is not None:
            self._pool.shutdown(wait=False)
            self._pool = None

    @staticmethod
    def camera_prior(record, reference_H, current_H, region, image_alignment):
        if not record.get('camera_model'):
            return transported_reference_camera(reference_H,current_H,region)
        model=record['camera_model'];P=image_alignment@np.asarray(model['projection_xyz_up_to_normalized_source'])
        return {'camera':{'plane':P[:,[0,1,3]],'vertical':P[:,2]},'alternatives':[],
                'uncertainty_scope':'One-at-a-time ±2 cm feature height only. Camera calibration error and intrinsic assumptions are not included; not an accuracy bound.',
                'diagnostic':{'status':'fitted_physical_camera','camera_centre_m':model['camera_centre_m'],
                    'orthogonality_residual':model['orthogonality_residual'],
                    'physical_accuracy_validated':False,'assumptions':model['assumptions'],
                    'temporal_model':'One fitted static camera, transported only through verified source-image registration.'}}

    def observe(self, frame, time_s):
        start = time.perf_counter()
        image = frame if frame.shape[:2] == (1080, 1920) else cv2.resize(frame, (1920, 1080))
        result = {}; self._current = {}
        active_anchors = {}
        for panel in ('left', 'right'):
            anchors = [a for a in self.anchors if a['panel'] == panel and a['interval'][0] <= time_s < a['interval'][1]]
            if len(anchors) != 1:
                result[panel] = None, {'status': 'calibration_required', 'reason': 'No unambiguous calibration interval'}, None
                self.counts[panel+':calibration_required'] += 1
            else:
                active_anchors[panel] = anchors[0]
        foreground = None
        fast_results = {}
        if self.alignment == 'static_feature_similarity' and self.fast_scale is not None and active_anchors:
            def run_fast(panel_name):
                anc = active_anchors[panel_name]
                try:
                    return register(anc['fast_features'], panel_features(image, panel_name, None,
                                                                         scale=self.fast_scale,
                                                                         nfeatures=self.fast_nfeatures))
                except (ValueError, cv2.error, np.linalg.LinAlgError) as exc:
                    return None, {'status': 'alignment_unverified', 'reason': str(exc)}
            if self._pool is not None and len(active_anchors) == 2:
                futs = {p: self._pool.submit(run_fast, p) for p in active_anchors}
                fast_results = {p: f.result() for p, f in futs.items()}
            else:
                fast_results = {p: run_fast(p) for p in active_anchors}
        elif self.foreground is not None and active_anchors:
            foreground = self.foreground.mask(image)
        for panel, anchor in active_anchors.items():
            try:
                inverse_alignment=np.eye(3)
                if self.alignment=='static_feature_similarity':
                    if panel in fast_results:
                        A, diagnostic = fast_results[panel]
                        if A is not None:
                            self.fast_accepted += 1
                            diagnostic['registration_tier'] = f'fast_scale_{self.fast_scale:g}'
                        else:
                            self.fallback_attempts += 1
                            if self.foreground is not None and foreground is None:
                                foreground = self.foreground.mask(image)
                            A, diagnostic = register(anchor['features'], panel_features(image, panel, foreground))
                            diagnostic['registration_tier'] = 'full_res_fallback'
                    else:
                        A,diagnostic=register(anchor['features'],panel_features(image,panel,foreground))
                    supported=A is not None
                    if supported:
                        scale=np.diag([1/3.,1/3.,1.])
                        inverse_alignment=np.linalg.inv(scale@A@np.linalg.inv(scale))
                else:
                    supported, diagnostic = anchor['verifier'].check(image)
                H=anchor['H']@inverse_alignment if supported else None
                prior=(self.camera_prior(anchor['record'],anchor['H'],H,
                       (0,0,320,360) if panel=='left' else (320,0,640,360),np.linalg.inv(inverse_alignment))
                       if supported and self.alignment=='static_feature_similarity' else anchor['prior'] if supported else None)
                if supported:
                    self._current[panel] = anchor, inverse_alignment
                diagnostic.update(calibration_id=anchor['id'], calibration_origin='explicit_operator_markings',
                                  calibration_frame_s=anchor['record']['frame']['time_s'],
                                  projection_scope=anchor['record']['projection_scope'],
                                  no_new_calibration_fit=True)
                result[panel] = H, diagnostic, prior
                self.counts[panel+':'+diagnostic['status']] += 1
            except (ValueError, cv2.error, np.linalg.LinAlgError) as exc:
                result[panel] = None, {'status': 'alignment_unverified', 'reason': str(exc)}, None
                self.counts[panel+':alignment_unverified'] += 1
        self.wall_seconds += time.perf_counter()-start
        return result

    def point_supported(self, panel, normalized_pixel):
        if panel not in self._current:
            return False
        anchor, current_to_anchor = self._current[panel]
        if anchor['record']['projection_scope'] in ('perspective_constrained','operator_template_alignment'):
            return True
        p = project(current_to_anchor, [normalized_pixel])[0] / [640., 360.]
        hull = np.asarray(anchor['record']['image_hull_normalized'], np.float32)
        return cv2.pointPolygonTest(hull, tuple(map(float, p)), False) >= 0

    def provenance(self):
        return {'mode': 'explicit_source_calibration_v1', 'bundle': str(self.bundle_path),
                'calibration_ids': [a['id'] for a in self.bundle['calibrations']],
                'origin': 'Explicit operator-selected static rink landmarks and reviewed projection overlays',
                'new_calibration_fits': 0, 'status_counts': dict(self.counts),
                'registration_policy': REGISTRATION_POLICY if self.alignment=='static_feature_similarity' else POSE_POLICY,
                'alignment_method':self.alignment,'wall_seconds': self.wall_seconds,
                'image_alignment_attempts':sum(self.counts.values()) if self.alignment=='static_feature_similarity' else 0,
                'accepted_image_alignments':sum(n for k,n in self.counts.items() if k.endswith(':source_calibration_registered')),
                'foreground_model':self.foreground.provenance if self.foreground is not None else None,
                'foreground_mask_frames':self.foreground.frames if self.foreground is not None else 0,
                'foreground_seconds':self.foreground.seconds if self.foreground is not None else 0.,
                'fast_scale':self.fast_scale,
                'fast_nfeatures':self.fast_nfeatures if self.fast_scale is not None else None,
                'parallel_panels':self.parallel_panels,
                'fast_accepted':self.fast_accepted,
                'fallback_attempts':self.fallback_attempts,
                'failure_policy': 'No inferred replacement geometry; missing alignment or unsupported image region remains missing.',
                'physical_metric_accuracy_validated': False, 'camera_feed_synchronization_verified': False}
