"""Synchronized source-video review for model points and gap estimates."""
import json
import os
from pathlib import Path
from urllib.parse import quote


def write_report(result, output, video):
    output = Path(output)
    video_url = quote(os.path.relpath(Path(video).resolve(), output.resolve()))
    payload = json.dumps(result, allow_nan=False).replace('<', '\\u003c')
    html = TEMPLATE.replace('__DATA__', payload).replace('__VIDEO__', video_url)
    (output / 'index.html').write_text(html)


TEMPLATE = r'''<!doctype html><meta charset="utf-8"><title>Spin development review</title>
<style>body{font:16px system-ui;max-width:1350px;margin:24px auto;padding:0 20px;background:#f5f7fa;color:#182334}h1{font-size:25px}button{padding:9px;margin:4px}#views{display:grid;grid-template-columns:2fr 1fr;gap:16px}canvas{width:100%;background:#fff}#source{position:relative}video{width:100%}#overlay{position:absolute;left:0;top:0;pointer-events:none;background:transparent}pre{white-space:pre-wrap;font-size:13px}#status{padding:12px;background:white;min-height:70px}.note{padding:12px;border-left:4px solid #cc8300;background:#fff}#scrub{width:100%}table{border-collapse:collapse;width:100%}td,th{padding:7px;text-align:left;border-bottom:1px solid #ccc}</style>
<h1>Stone tracking and rotation review</h1>
<p class="note" id="scope"></p><p id="seed"></p>
<div id="workspace" style="display:grid;grid-template-columns:minmax(0,3fr) minmax(220px,1fr);gap:24px"><div><div id="views"><div id="source"><video id="video" controls preload="metadata" src="__VIDEO__"></video><canvas id="overlay"></canvas></div><div><canvas id="zoom" width="440" height="440"></canvas><p>Source crop and model point IDs. Hidden points are not drawn.</p></div></div>
<button id="play">Play analyzed interval</button><button id="back">Previous frame</button><button id="next">Next frame</button>
<label>Tracked point <select id="point-selection"></select></label>
<label><input id="markers" type="checkbox" checked> Show model points</label>
<input id="scrub" type="range" min="0" step="1"><div id="status"></div></div>
<section id="projection-section" style="display:none"><h2 style="font-size:19px;margin-top:0">Camera-local top view</h2><p>Tracked feature, not a verified stone centre.</p><select id="projection-mode"><option value="height">Height-adjusted estimate (conditional)</option><option value="raw">Raw cap-on-ice projection</option></select><p id="projection-state"></p><canvas id="plane" width="360" height="900"></canvas><details><summary>Projection details</summary><p id="projection-note"></p></details></section></div>
<section id="angle-section">
<canvas id="chart" width="1200" height="230"></canvas>
<p>Green: model-visible orientation. Orange: constant-rate gap estimate. Empty: unresolved. Lines never cross unresolved gaps. Phase groups after an unresolved gap have independent origins.</p>
<h2>Masked-interval checks</h2><p id="evaluation-scope"></p><table id="evaluation"></table>
</section>
<details><summary>Configuration, runtime and provenance</summary><pre id="meta"></pre></details>
<script>
const D=__DATA__;
const video=document.getElementById('video'),overlay=document.getElementById('overlay'),zoom=document.getElementById('zoom'),chart=document.getElementById('chart'),scrub=document.getElementById('scrub');
const samples=D.reconstruction.samples, ts=D.times_s; let frame=0, playingInterval=false;
const colors=['#0075ff','#e33444','#944bd0','#ca8400','#008977'];
const pointSelection=document.getElementById('point-selection');
D.point_names.forEach((name,index)=>pointSelection.add(new Option(name,String(index))));
pointSelection.add(new Option('All tracked points (not verified in-play stones)','all'));
function selectedIndices(){return pointSelection.value==='all'?D.point_names.map((_,i)=>i):[Number(pointSelection.value)];}

if(D.config.orientation_pair==null)document.getElementById('angle-section').style.display='none';
if(!D.projection)document.getElementById('workspace').style.display='block';
if(D.projection&&!D.projection.height_adjusted_point_count)document.getElementById('projection-mode').value='raw';
if(D.projection){document.getElementById('projection-section').style.display='block';document.getElementById('projection-note').textContent=(D.projection.interpretation||'No compatible existing calibration; projections unavailable.')+' '+(D.projection.coordinate_system||'')+' '+(D.projection.height_adjustment_assumptions||'')+' New rink-calibration fits: '+D.projection.new_calibration_fits+'. Projection time: '+D.projection.wall_seconds.toFixed(2)+' s. Missing projections remain gaps.';}
document.getElementById('scope').textContent=D.orientation_scope;
document.getElementById('seed').textContent='Initialization: '+D.seed_provenance+' | '+D.model.mode+' CoTracker3';
document.getElementById('evaluation-scope').textContent=D.evaluation_scope;
document.getElementById('meta').textContent=JSON.stringify({model:D.model,config:D.config,provenance:D.provenance,counts:{observed:D.reconstruction.observed_count,estimated:D.reconstruction.estimated_count,unresolved:D.reconstruction.unresolved_count},gaps:D.reconstruction.gaps},null,2);
scrub.max=ts.length-1;
function indexAt(t){let lo=0,hi=ts.length;while(lo<hi){const m=(lo+hi)>>1;if(ts[m]<=t+0.001)lo=m+1;else hi=m;}return Math.max(0,Math.min(ts.length-1,lo-1));}
function dots(ctx,offset=[0,0],scale=1){if(!document.getElementById('markers').checked)return;D.tracks_px[frame].forEach((p,j)=>{if(!selectedIndices().includes(j)||!D.point_visible[frame][j])return;ctx.strokeStyle=colors[j%colors.length];ctx.fillStyle=colors[j%colors.length];ctx.lineWidth=2;ctx.beginPath();ctx.arc((p[0]-offset[0])*scale,(p[1]-offset[1])*scale,5,0,Math.PI*2);ctx.stroke();ctx.font='14px system-ui';ctx.fillText(D.point_names[j],(p[0]-offset[0])*scale+7,(p[1]-offset[1])*scale-7);});}
function plot(){const c=chart.getContext('2d');c.clearRect(0,0,chart.width,chart.height);const values=samples.filter(s=>s.phase_rad!==null).map(s=>s.phase_rad*180/Math.PI);let low=values.length?Math.min(...values):0,high=values.length?Math.max(...values):1;if(high-low<10){low-=5;high+=5;}const px=t=>55+(t-ts[0])/(ts.at(-1)-ts[0])*1120,py=v=>195-(v-low)/(high-low)*165;c.fillStyle='#182334';c.font='13px system-ui';c.fillText('Orientation (degrees); '+D.angle_coordinate_system,10,18);c.fillText(high.toFixed(1),4,40);c.fillText(low.toFixed(1),4,195);for(let i=0;i<samples.length;i++){let s=samples[i];if(s.phase_rad===null)continue;let p=i?samples[i-1]:null;c.strokeStyle=c.fillStyle=s.status==='estimated'?'#c77500':'#00865b';if(p&&p.phase_rad!==null&&p.phase_group===s.phase_group){c.beginPath();c.moveTo(px(p.time_s),py(p.phase_rad*180/Math.PI));c.lineTo(px(s.time_s),py(s.phase_rad*180/Math.PI));c.stroke();}c.beginPath();c.arc(px(s.time_s),py(s.phase_rad*180/Math.PI),2,0,Math.PI*2);c.fill();}c.strokeStyle='#444';c.beginPath();c.moveTo(px(ts[frame]),25);c.lineTo(px(ts[frame]),200);c.stroke();c.fillStyle='#182334';c.fillText(ts[0].toFixed(2)+' s',55,222);c.fillText(ts.at(-1).toFixed(2)+' s',1110,222);}
function planePlot(){
 if(!D.projection||!D.projection.samples.length)return;
 const useHeight=document.getElementById('projection-mode').value==='height';
 const field=useHeight?'height_adjusted_points_camera_local_m':'points_camera_local_m';
 const el=document.getElementById('plane'),c=el.getContext('2d'),rows=D.projection.samples,indices=selectedIndices();
 const all=rows.flatMap(r=>indices.map(j=>r[field]?.[j]).filter(p=>p!=null));
 c.clearRect(0,0,360,900);
 if(!all.length){document.getElementById('projection-state').textContent='No projections available for this selection.';window.projectionMap=null;return;}
 const hog=Number.isFinite(D.projection.local_hog_y_m)?D.projection.local_hog_y_m:null;
 const xmin=Math.min(-2.375,...all.map(p=>p[0])),xmax=Math.max(2.375,...all.map(p=>p[0]));
 const ymin=Math.min(-1.829,hog??0,...all.map(p=>p[1]))-1,ymax=Math.max(1.829,hog??0,...all.map(p=>p[1]))+1;
 const scale=Math.min(280/(xmax-xmin),820/(ymax-ymin));
 const pos=p=>[180+(p[0]-(xmin+xmax)/2)*scale,450+((ymin+ymax)/2-p[1])*scale];
 const current=indices.map(j=>({index:j,name:D.point_names[j],position:rows[frame]?.[field]?.[j]??null}));
 document.getElementById('projection-state').textContent=(useHeight?'Conditional height estimate.':'Raw ice-plane projection.')+' Physical accuracy unverified. '+current.map(p=>p.name+': '+(p.position?p.position.map(v=>v.toFixed(3)).join(', ')+' m':'projection unavailable')).join(' | ');
 window.projectionMap={scale,xUnit:pos([1,0])[0]-pos([0,0])[0],yUnit:pos([0,0])[1]-pos([0,1])[1],mode:useHeight?'height':'raw',current,selectedIndices:indices,hogY:hog,bounds:{xmin,xmax,ymin,ymax}};
 c.strokeStyle='#b6c9d0';c.lineWidth=1;const center=pos([0,0]);
 [1.829,1.219,.610].forEach(r=>{c.beginPath();c.arc(...center,r*scale,0,Math.PI*2);c.stroke();});
 const a=pos([-2.375,ymax]),b=pos([2.375,ymin]);c.strokeRect(a[0],a[1],b[0]-a[0],b[1]-a[1]);
 c.fillStyle='#344955';c.font='12px system-ui';
 if(hog!==null){const h1=pos([-2.375,hog]),h2=pos([2.375,hog]);c.beginPath();c.moveTo(...h1);c.lineTo(...h2);c.stroke();c.fillText('hog line: y = '+hog+' m',h1[0],h1[1]-5);}
 c.fillText('tee: y = 0',center[0]+5,center[1]+5);
 for(const j of indices){c.strokeStyle=colors[j%colors.length];c.beginPath();let active=false;
  for(let i=0;i<=frame;i++){const p=rows[i][field]?.[j];if(p==null){active=false;continue;}const q=pos(p);if(active)c.lineTo(...q);else c.moveTo(...q);active=true;}
  c.stroke();const p=rows[frame]?.[field]?.[j];if(p!=null){c.fillStyle=colors[j%colors.length];c.beginPath();c.arc(...pos(p),4,0,Math.PI*2);c.fill();}
 }
}

function draw(){if(!video.videoWidth)return;if(video.seeking||video.currentTime<ts[0]-0.5/D.fps||video.currentTime>ts.at(-1)+0.5/D.fps){overlay.getContext('2d').clearRect(0,0,overlay.width,overlay.height);zoom.getContext('2d').clearRect(0,0,440,440);document.getElementById('plane').getContext('2d').clearRect(0,0,360,900);document.getElementById('status').textContent=video.seeking?'Seeking source frame…':'Outside analyzed interval — no predictions shown';return;}frame=indexAt(video.currentTime);scrub.value=frame;overlay.width=video.videoWidth;overlay.height=video.videoHeight;const c=overlay.getContext('2d');c.clearRect(0,0,overlay.width,overlay.height);dots(c);const z=zoom.getContext('2d');z.clearRect(0,0,440,440);const crop=D.crop_px;const side=Math.max(crop[2]-crop[0],crop[3]-crop[1]);z.drawImage(video,crop[0],crop[1],side,side,0,0,440,440);dots(z,crop.slice(0,2),440/side);const s=samples[frame];const state=D.point_visible[frame].map((v,i)=>D.point_names[i]+': '+(v?'model-visible':'model-hidden')).join(' | ');document.getElementById('status').textContent='Video '+video.currentTime.toFixed(3)+' s · sample '+ts[frame].toFixed(3)+' s · frame '+D.frame_indices[frame]+(D.config.orientation_pair==null?'':' · '+s.status)+'\n'+state+(s.phase_rad===null?'':' · angle '+(s.phase_rad*180/Math.PI).toFixed(1)+'°');plot();planePlot();}
function seek(i){video.pause();playingInterval=false;frame=Math.max(0,Math.min(ts.length-1,i));video.currentTime=ts[frame]+0.0001;}
video.addEventListener('loadedmetadata',()=>{video.currentTime=ts[0]+0.0001;draw();});video.addEventListener('seeked',draw);video.addEventListener('timeupdate',draw);
function tick(){if(playingInterval&&video.currentTime>=D.interval_s[1]-0.001){video.pause();playingInterval=false;}draw();requestAnimationFrame(tick);}requestAnimationFrame(tick);
document.getElementById('play').onclick=()=>{playingInterval=true;video.currentTime=ts[0];video.play();};document.getElementById('back').onclick=()=>seek(frame-1);document.getElementById('next').onclick=()=>seek(frame+1);scrub.oninput=()=>seek(Number(scrub.value));document.getElementById('markers').onchange=draw;document.getElementById('projection-mode').onchange=draw;pointSelection.onchange=draw;
const table=document.getElementById('evaluation');table.innerHTML='<tr><th>Hidden interval (s)</th><th>Estimated / withheld</th><th>Angle MAE</th><th>Reconnection</th></tr>';
D.masked_evaluation.forEach(r=>{const row=table.insertRow();[r.interval_s.join('–'),r.estimated_withheld_samples+' / '+r.withheld_observed_samples,r.wrapped_angle_mae_deg===null?'Unresolved':r.wrapped_angle_mae_deg.toFixed(2)+'°',r.gaps.map(g=>g.reason).join('; ')].forEach(v=>{row.insertCell().textContent=v;});});
</script>'''
