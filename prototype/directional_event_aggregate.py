"""Development bridge with per-event motion roles and bidirectional hypotheses.

Reuses the existing learned aggregate's observation joining and typed segments.
Does not modify detections, fit geometry, tune a match or assert physical identity.
"""
from bisect import bisect_left, bisect_right
from collections import Counter
import copy
import json
from pathlib import Path
import numpy as np
from prototype.body_localization import BODY_CENTRE_HEIGHT_M, conditional_camera, height_correct, project
from prototype.detection_cache import digest
from prototype.learned_event_aggregate import assemble
from prototype.camera_motion_role import ROLE_LOOKAROUND_S, recover_missing_role, role_for_event
from prototype.directional_handoff import (
    hypotheses,
    metric_crossings,
    resolve_colour_ties,
    resolve_post_hog_departures,
    resolve_short_receiving_approaches,
)


def _cached_camera_prior(H_np, region, cache_key, camera_cache):
    if cache_key in camera_cache:
        return camera_cache[cache_key]
    try:
        camera, diagnostic = conditional_camera(H_np, region)
        if camera is None:
            camera_cache[cache_key] = None
            return None
    except (ValueError, np.linalg.LinAlgError, FloatingPointError):
        camera_cache[cache_key] = None
        return None
    prior = {'camera': camera, 'diagnostic': diagnostic}
    camera_cache[cache_key] = prior
    return prior


def _build_registered_index(row_iter):
    entries = {'left': [], 'right': []}
    for row in row_iter:
        t = row['time_s']
        boards = row.get('boards') or {}
        for panel in ('left', 'right'):
            board = boards.get(panel) or {}
            H = board.get('homography_normalized_pixels_to_local_metres')
            if H is not None:
                cal_id = (board.get('registration') or {}).get('calibration_id')
                entries[panel].append((t, np.asarray(H, dtype=float), cal_id))
    return {
        panel: {'times': [e[0] for e in panel_entries], 'entries': panel_entries}
        for panel, panel_entries in entries.items()
    }


def _backfill_row(row, index, source_size_px, *, max_gap_s=15.0, camera_cache=None):
    width, height = source_size_px
    t = row['time_s']
    cache = camera_cache if camera_cache is not None else {}
    boards = row.get('boards') or {}
    for panel in ('left', 'right'):
        board = boards.get(panel)
        if not board or board.get('homography_normalized_pixels_to_local_metres') is not None:
            continue
        reg = board.get('registration') or {}
        if reg.get('status') not in ('geometry_skipped_inactive_interval', 'alignment_unverified'):
            continue
        panel_index = index[panel]
        times = panel_index['times']
        if not times:
            continue
        entries = panel_index['entries']
        pos = bisect_left(times, t)
        prev_entry = entries[pos - 1] if pos > 0 else None
        next_entry = entries[pos] if pos < len(entries) else None
        if (
            prev_entry is not None and next_entry is not None
            and prev_entry[2] is not None and next_entry[2] is not None
            and prev_entry[2] != next_entry[2]
        ):
            continue
        best = None
        best_dt = max_gap_s + 1.0
        for cand in (prev_entry, next_entry):
            if cand is None:
                continue
            dt = abs(cand[0] - t)
            if dt <= max_gap_s and dt < best_dt:
                best_dt = dt
                best = cand
        if best is None:
            continue
        nearest_t, H_np, _cal_id = best
        board['homography_normalized_pixels_to_local_metres'] = H_np.tolist()
        board['registration'] = {**reg, 'backfilled_from_time_s': nearest_t}
        region = (0, 0, 320, 360) if panel == 'left' else (320, 0, 640, 360)
        prior = _cached_camera_prior(H_np, region, (panel, nearest_t), cache)
        if prior is None:
            continue
        for stone in board.get('stones', []):
            if stone.get('height_adjusted_local_m') is not None:
                continue
            if not (stone.get('body_point_support') or {}).get('centre_supported'):
                continue
            px = np.asarray(
                [stone['pixel'][0] * 640.0 / width, stone['pixel'][1] * 360.0 / height],
                dtype=float,
            )
            try:
                raw = project(H_np, [px])[0]
                q = height_correct(prior['camera'], px, BODY_CENTRE_HEIGHT_M)
            except (ValueError, np.linalg.LinAlgError, FloatingPointError):
                continue
            if q is not None and np.isfinite(q).all():
                raw_list = raw.tolist() if raw is not None and np.isfinite(raw).all() else None
                stone['ice_plane_local_m'] = raw_list
                stone['height_adjusted_local_m'] = q.tolist()
                stone['height_correction'] = {
                    'status': 'conditional_height_corrected',
                    'height_m': BODY_CENTRE_HEIGHT_M,
                    'uncorrected_position_m': raw_list,
                    'camera': prior['diagnostic'],
                    'backfilled_from_nearest_registered_frame_s': nearest_t,
                }
    return row


