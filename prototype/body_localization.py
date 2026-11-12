"""Geometry-conditioned stone-body proposals and conditional height-aware localization.

This is a classical vision baseline, not a trained neural network. Inference never reads
benchmark stone labels or diagram positions. Camera intrinsics/stone heights are explicit
assumptions, not measured parameters; output positions remain provisional.
"""
from __future__ import annotations
import cv2
import numpy as np
from vision_core import project, detect_caps

VERSION = 'body-geometry-v1'
STONE_RADIUS_M = .139
CAP_PLANE_HEIGHT_M = .136
BODY_CENTRE_HEIGHT_M = .068


def feature_heights(values=None):
    """Resolve physical feature-height assumptions in metres, independent of video."""
    defaults = {'cap_with_body_support': CAP_PLANE_HEIGHT_M,
                'body_box_center': BODY_CENTRE_HEIGHT_M}
    if values is None:
        return defaults
    if not isinstance(values, dict) or set(values) - set(defaults):
        raise ValueError('Unknown projection height setting')
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
            raise ValueError('Feature heights must be finite nonnegative metres')
        defaults[key] = float(value)
    return defaults


def local_shape(H, pixel):
    """Expected plane foreshortening from the local metric-to-image Jacobian."""
    world=project(H,[pixel])[0];inv=np.linalg.inv(H)
    pts=project(inv,[world,world+[.01,0],world+[0,.01]])
    J=np.column_stack([(pts[1]-pts[0])/.01,(pts[2]-pts[0])/.01])
    sv=np.linalg.svd(J,compute_uv=False)
    return float(sv[-1]/sv[0]),float(np.linalg.norm(J[:,0])*STONE_RADIUS_M)


def conditional_camera(H,region,aspect=1.,principal_shift=(0.,0.)):
    """Infer a pinhole model conditional on zero skew and specified pixel aspect/centre.

    Two orthonormal-plane constraints estimate squared focal length. Near frontoparallel
    views may be unidentifiable; return None instead of inventing a focal length.
    The measured plane homography is retained exactly; residual orthogonality is reported.
    """
    x0,y0,x1,y1=region;cx=(x0+x1)/2+principal_shift[0]*(x1-x0);cy=(y0+y1)/2+principal_shift[1]*(y1-y0)
    M=np.linalg.inv(H);M/=M[2,2]
    u=M[:,0].copy();v=M[:,1].copy();u[:2]-=[cx*u[2],cy*u[2]];v[:2]-=[cx*v[2],cy*v[2]]
    # fx = aspect * fy.
    a=np.array([u[0]*v[0]/aspect**2+u[1]*v[1],(u[0]**2-v[0]**2)/aspect**2+u[1]**2-v[1]**2])
    b=np.array([u[2]*v[2],u[2]**2-v[2]**2])
    if float(b@b)<1e-12:return None,{'status':'unidentifiable','reason':'Near-affine plane does not identify focal length'}
    f2=float(-a@b/(b@b))
    if not np.isfinite(f2) or f2<=0:return None,{'status':'inconsistent','reason':'No positive focal-length solution under assumed intrinsics'}
    focal=np.sqrt(f2);K=np.array([[aspect*focal,0,cx],[0,focal,cy],[0,0,1.]])
    B=np.linalg.inv(K)@M;scale=2/(np.linalg.norm(B[:,0])+np.linalg.norm(B[:,1]));r1=B[:,0]*scale;r2=B[:,1]*scale
    dot=abs(float(r1@r2));norm_error=abs(float(np.linalg.norm(r1)-np.linalg.norm(r2)))
    # Image-right/image-down plane coordinates use the opposite normal for above-ice height.
    up=-np.cross(r1,r2);up/=np.linalg.norm(up)
    camera=-np.linalg.inv(np.column_stack([r1,r2,up]))@(B[:,2]*scale)
    if not np.isfinite(camera).all() or camera[2]<=0:return None,{'status':'inconsistent','reason':'Camera is nonfinite or not above the ice plane'}
    vertical=K@up/scale
    return {'plane':M,'vertical':vertical}, {'status':'conditional','focal_y_px':float(focal),'principal_point_px':[cx,cy],
          'assumed_pixel_aspect':aspect,'camera_centre_m':camera.tolist(),'orthogonality_residual':dot,'axis_norm_difference':norm_error,
          'quality_rejection_applied':False,'physical_accuracy_validated':False,
          'assumptions':'Zero skew, principal point at panel centre, square pixels by default, no lens distortion. Not an independently calibrated 3D camera.'}


