"""Fit one consistent pinhole camera to the operator's static rink markings.

Seven camera parameters (rotation, translation, focal length), plus unknown
lateral positions of guide lines. The principal point is explicitly assumed
at the panel centre, with square pixels, zero skew and no lens distortion.
Only static fit observations enter optimisation; check points remain withheld.
"""
import copy
import math
import cv2
import numpy as np
from scipy.optimize import least_squares

from prototype.rink_calibration import (CANONICAL_SIZE, POLICY, _point, _guide_errors,
                                       _overlay, marking_types, project, evidence_digest)


def refine_camera(record):
    panel=record['panel'];fit=record['fit_points'];checks=record['check_points']
    catalogue={r['id']:r for r in marking_types(panel)}
    def observation(row):
        if 'feature_id' in row:
            return np.asarray(row['pixel_normalized'])*CANONICAL_SIZE,None,catalogue[row['feature_id']]
        px,world=_point(row,panel)
        return px,np.asarray(world),None
    observations=[observation(r) for r in fit+checks];n=len(fit)
    guides=[np.asarray(line)*CANONICAL_SIZE for line in record['parallel_lines']]
    initial_H=np.asarray(record['H_normalized_source_to_local_m'])@np.diag([1/3.,1/3.,1.])
    G=np.linalg.inv(initial_H);G/=G[2,2]
    cx=480. if panel=='left' else 1440.;cy=540.
    def camera(p):
        focal=np.exp(p[6]);K=np.array([[focal,0,cx],[0,focal,cy],[0,0,1.]])
        R=cv2.Rodrigues(p[:3])[0]
        plane=K@np.column_stack([R[:,:2],p[3:6]])
        return plane,K,R
    def marking_errors(H,rows):
        pixels=[];metres=[]
        for px,world,feature in rows:
            if world is not None:
                pixels.extend(project(np.linalg.inv(H),[world])[0]-px)
                metres.append(float(np.linalg.norm(project(H,[px])[0]-world)))
            else:
                q=project(H,[px,px+[.5,0],px-[.5,0],px+[0,.5],px-[0,.5]])
                values=(np.linalg.norm(q,axis=1)-feature['value_m'] if feature['kind']=='ring'
                        else q[:,0 if feature['kind']=='x' else 1]-feature['value_m'])
                pixels.append(values[0]/max(np.linalg.norm([values[1]-values[2],values[3]-values[4]]),1e-9))
                metres.append(abs(float(values[0])))
        return np.asarray(pixels),metres
    constraint_count=sum(2 if world is not None else 1 for _,world,_ in observations[:n])+2*len(guides)
    def residual(p):
        try:
            plane,_,_=camera(p);H=np.linalg.inv(plane)
            return np.r_[marking_errors(H,observations[:n])[0],_guide_errors(H,p[7:],guides)]
        except (ValueError,np.linalg.LinAlgError):return np.full(constraint_count,1e8)
    solutions=[]
    # Fixed, source-independent initialisations; select on fit pixels only.
    for focal in [1080.,2160.,4320.]:
        K=np.array([[focal,0,cx],[0,focal,cy],[0,0,1.]])
        B=np.linalg.inv(K)@G;scale=2/(np.linalg.norm(B[:,0])+np.linalg.norm(B[:,1]))
        first,second=B[:,0]*scale,B[:,1]*scale
        R=np.column_stack([first,second,np.cross(first,second)])
        U,_,V=np.linalg.svd(R);R=U@np.diag([1,1,np.linalg.det(U@V)])@V
        p=np.r_[cv2.Rodrigues(R)[0].ravel(),B[:,2]*scale,np.log(focal),
                [np.mean(project(initial_H,line)[:,0]) for line in guides]]
        lo=np.full(len(p),-np.inf);hi=np.full(len(p),np.inf)
        lo[6],hi[6]=math.log(1.),math.log(1e7)
        opt=least_squares(residual,p,x_scale='jac',bounds=(lo,hi),max_nfev=1000)
        if opt.success and np.isfinite(opt.fun).all():solutions.append(opt)
    if not solutions:raise ValueError('Physical camera calibration did not converge')
    opt=min(solutions,key=lambda r:r.fun@r.fun)
    plane,K,R=camera(opt.x);H=np.linalg.inv(plane)
    fit_px,fit_m=marking_errors(H,observations[:n]);check_px,check_m=marking_errors(H,observations[n:])
    guide_px=_guide_errors(H,opt.x[7:],guides)
    reasons=[]
    rank=int(np.linalg.matrix_rank(opt.jac))
    if rank<len(opt.x):reasons.append('Physical camera parameters are unidentifiable from these static markings')
    if max(abs(fit_px))>POLICY['maximum_fit_error_px_at_1080p']:reasons.append('Static fit markings fail the physical camera model')
    if max(abs(check_px))>POLICY['maximum_check_error_px_at_1080p']:reasons.append('Withheld markings fail the physical camera image check')
    if max(check_m)>POLICY['maximum_check_error_m']:reasons.append('Withheld markings fail the physical camera metric check')
    if len(guide_px) and max(abs(guide_px))>POLICY['maximum_fit_error_px_at_1080p']:reasons.append('Longitudinal guides fail the physical camera model')
    # The local X-right/Y-foreground convention has Z-up opposite R's third
    # column. Both the ground plane and the elevated stone model use this P.
    P=np.column_stack([plane[:,:2],-K@R[:,2],plane[:,2]])
    centre=-np.linalg.inv(P[:,:3])@P[:,3]
    if centre[2]<=0:reasons.append('Camera is not above the ice plane')
    depths=[float((plane@np.r_[world,1.])[2]) for _,world,_ in observations if world is not None]
    if depths and min(depths)<=0:reasons.append('Marked rink lies behind the fitted camera')
    normalise=np.diag([1/3.,1/3.,1.])
    result=copy.deepcopy(record)
    result.update(status='rejected' if reasons else 'checks_passed',reasons=reasons,
                  H_normalized_source_to_local_m=(H@np.diag([3.,3.,1.])).tolist(),
                  overlay_lines_normalized=_overlay(H,panel),
                  maximum_check_error_m=float(max(check_m)),
                  maximum_check_reprojection_px_at_1080p=float(max(abs(check_px))),
                  fit_rank=rank,free_parameters=len(opt.x),optimizer_evaluations=opt.nfev)
    result['checks']=[]
    for i,(row,obs) in enumerate(zip(fit+checks,observations)):
        pe,me=marking_errors(H,[obs])
        result['checks'].append({'landmark_id':row.get('landmark_id',row.get('feature_id')),
            'use':'fit' if i<n else 'check','reprojection_error_px_at_1080p':float(np.linalg.norm(pe)),
            'local_error_m':me[0],'metric_error_kind':'point_distance' if obs[1] is not None else 'distance_to_marking'})
    result['camera_model']={'type':'pinhole_fixed_panel_principal_square_pixels_v1',
        'projection_xyz_up_to_normalized_source':(normalise@P).tolist(),
        'focal_native_px':float(K[0,0]),'principal_point_native_px':[cx,cy],
        'camera_centre_m':centre.tolist(),'orthogonality_residual':float(abs(R[:,0]@R[:,1])),
        'assumptions':'Panel-centred principal point, square source pixels, zero skew, no lens distortion; fixed physical stone feature heights are separate inputs.',
        'fit_uses':'Operator static rink fit observations only; no trajectory, stone correspondence or withheld check enters optimisation.',
        'independent_physical_accuracy_verified':False}
    result['evidence_sha256']=evidence_digest(result)
    return result
