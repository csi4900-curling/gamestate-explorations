"""Connect learned event observations to the existing typed CoTracker interface.

The default preserves the primary crossing track. The explicit development
handoff option attaches incoming metric hog-crossing hypotheses in event order.
Links remain provisional: no colour identity or physical identity is asserted.
"""
import json
from itertools import zip_longest
from pathlib import Path
from prototype.detection_cache import digest


def make_segment(segment_id,track_id,panel,points,foreign,roles,sample_step_frames,sample_step_s=None):
    geometry=[{'time_s':s['time_s'],'pixel':s['pixel'],
               'top_view_m':s['stone']['ice_plane_local_m'],
               'conditional_height_adjusted_position_m':s['stone']['height_adjusted_local_m'],
               'homography_source_pixels_to_local_metres':s['geometry']['homography_normalized_pixels_to_local_metres'],
               'status':s['geometry']['registration']['status'],'calibration':s['geometry']['registration'],
               'body_point_support':s['stone'].get('body_point_support'),
               'localization':s['stone'].get('height_correction'),
               'rink_position_m':None} for s in points]
    pixel_points=[{k:s[k] for k in ('time_s','frame_index','pixel','confidence')} for s in points]
    segment={'segment_id':segment_id,'camera':panel+'_split','role':roles.get(panel,'unassigned'),'colour':None,
             'point_kind':'body_box_center','pixel_points':pixel_points,'geometry_samples':geometry,
             'associated':False,'physical_identity_verified':False,'camera_cut_times_s':[],
             'tracker_id':track_id,'point_coordinate_system':'normalized full-source 640x360',
             'sample_step_s':sample_step_s,
             'detection_gaps':[{'after_s':a['time_s'],'before_s':b['time_s']} for a,b in zip(points,points[1:]) if b['frame_index']-a['frame_index']>sample_step_frames],
             'foreign_panel_observations':foreign,
             'role_status':'Configured broadcast camera role, not physical-end identity' if panel in roles else 'Unassigned camera role; physical throwing end unverified'}
    return segment


def assemble(events,observations,boards,source_size,*,camera_roles=None,incoming_crossings=None):
    width,height=source_size
    sample_step_s=events['sample_step_frames']/events['source_fps'] if events.get('source_fps') else None
    roles=camera_roles or {}
    if set(roles)-{'left','right'} or any(v not in ('departure','receiving','unassigned') for v in roles.values()):
        raise ValueError('Invalid configured camera roles')
    handoffs=None
    if incoming_crossings is not None:
        from prototype.learned_handoff import temporal_candidates
        if list(roles.values()).count('receiving')!=1 or list(roles.values()).count('departure')!=1:
            raise ValueError('Handoff development requires explicit departure/receiving camera roles')
        handoffs=temporal_candidates(events['events'],incoming_crossings,events['source_interval_s'][1])
    wanted={e['track_id'] for e in events['events']}|{e['track_id'] for e in (incoming_crossings or [])};samples={k:[] for k in wanted}
    for raw,state in zip_longest(observations,boards):
        if raw is None or state is None or raw['frame_index']!=state['frame_index'] or raw['time_s']!=state['time_s']:
            raise ValueError('Detector/board streams do not share source frames')
        for obs in raw['tracked_observations']:
            key=obs['track_id']
            if key not in wanted:continue
            panel='left' if obs['point_normalized'][0]<.5 else 'right'
            board=state['boards'][panel]
            matching=[s for s in board['stones'] if s['tracker_id']==key and s['pixel']==obs['pixel']]
            if len(matching)!=1:raise ValueError('Tracker observation has no unique matching board observation')
            stone=matching[0]
            samples[key].append({'time_s':raw['time_s'],'frame_index':raw['frame_index'],'panel':panel,
                                'pixel':[obs['pixel'][0]*640/width,obs['pixel'][1]*360/height],
                                'confidence':obs['confidence'],'geometry':board,'stone':stone})
    result=[]
    for e in events['events']:
        panel='left' if e['crossing_point_normalized'][0]<.5 else 'right'
        points=[s for s in samples[e['track_id']] if s['panel']==panel]
        foreign=sum(s['panel']!=panel for s in samples[e['track_id']])
        segment=make_segment(e['id']+':primary',e['track_id'],panel,points,foreign,roles,events['sample_step_frames'],sample_step_s)
        pixel_points=segment['pixel_points']
        result.append({'candidate_id':e['id'],'event_prediction':{**e,'observed_track_points':pixel_points},
                       'segments':[segment],'cross_view_links':[],
                       'failure_reasons':['cross_view_identity_unresolved']+(['tracker_label_observed_in_both_panels'] if foreign else []),
                       'other_camera_evidence':'Retained in match-observations.jsonl, not assigned to this stone'})
        if handoffs is not None and roles.get(panel)=='departure':
            event=result[-1];hypothesis=handoffs[e['id']];event['handoff_hypothesis']=hypothesis
            event['association_method']=hypothesis['basis'];event['association_issues']=[]
            receiving=next(k for k,v in roles.items() if v=='receiving')
            start,end=hypothesis['interval_s']
            for incoming in hypothesis['candidates']:
                key=incoming['track_id'];pp=[s for s in samples[key] if s['panel']==receiving and start<=s['time_s']<end]
                receiver=make_segment(e['id']+':receiving:'+str(key),key,receiving,pp,0,roles,events['sample_step_frames'],sample_step_s)
                receiver['hog_crossing_evidence']=incoming;event['segments'].append(receiver)
                if len(hypothesis['candidates'])==1 and points and pp:
                    event['cross_view_links'].append({'departure_segment':segment['segment_id'],'receiving_segment':receiver['segment_id'],
                        'identity_status':hypothesis['status'],'physical_identity_verified':False,'interpolated':False,
                        'gap_s':max(0,pp[0]['time_s']-points[-1]['time_s'])})
                    segment['associated']=True;receiver['associated']=True
                    event['failure_reasons']=['cross_view_identity_provisional']
            if len(hypothesis['candidates'])>1:event['association_issues'].append('multiple_incoming_hog_crossings')
    return {'schema_version':'learned-primary-track-bridge-v1','source_interval_s':events['source_interval_s'],
            'context':{'source_sha256':events['source_sha256']},'events':result,
            'scope':'Typed primary crossing tracks for dense tracking integration; not complete two-view trajectories or physical identity',
            'physical_identity_verified':False,'handoff_development_enabled':handoffs is not None}


