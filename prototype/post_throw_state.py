"""Post-throw review proposals from saved public-pipeline observations.

This stage replays existing observations; it does not rerun detection/geometry.
Low apparent motion proposes a review frame, never certifies a settled board.
All event candidates, including missing receivers, are retained.
"""
import bisect
import html
import json
import os
from pathlib import Path
import time

import cv2
import numpy as np

from prototype.detection_cache import digest
from prototype.game_board_state import BoardStateEvidence
from prototype.board_timeline import BoardTimeline


def compact_events(path):
    import ijson
    events = []
    with Path(path).open('rb') as stream:
        for event in ijson.items(stream, 'events.item', use_float=True):
            events.append({
                'candidate_id': event['candidate_id'],
                'event_prediction': {'crossing_time_s': event['event_prediction']['crossing_time_s']},
                'colour': event.get('colour'),
                'colour_status': event.get('colour_status'),
                'segments': [dict(role=s['role'], camera=s['camera'],
                                  rink_panel=s.get('rink_panel'), tracker_id=s.get('tracker_id'),
                                  pixel_points=([{'time_s': s['pixel_points'][0]['time_s']}]
                                                if s.get('pixel_points') else []))
                             for s in event.get('segments', [])],
            })
    return sorted(events, key=lambda e: e['event_prediction']['crossing_time_s'])


