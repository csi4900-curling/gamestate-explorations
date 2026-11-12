"""Post-hoc detector/point-tracker identity conflict evidence.

Exact-frame body-box containment, without distance thresholds, reassignment or
suppression. A shared box is a conflict hypothesis, not a proved identity switch:
merged detector boxes, overlapping stones and duplicate initial queries can also
cause it. Raw predictions and their original visibility are preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path


def frame_conflicts(points, visible, detections):
    membership=[]
    for point,seen in zip(points,visible):
        membership.append([i for i,d in enumerate(detections)
                           if d['bbox_xyxy'][0]<=point[0]<=d['bbox_xyxy'][2]
                           and d['bbox_xyxy'][1]<=point[1]<=d['bbox_xyxy'][3]] if seen else [])
    unique={}
    for query,boxes in enumerate(membership):
        if len(boxes)==1:unique.setdefault(boxes[0],[]).append(query)
    return {'query_box_membership':membership,
            'shared_box_conflicts':[{'detection_index':box,'query_indices':queries}
                                    for box,queries in unique.items() if len(queries)>1],
            'ambiguous_box_query_indices':[i for i,m in enumerate(membership) if len(m)>1]}


def audit(result_path, observation_run, output):
    result_path,observation_run,output=map(Path,(result_path,observation_run,output))
    if output.exists():raise ValueError('Preserve previous audit')
    r=json.loads(result_path.read_text());protocol=json.loads((observation_run/'protocol.json').read_text())
    if r['provenance']['source_sha256']!=protocol['source_sha256']:raise ValueError('Source mismatch')
    lookup={f:i for i,f in enumerate(r['frame_indices'])}
    if len(lookup)!=len(r['frame_indices']):raise ValueError('Duplicate tracking source frames')
    records=[];path=observation_run/'observations.jsonl';digest=hashlib.sha256()
    with path.open('rb') as stream:
        for raw in stream:
            digest.update(raw);row=json.loads(raw);frame=row['frame_index']
            if frame not in lookup:continue
            i=lookup[frame]
            if abs(row['time_s']-r['times_s'][i])>1e-6:raise ValueError('Frame/time mismatch')
            check=frame_conflicts(r['tracks_px'][i],r['point_visible'][i],row['detections'])
            records.append({'frame_index':frame,'time_s':row['time_s'],**check})
    data={'development':True,'method':'Exact-frame visible point containment in learned body boxes; no assignment changes',
          'result_sha256':hashlib.sha256(result_path.read_bytes()).hexdigest(),
          'observations_sha256':digest.hexdigest(),'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'source_sha256':protocol['source_sha256'],'query_names':r['point_names'],
          'sampled_frames_compared':len(records),'frames_with_shared_box_conflict':sum(bool(x['shared_box_conflicts']) for x in records),
          'frames_with_ambiguous_box_membership':sum(bool(x['ambiguous_box_query_indices']) for x in records),
          'physical_identity_switch_count':None,'predictions_modified':False,
          'limitations':['Merged or incorrect detections can cause false conflicts.','No detected conflict does not establish correct identity.','Only exact common sampled frames are checked.','Box membership does not distinguish colour or verify physical stone identity.'],
          'frames':records}
    output.write_text(json.dumps(data,indent=2)+'\n');return data


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--result',required=True);p.add_argument('--observations',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=audit(a.result,a.observations,a.output);print(json.dumps({k:v for k,v in r.items() if k!='frames'}))
