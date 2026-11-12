"""Compare existing cap proposals and an upstream learned detector on frozen frames.

Requires source-only annotations and a frame protocol. Does not tune thresholds,
change event detection, or establish independent trajectory ground truth.
"""
import argparse
import html
import os
from urllib.parse import quote
import hashlib
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from prototype.stone_detector import StoneDetector
from prototype.right_large_cap_proposals import right_large_cap_proposals


def contains(box,point):
    return box[0]<=point[0]<=box[2] and box[1]<=point[1]<=box[3]


def score(detections, annotation, region):
    preds = [p for p in detections if contains(region,p['pixel'])]
    boxes = annotation['boxes_xyxy']
    cost = np.ones((len(boxes),len(preds)),float)
    for i,b in enumerate(boxes):
        for j,p in enumerate(preds):
            if contains(b,p['pixel']):
                centre=np.array([(b[0]+b[2])/2,(b[1]+b[3])/2])
                cost[i,j]=np.linalg.norm(centre-p['pixel'])/(1+np.linalg.norm(np.array(b[2:])-b[:2]))*.01
    matched=[]
    if cost.size:
        ii,jj=linear_sum_assignment(cost)
        matched=[(int(i),int(j)) for i,j in zip(ii,jj) if cost[i,j]<1]
    used={j for _,j in matched}
    ignored=[j for j,p in enumerate(preds) if j not in used and any(contains(b,p['pixel']) for b in annotation.get('ignore_regions_xyxy',[]))]
    fp=[j for j in range(len(preds)) if j not in used and j not in ignored]
    return {'tp':len(matched),'fp':len(fp),'fn':len(boxes)-len(matched),'ignored':len(ignored),
            'matches':matched,'false_positive_indices':fp,'predictions':preds}


def render_report(result, output):
    output=Path(output)
    source=quote(os.path.relpath(Path(result['protocol']['video']).resolve(),output.resolve()))
    summary=result['summary']
    content='<!doctype html><meta charset="utf-8"><title>Stone detector comparison</title><style>body{font:16px system-ui;max-width:1400px;margin:25px auto;padding:20px}table{border-collapse:collapse;width:100%}td,th{padding:10px;border:1px solid #ccc;text-align:left}img{width:100%}video{width:70%}.pair{display:grid;grid-template-columns:1fr 1fr;gap:15px}</style><h1>Learned stone detector versus colour proposals</h1><p>Development comparison: 10 predetermined source frames, 24 visible receiving-panel stone appearances. Source-only annotations by the assistant before new model predictions; not independent human ground truth. Ambiguous parked-stone regions excluded explicitly. This is object-hit scoring, not IoU precision, full-match event accuracy, identity or geometry validation.</p><table><tr><th>Detector</th><th>Matches</th><th>Extras</th><th>Misses</th><th>Hit precision</th><th>Hit recall</th><th>Median frame time after first call</th></tr>'
    for name,v in summary.items():
        content+=f"<tr><td>{name}</td><td>{v['tp']}</td><td>{v['fp']}</td><td>{v['fn']}</td><td>{v['precision']:.1%}</td><td>{v['recall']:.1%}</td><td>{v['median_remaining_frame_seconds']:.4f}s</td></tr>"
    content+='</table><p>Same full source frames for both detectors; score only right-panel objects. Learned model uses checkpoint training size 1280 and upstream prediction confidence 0.25, unchanged for this comparison. Model outputs body boxes; baseline outputs cap proposals. A hit requires a prediction centre inside a labelled stone extent, with one-to-one matching. Predictions in ambiguous regions are ignored only after matching labelled objects. Learned confidence is not calibrated probability.</p><p>The learned extra at 729.8s is a duplicate box on the partially visible incoming stone. It remains counted. The final-frame delivery-stick false detection is absent with the learned model. Single-class stone detection does not identify colour, team, thrown-stone identity or score.</p><video id="source" controls preload="metadata" src="'+source+'"></video>'
    for row in result['rows']:
        i=row['frame_id'];t=row['time_s'];content+=f'<h2>{t:.3f}s <button onclick="const v=document.getElementById(&quot;source&quot;);v.pause();v.currentTime={t};v.scrollIntoView()">Seek source frame</button></h2><div class="pair">'
        for name in ['baseline','learned']:
            v=row[name];content+=f'<div><p>{name}: {v["tp"]} matches, {v["fp"]} extras, {v["fn"]} misses, {v["ignored"]} ignored</p><img src="{i:02d}-{name}.png"></div>'
        content+='</div>'
    content+='<p><a href="result.json">Full predictions, timings and provenance</a> · <a href="../annotations.json">Frozen source annotations and exclusions</a> · <a href="../protocol.json">Protocol</a></p>'
    (output/'index.html').write_text(content)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous comparison output')
    protocol=json.loads((a.input/'protocol.json').read_text());annotations=json.loads((a.input/'annotations.json').read_text())
    a.output.mkdir(parents=True)
    model=StoneDetector(a.checkpoint)
    rows=[]
    for f,annotation in zip(protocol['frames'],annotations['rows']):
        assert f['id']==annotation['frame_id']
        frame=cv2.imread(str(a.input/f['image']));assert frame is not None
        started=time.perf_counter();caps=right_large_cap_proposals(frame);elapsed=time.perf_counter()-started
        baseline=[]
        for colour,items in caps.items():
            for v in items:
                x,y,w,h=v['bbox'];baseline.append({**v,'colour':colour,'bbox_xyxy':[x,y,x+w,y+h]})
        neural=model.detect(frame)
        row={'frame_id':f['id'],'time_s':f['time_s'],'baseline_seconds':elapsed,
             'learned_seconds':neural['wall_seconds'],'upstream_speed_ms':neural['upstream_speed_ms'],
             'baseline':score(baseline,annotation,annotations['evaluation_region_xyxy']),
             'learned':score(neural['detections'],annotation,annotations['evaluation_region_xyxy']),
             'learned_full_frame':neural['detections']}
        rows.append(row)
        for label in ['baseline','learned']:
            image=frame.copy()
            for pred in row[label]['predictions']:
                x1,y1,x2,y2=map(round,pred['bbox_xyxy']);cv2.rectangle(image,(x1,y1),(x2,y2),(0,180,255),1)
            cv2.imwrite(str(a.output/f"{f['id']:02d}-{label}.png"),image)
        (a.output/'progress.json').write_text(json.dumps(rows,indent=2))
    summary={}
    for label in ['baseline','learned']:
        total={k:sum(row[label][k] for row in rows) for k in ['tp','fp','fn','ignored']}
        total.update(precision=total['tp']/(total['tp']+total['fp']) if total['tp']+total['fp'] else None,
                     recall=total['tp']/(total['tp']+total['fn']) if total['tp']+total['fn'] else None)
        times=[row[label+'_seconds'] for row in rows]
        total.update(first_frame_seconds=times[0],median_remaining_frame_seconds=float(np.median(times[1:])))
        summary[label]=total
    result={'scope':'Development sampled visible-object hit comparison; not full-match/event/identity/geometry accuracy',
            'annotation_provenance':{k:v for k,v in annotations.items() if k!='rows'},
            'provenance':model.provenance,'protocol':protocol,'summary':summary,'rows':rows,
            'confidence_operating_point':.25,'operating_point_basis':'Unchanged upstream predict default; not fitted on these annotations',
            'annotations_sha256':hashlib.sha256((a.input/'annotations.json').read_bytes()).hexdigest()}
    (a.output/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    render_report(result,a.output)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
