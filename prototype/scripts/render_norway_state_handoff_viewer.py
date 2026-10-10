"""Render an offline, schematic 128-shot evidence handoff viewer."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "validation/official-shot-sequence/norway-full-match-evidence-state-handoff-first.json"
DIR = ROOT / "validation/official-shot-sequence/norway-state-handoff"
HTML = DIR / "index.html"
PROVENANCE = DIR / "provenance.json"


TEMPLATE = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Norway match · 128-shot evidence handoff</title>
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#182c3c;background:#eef2f4}
*{box-sizing:border-box}body{margin:0}header{background:#102a3c;color:white;padding:24px max(24px,calc((100vw - 1160px)/2))}header h1{margin:0 0 6px;font-size:30px}header p{margin:0;color:#d1e0e9;max-width:850px;line-height:1.45}
main{max-width:1160px;margin:22px auto;padding:0 20px 40px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.stat,.card{background:white;border:1px solid #d7e0e5;border-radius:10px;box-shadow:0 2px 8px #1630470a}.stat{padding:14px}.stat strong{display:block;font-size:27px}.stat span{font-size:13px;color:#526979}
.controls{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:18px 0}button,select{font:inherit;border:1px solid #a6b7c1;background:white;color:#183246;border-radius:7px;padding:9px 12px}button{cursor:pointer}button:hover{background:#e6f1f6}select{min-width:220px}.small{font-size:13px;color:#526979}
.layout{display:grid;grid-template-columns:1fr 1fr;gap:16px}.card{padding:18px}.card h2{margin:0 0 6px;font-size:19px}.card p{margin:6px 0 12px;color:#526979;font-size:14px}.rink{height:400px;width:100%;background:#f9fbfc;border:1px solid #d9e3e8;border-radius:8px}.meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 16px;margin:14px 0 0}.meta dt{font-size:12px;color:#617584}.meta dd{margin:0;font-weight:600;overflow-wrap:anywhere}.pill{display:inline-block;font-size:12px;font-weight:700;padding:4px 8px;border-radius:20px;background:#e4edf3;color:#173b53}.pill.partial{background:#dff1e6;color:#1d6842}.pill.unknown{background:#f7e9d7;color:#845010}
.note{border-left:4px solid #b47430;background:#fff8eb;padding:13px 16px;margin:18px 0;line-height:1.45}.row{margin:6px 0;font-size:14px;color:#344e60}.sources{font-size:13px;color:#587082;margin-top:16px}.sources a{color:#245e82}
@media(max-width:800px){.stats{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}.rink{height:340px}}@media(max-width:480px){.stats{grid-template-columns:1fr 1fr}header h1{font-size:24px}.controls select{width:100%}}
</style>
<header><h1>Canada–Norway · 128-shot evidence handoff</h1><p>Browse the official shot sequence alongside what this broadcast actually supports. The left panel is an independent PDF diagram reference. The right panel shows partial source-video observations in camera-image coordinates.</p></header>
<main>
<div class="stats"><div class="stat"><strong id="countSlots"></strong><span>official shot slots</span></div><div class="stat"><strong id="countCounters"></strong><span>broadcast counter observations</span></div><div class="stat"><strong id="countBoards"></strong><span>slots with a stable video house observation</span></div><div class="stat"><strong>0</strong><span>video physics replays verified</span></div></div>
<div class="controls"><button id="previous" aria-label="Previous shot">← Previous</button><select id="shotSelect" aria-label="Shot"></select><button id="next" aria-label="Next shot">Next →</button><label class="small"><input id="onlyVideo" type="checkbox"> Show only slots with video board</label></div>
<div id="shotTitle" class="row"></div>
<div class="layout">
<section class="card"><h2>Official diagram reference</h2><p>Static post-shot stone symbols from the official PDF; schematic house-radius coordinates.</p><svg id="officialRink" class="rink" viewBox="-140 -330 280 460" role="img" aria-label="Official diagram stone positions"></svg><dl id="officialMeta" class="meta"></dl></section>
<section class="card"><h2>Source-video partial house</h2><p>Repeated visible stones in one camera shot. +x is image right; +y is image down. Orientation may be unknown.</p><svg id="videoRink" class="rink" viewBox="-140 -330 280 460" role="img" aria-label="Observed video stone positions"></svg><div class="controls"><select id="cameraSelect" aria-label="Camera shot"></select></div><dl id="videoMeta" class="meta"></dl></section>
</div>
<div class="note">The official diagram and video panel use separate evidence. Similar-looking positions do not prove the same stone was tracked across a camera cut. Video release time, complete sheet state, revolutions, metric trajectory and physical simulation remain unverified.</div>
<div class="sources">Data: <a href="../norway-full-match-evidence-state-handoff-first.json">full evidence ledger</a> · <a href="../NORWAY-FULL-MATCH-SLOT-SCAFFOLD.md">shot-slot method</a> · <a href="../NORWAY-FULL-MATCH-POST-BOARD-COVERAGE.md">video board coverage</a></div>
</main>
<script>const DATA=__DATA__;
const $=id=>document.getElementById(id), slots=DATA.slots;let index=0;
const esc=s=>String(s??'unknown').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function grid(svg,stones,key){const scale=100,parts=[`<rect x="-125" y="-315" width="250" height="430" fill="#f9fbfc"/>`,`<line x1="0" x2="0" y1="-315" y2="115" stroke="#b5c8d2" stroke-width="1"/>`,`<circle cx="0" cy="0" r="100" fill="#438dc1"/>`,`<circle cx="0" cy="0" r="65" fill="white"/>`,`<circle cx="0" cy="0" r="36" fill="#d45d59"/>`,`<circle cx="0" cy="0" r="9" fill="white"/>`];for(const stone of stones){const [x,y]=stone[key];if(!Number.isFinite(x)||!Number.isFinite(y))continue;parts.push(`<circle cx="${(x*scale).toFixed(2)}" cy="${(y*scale).toFixed(2)}" r="6.5" fill="${stone.colour==='red'?'#c73936':'#edc837'}" stroke="#34414a" stroke-width="1.4"/>`)}svg.innerHTML=parts.join('')}
function meta(el,entries){el.innerHTML=entries.map(([name,value])=>`<div><dt>${esc(name)}</dt><dd>${esc(value)}</dd></div>`).join('')}
function visibleIndices(){return slots.map((_,i)=>i).filter(i=>!$('onlyVideo').checked||slots[i].video_post_shot_state.camera_groups.length)}
function updateOptions(){const current=index,vis=visibleIndices();$('shotSelect').innerHTML=vis.map(i=>`<option value="${i}">End ${slots[i].end} · shot ${slots[i].shot_number}${slots[i].video_post_shot_state.camera_groups.length?' · video board':''}</option>`).join('');if(!vis.includes(current))index=vis[0]??0;$('shotSelect').value=index;render()}
function render(){const row=slots[index],ref=row.official_reference,evt=row.video_event_evidence,groups=row.video_post_shot_state.camera_groups;$('shotSelect').value=index;$('shotTitle').innerHTML=`<strong>End ${row.end}, shot ${row.shot_number}</strong> · ${esc(row.official_shot_id)} · <span class="pill ${groups.length?'partial':'unknown'}">${groups.length?'partial video board':'video board unknown'}</span>`;grid($('officialRink'),ref.post_shot_diagram_stones,'house_radius_coordinates');meta($('officialMeta'),[['Team / handle',`${ref.team} / ${ref.handle_colour}`],['Shooter',ref.shooter],['Shot type',ref.shot_type],['Official turn direction',ref.turn_direction],['Revolutions','unknown'],['Reference scope','PDF diagram, not full rink']]);$('cameraSelect').hidden=groups.length<2;$('cameraSelect').innerHTML=groups.map((g,i)=>`<option value="${i}">${esc(g.camera_shot_id)} · ${g.stable_image_relative_stones.length} visible</option>`).join('');renderVideo(0)}
function renderVideo(groupIndex){const row=slots[index],evt=row.video_event_evidence,groups=row.video_post_shot_state.camera_groups,group=groups[groupIndex];grid($('videoRink'),group?group.stable_image_relative_stones:[],'image_house_radius_coordinates');meta($('videoMeta'),[['Association',evt.association_basis.replaceAll('_',' ')],['Counter',evt.counter_id??'not observed'],['Candidate camera shot',evt.candidate_camera_shot_id??'none'],['Observed camera shot',group?.camera_shot_id??'none'],['Observation interval',group?group.observation_interval_s.map(n=>n.toFixed(1)+' s').join(' – '):'unknown'],['Layout side',group?.layout_side_proxy??'unknown'],['Motion approach proposal',group?.source_motion_approach_side_proposal??'none'],['Source state',group?'partial house':'unobserved']])}
function move(delta){const vis=visibleIndices();let at=vis.indexOf(index);at=Math.max(0,Math.min(vis.length-1,at+delta));index=vis[at]??index;render()}
$('countSlots').textContent=DATA.official_slot_count;$('countCounters').textContent=slots.filter(x=>x.video_event_evidence.counter_id).length;$('countBoards').textContent=DATA.slots_with_stable_video_house_observation;
$('shotSelect').onchange=e=>{index=Number(e.target.value);render()};$('cameraSelect').onchange=e=>renderVideo(Number(e.target.value));$('previous').onclick=()=>move(-1);$('next').onclick=()=>move(1);$('onlyVideo').onchange=updateOptions;window.onkeydown=e=>{if(e.target.tagName==='SELECT'||e.target.tagName==='INPUT')return;if(e.key==='ArrowLeft')move(-1);if(e.key==='ArrowRight')move(1)};updateOptions();
</script></html>'''


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if HTML.exists() or PROVENANCE.exists():
        raise SystemExit("First offline state viewer already exists")
    data = json.loads(SOURCE.read_text())
    if data["official_slot_count"] != 128:
        raise SystemExit("State handoff slot count changed")
    DIR.mkdir(parents=True, exist_ok=True)
    embedded = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    HTML.write_text(TEMPLATE.replace("__DATA__", embedded) + "\n")
    PROVENANCE.write_text(json.dumps({
        "status": "offline_schematic_reference_and_partial_video_state_viewer",
        "source_handoff_sha256": digest(SOURCE),
        "runner_sha256": digest(Path(__file__)),
        "html_sha256": digest(HTML),
        "official_slot_count": data["official_slot_count"],
        "video_physics_simulation_ready_count": data["video_physics_simulation_ready_count"],
        "limitations": ["Static official schematic and partial image-coordinate observations only.",
                        "No tracked physical throw animation or complete game state is inferred."],
    }, indent=2) + "\n")
    print(HTML)


if __name__ == "__main__":
    main()
