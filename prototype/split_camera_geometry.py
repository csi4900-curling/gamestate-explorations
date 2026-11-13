"""Reuse the existing split-camera calibration stages with shot-anchor registration.

Departure uses the original native-reference ViewCalibrator. Receiving initialization
is the existing automatic house/hog fit. The original departure reference and the
initialized receiving anchor are reused across events; later frames use registration.
No event IDs, match IDs, new manual landmarks or new rejection thresholds occur.
The legacy initializers still contain heuristics; these are explicitly recorded,
not represented as learned geometry or independently validated metric accuracy.
"""
from pathlib import Path
import json
import sys
import time
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from vision_core import ViewCalibrator
from camera_geometry import features,transfer
from source_specific_house_calibration import fit_source_house
from split_house_ellipse_v2 import fit_house_ellipse
from body_localization import transported_reference_camera


class SplitCameraGeometry:
    def __init__(self, calibration, annotations, reference_frames):
        self.calibration=json.loads(Path(calibration).read_text())
        views=json.loads(Path(annotations).read_text())['views']
        self.left=ViewCalibrator(views['left'],reference_frames)
        self.left.H=np.asarray(self.calibration['left']['refined_H'],float)
        self.right_reference=cv2.resize(cv2.imread(str(Path(reference_frames)/views['right']['reference_frame'])),(640,360))
        self.right_reference_ellipse=fit_house_ellipse(self.right_reference)
        self.anchors={};self.initialization_attempts={'left':0,'right':0};self.registration_attempts={'left':0,'right':0}
        self.source_house_fit_attempts=0;self.wall_seconds=0.
        self.stage_wall_seconds={}

    def observe(self,frame,time_s):
        started=time.perf_counter();normalized=cv2.resize(frame,(640,360));result={}
        for panel in ('left','right'):
            stage=('native_reference_registration' if panel=='left' else
                   'anchor_registration' if panel in self.anchors else 'house_initialization')
            panel_started=time.perf_counter()
            try:
                result[panel]=self._panel(frame,normalized,time_s,panel)
            except (ValueError,np.linalg.LinAlgError,FloatingPointError) as exc:
                result[panel]=(None,{'status':'undefined_geometry','reason':str(exc),'panel':panel},None)
            duration=time.perf_counter()-panel_started
            key=panel+':'+stage
            self.stage_wall_seconds[key]=self.stage_wall_seconds.get(key,0.)+duration
            H,diagnostic,prior=result[panel]
            result[panel]=(H,{**diagnostic,'runtime':{'stage':stage,'wall_seconds':duration}},prior)
        self.wall_seconds+=time.perf_counter()-started
        return result

    def _panel(self,frame,normalized,time_s,panel):
        region=(0,0,320,360) if panel=='left' else (320,0,640,360)
        if panel=='left':
            self.registration_attempts[panel]+=1
            H,diag=self.left.register(cv2.resize(frame,(1920,1080)))
            H=H@np.diag([3.,3.,1.]) if H is not None else None
            prior=transported_reference_camera(self.left.H@np.diag([3.,3.,1.]),H,region) if H is not None else None
            return (H,{**diag,'stage':'original_native_reference_registration','no_new_calibration_fit':True},prior)
        if panel not in self.anchors:
            self.initialization_attempts[panel]+=1
            ellipse=fit_house_ellipse(normalized)
            H,diag=None,{'status':'no_receiving_house_ellipse'}
            if ellipse and self.right_reference_ellipse:
                self.source_house_fit_attempts+=1
                H,diag=fit_source_house(normalized,ellipse,self.calibration['right']['refined_H'],self.right_reference_ellipse)
            prior=transported_reference_camera(H,H,region) if H is not None else None
            if H is not None:
                self.anchors[panel]={'time_s':time_s,'frame':normalized.copy(),'H':H,
                    'features':features(normalized,region),'prior':prior,'initialization':diag}
            return (H,{**diag,'stage':'existing_initializer','anchor_time_s':time_s if H is not None else None},prior)
        else:
            anchor=self.anchors[panel];self.registration_attempts[panel]+=1
            H,diag=transfer(anchor['frame'],normalized,anchor['H'],region,reference_features=anchor['features'])
            prior=None
            if H is not None and anchor['prior'] is not None:
                A=np.asarray(diag['reference_to_current'])
                transform=lambda c:{'plane':A@c['plane'],'vertical':A@c['vertical']}
                prior={'camera':transform(anchor['prior']['camera']),'diagnostic':anchor['prior']['diagnostic'],
                       'alternatives':[transform(c) for c in anchor['prior']['alternatives']]}
            return (H,{**diag,'stage':'registered_anchor_reuse','anchor_time_s':anchor['time_s'],
                'no_new_calibration_fit':True},prior)

    def provenance(self):
        return {'initializer':'existing native left registration; existing automatic right house/hog fit',
                'legacy_heuristics_retained':True,'new_application_quality_thresholds':False,
                'anchors':{k:{'time_s':a['time_s'],'H_normalized_source':a['H'].tolist(),'initialization':a['initialization']} for k,a in self.anchors.items()},
                'initialization_attempts':self.initialization_attempts,'source_house_fit_attempts':self.source_house_fit_attempts,
                'registration_attempts':self.registration_attempts,'wall_seconds':self.wall_seconds,
                'stage_wall_seconds':dict(self.stage_wall_seconds),
                'failure_policy':'Missing image registration stays missing; no event-triggered re-fit or unobserved mapping propagation',
                'physical_metric_accuracy_validated':False}
