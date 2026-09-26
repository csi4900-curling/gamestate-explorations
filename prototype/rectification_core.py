"""Metric ice-plane rectification. Elevated objects are not reconstructed in 3-D."""
from __future__ import annotations
import cv2
import numpy as np
from scipy.optimize import least_squares
from vision_core import project, fit_calibration

RADII = (1.829, 1.219, .610)
HOUSE_BOUNDS = (-2.10, -2.10, 2.10, 2.10)
PIXELS_PER_METRE = 140

def canvas_transform(bounds=HOUSE_BOUNDS, pixels_per_metre=PIXELS_PER_METRE):
    x0,y0,x1,y1=bounds
    if pixels_per_metre<=0 or x1<=x0 or y1<=y0:
        raise ValueError('Invalid metric canvas')
    return np.array([[pixels_per_metre,0,-x0*pixels_per_metre],
                     [0,pixels_per_metre,-y0*pixels_per_metre],[0,0,1.]]), (round((x1-x0)*pixels_per_metre),round((y1-y0)*pixels_per_metre))

def rectify(image,H,region,bounds=HOUSE_BOUNDS,pixels_per_metre=PIXELS_PER_METRE):
    if H is None: raise ValueError('Cannot rectify without accepted calibration')
    C,size=canvas_transform(bounds,pixels_per_metre)
    mask=np.zeros(image.shape[:2],np.uint8);x0,y0,x1,y1=region;mask[y0:y1,x0:x1]=255
    masked=cv2.bitwise_and(image,image,mask=mask)
    out=cv2.warpPerspective(masked,C@H,size,flags=cv2.INTER_LINEAR,borderValue=(24,31,36))
    valid=cv2.warpPerspective(mask,C@H,size,flags=cv2.INTER_NEAREST)
    out[valid==0]=(24,31,36)
    return out,valid

