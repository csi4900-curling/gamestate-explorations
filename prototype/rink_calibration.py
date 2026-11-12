"""Explicit source-frame calibration, independent checks, and immutable evidence.

User-selected physical markings are data. OpenCV/SciPy fit the plane; no stone
trajectory, recording ID, learned rink detector or per-recording rule is used.
Engineering gates check internal consistency, not absolute trajectory accuracy.
"""
from pathlib import Path
import hashlib
import json
import math

import cv2
import numpy as np
from scipy.optimize import least_squares

SCHEMA = 'explicit-rink-calibration-v1'
CANONICAL_SIZE = (1920, 1080)
POLICY = {
    'version': 'explicit-calibration-policy-v3',
    'minimum_fit_points': 6, 'minimum_check_points': 3,
    'minimum_trace_fit_constraints': 12, 'minimum_trace_check_points': 6,
    'maximum_fit_error_px_at_1080p': 6.,
    'maximum_check_error_px_at_1080p': 6.,
    'maximum_check_error_m': .15,
    'gate_status': 'Engineering consistency gates, not validated accuracy bounds or supervisor-approved accuracy targets.',
    'extrapolation': 'Two longitudinal guides required. Curve-only calibration also requires a fitted centre line and two separate centre-line checks. Otherwise local hull only.',
}


def evidence_digest(record):
    keys = ('panel', 'status', 'H_normalized_source_to_local_m', 'fit_points', 'check_points',
            'parallel_lines', 'projection_scope', 'image_hull_normalized', 'checks', 'policy')
    payload = {key: record[key] for key in keys}
    if 'camera_model' in record:payload['camera_model']=record['camera_model']
    for key in ('calibration_method','template_parameters','template_dimensions_m','check_status'):
        if key in record:payload[key]=record[key]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def verify_sealed_panel(record):
    if record.get('evidence_sha256') != evidence_digest(record):
        raise ValueError('Calibration evidence changed or needs a checked revision; inspect and preview it again')
    if record['policy']['version'] != POLICY['version']:
        raise ValueError('Calibration checks have changed; inspect and re-preview this saved calibration under the current policy')
    H = np.asarray(record['H_normalized_source_to_local_m'], float)
    if H.shape != (3, 3) or not np.isfinite(H).all() or abs(np.linalg.det(H)) < 1e-12:
        raise ValueError('Invalid saved camera mapping')
    scope = record.get('projection_scope')
    if scope not in ('perspective_constrained', 'landmark_hull_only','operator_template_alignment'):
        raise ValueError('Unknown calibration projection scope')
    if scope=='operator_template_alignment':
        from prototype.rink_template import template_panel
        rebuilt=template_panel(record['template_parameters'],record['panel'])
        if record.get('check_status')!='operator_visual_alignment_only' or record['fit_points'] or record['check_points'] or record['checks']:
            raise ValueError('Template alignment must not claim measured landmark checks')
        if not np.allclose(rebuilt['camera_model']['projection_xyz_up_to_normalized_source'],record['camera_model']['projection_xyz_up_to_normalized_source'],rtol=1e-10,atol=1e-10):
            raise ValueError('Template controls and saved physical camera disagree')
    if scope == 'perspective_constrained' and len(record.get('parallel_lines', [])) != 2:
        raise ValueError('Saved perspective mapping has no longitudinal guide evidence')
    if 'camera_model' in record:
        P=np.asarray(record['camera_model']['projection_xyz_up_to_normalized_source'],float)
        if P.shape!=(3,4) or not np.isfinite(P).all():raise ValueError('Invalid physical camera projection')
        camera_H=np.linalg.inv(P[:,[0,1,3]])
        if not np.allclose(camera_H/camera_H[2,2],H/H[2,2],rtol=1e-8,atol=1e-8):
            raise ValueError('Ground mapping and physical camera are inconsistent')
    return True


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def project(H, points):
    a = np.c_[np.asarray(points, float).reshape(-1, 2), np.ones(len(points))] @ np.asarray(H).T
    if np.any(abs(a[:, 2]) < 1e-10):
        raise ValueError('Projection crosses the camera horizon')
    result = a[:, :2] / a[:, 2:]
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite calibration projection')
    return result


