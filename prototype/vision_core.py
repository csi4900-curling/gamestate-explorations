"""Experimental, source-specific geometry and visible stone-cap proposals.
Metric results are ice-plane projections of above-ice pixels, NOT measured stone centres.
"""
from __future__ import annotations
import math
from pathlib import Path
import cv2
import numpy as np

DETECTOR_VERSION='colour-cap-baseline-v2'
def project(H,points):
 points=np.asarray(points,dtype=np.float64).reshape(-1,2)
 if not len(points):return np.empty((0,2))
 q=np.column_stack([points,np.ones(len(points))])@np.asarray(H).T
 if not np.isfinite(q).all() or np.any(np.abs(q[:,2])<1e-10):raise ValueError('Invalid planar projection')
 return q[:,:2]/q[:,2,None]
def fit_calibration(view):
 px=np.array([p['pixel'] for p in view['fit']],float);world=np.array([p['metres'] for p in view['fit']],float)
 if len(px)<4 or np.linalg.matrix_rank(np.column_stack([world,np.ones(len(world))]))<3:raise ValueError('Degenerate calibration landmarks')
 H,_=cv2.findHomography(px,world,0)
 if H is None or not np.isfinite(H).all() or np.linalg.matrix_rank(H)<3:raise ValueError('Unidentifiable calibration')
 check=np.array([p['pixel'] for p in view['check']],float);expected=np.array([p['metres'] for p in view['check']],float)
 errors=np.linalg.norm(project(H,check)-expected,axis=1)
 return H,{'withheld_count':len(errors),'same_image_landmark_rmse_m':float(np.sqrt(np.mean(errors**2))),'max_error_m':float(errors.max()),'errors_m':errors.tolist(),'note':'Withheld painted landmarks, same image and annotator. Not physical stone-position accuracy.'}
class ViewCalibrator:
 def __init__(self,view,frame_folder):
  self.view=view;self.reference=cv2.imread(str(Path(frame_folder)/view['reference_frame']))
  if self.reference is None:raise ValueError('Missing calibration reference')
  self.H,self.check=fit_calibration(view);self.sift=cv2.SIFT_create(nfeatures=4000,contrastThreshold=.01)
  x0,y0,x1,y1=view['region'];self.mask=np.zeros(self.reference.shape[:2],np.uint8)
  self.mask[max(y0,int(.35*y1)):int(.97*y1),x0+15:x1-15]=255
  self.kp,self.desc=self.sift.detectAndCompute(cv2.cvtColor(self.reference,cv2.COLOR_BGR2GRAY),self.mask)
 def register(self,image,is_reference=False):
  if image.shape!=self.reference.shape:return None,{'status':'rejected','reason':'Resolution differs from calibration reference'}
  if is_reference:return self.H.copy(),{'status':'reference','inliers':None,'rmse_px':0.0}
  kp,desc=self.sift.detectAndCompute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),self.mask)
  if desc is None or self.desc is None:return None,{'status':'rejected','reason':'Insufficient features'}
  pairs=cv2.BFMatcher().knnMatch(self.desc,desc,k=2);good=[m for pair in pairs if len(pair)==2 for m,n in [pair] if m.distance<.75*n.distance]
  if len(good)<12:return None,{'status':'rejected','reason':'Too few reliable feature matches','matches':len(good)}
  a=np.array([self.kp[m.queryIdx].pt for m in good],np.float32);b=np.array([kp[m.trainIdx].pt for m in good],np.float32)
  A,mask=cv2.findHomography(a,b,cv2.RANSAC,2.5,maxIters=3000,confidence=.995)
  if A is None or mask is None:return None,{'status':'rejected','reason':'No registration homography'}
  inside=mask.ravel().astype(bool);n=int(inside.sum());x0,y0,x1,y1=self.view['region'];span=np.ptp(a[inside],axis=0) if n else [0,0]
  if n<12 or span[0]<(x1-x0)*.25 or span[1]<(y1-y0)*.12:return None,{'status':'rejected','reason':'Insufficient spatial support','inliers':n}
  corners=np.array([[x0,y0],[x1,y0],[x1,y1],[x0,y1]],float)
  try:movement=np.linalg.norm(project(A,corners)-corners,axis=1);H=self.H@np.linalg.inv(A)
  except (ValueError,np.linalg.LinAlgError):return None,{'status':'rejected','reason':'Invalid transform'}
  error=np.linalg.norm(project(A,a[inside])-b[inside],axis=1);rmse=float(np.sqrt(np.mean(error**2)))
  if movement.max()>120 or rmse>2:return None,{'status':'rejected','reason':'Excessive registration motion/error','inliers':n,'rmse_px':rmse}
  return H,{'status':'registered','inliers':n,'matches':len(good),'rmse_px':rmse,'max_corner_displacement_px':float(movement.max()),'reference_to_current':A.tolist(),'note':'Feature consistency only; not proof of correct camera identity or metric accuracy.'}
