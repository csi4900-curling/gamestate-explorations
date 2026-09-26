"""Evaluation helpers: fixed image-space matching, uncensored metric discrepancies."""
import numpy as np
from scipy.optimize import linear_sum_assignment

def match_observations(predictions,references):
    """Maximise valid one-to-one matches, then minimise normalized pixel distances.

    Gate belongs to the frozen image annotation, never the predicted metric position.
    Dummy assignments allow misses. Large metric errors cannot be gated out here.
    """
    if not predictions or not references:return [],list(range(len(predictions))),list(range(len(references)))
    costs=np.full((len(references),len(predictions)+len(references)),1e6,float)
    for j,r in enumerate(references):
        costs[j,len(predictions):]=1000.
        for i,p in enumerate(predictions):
            d=float(np.linalg.norm(np.array(p['pixel_center'])-r['pixel']))
            if p['colour']==r['colour'] and d<=r['matching_radius_px']:costs[j,i]=d/r['matching_radius_px']
    rows,cols=linear_sum_assignment(costs);pairs=[];usedp=set();usedr=set()
    for j,i in zip(rows,cols):
        if i<len(predictions) and costs[j,i]<1000:
            pairs.append((i,j));usedp.add(i);usedr.add(j)
    return pairs,[i for i in range(len(predictions)) if i not in usedp],[j for j in range(len(references)) if j not in usedr]

def position_statistics(errors_cm):
    a=np.asarray(errors_cm,float)
    if not len(a):return {'n':0,'median_cm':None,'rmse_cm':None,'p95_cm':None,'max_cm':None}
    if not np.isfinite(a).all():raise ValueError('Non-finite position errors')
    return {'n':len(a),'median_cm':float(np.median(a)),'rmse_cm':float(np.sqrt(np.mean(a*a))),
            'p95_cm':float(np.percentile(a,95)),'max_cm':float(a.max())}
