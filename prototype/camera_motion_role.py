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


# Only infer a direction across the original line crossing. Never fill a missing position.
ROLE_LOOKAROUND_S = 2.0


def recover_missing_role(event, samples, step_s, primary):
    """Use separated longitudinal ranges on a continuous image track straddling the crossing."""
    if primary.get('reason') != 'missing_or_undefined_geometry':
        return primary
    start, stop = event['observed_bracket_s']
    nearby = [(t, point) for t, point in samples
              if start - ROLE_LOOKAROUND_S <= t <= stop + ROLE_LOOKAROUND_S]
    before = [(t, p) for t, p in nearby if t <= start and p is not None]
    after = [(t, p) for t, p in nearby if t >= stop and p is not None]
    if len(before) >= 2 and len(after) >= 2:
        times = [t for t, _ in nearby if before[0][0] <= t <= after[-1][0]]
        if start in times and stop in times and not any(
                not math.isclose(b-a, step_s, abs_tol=1e-6) for a,b in zip(times,times[1:])):
            y = [p[1] for _,p in before + after]
            if all(math.isfinite(v) for v in y) and not (min(y) <= 0 <= max(y)):
                earlier = [abs(p[1]) for _,p in before]
                later = [abs(p[1]) for _,p in after]
                if min(later) > max(earlier):
                    role = 'departure'
                elif max(later) < min(earlier):
                    role = 'receiving'
                else:
                    role = None
                if role is not None:
                    return dict(role=role, panel='left' if event['crossing_point_normalized'][0] < .5 else 'right',
                                track_id=event['track_id'], status='neighbouring_registered_track_observations',
                                basis='Non-overlapping ranges of distance from the tee on either side of the line crossing',
                                original_role_evidence=primary, crossing_bracket_s=[start,stop],
                                before_time_s=[before[0][0],before[-1][0]], after_time_s=[after[0][0],after[-1][0]],
                                before_abs_longitudinal_range_m=[min(earlier),max(earlier)],
                                after_abs_longitudinal_range_m=[min(later),max(later)],
                                mapped_sample_counts=[len(before),len(after)], physical_identity_verified=False,
                                learned_role_classifier=False)
    # Fallback when a brief registration gap covers one side of the crossing line
    # while the same image track remains continuous on the other side.
    mapped = [(t, p) for t, p in nearby if p is not None]
    if len(mapped) < 4 or mapped[-1][0] - mapped[0][0] < 0.4:
        return primary
    span_lo = min(start, mapped[0][0])
    span_hi = max(stop, mapped[-1][0])
    times = [t for t, _ in nearby if span_lo <= t <= span_hi]
    if start not in times or stop not in times or any(
            not math.isclose(b - a, step_s, abs_tol=1e-6) for a, b in zip(times, times[1:])):
        return primary
    y = [p[1] for _, p in mapped]
    if not all(math.isfinite(v) for v in y) or min(y) <= 0 <= max(y):
        return primary
    mid = len(mapped) // 2
    earlier = [abs(p[1]) for _, p in mapped[:mid]]
    later = [abs(p[1]) for _, p in mapped[mid:]]
    if min(later) > max(earlier) and max(later) - min(earlier) >= 0.3:
        role = 'departure'
    elif max(later) < min(earlier) and max(earlier) - min(later) >= 0.3:
        role = 'receiving'
    else:
        return primary
    return dict(role=role, panel='left' if event['crossing_point_normalized'][0] < .5 else 'right',
                track_id=event['track_id'], status='one_sided_registered_track_observations',
                basis='Non-overlapping radial distance halves along a continuous image track adjacent to a registration gap at the crossing',
                original_role_evidence=primary, crossing_bracket_s=[start, stop],
                mapped_time_s=[mapped[0][0], mapped[-1][0]],
                before_abs_longitudinal_range_m=[min(earlier), max(earlier)],
                after_abs_longitudinal_range_m=[min(later), max(later)],
                mapped_sample_counts=[len(earlier), len(later)], physical_identity_verified=False,
                learned_role_classifier=False)