def backfill_stationary_panel_geometry(rows, source_size_px, *, max_gap_s=15.0):
    """Project skipped/unverified stationary-panel detections using the nearest verified homography."""
    rows = list(rows)
    index = _build_registered_index(rows)
    camera_cache = {}
    for row in rows:
        _backfill_row(row, index, source_size_px, max_gap_s=max_gap_s, camera_cache=camera_cache)
    return rows


def trim_far_field_overlap(departure, receiving, sample_step_frames):
    """Trim redundant far-field extrapolation tails once the opposite camera observes near-field motion."""
    dep_mapped = [
        g for g in departure.get('geometry_samples', [])
        if g.get('conditional_height_adjusted_position_m') is not None
    ]
    rec_mapped = [
        g for g in receiving.get('geometry_samples', [])
        if g.get('conditional_height_adjusted_position_m') is not None
    ]
    if not dep_mapped or not rec_mapped or dep_mapped[-1]['time_s'] <= rec_mapped[0]['time_s']:
        return departure, receiving

    dep_near = [
        g['time_s'] for g in dep_mapped
        if abs(g['conditional_height_adjusted_position_m'][1]) <= 17.5
    ]
    if dep_near and receiving.get('pixel_points'):
        cutoff_rec = dep_near[-1] - 0.2
        rec_keep = [
            g for g in rec_mapped
            if not (
                abs(g['conditional_height_adjusted_position_m'][1]) > 18.0
                and g['time_s'] < cutoff_rec
            )
        ]
        if len(rec_keep) >= 5 and len(rec_keep) < len(rec_mapped):
            receiving = clip_segment(
                receiving,
                [rec_keep[0]['time_s'], receiving['pixel_points'][-1]['time_s']],
                sample_step_frames,
            )

    rec_near = [
        g for g in receiving.get('geometry_samples', [])
        if g.get('conditional_height_adjusted_position_m') is not None
        and abs(g['conditional_height_adjusted_position_m'][1]) <= 18.5
    ]
    if rec_near and departure.get('pixel_points'):
        t_hand = rec_near[0]['time_s']
        y_hand_dep = 34.747 - abs(rec_near[0]['conditional_height_adjusted_position_m'][1])
        y_lim = max(17.5, y_hand_dep + 0.5)
        dep_keep = [
            g for g in dep_mapped
            if not (
                g['time_s'] > t_hand + 0.4
                and abs(g['conditional_height_adjusted_position_m'][1]) > y_lim
            )
        ]
        if len(dep_keep) >= 5 and len(dep_keep) < len(dep_mapped):
            departure = clip_segment(
                departure,
                [departure['pixel_points'][0]['time_s'], dep_keep[-1]['time_s']],
                sample_step_frames,
            )

    return departure, receiving


def clip_segment(segment, interval, sample_step):
    segment=copy.deepcopy(segment);start,end=interval
    segment['pixel_points']=[p for p in segment['pixel_points'] if start<=p['time_s']<=end]
    segment['geometry_samples']=[p for p in segment['geometry_samples'] if start<=p['time_s']<=end]
    points=segment['pixel_points']
    segment['detection_gaps']=[{'after_s':a['time_s'],'before_s':b['time_s']}
        for a,b in zip(points,points[1:]) if b['frame_index']-a['frame_index']>sample_step]
    return segment