def height_correct(camera,pixel,height):
    M=camera['plane'].copy();M[:,2]+=height*camera['vertical']
    return project(np.linalg.inv(M),[pixel])[0]


def transported_reference_camera(reference_H,current_H,region):
    """Transport a fixed-camera prior with the accepted reference-to-current image map.

    This assumes camera changes act as an image homography (e.g. registration/zoom),
    not an unmodelled 3D camera translation. Re-estimating focal length on every noisy
    frame is avoided. Reference intrinsics remain assumptions.
    """
    camera,diagnostic=conditional_camera(reference_H,region)
    if camera is None:return None
    A=np.linalg.inv(current_H)@reference_H
    def transport(c):return {'plane':A@c['plane'],'vertical':A@c['vertical']}
    alternatives=[]
    for aspect,shift in [(a,(0.,0.)) for a in [.9,1.1]]+[(1.,s) for s in [(-.05,0),(.05,0),(0,-.05),(0,.05)]]:
        alt,_=conditional_camera(reference_H,region,aspect=aspect,principal_shift=shift)
        if alt is not None:alternatives.append(transport(alt))
    diagnostic=dict(diagnostic,temporal_model='Reference camera transported through accepted image registration; physical camera translation is not modelled.')
    return {'camera':transport(camera),'diagnostic':diagnostic,'alternatives':alternatives}


def localize(H,pixel,region,kind,camera_prior=None, *, heights_m=None):
    ratio,_=local_shape(H,pixel);raw=project(H,[pixel])[0]
    height=feature_heights(heights_m)['cap_with_body_support' if kind=='cap_with_body_support' else 'body_box_center']
    camera,diagnostic=(camera_prior['camera'],camera_prior['diagnostic']) if camera_prior is not None else conditional_camera(H,region)
    if camera is not None:
        xy=height_correct(camera,pixel,height);alternatives=[]
        for h in [height-.02,height+.02]:alternatives.append(height_correct(camera,pixel,h))
        if camera_prior is not None:
            alternatives.extend(height_correct(c,pixel,height) for c in camera_prior['alternatives'])
        else:
            for aspect in [.9,1.1]:
                c,_=conditional_camera(H,region,aspect=aspect)
                if c is not None:alternatives.append(height_correct(c,pixel,height))
            for shift in [(-.05,0),(.05,0),(0,-.05),(0,.05)]:
                c,_=conditional_camera(H,region,principal_shift=shift)
                if c is not None:alternatives.append(height_correct(c,pixel,height))
        sensitivity=max(float(np.linalg.norm(p-xy)) for p in alternatives)
        return xy,{'status':'conditional_height_corrected','height_m':height,'uncorrected_position_m':raw.tolist(),
                   'height_intrinsics_sensitivity_m':sensitivity,'sensitivity_note':camera_prior.get('uncertainty_scope','One-at-a-time ±2 cm feature height, ±10% pixel aspect, ±5% panel principal-point shifts. Not a confidence interval or total error bound.') if camera_prior is not None else 'One-at-a-time ±2 cm feature height, ±10% pixel aspect, ±5% panel principal-point shifts. Not a confidence interval or total error bound.', 'camera':diagnostic}
    if ratio>=.75 and kind=='body_outline':
        # With a high viewing angle, retain the body-centre projection while declaring height bias.
        sensitivity=height*np.sqrt(max(0.,1/ratio**2-1))
        return raw,{'status':'near_overhead_body_approximation','height_m':height,'uncorrected_position_m':raw.tolist(),
                    'height_intrinsics_sensitivity_m':float(sensitivity),'sensitivity_note':'Weak-perspective height-bias scale from local foreshortening. Not a confidence interval or full uncertainty.','camera':diagnostic}
    return None,{'status':'unavailable','reason':'Low-angle footprint cannot be supported by the conditional camera model','camera':diagnostic}


