"""Build an offline browser viewer for full-match provisional review clips."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-full-match-event-review-segments-development.json"
)
OUTPUT = ROOT / "prototype/full-match-event-review/index.html"


def main(
    input_path=INPUT, output_path=OUTPUT, *, method_link="FULL-MATCH-EVENT-REVIEW-SEGMENTS.md"
):
    source = json.loads(input_path.read_text())
    viewer_data = {
        "evidence_sha256": sha256(input_path.read_bytes()).hexdigest(),
        "games": [
            {
                "code": game["official_game_code"],
                "video": "../../" + game["source_video_path"],
                "source_interval_s": game["source_interval_s"],
                "segments": [
                    {
                        key: row[key]
                        for key in (
                            "event_id",
                            "candidate_class",
                            "counter_id",
                            "colour",
                            "colour_status",
                            "review_shot_ids",
                            "evidence_core_s",
                            "review_window_s",
                            "possible_internal_edit_times_s",
                            "delivery_window_s",
                            "observed_travel_window_s",
                            "physical_release_time_s",
                            "physical_settle_time_s",
                            "simulation_ready",
                        )
                    }
                    for row in game["segments"]
                ],
            }
            for game in source["games"]
        ],
    }
    data = json.dumps(viewer_data, separators=(",", ":")).replace("</", "<\\/")
    html = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Full-match curling event review</title>
<style>
:root{--ink:#16313b;--teal:#126e7b;--line:#d8e3e2;--paper:#fffefb;--bg:#f4f6f3;--warn:#b25245;--muted:#5a6d72}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--teal)}button,input,select{font:inherit}button{cursor:pointer}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #e6b752;outline-offset:2px}
header{padding:27px clamp(18px,4vw,56px);background:#102832;color:white}header small{display:block;color:#8ccbd0;text-transform:uppercase;letter-spacing:1.8px;font-weight:800}h1{font:normal clamp(30px,3.4vw,48px)/1.1 Georgia,serif;margin:10px 0}header p{color:#c7dadd;max-width:900px;margin:0}.shell{display:grid;grid-template-columns:minmax(280px,350px) minmax(0,1fr);gap:22px;max-width:1600px;margin:auto;padding:24px}
.panel{background:var(--paper);border:1px solid var(--line);border-radius:12px;overflow:hidden}.controls{padding:18px;border-bottom:1px solid var(--line)}label{display:block;font-size:12px;font-weight:750;margin:0 0 12px}select,input[type=search]{display:block;width:100%;padding:10px;margin-top:5px;border:1px solid #b8cac9;border-radius:7px;background:white;color:var(--ink)}.filters{display:flex;gap:12px;align-items:center}.filters label{font-weight:500}.list{height:min(68vh,760px);overflow:auto}.item{display:block;width:100%;border:0;border-bottom:1px solid var(--line);background:white;text-align:left;padding:12px 17px;color:var(--ink)}.item:hover,.item.active{background:#e7f1f0}.item strong{display:block}.item span{font-size:12px;color:var(--muted)}.item .bad{color:var(--warn);font-weight:700}.viewer{padding:20px}video{display:block;width:100%;max-height:70vh;background:#09171b;border-radius:8px}.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:13px 0}.bar button{border:1px solid #a7c3c4;background:#e8f2f1;color:#124854;padding:8px 12px;border-radius:6px}.bar button:hover{background:#d4e9e7}.bar .stop{margin-left:auto;font-size:12px}.meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:16px 0}.metric{border:1px solid var(--line);border-radius:8px;padding:12px}.metric b{display:block;font-size:18px}.metric span{font-size:11px;color:var(--muted)}.notice{border-left:4px solid var(--warn);background:#faf0eb;padding:13px 16px;font-size:13px}.details{font-size:13px}.details dt{font-weight:800;margin-top:11px}.details dd{margin:2px 0 0;color:var(--muted)}.foot{padding:18px;font-size:12px;color:var(--muted)}
@media(max-width:850px){.shell{grid-template-columns:1fr}.list{height:250px}.meta{grid-template-columns:1fr 1fr}}@media(max-width:520px){.meta{grid-template-columns:1fr}.bar .stop{margin-left:0}}
</style>
<header><small>Curling research prototype · full-recording review</small><h1>Inspect the evidence for each provisional event.</h1><p>Camera-shot windows let you review what the system saw. The clips are not validated physical throw segments; exact release, stone identity, and settling remain unknown.</p></header>
<main class="shell"><aside class="panel"><div class="controls"><label>Recording<select id="game"></select></label><label>Find event, counter or shot<input id="search" type="search" placeholder="Try B26 or S124"></label><div class="filters"><label><input type="checkbox" id="conflicts"> Colour conflicts</label><label><input type="checkbox" id="edits"> Possible edits</label></div><div id="count" class="details"></div></div><div id="list" class="list" role="listbox" aria-label="Provisional event candidates"></div></aside>
<section class="panel viewer"><h2 id="title" style="margin:0 0 12px;font:normal 27px Georgia,serif"></h2><video id="video" controls preload="metadata" playsinline></video><div class="bar"><button id="play">Play review window</button><button id="core">Jump to evidence core</button><button id="travel">Jump to observed travel</button><label class="stop"><input id="stop" type="checkbox" checked> Stop at review-window end</label></div><div class="meta"><div class="metric"><b id="review"></b><span>Review window (source video)</span></div><div class="metric"><b id="coretime"></b><span>Evidence camera shots</span></div><div class="metric"><b id="colour"></b><span>Colour evidence</span></div></div><div class="notice">Release and settling times are unverified. A counter link is delayed broadcast evidence, and a possible edit is not a confirmed identity break. No event here is simulation-ready.</div><dl class="details"><dt>Evidence class</dt><dd id="class"></dd><dt>Camera shots included</dt><dd id="shots"></dd><dt>Counter</dt><dd id="counter"></dd><dt>Possible internal edit times</dt><dd id="editlist"></dd><dt>Candidate delivery window</dt><dd id="delivery"></dd><dt>Observed travel interval</dt><dd id="travelwindow"></dd></dl><p class="foot">Open this page from the project folder so its local source videos remain available. <a href="../../validation/official-shot-sequence/FULL-MATCH-EVENT-REVIEW-SEGMENTS.md">Method and limits</a> · <a href="../../supervisor-progress-2026-10-09.html">Supervisor report</a></p></section></main>
<script>const D=__DATA__;
const $=id=>document.getElementById(id),v=$('video');let gi=0,selected=null,visible=[];
const names={'PREL000101':'Sweden–Switzerland','PREL000102':'Canada–China','PREL000103':'Slovakia–USA'};
const fmt=t=>t==null?'unknown':`${Math.floor(t/3600)}:${String(Math.floor(t%3600/60)).padStart(2,'0')}:${String((t%60).toFixed(1)).padStart(4,'0')}`;
const interval=x=>x?`${fmt(x[0])}–${fmt(x[1])}`:'unknown';
const safe=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function choose(row){selected=row;$('title').textContent=row.event_id;$('review').textContent=interval(row.review_window_s);$('coretime').textContent=interval(row.evidence_core_s);$('colour').textContent=row.colour_status==='conflict'?'conflict':row.colour||'unknown';$('class').textContent=row.candidate_class.replaceAll('_',' ');$('shots').textContent=row.review_shot_ids.join(', ');$('counter').textContent=row.counter_id||'none';$('editlist').textContent=row.possible_internal_edit_times_s.length?row.possible_internal_edit_times_s.map(fmt).join(', '):'none proposed';$('delivery').textContent=interval(row.delivery_window_s);$('travelwindow').textContent=interval(row.observed_travel_window_s);$('travel').disabled=!row.observed_travel_window_s;document.querySelectorAll('.item').forEach(button=>button.classList.toggle('active',button.dataset.id===row.event_id));if(v.readyState>=1)v.currentTime=row.review_window_s[0];else v.addEventListener('loadedmetadata',()=>v.currentTime=row.review_window_s[0],{once:true})}
function render(){const q=$('search').value.trim().toLowerCase(),conf=$('conflicts').checked,edit=$('edits').checked;visible=D.games[gi].segments.filter(r=>(!conf||r.colour_status==='conflict')&&(!edit||r.possible_internal_edit_times_s.length)&&(!q||[r.event_id,r.counter_id,...r.review_shot_ids].some(x=>String(x||'').toLowerCase().includes(q))));$('count').textContent=`${visible.length} of ${D.games[gi].segments.length} provisional candidates`;$('list').innerHTML=visible.map(r=>`<button class="item" role="option" data-id="${safe(r.event_id)}"><strong>${safe(r.event_id)} · ${safe(r.counter_id||'no counter')}</strong><span class="${r.colour_status==='conflict'?'bad':''}">${safe(r.colour_status==='conflict'?'colour conflict':r.colour||'unknown colour')} · ${safe(interval(r.evidence_core_s))}${r.possible_internal_edit_times_s.length?' · possible edit':''}</span></button>`).join('');document.querySelectorAll('.item').forEach(b=>b.onclick=()=>choose(visible.find(r=>r.event_id===b.dataset.id)));if(!selected||!visible.some(r=>r.event_id===selected.event_id))choose(visible[0]||D.games[gi].segments[0])}
function setGame(index){gi=index;selected=null;v.pause();v.src=D.games[gi].video;v.load();render()}
$('game').innerHTML=D.games.map((g,i)=>`<option value="${i}">${safe(names[g.code]||g.code)} · ${g.segments.length} candidates</option>`).join('');$('game').onchange=e=>setGame(+e.target.value);for(const id of ['search','conflicts','edits'])$(id).oninput=render;
$('play').onclick=()=>{if(!selected)return;v.currentTime=selected.review_window_s[0];v.play()};$('core').onclick=()=>{if(selected)v.currentTime=selected.evidence_core_s[0]};$('travel').onclick=()=>{if(selected?.observed_travel_window_s)v.currentTime=selected.observed_travel_window_s[0]};v.ontimeupdate=()=>{if(selected&&$('stop').checked&&!v.paused&&v.currentTime>=selected.review_window_s[1])v.pause()};setGame(0);
</script></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = html.replace("__DATA__", data)
    if method_link != "FULL-MATCH-EVENT-REVIEW-SEGMENTS.md":
        payload = payload.replace("FULL-MATCH-EVENT-REVIEW-SEGMENTS.md", method_link)
    if output_path.exists():
        if output_path.read_text() != payload:
            raise SystemExit("Existing viewer differs from current evidence or code")
        print(f"Verified {output_path}")
    else:
        output_path.write_text(payload)
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--method-link", default="FULL-MATCH-EVENT-REVIEW-SEGMENTS.md")
    args = parser.parse_args()
    main(args.input, args.output, method_link=args.method_link)
