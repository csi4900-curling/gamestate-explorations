"""Build a source-linked viewer directly from final aggregate predictions."""

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from aggregate_evaluation import score_event_to_top_view
from cache_contract import file_sha256
from score_integrated_source_review import score as score_source_review


def build(folder):
    datasets = []
    summary = {}
    inputs = {}
    for name in ("sweden22", "sweden24"):
        path = folder / name / "aggregate.json"
        data = json.loads(path.read_text())
        inputs[name] = file_sha256(path)
        summary[name] = data["summary"]
        for event in data["events"]:
            datasets.append(
                {
                    "match": name,
                    "id": event["candidate_id"],
                    "event_time_s": event["event_prediction"].get("observation_anchor_s", event["event_prediction"].get("first_observed_s", event["event_prediction"].get("crossing_time_s"))),
                    "segments": event["segments"],
                    "links": event.get("cross_view_links", []),
                    "failures": event["failure_reasons"],
                    "hypotheses": len(event.get("motion_hypotheses", [])),
                }
            )
    fresh = ROOT / "validation/fresh-same-format-transfer-2026-10-21"
    refs = list(csv.DictReader((fresh / "sweden22/source-reviewed-event-score.csv").open()))
    official = json.loads((fresh / "sweden22/source-reviewed-event-score.json").read_text())
    beijing = json.loads((folder / "sweden22/aggregate.json").read_text())
    if beijing["context"]["events_sha256"] != official["input_sha256"]["candidates"]:
        raise ValueError("Reviews differ from predictions")
    score = score_event_to_top_view(beijing, refs, official["official_shots"])
    reviewed = score_source_review(folder.resolve())
    event24 = json.loads((folder / "sweden24/event-audit/score.json").read_text())
    evaluation = {
        "source_review": reviewed,
        "sweden24_event_score": event24,
        "aggregate_inputs_sha256": inputs,
        "output_availability": summary,
        "beijing_event_to_output": score,
        "correctness": "Output availability is separate from reviewed correctness. Review labels, when present, are separate from inference.",
    }
    (folder / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
    # Keep only displayed data; raw hypotheses remain in the linked aggregate files.
    for e in datasets:
        e["segments"] = [
            {
                k: s.get(k)
                for k in (
                    "segment_id",
                    "camera",
                    "role",
                    "colour",
                    "pixel_points",
                    "geometry_samples",
                    "orientation_status",
                )
            }
            for s in e["segments"]
        ]
        for s in e["segments"]:
            s["pixel_points"] = [
                {"time_s": p["time_s"], "pixel": p["pixel"]} for p in s["pixel_points"]
            ]
            s["geometry_samples"] = [
                {
                    k: p.get(k)
                    for k in ("time_s", "pixel", "top_view_m", "rink_position_m", "status")
                }
                for p in s["geometry_samples"]
            ]
    page = """<!doctype html><html><meta charset="utf-8"><title>Integrated throw trajectories</title>
<style>body{max-width:1200px;margin:30px auto;padding:0 20px;font:16px/1.5 system-ui;color:#18343d}select,button{padding:9px;margin:5px}.layout{display:grid;grid-template-columns:2fr 1fr;gap:24px}.video{position:relative}video{width:100%}.video canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}#top{width:100%;background:#f4f7f8}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #ccd9d7;padding:7px;text-align:left}.box{padding:16px;background:#edf5f3}a{color:#076e65}@media(max-width:750px){.layout{display:block}}</style>
<h1>Detected throws → tracked stones → top-view paths</h1>
<p>Video-derived outputs from both complete matches. Select any candidate, inspect its source observations and projected points, and inspect failures alongside successes.</p>
<div class="box" id="summary"></div>
<p><b>Coordinate meaning:</b> ice-plane projections of stone-cap pixels. Local axes follow each camera; common-rink coordinates require a provisional orientation/identity assignment. Gaps are retained. Geometry gates and a successfully produced file do not establish trajectory accuracy.</p>
<p id="reviewscore" class="box"></p><select id="view"><option value="local">Camera-local segment</option><option value="rink">Both views on common rink</option></select><select id="event"></select><select id="segment"></select><button id="seek">Play segment</button>
<div class="layout"><div><div class="video"><video id="video" controls preload="metadata"></video><canvas id="overlay" width="640" height="360"></canvas></div><p id="details"></p></div><div><canvas id="top" width="360" height="650"></canvas><p>Choose camera-local or common-rink view. Both plots use equal metres per pixel on each axis. Paths remain separate across camera gaps; no hidden flight is invented. Common axes are provisional. A circle marks the nearest observed point.</p></div></div>
<p id="failures"></p><p><a href="sweden22/aggregate.json">2022 raw outputs</a> · <a href="sweden24/aggregate.json">2024 raw outputs</a> · <a href="evaluation.json">Evaluation inputs and counts</a></p>
<h2>All candidates</h2><table><thead><tr><th>Match</th><th>Candidate</th><th>Segments</th><th>Provisional links</th><th>Source review</th><th>Failures</th></tr></thead><tbody id="rows"></tbody></table>
<script>const D=DATA,S=SUMMARY,E=EVAL,R=REVIEW;const ev=document.querySelector('#event'),seg=document.querySelector('#segment'),v=document.querySelector('#video'),c=document.querySelector('#top'),g=c.getContext('2d'),o=document.querySelector('#overlay').getContext('2d');let ei=0,si=0;
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
ev.innerHTML=D.map((e,i)=>`<option value="${i}">${e.match} · ${e.id} · ${e.segments.some(s=>s.geometry_samples.some(p=>p.top_view_m))?"projected samples":e.segments.length?"pixel track only":"NO TRACK"}</option>`).join('');
document.querySelector('#summary').innerHTML=Object.entries(S).map(([k,s])=>`<b>${k}</b>: ${s.events_with_image_supported_top_view_segment}/${s.event_candidates} candidates with projected segments; ${s.events_with_cross_view_link} provisional cross-view links.`).join('<br>')+`<br>2022 official-event denominator: ${E.true_throws_with_top_view_output}/${E.official_throws} true throws have some top-view output. This is output coverage, Output coverage; exhaustive source-point correctness is reported below.`;
document.querySelector('#reviewscore').innerHTML=Object.entries(R).map(([k,r])=>`<b>${k} source check:</b> ${r.strict_source_point_passes}/${r.candidates_with_projected_segment} emitted trajectories pass the delivery + all-projected-points-on-stone check (${(100*r.strict_source_point_precision).toFixed(1)}%); coverage ${r.strict_source_point_passes}/${r.reference_deliveries} (${(100*r.strict_source_point_recall).toFixed(1)}%). ${r.samples_on_visible_stone}/${r.projected_samples_reviewed} projected samples land on stones.`).join('<br>')+'<br>This is a partial-trajectory source check, not physical metre accuracy or full-flight identity. All projected samples were inspected; same-colour collisions remain ambiguous.';
document.querySelector('#rows').innerHTML=D.map((e,i)=>`<tr><td>${e.match}</td><td><button onclick="choose(${i})">${esc(e.id)}</button></td><td>${e.segments.length}</td><td>${e.links.length}</td><td>${R[e.match].rows.find(r=>r.candidate_id===e.id).strict_source_point_pass?'Pass: partial source-point check':'Fail or no projected segment'}</td><td>${esc(e.failures.join(', '))}</td></tr>`).join('');
function selectedTime(){return D[ei]?.segments[si]?.pixel_points[0]?.time_s ?? D[ei]?.event_time_s;}
function seekSelected(){const t=selectedTime();if(Number.isFinite(t)&&v.readyState>=1)v.currentTime=t;}
v.onloadedmetadata=seekSelected;
function choose(i){v.pause();ei=i;si=0;ev.value=i;const e=D[i];const src=new URL(`../fresh-same-format-transfer-2026-10-21/${e.match}/source.mp4`,location.href).href;seg.innerHTML=e.segments.map((s,j)=>`<option value="${j}">${esc(s.segment_id)} · ${esc(s.camera)}</option>`).join('');document.querySelector('#failures').textContent=e.failures.join('; ')||'No recorded stage failures';document.querySelector('#seek').disabled=!Number.isFinite(selectedTime());document.querySelector('#seek').textContent=e.segments.length?'Play segment':'Play event (no track)';seg.disabled=!e.segments.length;document.querySelector('#view').value=e.links.length?'rink':'local';if(v.src!==src){v.src=src;v.load()}else seekSelected();details();}
function details(){const e=D[ei],s=e.segments[si];document.querySelector('#details').textContent=s?`${s.camera}: ${s.pixel_points.length} pixel observations; ${s.geometry_samples.filter(p=>p.top_view_m).length} projected samples. ${document.querySelector('#view').value==='local'?'Local view: right/down follows the calibrated source image.':'Common rink: travel points upward; camera orientation is provisional.'}`:`No accepted trajectory for this candidate. Video seeks to its event at ${e.event_time_s.toFixed(1)} s; ${e.hypotheses} retained hypotheses.`;}
ev.onchange=()=>choose(+ev.value);seg.onchange=()=>{v.pause();si=+seg.value;seekSelected();details()};document.querySelector('#seek').onclick=()=>{seekSelected();v.play()};
document.querySelector('#view').onchange=details;
function drawRink(){const e=D[ei];g.clearRect(0,0,360,650);const xy=p=>[180+p[0]*16,610-p[1]*16];g.strokeStyle='#bbcdd0';g.strokeRect(180-2.375*16,24,4.75*16,618);for(const y of [0,34.747])for(const r of [1.829,1.219,.610]){g.beginPath();g.ellipse(180,xy([0,y])[1],r*16,r*16,0,0,7);g.stroke()}for(const s of e.segments){let prev=null;g.strokeStyle=s.role==='departure'?'#087f8c':'#b35b0c';g.fillStyle=g.strokeStyle;for(const p of s.geometry_samples){if(!p.rink_position_m){prev=null;continue}const q=xy(p.rink_position_m);if(prev&&p.time_s-prev.time_s<=1.6){g.beginPath();g.moveTo(...xy(prev.rink_position_m));g.lineTo(...q);g.stroke()}g.beginPath();g.arc(...q,2,0,7);g.fill();prev=p;}}g.fillStyle='#18343d';g.fillText('Teal: departure · orange: receiving',75,640);}
function draw(){g.clearRect(0,0,360,650);o.clearRect(0,0,640,360);const s=D[ei]?.segments[si];if(s){const pts=s.geometry_samples;const ys=pts.filter(p=>p.top_view_m).map(p=>p.top_view_m[1]);const lo=Math.min(-2,...ys),hi=Math.max(2,...ys),scale=Math.min(55,590/(hi-lo));const xy=p=>[180+p[0]*scale,30+(p[1]-lo)*scale];g.strokeStyle='#b4c7ce';for(const r of [1.829,1.219,.610]){g.beginPath();g.ellipse(180,xy([0,0])[1],r*scale,r*scale,0,0,7);g.stroke()}g.strokeRect(180-2.375*scale,10,4.75*scale,630);let prev=null;for(const p of pts){if(!p.top_view_m){prev=null;continue}const q=xy(p.top_view_m);g.strokeStyle='#007f73';g.fillStyle='#007f73';if(prev&&p.time_s-prev.time_s<=1.6){g.beginPath();g.moveTo(...xy(prev.top_view_m));g.lineTo(...q);g.stroke()}g.beginPath();g.arc(...q,2,0,7);g.fill();prev=p;if(Math.abs(p.time_s-v.currentTime)<.26){g.strokeStyle='#e88920';g.beginPath();g.arc(...q,7,0,7);g.stroke()}}for(const p of s.pixel_points){if(Math.abs(p.time_s-v.currentTime)<.26){o.strokeStyle='#00dfc0';o.lineWidth=2;o.beginPath();o.arc(...p.pixel,9,0,7);o.stroke()}}}if(document.querySelector('#view').value==='rink')drawRink();if(!s||!s.geometry_samples.some(p=>p.top_view_m)){g.fillStyle='#18343d';g.font='16px system-ui';g.fillText(s?'No accepted top-view projection':'No accepted trajectory',35,300);}requestAnimationFrame(draw)}choose(D.findIndex(e=>e.match==='sweden24'&&e.id==='R01-S05'));document.querySelector('#view').value='rink';draw();</script></html>"""
    page = (
        page.replace("DATA", json.dumps(datasets).replace("</", "<\\/"))
        .replace("SUMMARY", json.dumps(summary))
        .replace("EVAL", json.dumps(score))
        .replace("REVIEW", json.dumps(reviewed))
    )
    (folder / "index.html").write_text(page)
    print(json.dumps(evaluation, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    a = p.parse_args()
    build(a.folder)