def ring_edges(image,H,radius,region,angles=None,search_px=7.,min_contrast=10.):
    """Find colour-to-ice transitions near an initial projected ring, with subpixel peaks.

    Search normal to the projected ellipse (not along world radial rays). Angular
    coverage/contrast filtering reduces occlusion contamination; does not eliminate it.
    """
    if angles is None:angles=np.arange(0,360,3,dtype=float)+1.5
    angles=np.asarray(angles,float);a=np.deg2rad(angles)
    world=np.column_stack([radius*np.cos(a),radius*np.sin(a)])
    inv=np.linalg.inv(H);p=project(inv,world)
    tangent=project(inv,np.column_stack([radius*np.cos(a+.001),radius*np.sin(a+.001)]))-p
    normal=np.column_stack([tangent[:,1],-tangent[:,0]])
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-9)
    outward=project(inv,world*(1.01))-p
    normal*=np.where(np.sum(normal*outward,axis=1)<0,-1.,1.)[:,None]
    offsets=np.arange(-search_px,search_px+.125,.25)
    pixels=p[:,None,:]+normal[:,None,:]*offsets[None,:,None]
    hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV).astype(np.float32)
    sat=cv2.GaussianBlur(hsv[:,:,1],(3,3),.6)
    vals=cv2.remap(sat,pixels[:,:,0].astype('float32'),pixels[:,:,1].astype('float32'),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    brightness=cv2.remap(hsv[:,:,2],pixels[:,:,0].astype('float32'),pixels[:,:,1].astype('float32'),cv2.INTER_LINEAR)
    # 1.5-pixel samples on either side: outer/inner coloured-inside, middle coloured-outside.
    gap=6;sign=1 if abs(radius-RADII[1])<.01 else -1
    contrast=sign*(vals[:,2*gap:]-vals[:,:-2*gap])
    scores=contrast.copy();indices=np.argmax(scores,axis=1);results=[]
    x0,y0,x1,y1=region
    for i,j in enumerate(indices):
        k=j+gap
        if j==0 or j==scores.shape[1]-1 or scores[i,j]<min_contrast:continue
        if brightness[i,k]<85:continue
        left,right=scores[i,j-1],scores[i,j+1];centre=scores[i,j]
        denominator=left-2*centre+right
        delta=float(np.clip(.5*(left-right)/denominator,-.5,.5)) if abs(denominator)>1e-6 else 0.
        offset=float(offsets[k]+delta*.25);point=p[i]+normal[i]*offset
        if not (x0+3<point[0]<x1-3 and y0+3<point[1]<y1-3):continue
        # Convert radial metric error to pixel-normal error at this location.
        radial=np.linalg.norm(project(H,[point+normal[i],point-normal[i]]),axis=1)
        sensitivity=max(abs(float(radial[0]-radial[1]))/2,1e-5)
        results.append({'pixel':point.tolist(),'angle_deg':float(angles[i]),'radius_m':radius,
                        'contrast':float(centre),'offset_px':offset,'metres_per_normal_pixel':sensitivity})
    return results

def ring_summary(H,edges):
    if not edges:return {'count':0,'radial_rmse_m':None,'median_abs_radial_error_m':None,'p95_abs_radial_error_m':None,'angular_bins':0}
    p=project(H,[e['pixel'] for e in edges]);err=np.linalg.norm(p,axis=1)-[e['radius_m'] for e in edges]
    return {'count':len(edges),'radial_rmse_m':float(np.sqrt(np.mean(err**2))),
            'median_abs_radial_error_m':float(np.median(abs(err))),
            'p95_abs_radial_error_m':float(np.percentile(abs(err),95)),
            'angular_bins':len({int(e['angle_deg']//30) for e in edges})}

def refine_calibration(image,view):
    """Refine on outer+middle ring boundaries; inner ring never enters the objective."""
    initial,_=fit_calibration(view)
    edges=[e for r in RADII[:2] for e in ring_edges(image,initial,r,view['region'])]
    if len(edges)<70:raise ValueError('Too few ring boundary observations')
    # Hold out one quarter of angular samples from fitting; retain inner ring separately.
    train=[e for e in edges if int(e['angle_deg']//3)%4!=0]
    hold=[e for e in edges if int(e['angle_deg']//3)%4==0]
    # Normalize source pixels to stabilize the eight homography parameters.
    N=np.array([[1/1000.,0,-image.shape[1]/2000.],[0,1/1000.,-image.shape[0]/2000.],[0,0,1.]])
    norm=initial@np.linalg.inv(N);norm/=norm[2,2]
    pts=project(N,[e['pixel'] for e in train]);radii=np.array([e['radius_m'] for e in train]);scale=np.array([e['metres_per_normal_pixel'] for e in train])
    anchor_px=np.array([e['pixel'] for e in view['fit']],float);anchor_m=np.array([e['metres'] for e in view['fit']],float)
    def unpack(p):return np.r_[p,1.].reshape(3,3)
    def residual(p):
        H=unpack(p)@N
        ring=(np.linalg.norm(project(unpack(p),pts),axis=1)-radii)/scale
        # Original cardinal intersections anchor rotation and handedness. They are fit data.
        anchors=(project(np.linalg.inv(H),anchor_m)-anchor_px).ravel()/2.
        return np.r_[ring,anchors]
    opt=least_squares(residual,norm.ravel()[:8],loss='soft_l1',f_scale=1.,max_nfev=150,x_scale='jac')
    H=unpack(opt.x)@N;H/=H[2,2]
    if not opt.success or not np.isfinite(H).all():raise ValueError('Ring refinement did not converge')
    inner=ring_edges(image,initial,RADII[2],view['region'])
    # Same-image manually clicked inner intersections and tee, not middle-ring fit evidence.
    independent=[e for e in view['check'] if np.linalg.norm(e['metres'])<.7]
    def manual_error(mat):
        err=np.linalg.norm(project(mat,[e['pixel'] for e in independent])-[e['metres'] for e in independent],axis=1)
        return {'count':len(err),'rmse_m':float(np.sqrt(np.mean(err**2))),'max_m':float(max(err))}
    return H,{'initial_H':initial.tolist(),'refined_H':H.tolist(),'fit_edges':len(train),
              'training_before':ring_summary(initial,train),'training_after':ring_summary(H,train),
              'heldout_outer_middle_before':ring_summary(initial,hold),'heldout_outer_middle_after':ring_summary(H,hold),
              'withheld_inner_before':ring_summary(initial,inner),'withheld_inner_after':ring_summary(H,inner),
              'withheld_manual_inner_tee_before':manual_error(initial),'withheld_manual_inner_tee_after':manual_error(H),
              'fit_observations':train,'heldout_observations':hold,'inner_observations':inner,
              'note':'Same-image ring checks, not surveyed ground truth. Boundary search uses initial geometry. Lens distortion unmodelled.'}


def validate_rings(image,H,region):
    """Image-evidence gate. Thresholds are engineering checks, not confidence intervals."""
    edges=[e for r in RADII for e in ring_edges(image,H,r,region,angles=np.arange(1.5,360,6),search_px=5.)]
    summary=ring_summary(H,edges)
    if edges:
        world=project(H,[e['pixel'] for e in edges]);errors=np.abs(np.linalg.norm(world,axis=1)-[e['radius_m'] for e in edges])
        pixel_errors=errors/np.array([e['metres_per_normal_pixel'] for e in edges])
        summary['median_normal_error_px']=float(np.median(pixel_errors))
        summary['p90_normal_error_px']=float(np.percentile(pixel_errors,90))
    else:summary.update(median_normal_error_px=None,p90_normal_error_px=None)
    summary['rings_supported']=sum(sum(e['radius_m']==r for e in edges)>=12 for r in RADII)
    passed=(summary['count']>=50 and summary['angular_bins']>=8 and summary['rings_supported']>=2
            and summary['median_normal_error_px']<1.5 and summary['p90_normal_error_px']<3.
            and summary['p95_abs_radial_error_m']<.18)
    summary['status']='supported' if passed else 'insufficient_or_inconsistent_ring_evidence'
    summary['note']='Visible paint consistency; cannot certify occluded areas or physical stone positions.'
    return passed,summary


class VideoRectifier:
    """Absolute SIFT registration every 0.5 s; forward/backward LK flow between anchors.

    A failed registration/ring gate/flow update yields no transform, never a stale one.
    Ring support is measured on anchor frames. Intervening frames carry the age of that
    check and are gated by feature support, optical-flow residual and scene-change checks.
    """
    def __init__(self,view,frame_folder,H,anchor_interval_s=.5):
        from vision_core import ViewCalibrator
        self.cal=ViewCalibrator(view,frame_folder);self.refined=np.asarray(H,float)
        self.view=view;self.interval=anchor_interval_s;self.last_anchor=-1e9
        self.H=None;self.gray=None;self.points=None;self.quality=None
        self.thumbnail=None;self.reference_gray=cv2.cvtColor(self.cal.reference,cv2.COLOR_BGR2GRAY)

    def _seed(self,image,gray,A):
        mask=cv2.warpPerspective(self.cal.mask,A,(image.shape[1],image.shape[0]),flags=cv2.INTER_NEAREST)
        reference=cv2.warpPerspective(self.reference_gray,A,(image.shape[1],image.shape[0]))
        # Exclude large appearance changes (often people/stones) from tracked ice features.
        mask[cv2.absdiff(gray,reference)>28]=0
        self.points=cv2.goodFeaturesToTrack(gray,maxCorners=300,qualityLevel=.015,minDistance=10,mask=mask,blockSize=5)

    def step(self,image,t):
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        x0,y0,x1,y1=self.view['region'];thumb=cv2.resize(gray[y0:y1,x0:x1],(96,108))
        change=float(np.mean(cv2.absdiff(thumb,self.thumbnail)>40)) if self.thumbnail is not None else 0.
        self.thumbnail=thumb
        force=t-self.last_anchor>=self.interval-1e-6 or self.H is None or change>.35
        if force:
            self.last_anchor=t
            _,reg=self.cal.register(image)
            H=None;quality=None
            if reg['status']=='registered':
                A=np.array(reg['reference_to_current']);H=self.refined@np.linalg.inv(A)
                good,quality=validate_rings(image,H,self.view['region'])
                if not good:H=None
            self.H=H;self.gray=gray;self.quality=quality
            if H is not None:self._seed(image,gray,A)
            else:self.points=None
            return H,{'status':'supported' if H is not None else 'unavailable','method':'absolute_registration',
                      'registration':reg,'ring_check':quality,'ring_check_age_s':0.,'scene_change_fraction':change}
        diagnostic={'method':'optical_flow','ring_check_age_s':t-self.last_anchor,'scene_change_fraction':change}
        H=None
        if self.points is not None and len(self.points)>=16:
            p,status,_=cv2.calcOpticalFlowPyrLK(self.gray,gray,self.points,None,winSize=(21,21),maxLevel=3)
            back,bs,_=cv2.calcOpticalFlowPyrLK(gray,self.gray,p,None,winSize=(21,21),maxLevel=3)
            ok=(status.ravel()>0)&(bs.ravel()>0)&(np.linalg.norm(back-self.points,axis=2).ravel()<.75)
            a=self.points.reshape(-1,2)[ok];b=p.reshape(-1,2)[ok]
            if len(a)>=16:
                A,mask=cv2.findHomography(a,b,cv2.RANSAC,1.,maxIters=1000,confidence=.995)
                if A is not None and mask is not None:
                    keep=mask.ravel().astype(bool);span=np.ptp(a[keep],axis=0) if keep.any() else [0,0]
                    error=np.linalg.norm(project(A,a[keep])-b[keep],axis=1)
                    movement=np.linalg.norm(b[keep]-a[keep],axis=1)
                    diagnostic.update(inliers=int(keep.sum()),rmse_px=float(np.sqrt(np.mean(error**2))) if len(error) else None,
                                      support_span_px=np.asarray(span).tolist())
                    if (keep.sum()>=16 and span[0]>.25*(x1-x0) and span[1]>.10*(y1-y0)
                        and diagnostic['rmse_px']<.7 and np.percentile(movement,90)<20):
                        try:H=self.H@np.linalg.inv(A)
                        except np.linalg.LinAlgError:pass
                        self.points=b[keep].astype(np.float32).reshape(-1,1,2)
        self.H=H;self.gray=gray;diagnostic['status']='supported' if H is not None else 'unavailable'
        if H is None:diagnostic['reason']='Insufficient consistent ice-plane optical flow; no stale transform emitted'
        return H,diagnostic
