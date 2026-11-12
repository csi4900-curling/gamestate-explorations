"""Infer a crossing track's role from observed motion relative to its local house.

Camera panels identify views, not permanent departure/receiving roles. This is
geometric interpretation of an observed track, not learned re-identification or
proof that the motion is a delivery. No end-number parity or match IDs are used.
"""
import math


def crossing_role(before, after):
    """Two observations use local metres with the house tee at longitudinal zero."""
    result={'role':'unassigned','status':'unresolved','physical_identity_verified':False,
            'basis':'Change in absolute longitudinal distance from the local house tee',
            'learned_role_classifier':False}
    if before is None or after is None:
        return {**result,'reason':'missing_observation'}
    if before.get('panel') != after.get('panel') or before.get('panel') not in ('left','right'):
        return {**result,'reason':'observations_not_in_same_panel'}
    if before.get('track_id') is None or before.get('track_id') != after.get('track_id'):
        return {**result,'reason':'tracker_label_not_continuous'}
    if not after['time_s']>before['time_s']:
        raise ValueError('Role evidence must have increasing source time')
    a,b=before.get('local_m'),after.get('local_m')
    if a is None or b is None or len(a)!=2 or len(b)!=2 or not all(math.isfinite(v) for v in [*a,*b]):
        return {**result,'reason':'missing_or_undefined_geometry'}
    if a[1]*b[1]<=0:
        return {**result,'status':'ambiguous','reason':'motion_crosses_house_tee_or_touches_zero'}
    delta=abs(b[1])-abs(a[1])
    if delta==0:
        return {**result,'status':'ambiguous','reason':'no_observed_longitudinal_distance_change'}
    return {**result,'role':'departure' if delta>0 else 'receiving',
            'status':'observed_motion_role_hypothesis','panel':before['panel'],
            'distance_change_m':delta,'interval_s':[before['time_s'],after['time_s']],
            'evidence':[before,after],
            'limitations':'Depends on tracker continuity and geometry; clearing, rebounds and replay are not classified as live throws by this rule.'}


def role_for_event(event, board_rows, source_width):
    """Join the event's exact observed bracket to saved board measurements."""
    evidence=[]
    rows={row['time_s']:row for row in board_rows}
    for observation in event['observations']:
        row=rows.get(observation['time_s'])
        panel='left' if observation['pixel'][0]<source_width/2 else 'right'
        stones=[] if row is None else [s for s in row['boards'][panel]['stones']
            if s['tracker_id']==event['track_id'] and s['pixel']==observation['pixel']]
        evidence.append({'time_s':observation['time_s'],'panel':panel,'track_id':event['track_id'],
            'local_m':stones[0]['height_adjusted_local_m'] if len(stones)==1 else None})
    if len(evidence)!=2:raise ValueError('A crossing requires two bracketing observations')
    return crossing_role(*evidence)