def retain_camera_crossings(crossings, events, hypotheses, output_events):
    """Retain observations that the primary event line cannot uniquely explain.

    This records the existing hypotheses; it adds no association or suppression
    rule and never turns an unmatched receiving observation into a known throw.
    """
    result=[]
    for crossing in crossings:
        primary=[e['id'] for e in events if e['track_id']==crossing['track_id'] and
                 ('left' if e['crossing_point_normalized'][0]<.5 else 'right')==crossing['panel']]
        candidates=[key for key,h in hypotheses.items() if any(c['id']==crossing['id'] for c in h['candidates'])]
        linked=[e['candidate_id'] for e in output_events if e.get('cross_view_links') and
                e['candidate_id'] in candidates and
                hypotheses[e['candidate_id']].get('selected_counterpart_id', crossing['id']) == crossing['id']]
        result.append({**crossing,'primary_track_event_ids':primary,'candidate_event_ids':candidates,
                       'provisional_link_event_ids':linked,
                       'association_status':'primary_track_observation' if primary else
                          'provisional_unique_colour_match' if len(linked)==1 and hypotheses[linked[0]].get('selected_counterpart_id') else
                          'provisional_unique_temporal_link' if len(linked)==1 else 'unresolved_or_ambiguous',
                       'physical_identity_verified':False,'physical_delivery_verified':False})
    return result


def camera_fragment_events(crossings, by_id):
    """Expose existing tracked observations without inventing an event link."""
    fragments=[]
    for crossing in crossings:
        if crossing['association_status']!='unresolved_or_ambiguous':continue
        fragment=copy.deepcopy(by_id[crossing['id']])
        fragment['observation_only']=True
        fragment['camera_crossing']=crossing
        fragment['failure_reasons'].append('camera_crossing_not_uniquely_assigned_to_event')
        for segment in fragment['segments']:
            segment.update(role=crossing['role'],role_status='observed_metric_hog_motion_role',
                           associated=False,physical_identity_verified=False)
        fragments.append(fragment)
    return fragments


def promote_calibrated_receiving_crossings(primary_events, roles, metric, width, height, *, min_flight_s=3.0, max_flight_s=30.0):
    """Promote calibrated receiving hog crossings missed by a single-panel pixel event line.

    A single manual pixel line on one panel can miss an entire throwing direction
    when players or wheelchairs occlude departures on that camera while the
    opposite calibrated receiving hog line sees every stone cleanly. Because
    both hog lines are explicitly calibrated, unclaimed receiving crossings in
    ``metric`` represent physical arriving throws without per-video tuning.

    Returns ``(promoted_events, updated_roles)`` without mutating ``primary_events``.
    """
    updated_roles = dict(roles)
    ordered_primary = sorted(primary_events, key=lambda e: e['crossing_time_s'])
    rec_crossings = [mc for mc in metric if mc.get('role') == 'receiving']
    claimed = set()

    # Rule 1: already represented on the same panel (same track_id, or same-panel
    # receiving crossing within 2.0 s across a brief pixel-vs-metric offset).
    for mc in rec_crossings:
        for e in ordered_primary:
            ep = updated_roles.get(e['id'], {}).get('panel') or (
                'left' if e['crossing_point_normalized'][0] < 0.5 else 'right'
            )
            if ep != mc['panel']:
                continue
            if (e['track_id'] == mc['track_id'] or
                    (updated_roles.get(e['id'], {}).get('role') == 'receiving' and
                     abs(e['crossing_time_s'] - mc['crossing_time_s']) <= 2.0)):
                claimed.add(mc['id'])
                break

    # Rule 2: already represented by a primary departure on the opposite panel
    # within physical stone flight time [min_flight_s, max_flight_s].
    for e in ordered_primary:
        role_info = updated_roles.get(e['id'], {})
        if role_info.get('role') != 'departure' or role_info.get('panel') not in ('left', 'right'):
            continue
        opp = 'right' if role_info['panel'] == 'left' else 'left'
        cands = [mc for mc in rec_crossings
                 if mc['panel'] == opp and mc['id'] not in claimed
                 and min_flight_s <= mc['crossing_time_s'] - e['crossing_time_s'] <= max_flight_s]
        if cands:
            claimed.add(cands[0]['id'])

    promoted = []
    for mc in rec_crossings:
        if mc['id'] in claimed:
            continue
        pid = f'M{len(promoted) + 1:05d}'
        a, b = mc['observations']
        span = b['time_s'] - a['time_s']
        frac = (mc['crossing_time_s'] - a['time_s']) / span if span > 0 else 0.0
        px = [a['pixel'][i] + frac * (b['pixel'][i] - a['pixel'][i]) for i in range(2)]
        pe = {
            **mc,
            'id': pid,
            'metric_crossing_id': mc['id'],
            'metric_crossing_point_normalized': mc['crossing_point_normalized'],
            'crossing_point_normalized': [px[0] / width, px[1] / height],
            'source': 'calibrated_metric_hog_crossing',
            'physical_identity_verified': False,
        }
        promoted.append(pe)
        updated_roles[pid] = {
            'role': 'receiving',
            'panel': mc['panel'],
            'status': 'calibrated_metric_hog_crossing',
            'hog_y_m': mc['hog_y_m'],
        }
    return promoted, updated_roles