def in_bounds(xy,bounds):
 x,y=xy;x0,y0,x1,y1=bounds;return x0<=x<=x1 and y0<=y<=y1

def detect_caps(image,H,view,registered_reference=None):
 if H is None:return [],{'status':'abstained','reason':'No accepted calibration registration'}
 inv=np.linalg.inv(H);hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV);x0,y0,x1,y1=view['region'];bounds=view['world_bounds']
 region=np.zeros(image.shape[:2],np.uint8);region[y0:y1,x0:x1]=255
 background_hsv=cv2.cvtColor(registered_reference,cv2.COLOR_BGR2HSV) if registered_reference is not None else None
 yellow=cv2.inRange(hsv,np.array([18,85,65]),np.array([43,255,255]))
 red=cv2.bitwise_or(cv2.inRange(hsv,np.array([0,90,40]),np.array([9,255,255])),cv2.inRange(hsv,np.array([170,90,40]),np.array([179,255,255])))
 candidates=[];rejected=[]
 for colour,mask in [('yellow',yellow),('red',red)]:
  mask=cv2.bitwise_and(mask,region)
  if background_hsv is not None:
   if colour=='yellow':paint=cv2.inRange(background_hsv,np.array([18,85,65]),np.array([43,255,255]))
   else:paint=cv2.bitwise_or(cv2.inRange(background_hsv,np.array([0,90,40]),np.array([9,255,255])),cv2.inRange(background_hsv,np.array([170,90,40]),np.array([179,255,255])))
   paint=cv2.dilate(paint,np.ones((7,7),np.uint8));mask=cv2.bitwise_and(mask,cv2.bitwise_not(paint))
  mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
  contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
  for c in contours:
   area=cv2.contourArea(c)
   if area<16:continue
   x,y,w,h=cv2.boundingRect(c);mom=cv2.moments(c)
   if mom['m00']==0:continue
   cx=mom['m10']/mom['m00'];cy=mom['m01']/mom['m00']
   try:xy=project(H,[[cx,cy]])[0]
   except ValueError:continue
   if not in_bounds(xy,bounds):continue
   diameter=np.linalg.norm(np.diff(project(inv,[[xy[0]-.145,xy[1]],[xy[0]+.145,xy[1]]]),axis=0))
   reason=None
   if not .35*diameter<=w<=1.15*diameter:reason='width inconsistent with nominal stone scale'
   elif not .12<=h/max(w,1)<=.85:reason='colour component shape'
   elif area/(w*h)<.24:reason='thin or fragmented component'
   band=hsv[min(y+h,image.shape[0]-1):min(y+h+max(4,round(w*.35)),image.shape[0]),max(x,0):min(x+w,image.shape[1])]
   body=float(np.mean((band[:,:,1]<95)&(band[:,:,2]>40)&(band[:,:,2]<225))) if band.size else 0.
   if reason is None and body<.22:reason='weak grey stone-body support'
   record={'colour':colour,'pixel_center':[round(cx,2),round(cy,2)],'bbox':[x,y,w,h],'body_support':round(body,3),'expected_stone_width_px':round(float(diameter),2)}
   if reason:record['reason']=reason;rejected.append(record);continue
   sensitivity=np.linalg.norm(project(H,[[cx+2,cy],[cx,cy+2]])-xy,axis=1)
   record.update({'id':f'{colour}-{len(candidates)+1}','ice_plane_projection_m':xy.tolist(),'position_semantics':'Uncorrected ice-plane projection of coloured-cap centroid; NOT stone footprint centre.','two_pixel_sensitivity_m':sensitivity.tolist(),'identity':None,'in_play_status':'unknown','confidence':None})
   candidates.append(record)
 return candidates,{'status':'proposals','rejected':rejected,'note':'Heuristic visible cap proposals. False positives, merged caps, occlusions and parked stones remain possible.'}
def export_game_state(result):
 raise ValueError('Experimental cap projections are not validated metric stone positions; simulator export is unavailable')