def landmarks(panel):
    if panel not in ('left', 'right'):
        raise ValueError('Unknown camera panel')
    sign = -1 if panel == 'left' else 1
    rows = [{'id': 'tee', 'label': 'Tee: centre line × tee line', 'xy_m': [0., 0.]}]
    for name, radius in [('outer', 1.829), ('middle', 1.219), ('inner', .610)]:
        for direction, x, y, label in [('left', -radius, 0., 'camera-left tee-line intersection'),
                                       ('right', radius, 0., 'camera-right tee-line intersection'),
                                       ('play', 0., sign * radius, 'centre-line intersection toward play'),
                                       ('behind', 0., -sign * radius, 'centre-line intersection behind tee')]:
            rows.append({'id': name + '_' + direction, 'label': name.title() + ' ring: ' + label,
                         'xy_m': [x, y]})
    for name, x, label in [('centre', 0., 'centre line'), ('left', -.457, 'camera-left wheelchair line outer edge'),
                           ('right', .457, 'camera-right wheelchair line outer edge')]:
        rows.append({'id': 'hog_' + name, 'label': 'House-facing hog edge × ' + label,
                     'xy_m': [x, sign * 6.401]})
    return rows


def marking_types(panel):
    sign = -1 if panel == 'left' else 1
    return [*({'id': name+'_ring', 'label': name.title()+' ring outer edge (click visible arc)',
               'kind': 'ring', 'value_m': radius} for name, radius in [('outer',1.829),('middle',1.219),('inner',.610)]),
            {'id':'centre_line','label':'Centre line (click visible segment)','kind':'x','value_m':0.},
            {'id':'tee_line','label':'Tee line (click visible segment)','kind':'y','value_m':0.},
            {'id':'hog_line','label':'House-facing hog edge (click visible segment)','kind':'y','value_m':sign*6.401},
            {'id':'wheelchair_left','label':'Camera-left wheelchair line outer edge','kind':'x','value_m':-.457},
            {'id':'wheelchair_right','label':'Camera-right wheelchair line outer edge','kind':'x','value_m':.457}]


def _point(row, panel):
    choices = {r['id']: r for r in landmarks(panel)}
    if row.get('landmark_id') not in choices:
        raise ValueError('Choose a known rink landmark')
    pixel = np.asarray(row.get('pixel_normalized'), float)
    if pixel.shape != (2,) or not np.isfinite(pixel).all() or not (0 <= pixel).all() or not (pixel <= 1).all():
        raise ValueError('Landmark pixels must be normalized source-image coordinates')
    if (pixel[0] < .5) != (panel == 'left'):
        raise ValueError('Landmark is in the other camera panel')
    return pixel * CANONICAL_SIZE, choices[row['landmark_id']]['xy_m']


def _vanishing_point(lines, panel):
    if not lines:
        return None
    if len(lines) != 2:
        raise ValueError('Mark exactly two different longitudinal rink lines, two endpoints each')
    ls = []
    for segment in lines:
        a = np.asarray(segment, float)
        if a.shape != (2, 2) or not np.isfinite(a).all() or (a < 0).any() or (a > 1).any():
            raise ValueError('Invalid longitudinal line endpoints')
        if np.any((a[:, 0] < .5) != (panel == 'left')):
            raise ValueError('Longitudinal lines must remain inside their camera panel')
        a = a * CANONICAL_SIZE
        if np.linalg.norm(a[1] - a[0]) < 100:
            raise ValueError('Use longer visible segments of the longitudinal rink lines (at least 100 pixels at 1080p)')
        line = np.cross([*a[0], 1.], [*a[1], 1.])
        ls.append(line / np.linalg.norm(line[:2]))
    vp = np.cross(*ls)
    if np.linalg.norm(vp) < 1e-8:
        raise ValueError('The two marked lines are coincident')
    return vp / np.linalg.norm(vp)


def _guide_errors(H, guide_x, guides):
    errors=[]
    for x, line in zip(guide_x, guides):
        q=project(H,line)
        dx=project(H,line+[.5,0])[:,0]-project(H,line-[.5,0])[:,0]
        dy=project(H,line+[0,.5])[:,0]-project(H,line-[0,.5])[:,0]
        errors.extend((q[:,0]-x)/np.maximum(np.hypot(dx,dy),1e-9))
    return np.asarray(errors)