def body_proposals(image,H,view):
    """Find original-image circular body outlines, then verify local scale, rim and colour."""
    region=view['region'];x0,y0,x1,y1=region;crop=image[y0:y1,x0:x1]
    gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY);hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    centre=project(np.linalg.inv(H),[[0,0]])[0];_,radius=local_shape(H,centre)
    circles=cv2.HoughCircles(cv2.GaussianBlur(gray,(5,5),1.),cv2.HOUGH_GRADIENT_ALT,1.5,max(8,radius*.75),
              param1=150,param2=.80,minRadius=max(5,int(radius*.45)),maxRadius=max(8,int(radius*1.8)))
    candidates=[];rejected=[]
    for cx,cy,r in ([] if circles is None else circles[0]):
        cx=float(cx+x0);cy=float(cy+y0);r=float(r);xy=project(H,[[cx,cy]])[0]
        bx0,by0,bx1,by1=view['world_bounds']
        if not (bx0<=xy[0]<=bx1 and by0<=xy[1]<=by1):continue
        ratio,expected=local_shape(H,[cx,cy])
        if ratio<.65 or not .65<r/expected<1.2:continue
        xx,yy=np.meshgrid(np.arange(max(x0,int(cx-r*1.3)),min(x1,int(cx+r*1.3)+1)),np.arange(max(y0,int(cy-r*1.3)),min(y1,int(cy+r*1.3)+1)))
        dist=np.sqrt((xx-cx)**2+(yy-cy)**2)/r;values=hsv[yy,xx];inside=dist<.7;rim=(dist>.72)&(dist<1.08)
        if not inside.any() or not rim.any():continue
        red=((values[:,:,0]<12)|(values[:,:,0]>170))&(values[:,:,1]>80)
        yellow=(values[:,:,0]>16)&(values[:,:,0]<43)&(values[:,:,1]>80)
        rc=float(np.mean(red[inside]));yc=float(np.mean(yellow[inside]));body=float(np.mean(((values[:,:,1]<100)&(values[:,:,2]>30)&(values[:,:,2]<210))[rim]))
        record={'colour':'red' if rc>yc else 'yellow','pixel_center':[cx,cy],'bbox':[round(cx-r),round(cy-r),round(2*r),round(2*r)],
                'proposal_kind':'body_outline','radius_px':r,'rim_support':body,'colour_support':max(rc,yc),'expected_radius_px':expected,'plane_axis_ratio':ratio}
        if max(rc,yc)<=.18 or body<=.20:record['reason']='Insufficient coloured interior or neutral stone rim';rejected.append(record);continue
        record['support_score']=body+max(rc,yc);candidates.append(record)
    # Hough may return both an inner and an outer ring for the same stone. Keep one body.
    kept=[]
    for p in sorted(candidates,key=lambda p:p['support_score'],reverse=True):
        if any(np.linalg.norm(np.array(p['pixel_center'])-q['pixel_center'])<.65*max(p['radius_px'],q['radius_px']) for q in kept):continue
        kept.append(p)
    return kept,rejected


def detect_and_localize(image,H,view,registered_reference=None,camera_prior=None):
    if H is None:return [],{'status':'unavailable','reason':'No accepted ice calibration'}
    try:
        centre=project(np.linalg.inv(H),[[0,0]])[0];ratio,_=local_shape(H,centre)
    except (ValueError,np.linalg.LinAlgError):return [],{'status':'unavailable','reason':'Invalid ice projection'}
    if ratio>=.65:
        proposals,rejected=body_proposals(image,H,view);branch='body_outline'
    else:
        proposals,detail=detect_caps(image,H,view,registered_reference);rejected=detail['rejected'];branch='cap_with_body_support'
        for p in proposals:p['proposal_kind']=branch
    for i,p in enumerate(proposals):
        xy,details=localize(H,p['pixel_center'],view['region'],p['proposal_kind'],camera_prior)
        p.update(id=f"{p['colour']}-{i+1}",ground_position_m=xy.tolist() if xy is not None else None,localization=details,
                 position_semantics='Provisional ground centre under explicit geometry assumptions; not a validated game state.',confidence=None)
    return proposals,{'status':'proposals','version':VERSION,'branch':branch,'plane_axis_ratio_at_tee':ratio,'rejected':rejected}
