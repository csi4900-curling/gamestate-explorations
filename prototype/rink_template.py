"""One regulation-house template, positioned by an operator as a physical camera.

No generated marking is counted as an independent source measurement. This is
visual alignment, with structural camera checks and image-registration checks,
not a landmark residual or measured physical accuracy test.
"""
import math
import cv2
import numpy as np
from scipy.optimize import least_squares,minimize
from prototype.rink_calibration import POLICY, _overlay, evidence_digest, project

LIMITS={'camera_x_m':(-30.,30.),'distance_m':(2.,150.),'height_m':(.5,30.),
        'focal_px':(200.,50000.),'yaw_deg':(-45.,45.),'pitch_deg':(-45.,45.),'roll_deg':(-60.,60.)}


def _controls(parameters,panel):
    if panel not in ('left','right'):raise ValueError('Unknown camera panel')
    if set(parameters)!=set(LIMITS):raise ValueError('Supply the seven template camera controls')
    p={}
    for key,(lo,hi) in LIMITS.items():
        value=parameters[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not lo<=value<=hi:
            raise ValueError('Invalid template camera control: '+key)
        p[key]=float(value)
    return p


def _matrix(p,panel):
    C=np.array([p['camera_x_m'],p['distance_m'],p['height_m']])
    forward=-C/np.linalg.norm(C);right=np.array([C[1],-C[0],0.]);right/=np.linalg.norm(right)
    down=np.cross(right,forward);R=np.vstack([right,down,forward])
    # Proper camera-axis rotations preserve the fixed rink/vertical relationship.
    for axis,key in [(np.array([0.,1.,0.]),'yaw_deg'),(np.array([1.,0.,0.]),'pitch_deg'),(np.array([0.,0.,1.]),'roll_deg')]:
        R=cv2.Rodrigues(axis*math.radians(p[key]))[0]@R
    cx=480. if panel=='left' else 1440.
    K=np.array([[p['focal_px'],0,cx],[0,p['focal_px'],540.],[0,0,1.]])
    return K@np.column_stack([R,-R@C]),K,R,C


def template_panel(parameters,panel):
    p=_controls(parameters,panel)
    P,K,R,C=_matrix(p,panel);cx=K[0,2];plane=P[:,[0,1,3]]
    if abs(np.linalg.det(plane))<1e-8:raise ValueError('Template camera is degenerate')
    H=np.linalg.inv(plane)
    tee=project(plane,[[0.,0.]])[0]
    if not cx-480<=tee[0]<=cx+480 or not 0<=tee[1]<=1080:
        raise ValueError('Place the house centre inside this camera image')
    sign=-1 if panel=='left' else 1
    extent=np.array([[-1.829,-1.829],[1.829,-1.829],[-1.829,1.829],[1.829,1.829],[0.,sign*6.401]])
    if np.min(np.c_[extent,np.ones(len(extent))]@plane[2])<=0:
        raise ValueError('The visible house and hog line must be in front of the camera')
    result={'panel':panel,'status':'checks_passed','reasons':[],
        'calibration_origin':'Operator-positioned regulation rink template; visual alignment only',
        'calibration_method':'operator_template_alignment_v1','template_parameters':p,
        'template_dimensions_m':{'ring_radii':[1.829,1.219,.610],'tee_to_hog':6.401},
        'H_normalized_source_to_local_m':(H@np.diag([3.,3.,1.])).tolist(),
        'fit_points':[],'check_points':[],'parallel_lines':[],
        'projection_scope':'operator_template_alignment','image_hull_normalized':[],
        'checks':[],'maximum_check_error_m':None,'maximum_check_reprojection_px_at_1080p':None,
        'check_status':'operator_visual_alignment_only','absolute_accuracy_verified':False,
        'policy':{'version':POLICY['version'],'method':'operator_template_alignment_v1',
            'gate_status':'Finite physical camera and source-image registration support. Operator visual alignment only; no independent landmark residual or metric accuracy bound.',
            'extrapolation':'The physical template defines projection outside the house. Its accuracy there depends on the operator alignment; no independent extrapolation error bound is measured.'},
        'overlay_lines_normalized':_overlay(H,panel),
        'camera_model':{'type':'operator_positioned_pinhole_template_v1',
            'projection_xyz_up_to_normalized_source':(np.diag([1/3.,1/3.,1.])@P).tolist(),
            'focal_native_px':p['focal_px'],'principal_point_native_px':[cx,540.],
            'camera_centre_m':C.tolist(),'orthogonality_residual':float(abs(R[0]@R[1])),
            'assumptions':'Panel-centred principal point, square pixels, zero skew, no lens distortion. Camera pose and focal length chosen by the operator.',
            'fit_uses':'Operator placement of the connected rink template. No numerical landmark fit, generated check points, stone trajectory or camera-disagreement fitting.',
            'independent_physical_accuracy_verified':False}}
    result['evidence_sha256']=evidence_digest(result)
    return result


def edit_hog_handle(parameters,panel,target_native_px,maximum_house_drift_px,house_parameters=None):
    """Move the hog handle while protecting the visible, unparameterized rings.

    Points may slide along a ring. Protection uses symmetric distances to the
    original ellipse contours, not same-angle point correspondences. The input
    contours are operator template placements, never independent source labels.
    """
    p=_controls(parameters,panel);template_panel(p,panel)
    house=_controls(house_parameters if house_parameters is not None else parameters,panel)
    template_panel(house,panel)
    target=np.asarray(target_native_px,float)
    if target.shape!=(2,) or not np.isfinite(target).all():raise ValueError('Finite hog-handle target required')
    limit=float(maximum_house_drift_px)
    if not math.isfinite(limit) or not .1<=limit<=12:raise ValueError('Invalid house protection in image pixels')
    sign=-1 if panel=='left' else 1
    angles=np.linspace(0,2*math.pi,181,endpoint=False)
    radii=np.repeat([1.829,1.219,.610],len(angles))
    rings=np.vstack([r*np.c_[np.cos(angles),np.sin(angles)] for r in [1.829,1.219,.610]])
    world=np.vstack([rings,[[0.,0.],[0.,sign*6.401]]]);n=len(rings)
    keys=list(LIMITS);values=np.array([p[k] for k in keys]);scale=np.maximum(abs(values),1.)
    def matrix(x):return _matrix(dict(zip(keys,x*scale)),panel)[0][:,[0,1,3]]
    def predict(x):return project(matrix(x),world)
    initial=values/scale;reference_x=np.array([house[k] for k in keys])/scale
    reference=predict(reference_x);reference_H=np.linalg.inv(matrix(reference_x))
    def normal_errors(pixels,H):
        q=project(H,pixels);w=np.c_[pixels,np.ones(len(pixels))]@H[2]
        derivative=(H[:2,:2][None,:,:]-q[:,:,None]*H[2,:2][None,None,:])/w[:,None,None]
        radius=np.linalg.norm(q,axis=1)
        gradient=np.einsum('ni,nij->nj',q/np.maximum(radius[:,None],1e-12),derivative)
        return (radius-radii)/np.maximum(np.linalg.norm(gradient,axis=1),1e-12)
    def objective(x):
        b=predict(x)
        return float(np.sum((b[-1]-target)**2)+.0001*np.mean(normal_errors(b[:n],reference_H)**2))
    def constraints(x):
        b=predict(x);H=np.linalg.inv(matrix(x))
        return np.r_[limit**2-normal_errors(b[:n],reference_H)**2,
                     limit**2-normal_errors(reference[:n],H)**2,
                     .05**2-np.sum((b[-2]-reference[-2])**2)]
    # Exact closest-ellipse verification uses maintained OpenCV, independently
    # of the smooth normal-distance approximation used by the optimiser.
    dense_angles=np.linspace(0,2*math.pi,721,endpoint=False)
    dense_world=np.vstack([r*np.c_[np.cos(dense_angles),np.sin(dense_angles)] for r in [1.829,1.219,.610]])
    def contours(x):return np.array_split(project(matrix(x),dense_world),3)
    originals=contours(reference_x)
    original_ellipses=[cv2.fitEllipse(a.astype('float32')) for a in originals]
    def metrics(x):
        current=contours(x);maximum=0.
        for original,ellipse,points in zip(originals,original_ellipses,current):
            fitted=cv2.fitEllipse(points.astype('float32'))
            closest=cv2.getClosestEllipsePoints(ellipse,points.astype('float32')).reshape(-1,2)
            reverse=cv2.getClosestEllipsePoints(fitted,original.astype('float32')).reshape(-1,2)
            maximum=max(maximum,float(np.max(np.linalg.norm(points-closest,axis=1))),
                        float(np.max(np.linalg.norm(original-reverse,axis=1))))
        b=predict(x)
        return maximum,float(np.linalg.norm(b[-2]-reference[-2])),float(np.linalg.norm(b[-1]-target))
    initial_metrics=metrics(initial)
    if initial_metrics[0]>limit+.002 or initial_metrics[1]>.052:
        raise ValueError('The house changed since this lock; place the house again before adjusting the hog line')
    best=initial.copy();best_metrics=initial_metrics
    def retain_feasible(x):
        nonlocal best,best_metrics
        try:
            candidate=dict(zip(keys,map(float,x*scale)));template_panel(candidate,panel)
            measured=metrics(x)
            if measured[0]<=limit+.002 and measured[1]<=.052 and measured[2]<best_metrics[2]-1e-7:
                best=x.copy();best_metrics=measured
        except (ValueError,cv2.error,np.linalg.LinAlgError,FloatingPointError):pass
    limits=np.array([LIMITS[k] for k in keys])/scale[:,None]
    def warm_residual(x):
        b=predict(x)
        return np.r_[normal_errors(b[:n],reference_H),(b[-2]-reference[-2])*50,(b[-1]-target)*30]
    warm=least_squares(warm_residual,initial,bounds=limits.T,x_scale='jac',max_nfev=150)
    for fraction in [1.,.5,.25,.125,.0625]:retain_feasible(initial+fraction*(warm.x-initial))
    result=minimize(objective,warm.x,method='SLSQP',bounds=limits,
        constraints=[{'type':'ineq','fun':constraints}],callback=retain_feasible,
        options={'maxiter':150,'ftol':1e-7})
    retain_feasible(result.x)
    # A final infeasible trial must not discard earlier feasible progress.
    for fraction in [.5,.25,.125,.0625,.03125]:retain_feasible(initial+fraction*(result.x-initial))
    if best_metrics[2]>1.:
        fallback=minimize(objective,initial,method='SLSQP',bounds=limits,
            constraints=[{'type':'ineq','fun':constraints}],callback=retain_feasible,
            options={'maxiter':150,'ftol':1e-7})
        retain_feasible(fallback.x)
        for fraction in [.5,.25,.125,.0625,.03125]:retain_feasible(initial+fraction*(fallback.x-initial))
    movement=float(np.linalg.norm(predict(best)[-1]-predict(initial)[-1]))
    return {'parameters':dict(zip(keys,map(float,best*scale))),
            'pointer_error_px':best_metrics[2],'maximum_house_contour_error_px':best_metrics[0],
            'centre_drift_px':best_metrics[1],'house_contour_limit_px':limit,
            'house_protection_kind':'symmetric_distance_to_visible_ring_contours',
            'actual_hog_movement_px':movement,'target_reached':best_metrics[2]<=1.,
            'accepted':movement>1e-7,'optimizer_converged':bool(result.success),
            'scope':'Operator template editing constraints in image pixels; not independent physical accuracy.'}