def _fit(ice, pixels, vp, lines=()):
    # Human correspondences must all be accounted for, rather than silently
    # discarding mislabeled points through a robust estimator.
    H, _ = cv2.findHomography(ice.astype(float), pixels.astype(float), method=0)
    if H is None or not np.isfinite(H).all() or abs(np.linalg.det(H)) < 1e-10:
        raise ValueError('Calibration landmarks are degenerate')
    if vp is not None:
        # Clicked guide endpoints have finite image precision. Their extrapolated
        # intersection must not be an exact camera constraint. Fit the same
        # pixel-normal guide residual used by the curve-marking mode instead.
        guides=[np.asarray(line,float)*CANONICAL_SIZE for line in lines]
        H/=H[2,2]
        inverse=np.linalg.inv(H)
        initial=np.r_[H.ravel()[:8],[np.mean(project(inverse,line)[:,0]) for line in guides]]
        def matrix(p):
            return np.r_[p[:8],1.].reshape(3,3)
        def residual(p):
            try:
                G=matrix(p)
                return np.r_[(project(G,ice)-pixels).ravel(),_guide_errors(np.linalg.inv(G),p[8:],guides)]
            except (ValueError,np.linalg.LinAlgError):
                return np.full(2*len(ice)+2*len(guides),1e8)
        opt = least_squares(residual, initial, x_scale='jac', max_nfev=500)
        if not opt.success:
            raise ValueError('Constrained calibration did not converge')
        H = matrix(opt.x)
    return np.linalg.inv(H)


