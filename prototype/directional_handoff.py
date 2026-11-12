"""Bidirectional temporal handoff hypotheses from observed local geometry.

Uses the existing finite-line crossing implementation. Signed hog coordinates
are part of the calibrated coordinate convention, not inferred end parity.
Temporal uniqueness is not physical identity; all competing crossings survive.
"""
from prototype.line_crossing_events import LineCrossings


def metric_crossings(rows, *, hog_y_by_panel, sheet_half_width_m=2.375):
    if set(hog_y_by_panel)!={'left','right'} or any(not y for y in hog_y_by_panel.values()):
        raise ValueError('Explicit signed hog coordinates are required for both panels')
    engines={}
    for panel in hog_y_by_panel:
        engines[panel]=LineCrossings({'schema_version':'stone-line-events-v1','sample_hz':1,
            'detector_confidence':0,'tracker_config':'upstream_already_applied',
            'lines':[{'id':panel+'_hog','endpoints_normalized':[[0,1],[1,1]],
                      'direction':'both','deadband_normalized':0}]})
    result=[]
    for row in rows:
        for panel,hog_y in hog_y_by_panel.items():
            observations=[]
            for stone in row['boards'][panel]['stones']:
                xy=stone['height_adjusted_local_m'];identity=stone['tracker_id']
                if xy is None or identity is None:continue
                observations.append({'track_id':identity,
                    'point_normalized':[(xy[0]+sheet_half_width_m)/(2*sheet_half_width_m),xy[1]/hog_y],
                    'pixel':stone['pixel'],'camera_local_m':xy,'confidence':stone['confidence']})
            for event in engines[panel].update(observations,row['time_s']):
                result.append({**event,'id':'metric:'+panel+':'+event['id'],'panel':panel,
                    'role':'departure' if event['direction']=='positive' else 'receiving',
                    'coordinate_semantics':'Signed camera-local hog-normalized metres; not source pixels',
                    'hog_y_m':hog_y,'physical_identity_verified':False})
    return sorted(result,key=lambda e:e['crossing_time_s'])


def hypotheses(events, roles, crossings, source_interval):
    ordered=sorted(events,key=lambda e:e['crossing_time_s']);result={}
    for i,event in enumerate(ordered):
        evidence=roles[event['id']];role=evidence['role'];panel=evidence.get('panel')
        common={'role_evidence':evidence,'physical_identity_verified':False,
                'basis':'Temporal candidate association using observed motion roles; not learned re-identification'}
        if role not in ('departure','receiving') or panel not in ('left','right'):
            result[event['id']]={**common,'status':'unresolved','candidates':[],
                                 'reason':'primary_motion_role_unresolved','interval_s':None}
            continue
        t=event['crossing_time_s']
        if role=='departure':
            start=t;end=ordered[i+1]['crossing_time_s'] if i+1<len(ordered) else source_interval[1]
            target='receiving';candidates=[c for c in crossings if start<=c['crossing_time_s']<end]
        else:
            start=ordered[i-1]['crossing_time_s'] if i else source_interval[0];end=t
            target='departure';candidates=[c for c in crossings if start<c['crossing_time_s']<=end]
        candidates=[c for c in candidates if c['panel']!=panel and c['role']==target]
        result[event['id']]={**common,'interval_s':[start,end],'candidate_role':target,
            'candidates':candidates,'status':'provisional_unique_temporal_hog_crossing' if len(candidates)==1
            else 'ambiguous' if candidates else 'unresolved'}
    # A counterpart shared by primary events must not be called a unique link.
    users={}
    for key,h in result.items():
        for c in h['candidates']:users.setdefault(c['id'],[]).append(key)
    for key,h in result.items():
        conflicts={c['id']:users[c['id']] for c in h['candidates'] if len(users[c['id']])>1}
        if conflicts:h.update(status='ambiguous',shared_counterpart_candidates=conflicts)
    return result
