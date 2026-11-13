"""Exact-frame comparison against explicitly attributed source-point annotations.

Reports image-coordinate residuals only. No correctness cutoff, no interpolation,
no claim of physical identity or metric trajectory accuracy from these residuals.
"""
import math


def evaluate_source_points(result, reference, *, point_index=0):
    if result['provenance']['source_sha256']!=reference['source_sha256']:
        raise ValueError('Reference and prediction sources differ')
    frames=result['frame_indices']
    if len(set(frames))!=len(frames):raise ValueError('Duplicate predicted source frames')
    lookup={f:i for i,f in enumerate(frames)}
    rows=[]
    seen=set()
    for ref in reference['samples']:
        frame=ref['frame_index']
        if frame in seen:raise ValueError('Duplicate reference source frames')
        seen.add(frame)
        target=ref['pixel']
        if len(target)!=2 or not all(math.isfinite(x) for x in target):raise ValueError('Invalid reference point')
        row={'frame_index':frame,'reference_pixel':target,'model_visible':False,'pixel_error':None}
        if frame not in lookup:
            row['status']='no_predicted_frame'
        else:
            i=lookup[frame]
            if not 0<=point_index<len(result['tracks_px'][i]):raise ValueError('Unknown query index')
            visible=bool(result['point_visible'][i][point_index]);row['model_visible']=visible
            row['status']='visible_prediction' if visible else 'model_not_visible'
            if visible:
                point=result['tracks_px'][i][point_index]
                if not all(math.isfinite(x) for x in point):raise ValueError('Nonfinite visible prediction')
                row['predicted_pixel']=point;row['pixel_error']=math.dist(point,target)
        rows.append(row)
    errors=[r['pixel_error'] for r in rows if r['pixel_error'] is not None]
    return {'scope':'Selected source-point residuals, not physical trajectory accuracy',
            'reference_provenance':reference.get('provenance'), 'query_index':point_index,
            'reference_count':len(rows),'visible_prediction_count':len(errors),
            'mean_pixel_error':sum(errors)/len(errors) if errors else None,
            'maximum_pixel_error':max(errors) if errors else None,'samples':rows}