def fit_panel(spec, panel):
    fit, checks = spec.get('fit_points', []), spec.get('check_points', [])
    if any('feature_id' in r for r in fit+checks):
        result = fit_markings_panel(spec, panel)
        result['evidence_sha256'] = evidence_digest(result)
        return result
    if len(fit) < POLICY['minimum_fit_points'] or len(checks) < POLICY['minimum_check_points']:
        raise ValueError('Each camera needs at least six fit landmarks and three separate check landmarks')
    names = [r.get('landmark_id') for r in fit + checks]
    if len(names) != len(set(names)):
        raise ValueError('Fit and check landmarks must be different; duplicate labels are not independent checks')
    pairs = [_point(r, panel) for r in fit + checks]
    pixels = np.array([p[0] for p in pairs]); ice = np.array([p[1] for p in pairs])
    if len(np.unique(pixels.round(4), axis=0)) != len(pixels):
        raise ValueError('Different landmarks cannot use the same source pixel')
    n = len(fit)
    if not any(r['landmark_id'].startswith('hog_') for r in fit):
        raise ValueError('Include a house-facing hog-edge landmark in the fit')
    if not any(r['landmark_id'].startswith('hog_') for r in checks):
        raise ValueError('Include a different hog-edge landmark among the withheld checks')
    if np.linalg.matrix_rank(np.c_[ice[:n], np.ones(n)]) < 3 or np.linalg.matrix_rank(np.c_[ice[n:], np.ones(len(checks))]) < 3:
        raise ValueError('Fit and check landmarks must each span both rink axes')
    vp = _vanishing_point(spec.get('parallel_lines', []), panel)
    H = _fit(ice[:n], pixels[:n], vp, spec.get('parallel_lines', []))
    inv = np.linalg.inv(H)
    origin, x_axis, y_axis = project(inv, [[0., 0.], [.1, 0.], [0., .1]])
    if x_axis[0] <= origin[0] or y_axis[1] <= origin[1]:
        raise ValueError('Rink axes are reversed: +x is camera-right and +y is toward the foreground')
    projected_pixels = project(inv, ice)
    pixel_errors = np.linalg.norm(projected_pixels - pixels, axis=1)
    metric_errors = np.linalg.norm(project(H, pixels) - ice, axis=1)
    reasons = []
    guides=[np.asarray(line,float)*CANONICAL_SIZE for line in spec.get('parallel_lines',[])]
    guide_error=_guide_errors(H,[np.mean(project(H,line)[:,0]) for line in guides],guides)
    if len(guide_error) and max(abs(guide_error))>POLICY['maximum_fit_error_px_at_1080p']:
        reasons.append('Parallel guide lines disagree with fitted rink markings')
    if max(pixel_errors[:n]) > POLICY['maximum_fit_error_px_at_1080p']:
        reasons.append('Fit landmarks disagree with one mapping')
    if max(pixel_errors[n:]) > POLICY['maximum_check_error_px_at_1080p']:
        reasons.append('Withheld image landmarks fail the reprojection check')
    if max(metric_errors[n:]) > POLICY['maximum_check_error_m']:
        reasons.append('Withheld rink landmarks fail the metric check')
    hull = cv2.convexHull(pixels.astype('float32')).reshape(-1, 2)
    result = {
        'panel': panel, 'status': 'rejected' if reasons else 'checks_passed', 'reasons': reasons,
        'H_normalized_source_to_local_m': (H @ np.diag([3., 3., 1.])).tolist(),
        'fit_points': fit, 'check_points': checks, 'parallel_lines': spec.get('parallel_lines', []),
        'vanishing_point_canonical': vp.tolist() if vp is not None else None,
        'projection_scope': 'perspective_constrained' if vp is not None else 'landmark_hull_only',
        'image_hull_normalized': (hull / CANONICAL_SIZE).tolist(),
        'checks': [{'landmark_id': name, 'use': 'fit' if i < n else 'check',
                    'reprojection_error_px_at_1080p': float(pixel_errors[i]), 'local_error_m': float(metric_errors[i])}
                   for i, name in enumerate(names)],
        'maximum_check_error_m': float(max(metric_errors[n:])),
        'maximum_check_reprojection_px_at_1080p': float(max(pixel_errors[n:])),
        'absolute_accuracy_verified': False,
        'calibration_origin': 'Explicit operator-selected static rink markings; not learned predictions',
        'landmark_convention': 'Nominal outer ring radii and house-facing hog edge. Local origin tee, +x camera-right, +y foreground.',
        'policy': POLICY,
        'parallel_guide_max_residual_px_at_1080p':float(max(abs(guide_error))) if len(guide_error) else None,
        'parallel_guide_semantics':'Operator line clicks fitted in pixel space with unknown lateral positions; no exact vanishing-point constraint.',
    }
    # Overlay all nominal rings/axes/hog. Visibility is left to the source frame;
    # drawing an overlay is a review aid, never additional calibration evidence.
    lines = []
    sign = -1 if panel == 'left' else 1
    for radius in [1.829, 1.219, .610]:
        angles = np.linspace(0, 2 * math.pi, 181)
        world = radius * np.c_[np.cos(angles), np.sin(angles)]
        lines.append((project(inv, world) / CANONICAL_SIZE).tolist())
    for a, b in [([-2., 0.], [2., 0.]), ([0., -2.], [0., sign * 8.]),
                 ([-2., sign * 6.401], [2., sign * 6.401])]:
        lines.append((project(inv, [a, b]) / CANONICAL_SIZE).tolist())
    result['overlay_lines_normalized'] = _overlay(H,panel)
    result['evidence_sha256'] = evidence_digest(result)
    return result


def validate_interval(assets, interval, source_sha256):
    start, end = map(float, interval)
    if not math.isfinite(start + end) or start < 0 or start >= end:
        raise ValueError('Invalid calibration coverage interval')
    spans = []
    for asset in assets:
        if asset.get('schema_version') != SCHEMA or asset.get('source_sha256') != source_sha256:
            raise ValueError('Calibration belongs to another recording or schema')
        if asset.get('status') != 'confirmed' or set(asset.get('panels', {})) != {'left', 'right'}:
            raise ValueError('Both camera calibrations must be checked and confirmed')
        if any(p.get('status') != 'checks_passed' for p in asset['panels'].values()):
            raise ValueError('Rejected calibration cannot be used for analysis')
        a, b = map(float, asset['valid_interval_s'])
        if not math.isfinite(a + b) or a < 0 or a >= b:
            raise ValueError('Invalid saved calibration interval')
        if a < end and b > start:
            spans.append((max(a, start), min(b, end)))
    cursor = start
    for a, b in sorted(spans):
        if a > cursor + 1e-8:
            raise ValueError(f'Calibration required at source time {cursor:.3f} s')
        if a < cursor - 1e-8:
            raise ValueError('Selected calibrations overlap: choose one mapping for each camera pose interval')
        cursor = b
    if cursor < end - 1e-8:
        raise ValueError(f'Calibration required at source time {cursor:.3f} s')
    return True


