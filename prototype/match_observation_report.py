"""File-compatible synchronized viewer for shared match observation outputs."""
import json
import os
from pathlib import Path
from urllib.parse import quote


def render(output,video,events):
    output=Path(output);bounds={};key=None;chunk=[];last_marker=None
    event_metadata=json.loads((output/'events.json').read_text())
    state_path=output/'match-state/timeline.jsonl'
    states=None
    if state_path.exists():
        state_manifest=json.loads((state_path.parent/'manifest.json').read_text())
        if state_manifest['source_sha256']!=event_metadata['source_sha256']:
            raise ValueError('State/video source mismatch')
        def state_rows():
            with state_path.open() as stream:
                for line in stream:yield json.loads(line)
        states=state_rows()
    folder=output/'match-view-data';folder.mkdir(exist_ok=True)
    def flush(key,rows):
        if key is None:return
        (folder/f'{key}.js').write_text('window.receiveMatchChunk('+str(key)+','+json.dumps(rows).replace('<','\\u003c')+');')
        bounds[key]=[rows[0]['t'],rows[-1]['t']]
    for line in (output/'match-observations.jsonl').open():
        r=json.loads(line);new_key=int(r['time_s']//60)
        if new_key!=key:
            if key is not None and new_key<key:raise ValueError('Match observations must be chronological')
            flush(key,chunk);key=new_key;chunk=[]
        sample={'t':r['time_s'],'boards':{},'score':{k:{'value':v['value'],'age_s':v['age_s']} for k,v in r['last_observed_totals'].items()}}
        if states is not None:
            state=next(states,None)
            if state is None or (state['time_s'],state.get('frame_index'))!=(r['time_s'],r.get('frame_index')):
                raise ValueError('State/board source frames differ')
            sample['state']={k:state[k] for k in ['cumulative_match_score','current_end','current_points_in_house']}
        score = r.get('score_observation') or {}
        if score.get('displayed_end') is not None:
            last_marker = {'value':score['displayed_end'], 'observed_at_s':score['time_s'],
                           'evidence':score.get('displayed_end_evidence')}
        sample['last_displayed_end'] = ({**last_marker, 'age_s':r['time_s']-last_marker['observed_at_s']}
                                        if last_marker is not None else None)
        for panel,b in r['boards'].items():
            sample['boards'][panel]={'status':b['registration']['status'],'stones':[
                {'id':s['tracker_id'],'pixel':s['pixel'],'box':s['bbox_xyxy'],'xy':s['height_adjusted_local_m'],'confidence':s['confidence']} for s in b['stones']]}
        chunk.append(sample)
    flush(key,chunk)
    if states is not None and next(states,None) is not None:
        states.close()
        raise ValueError('State extends beyond board observations')
    groups={}
    aggregate_path=output/'aggregate.json'
    if aggregate_path.exists():
        aggregate=json.loads(aggregate_path.read_text())
        if aggregate['context']['source_sha256']!=event_metadata['source_sha256']:
            raise ValueError('Aggregate/video source mismatch')
        if {e['candidate_id'] for e in aggregate['events']}!={e['id'] for e in events}:
            raise ValueError('Aggregate and displayed event IDs differ')
        for event in aggregate['events']:
            groups[event['candidate_id']]={
                panel:sorted({segment['tracker_id'] for segment in event['segments']
                              if segment['camera']==panel+'_split' and segment.get('tracker_id') is not None})
                for panel in ['left','right']}
            groups[event['candidate_id']]['status']=event.get('handoff_hypothesis',{}).get('status','unresolved')
            times=[point['time_s'] for segment in event['segments'] for point in segment.get('pixel_points',[])]
            groups[event['candidate_id']]['observed_interval_s']=[min(times),max(times)] if times else None
    cfg={'chunks':bounds,'events':events,'source_interval_s':event_metadata['source_interval_s'],
         'source_sha256':event_metadata['source_sha256'],'event_track_groups':groups,
         'run_status':event_metadata.get('status'),'requested_full_interval_s':event_metadata.get('requested_full_interval_s'),
         'right_censored_event_id':events[-1]['id'] if events and str(event_metadata.get('status','')).startswith('partial_') else None}
    (folder/'manifest.json').write_text(json.dumps(cfg,indent=2))
    (output/'board-plot.js').write_bytes(Path(__file__).with_name('match_board_plot.js').read_bytes())
    url=quote(os.path.relpath(Path(video).resolve(),output.resolve()))
    (output/'match-observations.html').write_text(TEMPLATE.replace('__DATA__',json.dumps(cfg).replace('<','\\u003c')).replace('__VIDEO__',url))


TEMPLATE='''<!doctype html><meta charset="utf-8"><title>Match observations — development</title>
<style>body{font:16px system-ui;margin:24px;background:#f4f7f8;color:#243b48}main{display:grid;grid-template-columns:2fr 1fr;gap:16px}.source{position:relative}video{width:100%}#overlay{position:absolute;inset:0;width:100%;pointer-events:none}#boards{display:flex;gap:12px}#boards canvas{width:48%;background:white}select,button{padding:8px}p{max-width:1000px}</style>
<h1>Match observations — development</h1><p id="run-scope"></p><p>Learned detections and upstream tracker labels; physical identities and camera handoffs are unverified. Board plots use conditional height correction in separate camera-local coordinates. Missing geometry stays missing. Stored stones outside the playing area may also be detected.</p>
<label>Left tracker <select id="track-left"><option value="all">All</option></select></label> <label>Right tracker <select id="track-right"><option value="all">All</option></select></label><br><select id="events"></select><button id="play">Play</button><span id="clock"></span><p id="event-association"></p>
<main><div><div class="source"><video id="video" controls src="__VIDEO__"></video><canvas id="overlay"></canvas></div><p id="status"></p></div><div><div id="boards"><canvas id="left" width="240" height="760"></canvas><canvas id="right" width="240" height="760"></canvas></div><p>Both views use the same metre scale. Dots: observations at the displayed sample. Lines: adjacent samples of the same tracker label within the selected candidate’s observed interval (or the current minute when no interval is available); these are not CoTracker trajectories or verified physical identities.</p></div></main>
<a href="index.html">Crossing evidence</a> · <a href="match-observation-protocol.json">Provenance</a> · <a href="match-observation-summary.json">Runtime</a>
<script src="board-plot.js"></script>
<script>const D=__DATA__,v=document.querySelector('#video'),sel=document.querySelector('#events'),overlay=document.querySelector('#overlay'),cache={},loading=new Set();let current=[];
document.querySelector('#run-scope').textContent='Run status: '+D.run_status+'; available source interval '+D.source_interval_s.join('–')+' s.'+(D.requested_full_interval_s?' Full requested interval: '+D.requested_full_interval_s.join('–')+' s. Processing is incomplete.':'');
window.receiveMatchChunk=(key,rows)=>{cache[key]=rows;loading.delete(key)};
function load(key){if(!(key in D.chunks)||cache[key]||loading.has(key))return;loading.add(key);const s=document.createElement('script');s.src='match-view-data/'+key+'.js';document.body.append(s)}
D.events.forEach((e,i)=>{const o=document.createElement('option');o.value=i;o.textContent=e.id+' · '+e.crossing_time_s.toFixed(2)+' s';sel.append(o)});if(!D.events.length){const o=document.createElement('option');o.textContent='No crossings in this interval';sel.append(o)}
function choose(){v.pause();const event=D.events[+sel.value],group=D.event_track_groups?.[event?.id];if(group){for(const panel of ['left','right']){const select=document.querySelector('#track-'+panel),ids=group[panel];if(ids.length===1){const value=String(ids[0]);if(![...select.options].some(o=>o.value===value))select.add(new Option('Local ID '+value,value));select.value=value;}else select.value='all';}document.querySelector('#event-association').textContent='Camera association: '+group.status+'; physical identity unverified. Left local IDs: '+(group.left.join(', ')||'unresolved')+'; right local IDs: '+(group.right.join(', ')||'unresolved')+'. Ambiguous or missing associations keep all tracks visible in that panel.'+(event.id===D.right_censored_event_id?' Last candidate window is truncated at the snapshot boundary.':'');}v.currentTime=event?.crossing_time_s??D.source_interval_s[0]};sel.onchange=choose;document.querySelector('#play').onclick=()=>v.play();v.addEventListener('loadedmetadata',choose);if(v.readyState>=1)choose();
function selectedStone(panel,stone){const value=document.querySelector('#track-'+panel).value;return value==='all'||String(stone.id)===value;}
function updateTrackSelectors(rows){for(const panel of ['left','right']){const select=document.querySelector('#track-'+panel),old=select.value;const ids=[...new Set(rows.flatMap(r=>r.boards[panel].stones.map(s=>s.id).filter(id=>id!==null)))].sort((a,b)=>a-b);const signature=ids.join(',');if(select.dataset.ids===signature)continue;select.dataset.ids=signature;select.replaceChildren(new Option('All','all'));for(const id of ids)select.add(new Option('Local ID '+id,String(id)));if(old!=='all'&&!ids.includes(Number(old)))select.add(new Option('Local ID '+old+' — absent in chunk',old));select.value=old;}}
function candidateHistory(rows){window.candidateHistoryAudit=null;const interval=D.event_track_groups?.[D.events[+sel.value]?.id]?.observed_interval_s;if(!interval||v.currentTime<interval[0]||v.currentTime>interval[1])return rows;const result=[];let complete=true;for(let key=Math.floor(interval[0]/60);key<=Math.floor(interval[1]/60);key++){load(key);if(!cache[key])complete=false;else result.push(...cache[key].filter(r=>r.t>=interval[0]-1e-6&&r.t<=interval[1]+1e-6));}window.candidateHistoryAudit={interval,complete,samples:result.length};return result;}
function drawState(row){
 const state=row?.state;window.matchStateAudit=state??null;
}
function draw(){if(v.seeking){drawState(null);overlay.width=v.videoWidth;overlay.height=v.videoHeight;window.detectorViewerAudit={sourceTime:v.currentTime,sampleTime:null,rendered:[],seeking:true};window.candidateHistoryAudit=null;for(const panel of ['left','right'])drawBoard(panel,null,[]);document.querySelector('#clock').textContent=' Source '+v.currentTime.toFixed(2)+' s';document.querySelector('#status').textContent='';requestAnimationFrame(draw);return;}const key=Math.floor(v.currentTime/60);load(key);const rows=cache[key]??[];updateTrackSelectors(rows);let row=null;for(const r of rows){if(r.t<=v.currentTime+1e-5)row=r;else break}const step=rows.length>1?rows[1].t-rows[0].t:0;if(row&&v.currentTime-row.t>step+1e-5)row=null;overlay.width=v.videoWidth;overlay.height=v.videoHeight;const ctx=overlay.getContext('2d');const rendered=[];if(row)for(const [panel,b] of Object.entries(row.boards))for(const s of b.stones){if(!selectedStone(panel,s))continue;rendered.push({panel,id:s.id,box:s.box});ctx.strokeStyle='#168bd2';ctx.lineWidth=2;ctx.strokeRect(s.box[0],s.box[1],s.box[2]-s.box[0],s.box[3]-s.box[1]);ctx.font='18px sans-serif';ctx.fillStyle='#168bd2';ctx.fillText('ID '+(s.id??'?'),s.box[0],s.box[1]-5)}window.detectorViewerAudit={sourceTime:v.currentTime,sampleTime:row?.t??null,rendered};drawState(row);const history=candidateHistory(rows);for(const p of ['left','right'])drawBoard(p,row,history);document.querySelector('#clock').textContent=' Source '+v.currentTime.toFixed(2)+' s';document.querySelector('#status').textContent=row?Object.entries(row.boards).map(([k,b])=>k+': '+b.status).join(' · '):'';requestAnimationFrame(draw)}requestAnimationFrame(draw);</script>'''
