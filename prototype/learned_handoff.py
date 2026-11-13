"""Development handoff hypothesis: a unique incoming hog crossing in event order.

Reuses the line-crossing implementation on height-adjusted camera-local positions.
This is programmed temporal association, not a learned re-identification model.
It adds no pixel-distance, speed, colour or fixed-time-window gate. Wrong event
boundaries, geometry, clearing/replays and fragmented IDs can still produce errors.
"""
from prototype.line_crossing_events import LineCrossings
from prototype.cross_view import HOG_FROM_TEE_M
from itertools import chain


def receiving_crossings(rows,*,panel='right',sheet_half_width_m=2.375):
    if panel not in ('left','right') or sheet_half_width_m<=0:raise ValueError('Invalid receiving geometry configuration')
    iterator=iter(rows);first=next(iterator,None);second=next(iterator,None)
    if first is None or second is None:return []
    if second['time_s']<=first['time_s']:raise ValueError('Handoff observations must be chronological')
    config={'schema_version':'stone-line-events-v1','sample_hz':1/(second['time_s']-first['time_s']),'detector_confidence':0,
            'tracker_config':'upstream_already_applied','lines':[{'id':'receiving_hog','endpoints_normalized':[[0,1],[1,1]],'direction':'negative','deadband_normalized':0}]}
    crossings=LineCrossings(config)
    for row in chain((first,second),iterator):
        observations=[]
        for stone in row['boards'][panel]['stones']:
            xy=stone['height_adjusted_local_m'];identity=stone['tracker_id']
            if xy is None or identity is None:continue
            observations.append({'track_id':identity,'point_normalized':[(xy[0]+sheet_half_width_m)/(2*sheet_half_width_m),xy[1]/HOG_FROM_TEE_M],
                                 'pixel':stone['pixel'],'camera_local_m':xy,'confidence':stone['confidence']})
        crossings.update(observations,row['time_s'])
    return [{**e,'coordinate_semantics':'Normalized camera-local metres, not normalized image coordinates',
             'normalization':{'x_origin_m':-sheet_half_width_m,'x_span_m':2*sheet_half_width_m,'y_scale_m':HOG_FROM_TEE_M},
             'physical_identity_verified':False} for e in crossings.events]


def temporal_candidates(events,incoming,source_end_s):
    ordered=sorted(events,key=lambda e:e['crossing_time_s']);result={}
    for i,event in enumerate(ordered):
        start=event['crossing_time_s'];end=ordered[i+1]['crossing_time_s'] if i+1<len(ordered) else source_end_s
        candidates=[e for e in incoming if start<=e['crossing_time_s']<end]
        result[event['id']]={'interval_s':[start,end],'candidates':candidates,
                            'status':'provisional_unique_temporal_hog_crossing' if len(candidates)==1 else 'ambiguous' if candidates else 'unresolved',
                            'physical_identity_verified':False,
                            'basis':'Unique incoming metric hog-line crossing between consecutive configured departure-line candidates. No colour identity or common-rink lateral compatibility is established.'}
    return result