def load_bundle(path, source_sha256=None, interval=None):
    path = Path(path)
    bundle = json.loads(path.read_text())
    if bundle.get('schema_version') != 'source-calibration-bundle-v1':
        raise ValueError('Unsupported explicit calibration bundle')
    source_sha256 = source_sha256 or bundle['source_sha256']
    if source_sha256 != bundle['source_sha256']:
        raise ValueError('Calibration belongs to another source')
    validate_interval(bundle['calibrations'], interval or bundle['source_interval_s'], source_sha256)
    for asset in bundle['calibrations']:
        for name, panel in asset['panels'].items():
            # The confirmed mapping is authoritative. Re-running a nonlinear
            # optimizer here changes the experiment and can drift across SciPy
            # builds. Verify its sealed evidence; never recalibrate at load time.
            verify_sealed_panel(panel)
            frame = panel['frame']
            image = (path.parent / frame['image_path']).resolve()
            if not image.is_relative_to(path.parent.resolve()) or digest(image) != frame['image_sha256']:
                raise ValueError('Calibration anchor image is missing, changed, or outside the bundle')
    return bundle


def _overlay(H, panel):
    inv=np.linalg.inv(H);lines=[];sign=-1 if panel=='left' else 1
    for radius in [1.829,1.219,.610]:
        angles=np.linspace(0,2*math.pi,181)
        lines.append((project(inv,radius*np.c_[np.cos(angles),np.sin(angles)])/CANONICAL_SIZE).tolist())
    x0,x1=(0.,960.) if panel=='left' else (960.,1920.)
    for world_line in [[1.,0.,0.],[0.,1.,0.],[0.,1.,-sign*6.401]]:
        a,b,c=H.T@world_line;points=[]
        if abs(b)>1e-12:
            for x in [x0,x1]:
                y=-(a*x+c)/b
                if 0<=y<=1080:points.append([x,y])
        if abs(a)>1e-12:
            for y in [0.,1080.]:
                x=-(b*y+c)/a
                if x0<=x<=x1:points.append([x,y])
        if len(points)>=2:
            pair=max(((p,q) for p in points for q in points),key=lambda pair:np.linalg.norm(np.array(pair[0])-pair[1]))
            lines.append((np.array(pair)/CANONICAL_SIZE).tolist())
    return lines


