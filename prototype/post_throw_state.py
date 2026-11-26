"""Synchronized stone-observations viewer backed by saved detections, geometry, and track colours."""
from collections import Counter
import html
import json
import os
from pathlib import Path
import time

import cv2
import numpy as np

from prototype.board_timeline import BoardTimeline
from prototype.detection_cache import digest


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
<div class="views"><div><div class="player"><video id="video" controls preload="auto" src="VIDEO_URL"></video><canvas id="source-overlay"></canvas></div>
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
video.addEventListener('seeked',()=>{if(!hasDecodedFrame&&video.readyState>=2){presentedTime=video.currentTime;hasDecodedFrame=true}if(hasDecodedFrame)renderAt(presentedTime)});
if(video.requestVideoFrameCallback){const frame=(_,m)=>{presentedTime=m.mediaTime;hasDecodedFrame=true;renderAt(presentedTime);video.requestVideoFrameCallback(frame)};video.requestVideoFrameCallback(frame)}
else video.addEventListener('timeupdate',()=>{presentedTime=video.currentTime;renderAt(presentedTime)});
let initialized=false;
function initializeVideo(){if(initialized)return;initialized=true;overlay.width=video.videoWidth;overlay.height=video.videoHeight;show(!window.frameElement?.dataset?.tab)}
video.addEventListener('loadedmetadata',initializeVideo);clear('Waiting for source video…');show(false);window.showBoard=show;
// The cached local video can load metadata before states.js finishes loading.
if(video.readyState>=1)initializeVideo();
</script></html>'''
    if base_href:
        template=template.replace('<meta charset="utf-8">','<meta charset="utf-8"><base href="'+html.escape(base_href,quote=True)+'">',1)
    (output/'index.html').write_text(template.replace('VIDEO_URL',video_url))


def build_board_viewer(*, public_run, effects, config_path, video, output, track_colours=None):
    """Lightweight frame-indexed stone-observations viewer backed by throw_effect and track colours.

    Avoids superseded HMM motion fitting, duplicate board re-scoring, and hidden JPEG
    snapshot decoding while preserving the full synchronized video/projection board viewer.
    """
    from collections import Counter

    started = time.perf_counter()
    public_run, output = Path(public_run), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Preserve previous board output; choose a new output directory')
    config = json.loads(Path(config_path).read_text())
    protocol = json.loads((public_run / 'protocol.json').read_text())
    effects_doc = json.loads(Path(effects).read_text())
    source_hash = protocol['source_sha256']
    if digest(video) != source_hash or effects_doc['source_sha256'] != source_hash:
        raise ValueError('Video/effects source does not match public run')
    colour_map = {'left': {}, 'right': {}}
    if track_colours and Path(track_colours).exists():
        tc_doc = json.loads(Path(track_colours).read_text())
        for panel in ('left', 'right'):
            panel_cols = dict(tc_doc.get('tracks', {}).get(panel, {}))
            for tid, ev in tc_doc.get('evidence', {}).get(panel, {}).items():
                if panel_cols.get(tid) is None:
                    preds = [r.get('prediction') for r in ev.get('samples', []) if r.get('prediction')]
                    if preds:
                        panel_cols[tid] = Counter(preds).most_common(1)[0][0]
            colour_map[panel] = panel_cols
    output.mkdir(parents=True, exist_ok=True)
    timeline = BoardTimeline(output / 'board-timeline')
    with (public_run / 'match-observations.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            boards = {}
            for p, b in row['boards'].items():
                boards[p], _ = suppress_duplicates(b, config['duplicate_nms_iou'])
            timeline.append_raw({**row, 'boards': boards}, colour_map)
    proposals = []
    for ev in effects_doc.get('events', []):
        settle = ev.get('settle_interval_s')
        proposal = (
            {'status': 'review_proposal', 'time_s': settle[0], 'panel': ev.get('panel'),
             'receiving_tracker_id': ev.get('delivered_tracker_id'),
             'stationary_interval_s': settle}
            if ev.get('status') == 'review_proposal' and settle else
            {'status': 'unresolved', 'reason': ev.get('reason', 'unresolved')}
        )
        proposals.append({
            'event_id': ev['event_id'],
            'crossing_time_s': ev['crossing_time_s'],
            'proposal': proposal,
            'state': None,
            'points_lying_after': ev.get('points_lying_after'),
            'physical_revolutions': None,
            'rotation_status': 'Development crop-period probe attached in throws view; physical revolutions unvalidated.',
        })
    inputs = {
        'protocol': public_run / 'protocol.json',
        'boards': public_run / 'match-observations.jsonl',
        'effects': Path(effects),
        'config': Path(config_path),
    }
    if track_colours and Path(track_colours).exists():
        inputs['track_colours'] = Path(track_colours)
    payload = {
        'development': True,
        'source_sha256': source_hash,
        'events': proposals,
        'timeline': timeline.finish(protocol),
        'source_size_px': protocol.get('source_size_px'),
        'source_fps': protocol['source_fps'],
        'dimensions': {k: config[k] for k in ['house_radius_m', 'stone_radius_m']},
        'summary': {
            'candidates': len(proposals),
            'review_proposals': sum('time_s' in r['proposal'] for r in proposals),
            'snapshots': 0,
            'verified_settled_boards': 0,
            'physical_revolution_estimates': 0,
        },
        'provenance': {
            'input_sha256': {k: digest(v) for k, v in inputs.items()},
            'code_sha256': {k: digest(Path(__file__).parent / k) for k in ['post_throw_state.py', 'board_timeline.py']},
            'config': config,
            'wall_s': time.perf_counter() - started,
            'mode': 'Lightweight board observation viewer backed by throw_effect quiet intervals and track colours.',
            'opencv': cv2.__version__,
        },
    }
    render(output, video, payload, config)
    write_json(output / 'manifest.json', {k: v for k, v in payload.items() if k != 'events'})
    return payload


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('public-run', 'effects', 'video', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--config', dest='config_path', required=True)
    parser.add_argument('--track-colours')
    args = parser.parse_args()
    build_board_viewer(**vars(args))
