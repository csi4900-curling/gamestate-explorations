"""Development layout reuse for OCR totals, with source-frame registration.

Layout identity comes from an earlier frame where both teams and TOTAL were
observed. Numeric readings always come from the current frame's OCR tokens.
OpenCV SIFT/mutual matching/LMEDS estimate image motion; no manually supplied
landmarks or fitted pixel-error acceptance threshold. Occlusion can still cause
OCR hallucinations. This is not part of the frozen match baseline.
"""
import argparse
import json
import time
from pathlib import Path
import numpy as np


def probe(video, observations, output, teams, times, transform_model='homography_lmeds', feature_region='layout_only'):
    import cv2
    from prototype.detection_cache import digest
    from prototype.scoreboard_observation import parse_totals
    video,observations,output=map(Path,(video,observations,output))
    protocol=json.loads((observations.parent/'protocol.json').read_text())
    if digest(video)!=protocol['source_sha256']:raise ValueError('Source mismatch')
    if output.exists():raise ValueError('Preserve previous probe')
    output.mkdir(parents=True);rows=[json.loads(l) for l in observations.open()]
    anchor=next((r for r in rows if all(r['totals'][t]['value'] is not None for t in teams)),None)
    if anchor is None:raise ValueError('No observed layout anchor')
    labels=[anchor['totals'][t]['evidence'][1] for t in teams];header=anchor['totals'][teams[0]]['evidence'][0]
    layout=[header,*labels];bounds=np.asarray([t['bounds'] for t in layout]);region=[int(bounds[:,0].min()),int(bounds[:,1].min()),int(bounds[:,2].max()),int(bounds[:,3].max())]
    if feature_region=='header_and_layout':
        above=[t['bounds'][1] for t in anchor['tokens'] if t['bounds'][0]>=region[0] and t['bounds'][2]<=region[2] and t['bounds'][3]<=region[1]]
        if above:region[1]=int(min(above))
    elif feature_region!='layout_only':raise ValueError('Unknown feature region')
    cap=cv2.VideoCapture(str(video));cap.set(cv2.CAP_PROP_POS_FRAMES,anchor['frame_index']);ok,reference=cap.read()
    if not ok:raise ValueError('Cannot read anchor')
    mask=np.zeros(reference.shape[:2],np.uint8);x0,y0,x1,y1=region;mask[y0:y1,x0:x1]=255
    sift=cv2.SIFT_create();kp,desc=sift.detectAndCompute(cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY),mask);results=[]
    try:
        for row in rows:
            if times is not None and row['time_s'] not in times:continue
            started=time.perf_counter();out={'time_s':row['time_s'],'frame_index':row['frame_index'],'anchor_time_s':anchor['time_s'],'totals':{t:None for t in teams}}
            if row['time_s']<anchor['time_s']:out['status']='before_observed_anchor';results.append(out);continue
            cap.set(cv2.CAP_PROP_POS_FRAMES,row['frame_index']);ok,frame=cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=row['frame_index']:raise ValueError('Source frame mismatch')
            kq,dq=sift.detectAndCompute(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),mask)
            matches=cv2.BFMatcher(cv2.NORM_L2,crossCheck=True).match(desc,dq) if desc is not None and dq is not None else []
            A,inliers=None,None
            if len(matches)>=4:
                a=np.asarray([kp[m.queryIdx].pt for m in matches],np.float32);b=np.asarray([kq[m.trainIdx].pt for m in matches],np.float32)
                if transform_model=='homography_lmeds':A,inliers=cv2.findHomography(a,b,cv2.LMEDS)
                elif transform_model=='similarity_lmeds':
                    affine,inliers=cv2.estimateAffinePartial2D(a,b,method=cv2.LMEDS)
                    A=np.vstack([affine,[0,0,1]]) if affine is not None else None
                else:raise ValueError('Unknown transform model')
            if A is None or not np.isfinite(A).all():out['status']='registration_unavailable';results.append(out);continue
            warped=[]
            for token in layout:
                points=cv2.perspectiveTransform(np.asarray(token['box'],np.float32)[None],A)[0]
                warped.append({**token,'box':points.tolist(),'bounds':[float(points[:,0].min()),float(points[:,1].min()),float(points[:,0].max()),float(points[:,1].max())]})
                cv2.polylines(frame,[points.astype(np.int32)],True,(0,180,255),2)
            current=[t for t in row['tokens'] if t['normalized'] not in {*teams,'TOTAL'}];tokens=warped+current
            parsed=parse_totals([t['text'] for t in tokens],[t['confidence'] for t in tokens],[t['box'] for t in tokens],teams)
            out.update(status='registered_layout_current_ocr',totals={t:v['value'] for t,v in parsed['totals'].items()},reading_evidence=parsed['totals'],reference_to_current=A.tolist(),matches=len(matches),inliers=int(inliers.sum()),wall_seconds=time.perf_counter()-started)
            cv2.imwrite(str(output/f'{row["frame_index"]}.jpg'),frame);results.append(out)
    finally:cap.release()
    data={'development':True,'source_sha256':protocol['source_sha256'],'input_observations_sha256':digest(observations),'code_sha256':digest(__file__),'anchor_time_s':anchor['time_s'],'layout_region_px':region,'requested_times':sorted(times) if times is not None else 'all input observations','method':'Earlier observed team/TOTAL geometry, OpenCV SIFT mutual matching + LMEDS, current raw OCR digit tokens','inference_baseline_changed':False,'observations':results}
    data['feature_region']=feature_region
    data['transform_model']=transform_model
    data['transform_assumption']='Planar perspective mapping' if transform_model=='homography_lmeds' else 'Translation, in-plane rotation and uniform scale; no changing perspective'
    (output/'result.json').write_text(json.dumps(data,indent=2)+'\n');(output/'code.py').write_bytes(Path(__file__).read_bytes())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--video',required=True);p.add_argument('--observations',required=True);p.add_argument('--output',required=True);p.add_argument('--teams',nargs=2,required=True);p.add_argument('--times',nargs='+',type=float);p.add_argument('--transform-model',choices=['homography_lmeds','similarity_lmeds'],default='homography_lmeds');p.add_argument('--feature-region',choices=['layout_only','header_and_layout'],default='layout_only');a=p.parse_args();probe(a.video,a.observations,a.output,a.teams,a.times,a.transform_model,a.feature_region)
