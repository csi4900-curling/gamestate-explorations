"""Small, unit-aware planar calibration helpers."""
import numpy as np
import cv2
from itertools import combinations

def project(H,xy):
 xy=np.asarray(xy,dtype=float).reshape(-1,2)
 q=np.c_[xy,np.ones(len(xy))]@H.T
 if np.any(np.abs(q[:,2])<1e-10):raise ValueError('Projection at infinity')
 return q[:,:2]/q[:,2,None]
def world(key):
 radius={'o':1.829,'w':1.219,'r':0.610}[key[0]]
 return np.array({'L':[-radius,0],'R':[radius,0],'T':[0,-radius],'B':[0,radius]}[key[1]])
def has_projective_basis(metric):
 # Four correspondences in general position: no three collinear.
 # Test world coordinates, whose exact painted geometry is known.
 for quad in combinations(np.asarray(metric,float),4):
  if all(abs(np.linalg.det(np.c_[np.array(tri),np.ones(3)]))>1e-8 for tri in combinations(quad,3)):
   return True
 return False

def fit(pixel,metric,model='homography'):
 if model=='affine':
  P=np.c_[np.asarray(pixel,float),np.ones(len(pixel))]
  if np.linalg.matrix_rank(P)<3:raise ValueError('Affine calibration is also degenerate')
  A=np.linalg.lstsq(P,np.asarray(metric,float),rcond=None)[0].T
  return np.vstack([A,[0.,0.,1.]])
 if not has_projective_basis(metric):raise ValueError('Homography unidentifiable: no four landmarks in general position')
 H,_=cv2.findHomography(np.asarray(pixel,dtype=float),np.asarray(metric,dtype=float),method=0)
 if H is None or not np.isfinite(H).all() or np.linalg.matrix_rank(H)<3:raise ValueError('Invalid homography')
 return H/H[2,2]