def propose_frame(event, next_time, motion, step):
    receivers = [s for s in event['segments'] if s['role'] == 'receiving' and s['pixel_points']]
    if len(receivers) != 1:
        return {'status': 'unresolved', 'reason': 'missing_or_ambiguous_receiving_segment'}
    receiver = receivers[0]
    panel = receiver.get('rink_panel') or {'left_split': 'left', 'right_split': 'right'}[receiver['camera']]
    m = motion[panel]
    ids = np.flatnonzero((m['track_id'] == receiver['tracker_id']) &
                        (m['time_s'] >= receiver['pixel_points'][0]['time_s']) &
                        (m['time_s'] < next_time))
    if not len(ids):
        return {'status': 'unresolved', 'reason': 'no_receiving_motion_observations'}
    # A moving observation must precede the proposed stationary interval.
    # A visibility gap splits runs even if the same tracker ID reappears.
    runs = []; current = []; seen_moving = False; previous = None
    for i in ids[np.argsort(m['frame_index'][ids])]:
        contiguous = previous is not None and int(m['frame_index'][i])-previous == step
        if not contiguous:
            if current: runs.append(current)
            current = []; seen_moving = False
        if not m['stationary'][i]:
            if current: runs.append(current)
            current = []; seen_moving = True
        elif seen_moving:
            current.append(int(i))
        previous = int(m['frame_index'][i])
    if current: runs.append(current)
    if not runs:
        return {'status': 'unresolved', 'reason': 'no_observed_moving_to_stationary_transition'}
    # Longest contiguous run, earliest on ties. No per-event duration threshold.
    chosen = max(runs, key=len)
    i = chosen[len(chosen)//2]
    return {'status': 'review_proposal', 'frame_index': int(m['frame_index'][i]),
            'time_s': float(m['time_s'][i]), 'panel': panel,
            'receiving_tracker_id': receiver['tracker_id'],
            'stationary_interval_s': [float(m['time_s'][chosen[0]]), float(m['time_s'][chosen[-1]])],
            'motion_observations': len(chosen),
            'posterior_stationary': float(m['posterior_stationary'][i]),
            'selection': 'Midpoint of longest contiguous low-motion run after visible motion, before next candidate.',
            'limitations': ['Offline model posterior is not calibrated physical settlement confidence.',
                            'Collision, identity switch, camera motion or repositioning may invalidate this proposal.']}


def suppress_duplicates(board, iou):
    """Reuse upstream OpenCV NMS, preserving each suppression for inspection."""
    stones = board['stones']
    boxes = [[s['bbox_xyxy'][0], s['bbox_xyxy'][1],
              s['bbox_xyxy'][2]-s['bbox_xyxy'][0], s['bbox_xyxy'][3]-s['bbox_xyxy'][1]] for s in stones]
    kept = (np.asarray(cv2.dnn.NMSBoxes(boxes, [s['confidence'] for s in stones], 0., iou),
                       dtype=int).reshape(-1).tolist() if stones else [])
    keep = set(kept)
    return {**board, 'stones': [s for i,s in enumerate(stones) if i in keep]}, [
        {'tracker_id': s.get('tracker_id'), 'bbox_xyxy': s['bbox_xyxy'],
         'confidence': s['confidence']} for i,s in enumerate(stones) if i not in keep]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def render(output, video, payload, config, *, video_src=None, base_href=None, write_payload=True):
    """Standalone viewer: decoded source frame, both layouts, evidence and seeking."""
    output = Path(output)
    if write_payload:
        write_json(output/'states.json', payload)
        (output/'states.js').write_text('window.POST_THROW='+json.dumps(payload, allow_nan=False)+';\n')
    video_url = html.escape(video_src if video_src is not None else
                            os.path.relpath(Path(video).resolve(), output.resolve()), quote=True)
    template = '''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Stone observations</title>
<style>body{font:16px system-ui;margin:24px;color:#233746}select,button{font:inherit;padding:8px}
video{width:100%;display:block}.player{position:relative}#source-overlay{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;background:transparent}main{max-width:1440px}.views{display:grid;grid-template-columns:2fr 1fr;gap:16px}
canvas{width:100%;background:#f4f8fa}pre{white-space:pre-wrap;font:13px ui-monospace}
.note{background:#fff5d9;padding:12px}a{color:#175d90}</style><main>
<h1>Stone observations</h1>
<p class="note">Source detections and projected positions follow the video. Positions depend on calibration; missing observations remain gaps. Track IDs are provisional.</p>
<select id="pick" aria-label="Event candidate"></select><button id="seek">Go to crossing</button>
<label>Projection <select id="projection"><option value="height">Height-adjusted</option><option value="plane">Ice plane (no height correction)</option></select></label>
<label>Orientation <select id="orientation"><option value="source">Match source · +Y down</option><option value="math">Coordinate axes · +Y up</option></select></label>
<div class="views"><div><div class="player"><video id="video" controls preload="metadata" src="VIDEO_URL"></video><canvas id="source-overlay"></canvas></div>
<p id="clock"></p><a id="snapshot">Open timestamped source snapshot</a></div><div>
<canvas id="layout" width="600" height="680"></canvas></div></div>
<details><summary>Current observation evidence</summary><pre id="evidence"></pre></details></main><script src="states.js"></script><script>
const data=window.POST_THROW, pick=document.querySelector('#pick'),video=document.querySelector('#video');
const canvas=document.querySelector('#layout'),ctx=canvas.getContext('2d');
const overlay=document.querySelector('#source-overlay'),sourceCtx=overlay.getContext('2d');
const projection=document.querySelector('#projection'),cache=new Map(),loading=new Set();
const orientation=document.querySelector('#orientation');
let presentedTime=null,hasDecodedFrame=false;
for(const r of data.events){const o=document.createElement('option');o.textContent=r.event_id+' · '+r.crossing_time_s.toFixed(2)+' s';o.value=pick.length;pick.append(o)}
function draw(r){ctx.clearRect(0,0,600,680);ctx.font='17px system-ui';window.boardPlotAudit=[];
 const radius=data.dimensions.house_radius_m,scale=112/radius;
 const ySign=orientation.value==='source'?1:-1;
 for(const [j,p] of ['left','right'].entries()){const x=150+300*j,y=330;
 ctx.save();ctx.beginPath();ctx.rect(j*300+3,40,294,570);ctx.clip();
 let outside=0;
 ctx.strokeStyle='#c0d5dd';for(const k of [1,2/3,1/3]){ctx.beginPath();ctx.arc(x,y,radius*k*scale,0,Math.PI*2);ctx.stroke()}
 for(const s of (r.state?.boards[p]?.stones||[])){if(!s.position_m)continue;
 const [sx,sy]=s.position_m;const px=x+sx*scale,py=y+ySign*sy*scale;
 if(px<j*300+3||px>j*300+297||py<40||py>610){outside++;continue}
 ctx.fillStyle=({red:'#c23e40',yellow:'#caa820'})[s.group]||'#777';
 ctx.beginPath();ctx.arc(px,py,data.dimensions.stone_radius_m*scale,0,Math.PI*2);ctx.fill();
 ctx.fillText(String(s.tracker_id??'?'),px+9,py);
 window.boardPlotAudit.push({panel:p,tracker_id:s.tracker_id,position_m:s.position_m,screen_px:[px,py],tee_screen_px:[x,y],y_direction:ySign})}
 ctx.restore();ctx.fillStyle='#233746';ctx.fillText(p+' — local metres',j*300+35,25);
 ctx.font='13px system-ui';ctx.fillText('+X →  '+(ySign===1?'+Y ↓':'+Y ↑'),j*300+12,48);ctx.font='17px system-ui';
 ctx.fillText('Outside display: '+outside,j*300+12,630);
 }
 ctx.fillStyle='#555';ctx.fillText('Grey = colour unavailable. Current observations only.',12,665)}
function clear(message){draw({state:null});sourceCtx.clearRect(0,0,overlay.width,overlay.height);
 document.querySelector('#clock').textContent=message;
 document.querySelector('#evidence').textContent='';window.stateAudit=null;}
function upperBound(times,t){let lo=0,hi=times.length;while(lo<hi){const m=(lo+hi)>>1;if(times[m]<=t+1e-7)lo=m+1;else hi=m}return lo-1}
function renderAt(t){if(t===null||video.seeking)return;
 const index=upperBound(data.timeline.times,t),time=data.timeline.times[index];
 if(index<0||t-time>=data.timeline.sample_step_s+1e-7||t>data.timeline.source_interval_s[1]){clear('No current board observation at '+t.toFixed(3)+' s');return}
 const key=Math.floor(index/data.timeline.chunk_size);
 if(!cache.has(key)){clear('Loading board at '+t.toFixed(3)+' s');
 if(!loading.has(key)){loading.add(key);const s=document.createElement('script');s.src='board-timeline/'+key+'.js';
 s.onerror=()=>{loading.delete(key);clear('Board observations unavailable')};document.body.append(s)}return}
 const row=cache.get(key)[index%data.timeline.chunk_size],boards={};
 for(const [p,b] of Object.entries(row.boards)){boards[p]={stones:b.stones.map(s=>({tracker_id:s[0],pixel:[s[1],s[2]],
 position_m:(projection.value==='height'?[s[3],s[4]]:[s[6],s[7]]),group:s[5]}))};
 boards[p].stones.forEach(s=>{if(s.position_m.some(v=>v===null))s.position_m=null})}
 draw({state:{boards}});sourceCtx.clearRect(0,0,overlay.width,overlay.height);
 sourceCtx.font='18px system-ui';sourceCtx.lineWidth=2;
 for(const b of Object.values(boards))for(const s of b.stones){const [x,y]=s.pixel;
 sourceCtx.strokeStyle=({red:'#ef4444',yellow:'#f7d626'})[s.group]||'#00b6df';sourceCtx.fillStyle=sourceCtx.strokeStyle;
 sourceCtx.beginPath();sourceCtx.arc(x,y,8,0,Math.PI*2);sourceCtx.stroke();sourceCtx.fillText(String(s.tracker_id??'?'),x+11,y-8)}
 document.querySelector('#clock').textContent='Presented video: '+t.toFixed(3)+' s · board: '+row.time_s.toFixed(3)+' s · age '+(t-row.time_s).toFixed(3)+' s. Source circles mark body-box centres; projection is '+projection.value+'.';
 document.querySelector('#evidence').textContent=JSON.stringify({time_s:row.time_s,frame_index:row.frame_index,boards},null,2);
 window.stateAudit={video_time_s:t,source_time:row.time_s,source_frame:row.frame_index,projection:projection.value,orientation:orientation.value,boards};}
window.receiveBoardState=(key,rows)=>{cache.set(key,rows);loading.delete(key);
 while(cache.size>3){const oldest=cache.keys().next().value;if(oldest===key)break;cache.delete(oldest)}renderAt(presentedTime)};
function show(seek=true){const r=data.events[Number(pick.value)];if(!r){if(seek)video.currentTime=data.timeline.source_interval_s[0];return;}
 const a=document.querySelector('#snapshot');a.href=r.snapshot||'#';a.style.display=r.snapshot?'':'none';
 a.textContent='Selected proposal snapshot at '+r.proposal.time_s+' s (static image)';
 if(seek)video.currentTime=r.crossing_time_s}
pick.onchange=()=>show();document.querySelector('#seek').onclick=()=>show();projection.onchange=()=>renderAt(presentedTime);
orientation.onchange=()=>renderAt(presentedTime);
video.addEventListener('seeking',()=>{
 // A paused seek within the already presented frame may produce no new callback.
 const sameFrame=hasDecodedFrame&&presentedTime!==null&&video.currentTime>=presentedTime-1e-7&&video.currentTime<presentedTime+1/data.source_fps+1e-7;
 if(!sameFrame){hasDecodedFrame=false;presentedTime=null;clear('Seeking source video…')}});
video.addEventListener('seeked',()=>{if(hasDecodedFrame)renderAt(presentedTime)});
if(video.requestVideoFrameCallback){const frame=(_,m)=>{presentedTime=m.mediaTime;hasDecodedFrame=true;renderAt(presentedTime);video.requestVideoFrameCallback(frame)};video.requestVideoFrameCallback(frame)}
else video.addEventListener('timeupdate',()=>{presentedTime=video.currentTime;renderAt(presentedTime)});
let initialized=false;
function initializeVideo(){if(initialized)return;initialized=true;overlay.width=video.videoWidth;overlay.height=video.videoHeight;show()}
video.addEventListener('loadedmetadata',initializeVideo);clear('Waiting for source video…');show(false);
// The cached local video can load metadata before states.js finishes loading.
if(video.readyState>=1)initializeVideo();
</script></html>'''
    if base_href:
        template=template.replace('<meta charset="utf-8">','<meta charset="utf-8"><base href="'+html.escape(base_href,quote=True)+'">',1)
    (output/'index.html').write_text(template.replace('VIDEO_URL',video_url))


def run(*, public_run, aggregate, event_colours, motion_dir, config_path, video, output,
        state_timeline=None):
    started = time.perf_counter()
    public_run, motion_dir, output = map(Path, (public_run, motion_dir, output))
    if output.exists() and any(output.iterdir()):
        raise ValueError('Preserve previous post-throw output; choose a new output directory')
    config = json.loads(Path(config_path).read_text())
    protocol = json.loads((public_run/'protocol.json').read_text())
    model = json.loads((motion_dir/'manifest.json').read_text())
    source_hash = protocol['source_sha256']
    if digest(video) != source_hash or model['source_sha256'] != source_hash:
        raise ValueError('Video/motion source does not match public run')
    if model['observations_sha256'] != digest(public_run/'observations.jsonl'):
        raise ValueError('Motion model does not match saved tracker observations')
    import ijson
    with Path(aggregate).open('rb') as stream:
        aggregate_source = next(ijson.items(stream, 'context.source_sha256'), None)
    colours = json.loads(Path(event_colours).read_text()) if event_colours is not None else {'source_sha256': source_hash, 'events': []}
    if aggregate_source != source_hash or colours['source_sha256'] != source_hash:
        raise ValueError('Aggregate/colour source does not match public run')
    events = compact_events(aggregate)
    merged_colours = list(colours['events'])
    seen_colour_ids = {r['event_id'] for r in merged_colours}
    for ev in events:
        if ev['candidate_id'] not in seen_colour_ids and ev.get('colour'):
            merged_colours.append({
                'event_id': ev['candidate_id'],
                'colour': ev['colour'],
                'colour_status': ev.get('colour_status') or 'aggregate_track_colour_fallback',
            })
            seen_colour_ids.add(ev['candidate_id'])
    observer = BoardStateEvidence(events, merged_colours, group_to_team=config['group_to_team'],
                                  house_radius_m=config['house_radius_m'], stone_radius_m=config['stone_radius_m'])
    # NpzFile decompresses on every key lookup: materialize each array once.
    motion = {}
    for p in ('left', 'right'):
        with np.load(motion_dir/(p+'.npz')) as archive:
            motion[p] = {key: archive[key] for key in archive.files}
    proposals = []
    for i,event in enumerate(events):
        proposal = propose_frame(event, events[i+1]['event_prediction']['crossing_time_s']
                                 if i+1<len(events) else protocol['source_interval_s'][1],
                                 motion, protocol['sample_step_frames'])
        proposals.append({'event_id':event['candidate_id'],
                          'crossing_time_s':event['event_prediction']['crossing_time_s'], 'proposal':proposal,
                          'state':None, 'physical_revolutions':None,
                          'rotation_status':'No identifiable angular observations supplied; not inferred from translation.'})
    targets = {r['proposal']['frame_index'] for r in proposals if 'frame_index' in r['proposal']}
    context_payload = json.loads(Path(state_timeline).read_text()) if state_timeline else {}
    contexts = context_payload.get('samples', [])
    from prototype.detected_throw_score import DeliveryEndContext
    from prototype.scripts.build_state_timeline import END_SIZE
    end_size = config.get('deliveries_per_end', context_payload.get('summary', {}).get('end_size_assumption', END_SIZE))
    delivery_context = DeliveryEndContext(events, end_size=end_size, start_s=protocol['source_interval_s'][0])
    times = [s['t'] for s in contexts]
    epochs = []; previous = object(); epoch = None
    for s in contexts:
        if s['current_end'] != previous: epoch=s['t'];previous=s['current_end']
        epochs.append(epoch)
    output.mkdir(parents=True,exist_ok=True)
    timeline = BoardTimeline(output/'board-timeline')
    selected = {};track_memory={'left':{},'right':{}}
    with (public_run/'match-observations.jsonl').open() as stream:
        for line in stream:
            row=json.loads(line)
            for p,b in row['boards'].items():
                for s in b['stones']:
                    tracker_id=s.get('tracker_id')
                    if tracker_id is not None:
                        track_memory[p][tracker_id]={
                            'time_s':row['time_s'],'frame_index':row['frame_index'],
                            'pixel':s['pixel'],'position_m':s.get('height_adjusted_local_m')}
            raw=row; suppressed={}; boards={}
            for p,b in row['boards'].items():
                boards[p],suppressed[p]=suppress_duplicates(b, config['duplicate_nms_iou'])
            row={**row,'boards':boards}
            index=bisect.bisect_right(times,row['time_s'])-1
            context = delivery_context.at(row['time_s'])
            if index >= 0 and contexts[index]['current_end_status'].startswith('observed'):
                context = {'current_end': contexts[index]['current_end'],
                           'status': contexts[index]['current_end_status'], 'epoch_start_s': epochs[index],
                           'basis': 'Existing observed scoreboard marker context; observation remains unverified.'}
            # Never promote a motion proposal to a physically settled state.
            settlement={'status':'candidate_low_motion_unverified',
                        'basis':'Per-recording upstream HMM; source review pending.'}
            state=observer.observe(row,settlement=settlement,end_context=context,track_memory=track_memory)
            state['last_observed_totals']=raw.get('last_observed_totals',{})
            state['totals_provenance']='Saved OCR with observation time/age; not confirmed end points.'
            timeline.append(state,raw)
            if row['frame_index'] not in targets: continue
            before_state=observer.observe(raw,settlement=settlement,end_context=context,track_memory=track_memory)
            state['suppressed_duplicate_observations']=suppressed
            state['conditional_visible_points_before_nms']={p:b['conditional_visible_board_points']
                                                           for p,b in before_state['boards'].items()}
            state['motion_evidence']={}
            for p,b in boards.items():
                m=motion[p]; at=np.flatnonzero(m['frame_index']==row['frame_index'])
                by_id={int(m['track_id'][i]):int(i) for i in at}
                state['motion_evidence'][p]=[{
                    'tracker_id':s.get('tracker_id'),
                    'stationary_hypothesis':bool(m['stationary'][by_id[s['tracker_id']]]) if s.get('tracker_id') in by_id else None,
                    'posterior_stationary':float(m['posterior_stationary'][by_id[s['tracker_id']]]) if s.get('tracker_id') in by_id else None,
                } for s in b['stones']]
            selected[row['frame_index']]=state
    output.mkdir(parents=True,exist_ok=True); (output/'snapshots').mkdir()
    cap=cv2.VideoCapture(str(Path(video).resolve()))
    if not cap.isOpened(): raise ValueError('Cannot open source video')
    try:
        for r in proposals:
            frame=r['proposal'].get('frame_index')
            if frame is None: continue
            r['state']=selected.get(frame)
            if r['state'] is None:
                r['proposal']['board_status']='missing_saved_board_row';continue
            cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,image=cap.read()
            decoded=round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1
            if not ok or decoded!=frame:
                r['snapshot_status']={'status':'failed','decoded_frame':decoded};continue
            filename='snapshots/'+r['event_id']+'.jpg'
            if not cv2.imwrite(str(output/filename),image):raise IOError('Snapshot write failed')
            r['snapshot']=filename;r['snapshot_status']={'status':'decoded_source_frame','frame_index':decoded}
    finally: cap.release()
    inputs={'protocol':public_run/'protocol.json','observations':public_run/'observations.jsonl',
            'boards':public_run/'match-observations.jsonl','aggregate':Path(aggregate),
            'motion':motion_dir/'manifest.json','config':Path(config_path),
            'left_motion':motion_dir/'left.npz','right_motion':motion_dir/'right.npz'}
    if event_colours is not None:inputs['colours']=Path(event_colours)
    if state_timeline:inputs['state_timeline']=Path(state_timeline)
    payload={'development':True,'source_sha256':source_hash,'events':proposals,
             'timeline':timeline.finish(protocol), 'source_size_px':protocol.get('source_size_px'),
             'source_fps':protocol['source_fps'],
             'dimensions':{k:config[k] for k in ['house_radius_m','stone_radius_m']},
             'summary':{'candidates':len(proposals),'review_proposals':sum('time_s' in r['proposal'] for r in proposals),
                        'snapshots':sum('snapshot' in r for r in proposals),
                        'verified_settled_boards':0,'physical_revolution_estimates':0},
             'provenance':{'input_sha256':{k:digest(v) for k,v in inputs.items()},
                           'code_sha256':{k:digest(Path(__file__).parent/k) for k in ['post_throw_state.py','game_board_state.py','house_points.py','board_timeline.py','detected_throw_score.py']},
                           'config':config,'wall_s':time.perf_counter()-started,
                           'mode':'Postprocessing replay; saved detection, tracking and geometry unchanged.',
                           'opencv':cv2.__version__,
                           'changed_component':'OpenCV NMS on saved board boxes only; original detections/tracks preserved.'}}
    payload['detected_throw_scoring'] = {
        'scope': 'Event-associated stone subset, provisional points per throw; never summed into official totals.',
        'physical_identity_verified': False,
        'history': [dict(event_id=r['event_id'], time_s=r['proposal']['time_s'],
                         panel=r['proposal']['panel'],
                         end_context=r['state']['end_context'],
                         **{k: v for k, v in r['state']['boards'][r['proposal']['panel']]['detected_throw_score'].items()
                            if k in ('estimated_points', 'status', 'stale_event_ids', 'unresolved')})
                    for r in proposals if r['state'] is not None and 'time_s' in r['proposal']],
        'unresolved_post_throw_candidates': [r['event_id'] for r in proposals if r['state'] is None],
    }
    from prototype.detected_throw_score import build_match_ledger
    payload['detected_throw_scoring']['match_ledger'] = build_match_ledger(
        events, proposals, end_size=end_size, teams=list(config['group_to_team'].values()),
        start_s=protocol['source_interval_s'][0])
    from prototype.score_tracking import build as build_scores
    score_observations = public_run/'score-observations.jsonl'
    if score_observations.exists():
        payload['score_tracking'] = build_scores(score_observations)
    render(output,video,payload,config)
    write_json(output/'manifest.json',{k:v for k,v in payload.items() if k!='events'})
    return payload


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('public-run', 'aggregate', 'event-colours', 'motion-dir', 'video', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--config', dest='config_path', required=True)
    parser.add_argument('--state-timeline')
    args = parser.parse_args()
    run(**vars(args))
