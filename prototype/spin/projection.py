"""Reuse an existing accepted calibration with the existing camera-transfer code.

This does not fit a new rink calibration. Per-frame camera registration remains
necessary before projecting a model-tracked cap point. Above-ice points are not
validated stone contact locations. Failures retain explicit missing projections.
"""
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from camera_geometry import features, transfer
from vision_core import project
from body_localization import transported_reference_camera, localize, feature_heights
from .point_tracking import digest


def project_existing(video, aggregate_path, segment_id, times, tracks, visible, *, point_kinds=None, heights_m=None):
    started=time.perf_counter()
    heights=feature_heights(heights_m)
    kinds=point_kinds or ['cap_with_body_support']*len(tracks[0])
    if len(kinds)!=len(tracks[0]) or any(k not in ('cap_with_body_support','body_box_center') for k in kinds):
        raise ValueError('Projection point kinds must match queries')
    data=json.loads(Path(aggregate_path).read_text())
    if data['context']['source_sha256'] != digest(video):
        raise ValueError('Projection aggregate/source mismatch')
    matches=[s for e in data['events'] for s in e['segments'] if s['segment_id']==segment_id]
    if len(matches)!=1:
        raise ValueError('Projection requires a unique existing segment')
    segment=matches[0]
    anchors=[s for s in segment.get('geometry_samples',[]) if s.get('top_view_m') is not None
             and s.get('homography_source_pixels_to_local_metres') is not None]
    if not anchors:
        return {'status':'no_existing_calibration','samples':[], 'wall_seconds':time.perf_counter()-started,
                'new_calibration_fits':0}
    anchor=min(anchors,key=lambda s:abs(s['time_s']-times[0]))
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise ValueError('Cannot open projection source')
    fps=cap.get(cv2.CAP_PROP_FPS)
    width,height=cap.get(cv2.CAP_PROP_FRAME_WIDTH),cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    region=(0,0,320,360) if segment['camera']=='left_split' else (320,0,640,360)
    H=np.asarray(anchor['homography_source_pixels_to_local_metres'],float)
    cap.set(cv2.CAP_PROP_POS_FRAMES,round(anchor['time_s']*fps))
    ok,reference=cap.read()
    if not ok:raise ValueError('Cannot read calibration anchor frame')
    reference=cv2.resize(reference,(640,360))
    cv2.setNumThreads(2);cv2.setRNGSeed(0)
    reference_features=features(reference,region)
    height_prior=transported_reference_camera(H,H,region)
    cuts=segment.get('camera_cut_times_s',[])
    samples=[]
    cap.set(cv2.CAP_PROP_POS_FRAMES,round(times[0]*fps))
    try:
        for index,t in enumerate(times):
            expected=round(t*fps)
            if round(cap.get(cv2.CAP_PROP_POS_FRAMES))!=expected:
                cap.set(cv2.CAP_PROP_POS_FRAMES,expected)
            ok,frame=cap.read()
            if not ok:raise ValueError(f'Projection decode failed at {t}')
            frame=cv2.resize(frame,(640,360))
            if any(min(anchor['time_s'],t)<c<=max(anchor['time_s'],t) for c in cuts):
                target,diag=None,{'status':'camera_cut_since_anchor'}
            elif abs(t-anchor['time_s'])<.5/fps:
                target,diag=H,{'status':'existing_anchor_frame'}
            else:
                target,diag=transfer(reference,frame,H,region,reference_features=reference_features)
            projected=[]
            adjusted=[]
            adjustment_diagnostics=[]
            current_prior=None
            if height_prior is not None and target is not None:
                A=np.asarray(diag.get('reference_to_current',np.eye(3)),float)
                def transport_camera(camera):
                    return {'plane':A@camera['plane'], 'vertical':A@camera['vertical']}
                current_prior={'camera':transport_camera(height_prior['camera']),
                               'diagnostic':height_prior['diagnostic'],
                               'alternatives':[transport_camera(c) for c in height_prior['alternatives']]}
            for p,is_visible,kind in zip(tracks[index],visible[index],kinds):
                xy=np.asarray(p)*[640/width,360/height]
                q=project(target,[xy])[0] if target is not None and is_visible else None
                projected.append(q.tolist() if q is not None and np.isfinite(q).all() else None)
                if current_prior is not None and is_visible:
                    corrected,correction=localize(target,xy,region,'cap_with_body_support' if kind=='cap_with_body_support' else 'body_box_center',camera_prior=current_prior, heights_m=heights)
                    adjusted.append(corrected.tolist() if corrected is not None else None)
                    adjustment_diagnostics.append(correction)
                else:
                    adjusted.append(None)
                    adjustment_diagnostics.append({'status':'unavailable','reason':'No supported camera prior, registration or visible point'})
            samples.append({'time_s':float(t),'points_camera_local_m':projected,
                            'height_adjusted_points_camera_local_m':adjusted,
                            'height_adjustment':adjustment_diagnostics,'registration':diag})
    finally:
        cap.release()
    return {'status':'conditional_camera_local_cap_projection','camera':segment['camera'],
            'coordinate_system':'Existing camera-local metres: tee at (0,0), saved calibration axes. Not a common-rink orientation.',
            'local_hog_y_m':data.get('provenance',{}).get('local_hog_y_m',{}).get(segment['camera'].removesuffix('_split')),
            'interpretation':'Tracked image features projected onto ice plane; point_kinds distinguish cap queries from body-box centres. Neither establishes verified contact points or physical trajectory accuracy.',
            'anchor_time_s':anchor['time_s'],'anchor_homography':H.tolist(),
            'aggregate_sha256':digest(aggregate_path),
            'new_calibration_fits':0,'reference_feature_extractions':1,
            'camera_registration_attempts':sum(s['registration']['status']!='existing_anchor_frame' for s in samples),
            'samples':samples,'wall_seconds':time.perf_counter()-started,
            'source_point_visible_count':int(np.asarray(visible).sum()),
            'projected_point_count':sum(p is not None for s in samples for p in s['points_camera_local_m']),
            'height_adjusted_point_count':sum(p is not None for s in samples for p in s['height_adjusted_points_camera_local_m']),
            'height_adjustment_method':'Existing body_localization.localize with a single reference camera prior transported by image registration',
            'point_kinds':kinds,
            'feature_heights_m':heights,
            'body_box_height_assumption_m':heights['body_box_center'] if 'body_box_center' in kinds else None,
            'height_adjustment_assumptions':f"Cap-plane height {heights['cap_with_body_support']} m; body-box queries use conditional body-centre height {heights['body_box_center']} m. A box centre is not a measured surface height. Conditional camera intrinsics. Tracked point is not independently verified as cap-plane or stone-centre in every frame. Sensitivity is not a calibrated confidence interval.",
            'height_camera_prior':height_prior['diagnostic'] if height_prior is not None else None,
            'height_reference_prior_constructions':1,
            'physical_accuracy_validated':False}
