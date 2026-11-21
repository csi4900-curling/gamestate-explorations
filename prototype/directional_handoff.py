"""Bidirectional temporal handoff hypotheses from observed local geometry.

Uses the existing finite-line crossing implementation. Signed hog coordinates
are part of the calibrated coordinate convention, not inferred end parity.
Temporal uniqueness is not physical identity; all competing crossings survive.
"""
from prototype.line_crossing_events import LineCrossings


def metric_crossings(rows, *, hog_y_by_panel, sheet_half_width_m=2.375, max_geometry_gap_s=1.5):
    if set(hog_y_by_panel)!={'left','right'} or any(not y for y in hog_y_by_panel.values()):
        raise ValueError('Explicit signed hog coordinates are required for both panels')
    engines={}
    last_mapped={panel:{} for panel in hog_y_by_panel}
    for panel in hog_y_by_panel:
        engines[panel]=LineCrossings({'schema_version':'stone-line-events-v1','sample_hz':1,
            'detector_confidence':0,'tracker_config':'upstream_already_applied',
            'lines':[{'id':panel+'_hog','endpoints_normalized':[[0,1],[1,1]],
                      'direction':'both','deadband_normalized':0}]})
    result=[]
    for row in rows:
        t = row['time_s']
        for panel,hog_y in hog_y_by_panel.items():
            engine = engines[panel]
            line_id = panel + '_hog'
            active_image_ids = set()
            observations=[]
            for stone in row['boards'][panel]['stones']:
                identity=stone['tracker_id']
                if identity is None:continue
                active_image_ids.add(identity)
                xy=stone['height_adjusted_local_m']
                if xy is None:continue
                observations.append({'track_id':identity,
                    'point_normalized':[(xy[0]+sheet_half_width_m)/(2*sheet_half_width_m),xy[1]/hog_y],
                    'pixel':stone['pixel'],'camera_local_m':xy,'confidence':stone['confidence']})
            # Keep previous mapped positions alive only while the image track stays
            # continuously present across a brief camera-registration gap.
            pmap = last_mapped[panel]
            for tid in list(pmap):
                if tid not in active_image_ids or t - pmap[tid]['time_s'] > max_geometry_gap_s:
                    del pmap[tid]
            # Seed engine.previous for tracks returning after a brief geometry-only gap
            # while continuously tracked in the image.
            bridged_ids = set()
            for obs in observations:
                key = (line_id, obs['track_id'])
                if key not in engine.previous and obs['track_id'] in pmap:
                    engine.previous[key] = pmap[obs['track_id']]
                    bridged_ids.add(obs['track_id'])
            for event in engine.update(observations, t):
                extra = {'geometry_gap_bridged_on_continuous_track': True} if event['track_id'] in bridged_ids else {}
                result.append({**event,'id':'metric:'+panel+':'+event['id'],'panel':panel,
                    'role':'departure' if event['direction']=='positive' else 'receiving',
                    'coordinate_semantics':'Signed camera-local hog-normalized metres; not source pixels',
                    'hog_y_m':hog_y,'physical_identity_verified':False, **extra})
            for obs in observations:
                key = (line_id, obs['track_id'])
                if key in engine.previous:
                    pmap[obs['track_id']] = engine.previous[key]
    return sorted(result,key=lambda e:e['crossing_time_s'])