def build(video,run_dir,output,*,camera_roles=None,receiving_hog_association=False):
    import cv2
    run_dir=Path(run_dir);output=Path(output)
    if output.exists():raise ValueError('Preserve previous aggregate')
    events=json.loads((run_dir/'events.json').read_text())
    if events['source_sha256']!=digest(video):raise ValueError('Event/video source mismatch')
    cap=cv2.VideoCapture(str(video));size=[cap.get(cv2.CAP_PROP_FRAME_WIDTH),cap.get(cv2.CAP_PROP_FRAME_HEIGHT)];cap.release()
    if not all(v>0 for v in size):raise ValueError('Invalid source dimensions')
    raw_path=run_dir/'observations.jsonl';board_path=run_dir/'match-observations.jsonl'
    incoming=None
    if receiving_hog_association:
        from prototype.learned_handoff import receiving_crossings
        panels=[k for k,v in (camera_roles or {}).items() if v=='receiving']
        if len(panels)!=1:raise ValueError('Configure a single receiving camera role')
        with board_path.open() as boards:incoming=receiving_crossings((json.loads(l) for l in boards),panel=panels[0])
    with raw_path.open() as raw,board_path.open() as boards:
        result=assemble(events,(json.loads(l) for l in raw),(json.loads(l) for l in boards),size,camera_roles=camera_roles,incoming_crossings=incoming)
    result['provenance']={'events_sha256':digest(run_dir/'events.json'),'observations_sha256':digest(raw_path),
                          'board_observations_sha256':digest(board_path),'bridge_code_sha256':digest(__file__),
                          'configured_camera_roles':camera_roles or {}}
    result['provenance']['match_observation_run']=str(run_dir.resolve())
    if receiving_hog_association:
        result['provenance']['handoff_code_sha256']=digest(Path(__file__).with_name('learned_handoff.py'))
        result['scope']='Development typed two-view tracks with explicit temporal handoff hypotheses; physical identity and metric accuracy remain unverified'
        result['schema_version']='learned-event-track-bridge-v2'
    snapshot=output.with_suffix('.code');snapshot.mkdir()
    for name in ('learned_event_aggregate.py','learned_handoff.py','line_crossing_events.py','cross_view.py'):
        (snapshot/name).write_bytes(Path(__file__).with_name(name).read_bytes())
    output.write_text(json.dumps(result,indent=2,allow_nan=False));return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video',required=True);p.add_argument('--run-dir',required=True);p.add_argument('--output',required=True)
    p.add_argument('--left-role',choices=['departure','receiving','unassigned'],default='unassigned')
    p.add_argument('--right-role',choices=['departure','receiving','unassigned'],default='unassigned')
    p.add_argument('--receiving-hog-association',action='store_true',help='Explicit development temporal association; not verified re-identification')
    a=p.parse_args();build(a.video,a.run_dir,a.output,camera_roles={'left':a.left_role,'right':a.right_role},receiving_hog_association=a.receiving_hog_association)
