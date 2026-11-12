"""Compare observed box centres and existing ByteTrack position estimates.

Replays identical detections, first requiring exact saved assignment parity.
Static camera inputs are fixed. Camera agreement is a diagnostic, not reference
trajectory accuracy; this experiment does not select or change associations.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
import time
import numpy as np
from prototype.detection_cache import digest
from prototype.rink_calibration import project
from prototype.rink_coordinates import rink_position
from prototype.stone_measurement import body_point_support


def compare(job,camera_panels,output):
    from ultralytics.trackers.byte_tracker import BYTETracker
    from ultralytics.engine.results import Boxes
    job,camera_panels,output=map(Path,(job,camera_panels,output))
    if output.exists():raise ValueError('Preserve previous comparison')
    source=job/'observations/observations.jsonl'
    protocol=json.loads((job/'observations/protocol.json').read_text())
    aggregate=json.loads((job/'result/aggregate-rink.json').read_text())
    config=json.loads((job/'match.json').read_text())
    cameras=json.loads(camera_panels.read_text())
    width,height=protocol['source_size_px'];tracker=BYTETracker(SimpleNamespace(**protocol['tracker_config']))
    samples={};mismatches=[];started=time.perf_counter()
    with source.open() as stream:
        for line in stream:
            row=json.loads(line)
            boxes=np.array([[*d['bbox_xyxy'],d['confidence'],d['class_id']] for d in row['detections']],np.float32).reshape(-1,6)
            tracks=tracker.update(Boxes(boxes,(height,width)))
            pairs=sorted((int(t[4]),int(t[-1])) for t in tracks)
            expected=sorted((t['track_id'],t['detection_index']) for t in row['tracked_observations'])
            if pairs!=expected:mismatches.append(row['frame_index'])
            for tr in tracks:
                d=row['detections'][int(tr[-1])]
                if not body_point_support(d,[width,height])['centre_supported']:continue
                points={'observed':d['pixel'],'bytetrack':[(float(tr[0])+float(tr[2]))/2,(float(tr[1])+float(tr[3]))/2]}
                samples[(row['time_s'],int(tr[4]))]=points
    if mismatches:raise ValueError(f'ByteTrack baseline did not reproduce: {len(mismatches)} frames')
    comparison=[]
    for event in aggregate['events']:
        modes={}
        for mode in ['observed','bytetrack']:
            panels={}
            for segment in event['segments']:
                panel=segment['rink_panel'];P=np.asarray(cameras[panel]['camera_model']['projection_xyz_up_to_normalized_source'])
                G=P[:,[0,1,3]].copy();G[:,2]+=config['feature_heights_m']['body_box_center']*P[:,2]
                H=np.linalg.inv(G);values={}
                for p in segment['pixel_points']:
                    key=p['time_s'],segment['tracker_id']
                    if key not in samples:continue
                    pixel=np.array(samples[key][mode])*[640/width,360/height]
                    xy=project(H,[pixel])[0]
                    values[p['time_s']]=rink_position(xy,panel=panel,role=segment['role'],hog_y_m=config['local_hog_y_m'])
                panels[panel]=values
            shared=sorted(panels.get('left',{}).keys()&panels.get('right',{}).keys())
            errors=[float(np.linalg.norm(np.array(panels['left'][t])-panels['right'][t])) for t in shared]
            modes[mode]={'paired_samples':len(errors),'median_m':float(np.median(errors)) if errors else None,
                         'p95_m':float(np.percentile(errors,95)) if errors else None,
                         'maximum_m':max(errors) if errors else None}
        comparison.append({'candidate_id':event['candidate_id'],'modes':modes})
    result={'development':True,'scope':__doc__,'assignment_mismatch_frames':mismatches,'comparison':comparison,
            'wall_s':time.perf_counter()-started,'inputs_sha256':{'observations':digest(source),
                'camera_panels':digest(camera_panels),'aggregate':digest(job/'result/aggregate-rink.json'),
                'protocol':digest(job/'observations/protocol.json'),'adapter':digest(__file__)}}
    output.write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['job','camera-panels','output']:p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();print(json.dumps(compare(a.job,a.camera_panels,a.output)['comparison'],indent=2))
