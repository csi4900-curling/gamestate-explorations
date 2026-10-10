"""Render an offline video-linked viewer for provisional partial states."""

import argparse
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = (
    ROOT
    / "validation/throw-event-benchmark/canada-czech-2024/full-match-partial-state-sequence-postscore.json"
)
DEFAULT_DIR = ROOT / "prototype/full-match-canada-czech-state"

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Canada–Czechia · __BRANCH__ · video state evidence</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#183040;background:#f0f4f5}*{box-sizing:border-box}body{margin:0}header{background:#11394d;color:#fff;padding:28px max(22px,calc((100vw - 1250px)/2))}header h1{margin:5px 0;font-size:30px}header p{max-width:850px;line-height:1.5;margin:8px 0;color:#d7e6eb}.kicker{text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:700;color:#9ad3dc}main{max-width:1250px;margin:auto;padding:20px 22px 60px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stat,.panel{background:#fff;border:1px solid #d8e4e8;border-radius:12px;box-shadow:0 3px 14px #1734430b}.stat{padding:15px}.stat strong{font-size:28px;display:block}.stat span{font-size:13px;color:#607781}.controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:18px 0}button,select{font:inherit;border-radius:8px;border:1px solid #acc2cc;background:#fff;color:#173a4d;padding:9px 12px}button{cursor:pointer}button:hover{background:#e8f3f6}select{min-width:250px}.layout{display:grid;grid-template-columns:1.05fr 1fr;gap:16px}.panel{padding:18px;min-width:0}.panel h2{font-size:19px;margin:0 0 5px}.muted{color:#657b86;font-size:13px;line-height:1.45}.video{width:100%;background:#09151d;border-radius:8px;aspect-ratio:16/9}.boards{display:grid;grid-template-columns:1fr 1fr;gap:12px}.board{min-width:0}.board h3{font-size:14px;margin:10px 0 5px}.plot{width:100%;height:auto;border:1px solid #dae5e9;border-radius:8px;background:#f9fcfc}.status{margin:8px 0;padding:10px 12px;background:#eef5f7;border-radius:8px;font-size:14px;line-height:1.4}.warning{background:#fff2de;color:#75491c}.evidence{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px}.evidence div{border-top:1px solid #e2eaee;padding-top:7px;font-size:13px}.evidence b{display:block;color:#687b84;font-size:11px;text-transform:uppercase;letter-spacing:.04em}.note{background:#fff3df;border-left:4px solid #d39b40;margin-top:16px;padding:12px 15px;line-height:1.5}.sources{font-size:13px;margin-top:16px;color:#58717b}.sources a{color:#17607f}.pill{display:inline-block;border-radius:20px;background:#e6f2eb;color:#27684b;padding:3px 8px;font-size:12px;font-weight:700}.pill.gap{background:#faead9;color:#8d4f21}@media(max-width:900px){.layout{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}@media(max-width:520px){.boards{grid-template-columns:1fr}.evidence{grid-template-columns:1fr}select{width:100%}}
</style></head><body>
<header><div class="kicker">Curling research · full source · video evidence only</div><h1>Canada–Czechia: event-to-board sequence</h1><p>__BRANCH__. Step through provisional stone passages and the partial board observed after each one. The source video, camera-local positions and transition abstentions stay linked.</p></header>
<main><div class="stats"><div class="stat"><strong id="eventsCount"></strong><span>provisional passages</span></div><div class="stat"><strong id="boardsCount"></strong><span>post-event partial boards</span></div><div class="stat"><strong id="compCount"></strong><span>adjacent view-local comparisons</span></div><div class="stat"><strong id="readyCount"></strong><span>simulation-ready states</span></div></div>
<div class="controls"><button id="previous">← Previous</button><select id="eventSelect" aria-label="Choose provisional event"></select><button id="next">Next →</button><button id="seek">Seek source video</button><label><input type="checkbox" id="onlyBoards"> With observed board</label><label><input type="checkbox" id="onlyComparisons"> With adjacent comparison</label></div>
<div class="layout"><section class="panel"><h2 id="title"></h2><p class="muted" id="eventMeta"></p><p class="status warning" id="reviewFlag" hidden></p><video class="video" id="video" controls preload="metadata" playsinline src="../../validation/throw-event-benchmark/canada-czech-2024/source-360p.mp4"></video><div class="evidence" id="evidence"></div><div class="note">A crossing is a provisional event, not a verified physical throw or exact release. This video does not establish spin, exact settling, scoring or a complete stone inventory.</div></section>
<section class="panel"><h2>Partial state around this candidate</h2><p class="muted">Camera-local 2D coordinates. Axes are conditional metres around the detected target button; orientation and metric accuracy are unverified.</p><div class="boards"><div class="board"><h3 id="beforeTitle">Previous observation</h3><svg id="beforePlot" class="plot" viewBox="-100 -100 200 200" role="img" aria-label="Previous partial board"></svg><p class="muted" id="beforeMeta"></p></div><div class="board"><h3 id="afterTitle">After this candidate</h3><svg id="afterPlot" class="plot" viewBox="-100 -100 200 200" role="img" aria-label="Current partial board"></svg><p class="muted" id="afterMeta"></p></div></div><p class="status" id="transition"></p><p class="status warning" id="blockers"></p></section></div>
<div class="sources">Source: <a href="__SOURCE_LINK__">event-state JSON</a> · <a href="../../validation/throw-event-benchmark/canada-czech-2024/RESULTS.md">audit and reproduction</a> · <a href="provenance.json">viewer provenance</a></div></main>
<script>const DATA=__DATA__;
const $=id=>document.getElementById(id),events=DATA.events;let index=0;
function fmt(t){const m=Math.floor(t/60),s=(t%60).toFixed(1).padStart(4,'0');return `${m}:${s}`}
function text(id,value){$(id).textContent=value}
function svgNode(tag,attrs){const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));return el}
function plot(id,stones){const svg=$(id);svg.replaceChildren();svg.append(svgNode('rect',{x:-100,y:-100,width:200,height:200,fill:'#f9fcfc'}));for(let n=-4;n<=4;n++){const p=n*22;svg.append(svgNode('line',{x1:p,x2:p,y1:-100,y2:100,stroke:n===0?'#91aab5':'#e4edef','stroke-width':n===0?1.3:.7}));svg.append(svgNode('line',{x1:-100,x2:100,y1:p,y2:p,stroke:n===0?'#91aab5':'#e4edef','stroke-width':n===0?1.3:.7}))}svg.append(svgNode('circle',{cx:0,cy:0,r:3,fill:'#223e52'}));for(const stone of stones){const [x,y]=stone.position_m_conditional;if(!Number.isFinite(x)||!Number.isFinite(y))continue;const dot=svgNode('circle',{cx:x*22,cy:y*22,r:5.5,fill:stone.colour==='red'?'#d74643':'#f3c843',stroke:'#304655','stroke-width':1.3});const label=svgNode('title',{});label.textContent=`${stone.local_observation_id}: ${stone.colour}, (${x.toFixed(2)}, ${y.toFixed(2)}) conditional m`;dot.append(label);svg.append(dot)}}
function shown(){return events.map((_,i)=>i).filter(i=>(!$('onlyBoards').checked||events[i].post_event_observation.stones.length)&&(!$('onlyComparisons').checked||events[i].transition_from_previous_candidate.status==='view_local_partial_comparison'))}
function seekFrame(){if($('video').readyState>0)$('video').currentTime=Math.max(0,events[index].passage_time_s-8)}
function options(){const visible=shown();$('eventSelect').replaceChildren(...visible.map(i=>{const o=document.createElement('option');o.value=i;o.textContent=`${i+1}/${events.length} · ${events[i].candidate_id} · ${fmt(events[i].passage_time_s)} · ${events[i].candidate_colour}`;return o}));if(!visible.includes(index))index=visible[0]??0;render();seekFrame()}
function render(){const row=events[index],before=events[index-1],current=row.post_event_observation,prior=before?.post_event_observation,step=row.transition_from_previous_candidate;$('eventSelect').value=index;text('title',`${row.candidate_id} · ${row.candidate_colour} candidate`);text('eventMeta',`Passage ${fmt(row.passage_time_s)} · ${row.passage_time_semantics.replaceAll('_',' ')} · receiving view ${current.receiving_view}`);plot('beforePlot',prior?.stones??[]);plot('afterPlot',current.stones);text('beforeTitle',before?`After ${before.candidate_id}`:'No earlier candidate');text('afterTitle',`After ${row.candidate_id}`);text('beforeMeta',prior?`${prior.stones.length} stable visible proposal(s) · ${prior.receiving_view} camera`:'No previous board');text('afterMeta',`${current.stones.length} stable visible proposal(s) · ${current.status.replaceAll('_',' ')}`);const comparable=step.status==='view_local_partial_comparison';$('transition').className=`status ${comparable?'':'warning'}`;text('transition',comparable?`${step.matched_local_observations.length} nearby same-colour observation pair(s) in the same camera. Physical stone identity and additions/removals remain unverified.`:`Transition abstains: ${step.status.replaceAll('_',' ')}${step.intervening_passage_candidate_ids.length?`; intervening candidates ${step.intervening_passage_candidate_ids.join(', ')}`:''}. Panels must not be read as a complete before/after state.`);text('blockers',`Simulation blocked: ${row.simulation_blockers.map(x=>x.replaceAll('_',' ')).join('; ')}.`);const ev=$('evidence');ev.replaceChildren();for(const [label,value] of [['Quiet board interval',current.quiet_tail_s?current.quiet_tail_s.map(fmt).join('–'):'not observed'],['Observed stone proposals',current.stones.length],['Adjacent comparison',step.status.replaceAll('_',' ')],['Physical throw identity','unverified'],['Stone identity across states','unverified'],['Same end',step.same_end_verified?'verified':'unverified']]){const div=document.createElement('div'),b=document.createElement('b'),span=document.createElement('span');b.textContent=label;span.textContent=value;div.append(b,span);ev.append(div)}}
const baseRender=render;render=function(){baseRender();const review=events[index].agent_source_review,flag=$('reviewFlag');flag.hidden=!review;flag.textContent=review?`Agent source review (not independent validation): ${review.conclusion.replaceAll('_',' ')}. ${review.basis}`:''};
function move(delta){const visible=shown(),at=visible.indexOf(index);index=visible[Math.max(0,Math.min(visible.length-1,at+delta))]??index;render();seekFrame()}
$('eventsCount').textContent=DATA.event_count;$('boardsCount').textContent=DATA.observed_board_count;$('compCount').textContent=DATA.comparable_transition_count;$('readyCount').textContent=DATA.simulation_ready_count;$('eventSelect').onchange=e=>{index=Number(e.target.value);render();seekFrame()};$('previous').onclick=()=>move(-1);$('next').onclick=()=>move(1);$('seek').onclick=()=>{seekFrame();$('video').play()};$('video').addEventListener('loadedmetadata',seekFrame);$('onlyBoards').onchange=options;$('onlyComparisons').onchange=options;window.onkeydown=e=>{if(['INPUT','SELECT','VIDEO'].includes(e.target.tagName))return;if(e.key==='ArrowLeft')move(-1);if(e.key==='ArrowRight')move(1)};options();
</script></body></html>"""


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--branch", default="Frozen 79-candidate baseline")
    args = parser.parse_args()
    source = args.source.resolve()
    directory = args.directory.resolve()
    html = directory / "index.html"
    provenance = directory / "provenance.json"
    if html.exists() or provenance.exists():
        raise SystemExit("Viewer already exists; preserve first render")
    data = json.loads(source.read_text())
    if data["event_count"] != len(data["events"]) or any(
        row["simulation_ready"] for row in data["events"]
    ):
        raise ValueError("Input event accounting or simulation gate differs")
    directory.mkdir(parents=True, exist_ok=True)
    embedded = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    source_link = Path(os.path.relpath(source, directory)).as_posix()
    rendered = (
        TEMPLATE.replace("__DATA__", embedded)
        .replace("__BRANCH__", escape(args.branch))
        .replace("__SOURCE_LINK__", escape(source_link, quote=True))
    )
    html.write_text(rendered + "\n")
    provenance.write_text(
        json.dumps(
            {
                "status": "offline_provisional_event_partial_state_viewer_not_physics_simulation",
                "branch": args.branch,
                "source_sequence_sha256": digest(source),
                "runner_sha256": digest(Path(__file__)),
                "html_sha256": digest(html),
                "event_count": data["event_count"],
                "observed_board_count": data["observed_board_count"],
                "comparable_transition_count": data["comparable_transition_count"],
                "simulation_ready_count": data["simulation_ready_count"],
            },
            indent=2,
        )
        + "\n"
    )
    print(html)


if __name__ == "__main__":
    main()