def build(video, run_dir, output, *, hog_y_by_panel, track_colours=None):
    run_dir=Path(run_dir);output=Path(output)
    if output.exists():raise ValueError('Preserve existing aggregate')
    events=json.loads((run_dir/'events.json').read_text())
    if digest(video)!=events['source_sha256']:raise ValueError('Video/event mismatch')
    width,height=events['source_size_px']
    def rows(name):
        with (run_dir/name).open() as stream:
            for line in stream:yield json.loads(line)
    board_index=_build_registered_index(rows('match-observations.jsonl'))
    camera_cache={}
    def backfilled_rows():
        for row in rows('match-observations.jsonl'):
            yield _backfill_row(row,board_index,(width,height),camera_cache=camera_cache)
    wanted_times={o['time_s'] for e in events['events'] for o in e['observations']}
    role_rows=[]
    ordered = sorted(events['events'], key=lambda e:e['crossing_time_s'])
    crossing_times = [e['crossing_time_s'] for e in ordered]
    wanted_tids = {e['track_id'] for e in ordered}
    obs_counts = Counter()
    for raw_obs in rows('observations.jsonl'):
        for obs in raw_obs['tracked_observations']:
            if obs['track_id'] in wanted_tids:
                obs_counts[('left' if obs['point_normalized'][0] < .5 else 'right', obs['track_id'])] += 1
    step_s = events['sample_step_frames'] / events['source_fps'] if events.get('source_fps') else None
    margin = ROLE_LOOKAROUND_S + max((e['observations'][-1]['time_s']-e['observations'][0]['time_s']
                                      for e in ordered), default=0.)
    nearby = {e['id']:[] for e in ordered}
    bracket_pixels = {e['id']:{o['time_s']:o['pixel'] for o in e['observations']} for e in ordered}
    def evidence_rows():
        for row in backfilled_rows():
            if row['time_s'] in wanted_times:role_rows.append(row)
            t = row['time_s']
            for e in ordered[bisect_left(crossing_times,t-margin):bisect_right(crossing_times,t+margin)]:
                panel = 'left' if e['crossing_point_normalized'][0] < .5 else 'right'
                stones = [s for s in row['boards'][panel]['stones'] if s['tracker_id'] == e['track_id']]
                expected = bracket_pixels[e['id']].get(t)
                if len(stones) == 1 and (expected is None or stones[0]['pixel'] == expected):
                    nearby[e['id']].append((t, stones[0]['height_adjusted_local_m']))
            yield row
    metric=metric_crossings(evidence_rows(),hog_y_by_panel=hog_y_by_panel)
    roles={e['id']:role_for_event(e,role_rows,width) for e in events['events']}
    for e in ordered:
        if step_s is None or 'observed_bracket_s' not in e:
            continue
        roles[e['id']] = recover_missing_role(e, nearby[e['id']], step_s, roles[e['id']])
    metric_keys={(c['panel'], c['track_id']) for c in metric}
    active_primary=[];filtered_flickers=[]
    for event in ordered:
        p_panel = roles[event['id']].get('panel') or ('left' if event['crossing_point_normalized'][0] < 0.5 else 'right')
        p_role = roles[event['id']].get('role')
        obs_n = obs_counts.get((p_panel, event['track_id']), 0)
        if obs_n <= 2 and p_role != 'receiving' and (p_panel, event['track_id']) not in metric_keys:
            filtered_flickers.append({
                'event_id': event['id'], 'track_id': event['track_id'], 'panel': p_panel,
                'crossing_time_s': event['crossing_time_s'],
                'pixel_points': obs_n,
                'reason': 'short_pixel_line_flicker_without_metric_hog_or_receiving_observation',
            })
            continue
        active_primary.append(event)
    promoted, roles = promote_calibrated_receiving_crossings(
        active_primary, roles, metric, width, height
    )
    working_events = sorted(active_primary + promoted, key=lambda e: e['crossing_time_s'])
    handoffs=hypotheses(working_events,roles,metric,events['source_interval_s'])
    colour_tracks=None
    if track_colours is not None:
        colours = json.loads(Path(track_colours).read_text())
        if (colours['source_sha256'] != events['source_sha256'] or
                colours['provenance']['observations_sha256'] != digest(run_dir/'match-observations.jsonl')):
            raise ValueError('Track colours belong to a different observation stream')
        colour_tracks = colours['tracks']
        resolve_colour_ties(working_events, handoffs, colour_tracks)
    short_approaches = resolve_short_receiving_approaches(
        working_events, handoffs, backfilled_rows(), hog_y_by_panel=hog_y_by_panel)
    post_hog_deps = resolve_post_hog_departures(
        working_events, handoffs, backfilled_rows(),
        hog_y_by_panel=hog_y_by_panel, track_colours=colour_tracks)
    metric = sorted(metric + short_approaches + post_hog_deps, key=lambda e: e['crossing_time_s'])
    extras=[]
    for crossing in metric:
        a,b=crossing['observations'];fraction=(crossing['crossing_time_s']-a['time_s'])/(b['time_s']-a['time_s'])
        pixel=[a['pixel'][i]+fraction*(b['pixel'][i]-a['pixel'][i]) for i in range(2)]
        extras.append({**crossing,'metric_crossing_point_normalized':crossing['crossing_point_normalized'],
                       'crossing_point_normalized':[pixel[0]/width,pixel[1]/height]})
    raw=assemble({**events,'events':working_events+extras},rows('observations.jsonl'),
                 backfilled_rows(),[width,height])
    by_id={e['candidate_id']:e for e in raw['events']};output_events=[]
    metric_keys={(c['panel'], c['track_id']) for c in metric}
    for event in working_events:
        result=by_id[event['id']];primary=result['segments'][0];role=roles[event['id']];hypothesis=handoffs[event['id']]
        primary.update(role=role['role'],role_status=role['status'],role_evidence=role)
        if event.get('source') == 'calibrated_metric_hog_crossing':
            result['event_source'] = 'calibrated_metric_hog_crossing'
        result.update(handoff_hypothesis=hypothesis,association_method=hypothesis['basis'],association_issues=[])
        for candidate in hypothesis['candidates']:
            if candidate['id'] != hypothesis.get('selected_counterpart_id', candidate['id']):
                continue
            clip_interval = hypothesis['interval_s']
            if candidate['role'] == 'departure' and clip_interval:
                clip_interval = [max(clip_interval[0], candidate['crossing_time_s'] - 15.0), clip_interval[1]]
            other=clip_segment(by_id[candidate['id']]['segments'][0],clip_interval,events['sample_step_frames'])
            other.update(segment_id=event['id']+':'+candidate['role']+':'+str(candidate['track_id']),
                         role=candidate['role'],role_status='observed_metric_hog_crossing_role_hypothesis',
                         hog_crossing_evidence=candidate)
            result['segments'].append(other)
            if hypothesis['status'] in (
                'provisional_unique_temporal_hog_crossing',
                'provisional_unique_colour_match',
                'provisional_unique_receiving_approach_short_of_hog',
                'provisional_unique_post_hog_departure',
            ) and primary['pixel_points'] and other['pixel_points']:
                departure=primary if primary['role']=='departure' else other
                receiving=other if primary['role']=='departure' else primary
                dep_trimmed, rec_trimmed = trim_far_field_overlap(departure, receiving, events['sample_step_frames'])
                if primary['role'] == 'departure':
                    primary.update(dep_trimmed)
                    other.update(rec_trimmed)
                else:
                    other.update(dep_trimmed)
                    primary.update(rec_trimmed)
                result['cross_view_links'].append({'departure_segment':departure['segment_id'],
                    'receiving_segment':receiving['segment_id'],'identity_status':hypothesis['status'],
                    'physical_identity_verified':False,'interpolated':False,
                    'gap_s':max(0,receiving['pixel_points'][0]['time_s']-departure['pixel_points'][-1]['time_s'])})
                primary['associated']=other['associated']=True
                result['failure_reasons']=[x for x in result['failure_reasons'] if x!='cross_view_identity_unresolved']+['cross_view_identity_provisional']
        if hypothesis['status']=='ambiguous':result['association_issues'].append('multiple_or_shared_counterpart_crossings')
        p_panel = role.get('panel') or ('left' if event['crossing_point_normalized'][0] < 0.5 else 'right')
        has_receiving = any(s.get('role') == 'receiving' and s.get('pixel_points') for s in result['segments'])
        has_metric = (p_panel, event['track_id']) in metric_keys
        if (event.get('source') != 'calibrated_metric_hog_crossing'
                and len(primary.get('pixel_points', [])) <= 2
                and not has_receiving and not has_metric):
            filtered_flickers.append({
                'event_id': event['id'], 'track_id': event['track_id'], 'panel': p_panel,
                'crossing_time_s': event['crossing_time_s'],
                'pixel_points': len(primary.get('pixel_points', [])),
                'reason': 'short_pixel_line_flicker_without_metric_hog_or_receiving_observation',
            })
            continue
        output_events.append(result)
    kept_ids={e['candidate_id'] for e in output_events}
    kept_working=[e for e in working_events if e['id'] in kept_ids]
    camera_crossings=retain_camera_crossings(extras,kept_working,handoffs,output_events)
    result={**raw,'schema_version':'learned-directional-event-track-bridge-development-v1','events':output_events,
            'camera_crossings':camera_crossings,
            'unresolved_camera_fragments':camera_fragment_events(camera_crossings,by_id),
            'scope':'Observed motion roles and bidirectional temporal candidates; not verified physical identity',
            'handoff_development_enabled':True,'provenance':{
                'events_sha256':digest(run_dir/'events.json'),'observations_sha256':digest(run_dir/'observations.jsonl'),
                'board_observations_sha256':digest(run_dir/'match-observations.jsonl'),
                'match_observation_run':str(run_dir.resolve()),'local_hog_y_m':hog_y_by_panel,
                'primary_pixel_line_events':len(events['events']),
                'promoted_calibrated_receiving_crossings':len(promoted),
                'filtered_short_unconfirmed_pixel_line_flickers':filtered_flickers}}
    if track_colours is not None:
        result['provenance']['track_colours_sha256'] = digest(track_colours)
    code=output.with_suffix('.code');code.mkdir(parents=True)
    names=['directional_event_aggregate.py','directional_handoff.py','camera_motion_role.py',
           'learned_event_aggregate.py','line_crossing_events.py']
    result['provenance']['code_sha256']={}
    for name in names:
        source=Path(__file__).with_name(name);(code/name).write_bytes(source.read_bytes())
        result['provenance']['code_sha256'][name]=digest(source)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['video','run-dir','output']:p.add_argument('--'+name,required=True)
    p.add_argument('--left-hog-y',type=float,required=True);p.add_argument('--right-hog-y',type=float,required=True)
    a=p.parse_args();build(a.video,a.run_dir,a.output,hog_y_by_panel={'left':a.left_hog_y,'right':a.right_hog_y})