def fit_markings_panel(spec, panel):
    """Fit manually classified static curves/lines using upstream optimization.

    This removes the need to invent an occluded tee or assign an arbitrary angle
    to a visible ring arc. Checks measure distance to a marking, not a known 2D
    stone position. They are never included in the optimization.
    """
    fit,checks=spec.get('fit_points',[]),spec.get('check_points',[])
    catalog={m['id']:m for m in marking_types(panel)}
    observations=[];seen=set();names=set()
    for row in fit+checks:
        if 'feature_id' in row:
            feature=catalog.get(row['feature_id'])
            if feature is None:raise ValueError('Unknown static rink marking')
            pixel=np.asarray(row.get('pixel_normalized'),float)
            if pixel.shape!=(2,) or not np.isfinite(pixel).all() or (pixel<0).any() or (pixel>1).any() or ((pixel[0]<.5)!=(panel=='left')):
                raise ValueError('Marking point must be inside its source camera panel')
            point=(pixel*CANONICAL_SIZE,None,feature)
        else:
            px,world=_point(row,panel);point=(px,np.array(world),None)
            if row['landmark_id'] in names:raise ValueError('Fit/check landmark labels must be different')
            names.add(row['landmark_id'])
        key=tuple(np.round(point[0],4))
        if key in seen:raise ValueError('Fit and check points must use different source pixels')
        seen.add(key);observations.append(point)
    constraints=sum(2 if w is not None else 1 for _,w,_ in observations[:len(fit)])
    if constraints<POLICY['minimum_trace_fit_constraints'] or len(checks)<POLICY['minimum_trace_check_points']:
        raise ValueError('Markings mode needs at least 12 fit constraints and six separate check points')
    def includes_hog(rows):
        return any(r.get('feature_id')=='hog_line' or str(r.get('landmark_id','')).startswith('hog_') for r in rows)
    if not includes_hog(fit) or not includes_hog(checks):
        raise ValueError('Mark the house-facing hog edge in both fit and check sets, using different source pixels')
    kinds={r.get('feature_id') for r in fit}
    if not ({'centre_line','tee_line','wheelchair_left','wheelchair_right'} & kinds) and not any('landmark_id' in r for r in fit) and len(kinds & {'outer_ring','middle_ring','inner_ring'})<2 and len(spec.get('parallel_lines',[]))!=2:
        raise ValueError('Use two different ring radii, a visible axis line, two lengthwise guides, or known intersections to establish the rink origin')
    pixels=np.array([p[0] for p in observations]);n=len(fit)
    for points in [pixels[:n],pixels[n:]]:
        if np.linalg.matrix_rank(np.c_[points,np.ones(len(points))])<3:
            raise ValueError('Fit and check markings must each span a 2D image region')
    vp=_vanishing_point(spec.get('parallel_lines',[]),panel)
    if vp is not None:
        fit_axis=[r for r in fit if r.get('feature_id')=='centre_line']
        check_axis=[r for r in checks if r.get('feature_id')=='centre_line']
        if not fit_axis or len(check_axis)<2:
            raise ValueError('Long-range curve calibration requires centre-line fit points and at least two separate centre-line checks; ring arcs and unlabelled parallel guides alone are insufficient')
    exact=[p for p in observations[:n] if p[1] is not None]
    if len(exact)>=4 and np.linalg.matrix_rank(np.c_[[p[1] for p in exact],np.ones(len(exact))])==3:
        G,_=cv2.findHomography(np.array([p[1] for p in exact]),np.array([p[0] for p in exact]),0)
        initial=np.linalg.inv(G)
    else:
        # Ellipse only seeds the optimization. No ellipse centre is declared to
        # be the tee, and no automatically detected paint or stone is admitted.
        groups=[(m,[p[0] for p in observations[:n] if p[2] is not None and p[2]['id']==m['id']])
                for m in catalog.values() if m['kind']=='ring']
        supported=[g for g in groups if len(g[1])>=5]
        if not supported:raise ValueError('Mark at least five visible edge points on one fit ring to initialize the plane')
        feature,points=max(supported,key=lambda g:g[0]['value_m'])
        centre,axes,angle=cv2.fitEllipse(np.asarray(points,np.float32))
        if min(axes)<=1 or max(axes)>4000:raise ValueError('Marked ring arc does not identify a usable ellipse')
        theta=np.deg2rad(angle);R=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
        S=R@np.diag(2*feature['value_m']/np.array(axes))@R.T
        initial=np.eye(3);initial[:2,:2]=S;initial[:2,2]=-S@centre
    if vp is not None:
        v=initial@vp
        if abs(v[1])<1e-10:raise ValueError('Longitudinal direction is unidentifiable')
        C=np.array([[1.,-v[0]/v[1],0.],[0.,1.,0.],[0.,-v[2]/v[1],1.]])
        initial=C@initial
    G=np.linalg.inv(initial);G/=G[2,2]
    # Guide clicks have finite pixel precision. Fit their normal errors jointly,
    # rather than treating an intersection extrapolated hundreds of pixels away
    # as an exact vanishing point. Unknown guide x positions are nuisance values;
    # no rink width or camera pose is invented.
    guides=[np.asarray(line,float)*CANONICAL_SIZE for line in spec.get('parallel_lines',[])]
    guide_x=[float(np.mean(project(initial,line)[:,0])) for line in guides]
    params=np.r_[G.ravel()[:8],guide_x]
    def matrix(p):return np.r_[p[:8],1.].reshape(3,3)
    def guide_errors(H,p):
        return _guide_errors(H,p[8:],guides)
    def errors(H, obs):
        pixel_errors=[];metric_errors=[]
        for px,world,feature in obs:
            if world is not None:
                pe=project(np.linalg.inv(H),[world])[0]-px
                me=float(np.linalg.norm(project(H,[px])[0]-world))
                pixel_errors.extend(pe);metric_errors.append(me)
            else:
                q=project(H,[px,px+[.5,0],px-[.5,0],px+[0,.5],px-[0,.5]])
                if feature['kind']=='ring':
                    values=np.linalg.norm(q,axis=1)-feature['value_m']
                else:
                    values=q[:,0 if feature['kind']=='x' else 1]-feature['value_m']
                scale=np.linalg.norm([values[1]-values[2],values[3]-values[4]])
                pixel_errors.append(values[0]/max(scale,1e-9));metric_errors.append(abs(float(values[0])))
        return np.asarray(pixel_errors),metric_errors
    def residual(p):
        try:
            H=np.linalg.inv(matrix(p))
            return np.r_[errors(H,observations[:n])[0],guide_errors(H,p)]
        except (ValueError,np.linalg.LinAlgError):return np.full(constraints+2*len(guides),1e8)
    opt=least_squares(residual,params,x_scale='jac',max_nfev=500)
    if not opt.success:raise ValueError('Static-marking calibration did not converge')
    H=np.linalg.inv(matrix(opt.x))
    origin,x_axis,y_axis=project(np.linalg.inv(H),[[0.,0.],[.1,0.],[0.,.1]])
    if x_axis[0]<=origin[0] or y_axis[1]<=origin[1]:raise ValueError('Rink axes are reversed; inspect the selected markings')
    fit_px,fit_m=errors(H,observations[:n]);check_px,check_m=errors(H,observations[n:])
    reasons=[]
    rank=int(np.linalg.matrix_rank(opt.jac))
    if rank<len(params):reasons.append('Static markings do not identify all camera-plane parameters')
    guide_px=guide_errors(H,opt.x)
    if len(guide_px) and max(abs(guide_px))>POLICY['maximum_fit_error_px_at_1080p']:reasons.append('Parallel guide lines disagree with fitted rink markings')
    if max(abs(fit_px))>POLICY['maximum_fit_error_px_at_1080p']:reasons.append('Fit markings disagree with one mapping')
    if max(abs(check_px))>POLICY['maximum_check_error_px_at_1080p']:reasons.append('Withheld markings fail the image reprojection check')
    if max(check_m)>POLICY['maximum_check_error_m']:reasons.append('Withheld markings fail the metric residual check')
    rows=[]
    for row,obs in zip(fit+checks,observations):
        pe,me=errors(H,[obs])
        rows.append({'landmark_id':row.get('landmark_id',row.get('feature_id')),
                     'use':'fit' if len(rows)<n else 'check','reprojection_error_px_at_1080p':float(np.linalg.norm(pe)),
                     'local_error_m':me[0], 'metric_error_kind':'point_distance' if obs[1] is not None else 'distance_to_marking'})
    bounded_pixels=np.array([px for px,world,feature in observations if world is not None or feature['kind']!='x'])
    hull=cv2.convexHull(bounded_pixels.astype('float32')).reshape(-1,2)
    return {'panel':panel,'status':'rejected' if reasons else 'checks_passed','reasons':reasons,
            'H_normalized_source_to_local_m':(H@np.diag([3.,3.,1.])).tolist(),
            'fit_points':fit,'check_points':checks,'parallel_lines':spec.get('parallel_lines',[]),
            'vanishing_point_canonical':vp.tolist() if vp is not None else None,
            'projection_scope':'perspective_constrained' if vp is not None else 'landmark_hull_only',
            'image_hull_normalized':(hull/CANONICAL_SIZE).tolist(),'checks':rows,
            'maximum_check_error_m':float(max(check_m)),
            'maximum_check_reprojection_px_at_1080p':float(max(abs(check_px))),
            'absolute_accuracy_verified':False,'calibration_origin':'Explicit operator-classified static rink curves/lines; not learned predictions',
            'landmark_convention':'Nominal outer ring radii and house-facing hog edge. Tee origin, +x camera-right, +y foreground.',
            'policy':POLICY,'overlay_lines_normalized':_overlay(H,panel),
            'optimizer_evaluations':opt.nfev,'fit_rank':rank,'free_parameters':len(params),
            'parallel_guide_max_residual_px_at_1080p':float(max(abs(guide_px))) if len(guide_px) else None,
            'parallel_guide_semantics':'Operator line clicks are fitted in pixel space with unknown lateral line positions; observed VP is an initializer, not exact truth.'}
