"""Verify reuse of an explicitly calibrated, locked camera pose.

OpenCV normalized template correlation tests operator-marked static paint and
lengthwise guides at their original pixels. It estimates no homography and no
motion from players. Unsupported camera motion requires explicit recalibration.
"""
import cv2
import numpy as np

POLICY = {
    'version':'locked-calibration-pose-v3','patch_size_px_at_1080p':21,
    'minimum_patch_std_8bit':3.,'minimum_normalized_correlation':.8,
    'minimum_ring_support':3,'minimum_ring_supported_fraction':.3,
    'minimum_hog_support':2,'minimum_guide_supported_fraction':.5,
    'minimum_support_width_fraction':.25,'minimum_support_height_fraction':.12,
    'visibility_rule':'Distributed hog support plus either visible ring marks or both longitudinal guides. Occluded groups are not required when the other independent structural group supports the fixed pose.',
    'interpretation':'Shared engineering image-consistency gates, not calibrated confidence or absolute metric error bounds.',
    'motion':'No automatic image warp or calibration refit. This mode supports a fixed camera pose; unsupported movement remains missing.'}


class PoseVerifier:
    def __init__(self, image, record, panel):
        self.panel=panel;self.samples=[];self.reference_counts={}
        gray=cv2.cvtColor(cv2.resize(image,(1920,1080)),cv2.COLOR_BGR2GRAY)
        for row in record['fit_points']+record['check_points']:
            name=row.get('feature_id',row.get('landmark_id',''))
            if name=='hog_line' or name.startswith('hog_'):group='hog'
            elif name in ['centre_line','tee_line','wheelchair_left','wheelchair_right']:continue
            else:group='rings'
            self._sample(gray,row['pixel_normalized'],group)
        for i,segment in enumerate(record.get('parallel_lines',[])):
            # Only endpoints were observed by the operator. The interior may be
            # occluded; interpolating it would invent static image observations.
            for point in segment:self._sample(gray,point,'guide'+str(i))

    def _sample(self,gray,point,group):
        x,y=map(int,np.rint(np.asarray(point)*[1920,1080]));r=10
        lo,hi=(0,960) if self.panel=='left' else (960,1920)
        if not (lo+r<=x<hi-r and r<=y<1080-r):return
        patch=gray[y-r:y+r+1,x-r:x+r+1].copy()
        if float(patch.std())<3.:return
        self.samples.append((x,y,group,patch));self.reference_counts[group]=self.reference_counts.get(group,0)+1

    def check(self,image,details=False):
        gray=cv2.cvtColor(cv2.resize(image,(1920,1080)),cv2.COLOR_BGR2GRAY)
        support={};points=[];correlations=[]
        for x,y,group,patch in self.samples:
            score=float(cv2.matchTemplate(gray[y-10:y+11,x-10:x+11],patch,cv2.TM_CCOEFF_NORMED)[0,0])
            good=np.isfinite(score) and score>=.8
            if good:support[group]=support.get(group,0)+1;points.append([x,y])
            correlations.append({'pixel_at_1080p':[x,y],'group':group,'correlation':score if np.isfinite(score) else None,'supported':bool(good)})
        ring=self.reference_counts.get('rings',0)>=3 and support.get('rings',0)>=max(3,.3*self.reference_counts.get('rings',0))
        hog=self.reference_counts.get('hog',0)>=2 and support.get('hog',0)>=2
        guides=all(self.reference_counts.get(k,0)>0 and support.get(k,0)>=.5*self.reference_counts[k]
                   for k in ['guide0','guide1'])
        span=np.ptp(points,axis=0) if points else np.zeros(2)
        distributed=span[0]>=.25*960 and span[1]>=.12*1080
        ok=hog and distributed and (ring or guides)
        return bool(ok),{'status':'source_calibration_pose_supported' if ok else 'calibration_pose_unverified',
                   'reason':None if ok else 'Static marking image support is insufficient or the camera pose changed',
                   'source_patch_counts':self.reference_counts,'supported_patch_counts':support,
                   'supported_span_px_at_1080p':span.tolist(),'patch_correlations':[r['correlation'] for r in correlations],
                   'evidence_paths':(['rings_and_hog'] if ring and hog else [])+(['longitudinal_guides_and_hog'] if guides and hog else []),
                   **({'samples':correlations} if details else {}),
                   'image_motion_fitted':False,'calibration_refitted':False,'policy':POLICY['version'],
                   'physical_accuracy_verified':False}
