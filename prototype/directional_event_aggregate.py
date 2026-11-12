"""Development bridge with per-event motion roles and bidirectional hypotheses.

Reuses the existing learned aggregate's observation joining and typed segments.
Does not modify detections, fit geometry, tune a match or assert physical identity.
"""
import copy
import json
from pathlib import Path
from prototype.detection_cache import digest
from prototype.learned_event_aggregate import assemble
from prototype.camera_motion_role import role_for_event
from prototype.directional_handoff import metric_crossings,hypotheses


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
                e['candidate_id'] in candidates]
        result.append({**crossing,'primary_track_event_ids':primary,'candidate_event_ids':candidates,
                       'provisional_link_event_ids':linked,
                       'association_status':'primary_track_observation' if primary else
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


def build(video, run_dir, output, *, hog_y_by_panel):
    run_dir=Path(run_dir);output=Path(output)
    if output.exists():raise ValueError('Preserve existing aggregate')
    events=json.loads((run_dir/'events.json').read_text())
    if digest(video)!=events['source_sha256']:raise ValueError('Video/event mismatch')
    width,height=events['source_size_px']
    def rows(name):
        with (run_dir/name).open() as stream:
            for line in stream:yield json.loads(line)
    wanted_times={o['time_s'] for e in events['events'] for o in e['observations']}
    role_rows=[]
    def evidence_rows():
        for row in rows('match-observations.jsonl'):
            if row['time_s'] in wanted_times:role_rows.append(row)
            yield row
    metric=metric_crossings(evidence_rows(),hog_y_by_panel=hog_y_by_panel)
    roles={e['id']:role_for_event(e,role_rows,width) for e in events['events']}
    handoffs=hypotheses(events['events'],roles,metric,events['source_interval_s'])
    extras=[]
    for crossing in metric:
        a,b=crossing['observations'];fraction=(crossing['crossing_time_s']-a['time_s'])/(b['time_s']-a['time_s'])
        pixel=[a['pixel'][i]+fraction*(b['pixel'][i]-a['pixel'][i]) for i in range(2)]
        extras.append({**crossing,'metric_crossing_point_normalized':crossing['crossing_point_normalized'],
                       'crossing_point_normalized':[pixel[0]/width,pixel[1]/height]})
    raw=assemble({**events,'events':events['events']+extras},rows('observations.jsonl'),
                 rows('match-observations.jsonl'),[width,height])
    by_id={e['candidate_id']:e for e in raw['events']};output_events=[]
    for event in events['events']:
        result=by_id[event['id']];primary=result['segments'][0];role=roles[event['id']];hypothesis=handoffs[event['id']]
        primary.update(role=role['role'],role_status=role['status'],role_evidence=role)
        result.update(handoff_hypothesis=hypothesis,association_method=hypothesis['basis'],association_issues=[])
        for candidate in hypothesis['candidates']:
            other=clip_segment(by_id[candidate['id']]['segments'][0],hypothesis['interval_s'],events['sample_step_frames'])
            other.update(segment_id=event['id']+':'+candidate['role']+':'+str(candidate['track_id']),
                         role=candidate['role'],role_status='observed_metric_hog_crossing_role_hypothesis',
                         hog_crossing_evidence=candidate)
            result['segments'].append(other)
            if hypothesis['status']=='provisional_unique_temporal_hog_crossing' and primary['pixel_points'] and other['pixel_points']:
                departure=primary if primary['role']=='departure' else other
                receiving=other if primary['role']=='departure' else primary
                result['cross_view_links'].append({'departure_segment':departure['segment_id'],
                    'receiving_segment':receiving['segment_id'],'identity_status':hypothesis['status'],
                    'physical_identity_verified':False,'interpolated':False,
                    'gap_s':max(0,receiving['pixel_points'][0]['time_s']-departure['pixel_points'][-1]['time_s'])})
                primary['associated']=other['associated']=True
                result['failure_reasons']=[x for x in result['failure_reasons'] if x!='cross_view_identity_unresolved']+['cross_view_identity_provisional']
        if hypothesis['status']=='ambiguous':result['association_issues'].append('multiple_or_shared_counterpart_crossings')
        output_events.append(result)
    camera_crossings=retain_camera_crossings(extras,events['events'],handoffs,output_events)
    result={**raw,'schema_version':'learned-directional-event-track-bridge-development-v1','events':output_events,
            'camera_crossings':camera_crossings,
            'unresolved_camera_fragments':camera_fragment_events(camera_crossings,by_id),
            'scope':'Observed motion roles and bidirectional temporal candidates; not verified physical identity',
            'handoff_development_enabled':True,'provenance':{
                'events_sha256':digest(run_dir/'events.json'),'observations_sha256':digest(run_dir/'observations.jsonl'),
                'board_observations_sha256':digest(run_dir/'match-observations.jsonl'),
                'match_observation_run':str(run_dir.resolve()),'local_hog_y_m':hog_y_by_panel}}
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