def resolve_short_receiving_approaches(events, handoffs, rows, *, hog_y_by_panel, sheet_half_width_m=2.375):
    """Link unresolved departures to a unique receiving track stopping short of the far hog line."""
    unresolved = [e for e in events if handoffs[e['id']]['status'] == 'unresolved'
                  and handoffs[e['id']]['role_evidence'].get('role') == 'departure'
                  and handoffs[e['id']].get('interval_s')]
    if not unresolved:
        return []
    tracks = {}
    for row in rows:
        t = row['time_s']
        for panel in hog_y_by_panel:
            for s in row['boards'][panel]['stones']:
                tid = s.get('tracker_id')
                xy = s.get('height_adjusted_local_m')
                if tid is None or xy is None:
                    continue
                tracks.setdefault((panel, tid), []).append((t, xy, s['pixel'], s['confidence']))
    added = []
    for event in unresolved:
        h = handoffs[event['id']]
        dep_panel = h['role_evidence']['panel']
        rec_panel = 'right' if dep_panel == 'left' else 'left'
        hog_y = hog_y_by_panel[rec_panel]
        hog_abs = abs(hog_y)
        start, end = h['interval_s']
        matches = []
        for (panel, tid), pts in tracks.items():
            if panel != rec_panel:
                continue
            in_win = [p for p in pts if start <= p[0] < end]
            if len(in_win) < 5:
                continue
            # Must arrive from far ice beyond the hog line and travel steadily toward the house,
            # coming close to (or stopping just short of) the hog line inside sheet width.
            y_abs = [abs(p[1][1]) for p in in_win]
            x_in = [abs(p[1][0]) for p in in_win]
            if y_abs[0] < hog_abs + 2.0 or min(y_abs) > hog_abs + 1.5:
                continue
            if y_abs[0] - min(y_abs) < 4.0:
                continue
            if min(x_in) > sheet_half_width_m:
                continue
            # Ensure stone was not already sitting near the house before departure.
            earlier = [abs(p[1][1]) for p in pts if p[0] < start]
            if earlier and min(earlier) < hog_abs + 2.0:
                continue
            first_obs, second_obs = in_win[0], in_win[1]
            cand = {
                'id': f'approach:{rec_panel}:{tid}',
                'line_id': rec_panel + '_hog_approach',
                'track_id': tid,
                'crossing_time_s': first_obs[0],
                'observed_bracket_s': [first_obs[0], second_obs[0]],
                'confirmed_at_s': second_obs[0],
                'crossing_point_normalized': [(first_obs[1][0] + sheet_half_width_m) / (2 * sheet_half_width_m), first_obs[1][1] / hog_y],
                'direction': 'negative',
                'time_semantics': 'first_mapped_receiving_approach_short_of_hog',
                'release_time_s': None,
                'point_kind': 'body_box_center',
                'colour': None,
                'physical_identity_verified': False,
                'status': 'receiving_approach_short_of_hog',
                'observations': [
                    {'time_s': first_obs[0], 'track_id': tid, 'pixel': first_obs[2], 'camera_local_m': first_obs[1], 'confidence': first_obs[3]},
                    {'time_s': second_obs[0], 'track_id': tid, 'pixel': second_obs[2], 'camera_local_m': second_obs[1], 'confidence': second_obs[3]},
                ],
                'panel': rec_panel,
                'role': 'receiving',
                'hog_y_m': hog_y,
                'min_abs_y_m': min(y_abs),
                'approach_travel_m': y_abs[0] - min(y_abs),
            }
            matches.append(cand)
        if len(matches) == 1:
            cand = matches[0]
            h.update(
                status='provisional_unique_receiving_approach_short_of_hog',
                candidates=[cand],
                basis='Unique opposite-panel receiving track approaching from far ice and stopping short of the hog line.',
            )
            added.append(cand)
    return added


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


def resolve_colour_ties(events, handoffs, tracks):
    """Resolve only a unique same-colour counterpart with known opposite-colour rivals."""
    for event in events:
        h = handoffs[event['id']]
        candidates = h['candidates']
        if len(candidates) < 2 or h.get('shared_counterpart_candidates'):
            continue
        panel = h['role_evidence']['panel']
        primary = tracks.get(panel, {}).get(str(event['track_id']))
        colours = {c['id']: tracks.get(c['panel'], {}).get(str(c['track_id'])) for c in candidates}
        h['colour_evidence'] = {'primary': primary, 'counterparts': colours}
        if any(colour not in ('red', 'yellow') for colour in [primary, *colours.values()]):
            continue
        matches = [key for key, colour in colours.items() if colour == primary]
        if len(matches) == 1:
            h.update(status='provisional_unique_colour_match', selected_counterpart_id=matches[0],
                     basis='One temporal counterpart agrees with the primary track colour and every rival has the opposite colour. Colours require unanimous sampled crop predictions.')
