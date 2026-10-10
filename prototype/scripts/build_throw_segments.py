from pathlib import Path
import json, sys, csv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from throw_segmentation import review_segments, visible_settling

out = ROOT / "throw-segments"
events = json.loads((ROOT / "throw-analysis/predictions.json").read_text())["events"]
segments = review_segments(events, 1650, 2760)
data = []
for s in segments:
    r = json.loads((out / (s["id"] + ".json")).read_text())
    o = r["outcome"]
    s.update(
        colour=r["event"]["colour"],
        observed_motion_start_s=r["event"]["first_observed_s"],
        physical_release_s=None,
        outcome_status=o["status"],
        association_reason=o.get("reason", o.get("association_basis")),
        candidate_tracks=o.get("candidate_tracks"),
        settling=visible_settling(r),
        delivered_stone_settling=o.get("settled"),
        arrival_trajectory=o.get("trajectory", []),
        departure_trajectory=r["event"]["trajectory"],
        analysis_sample_count=r["analysis_sample_count"],
        accepted_calibration_samples=r["calibration_accepted_samples"],
        analysis_interval_s=r["receiving_analysis_interval_s"],
    )
    delivered_confirmation = o.get("settled", {}).get("time_s") if o.get("settled") else None
    scene_confirmation = s["settling"].get("confirmed_at_s")
    s["candidate_active_window"] = {
        "status": "provisional_delivered_stone_stability" if delivered_confirmation is not None else "end_unresolved",
        "start_s": s["observed_motion_start_s"],
        "end_confirmation_s": delivered_confirmation,
        "end_is_physical_stop": False,
        "reason": "Starts at first tracked stone observation; ends at the delivered-stone stability confirmation, when available. Physical release and stop times remain unknown.",
    }
    s["visible_scene_stability_confirmation_s"] = scene_confirmation
    s["pre_gate_path"] = {"status": "unobserved", "straight_line_assumption_used": False}
    data.append(s)
summary = {
    "review_segments": len(data),
    "associated_arrivals": sum(s["outcome_status"] == "provisional_association" for s in data),
    "delivered_stone_settling_candidates": sum(
        s["delivered_stone_settling"] is not None for s in data
    ),
    "visible_scene_settling_candidates": sum(
        s["settling"]["status"] == "visible_scene_stable_candidate" for s in data
    ),
    "physically_validated_ends": 0,
    "candidate_active_windows": sum(s["candidate_active_window"]["end_confirmation_s"] is not None for s in data),
}
result = {
    "summary": summary,
    "source_interval_s": [1650, 2760],
    "unassigned_pre_first_passage_s": [1650, data[0]["start_s"]],
    "segments": data,
    "claim": "Source-specific review segmentation and provisional receiving tracks; full physical throw boundaries and trajectories are not independently validated.",
}
(out / "results.json").write_text(json.dumps(result, indent=2))
with (out / "segments.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(
        [
            "throw",
            "colour",
            "source_start_s",
            "source_end_s",
            "boundary_reason",
            "arrival_status",
            "visible_stability_confirmation_s",
            "delivered_stone_stability_confirmation_s",
            "candidate_active_start_s",
            "candidate_active_end_confirmation_s",
            "physical_end_verified",
        ]
    )
    for s in data:
        w.writerow(
            [
                s["id"],
                s["colour"],
                s["start_s"],
                s["end_s"],
                s["end_reason"],
                s["outcome_status"],
                s["settling"].get("confirmed_at_s", ""),
                s["candidate_active_window"]["end_confirmation_s"] if s["candidate_active_window"]["end_confirmation_s"] is not None else "",
                s["candidate_active_window"]["start_s"],
                s["candidate_active_window"]["end_confirmation_s"] if s["candidate_active_window"]["end_confirmation_s"] is not None else "",
                False,
            ]
        )
html = """<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Lancers : segmentation continue</title><style>body{max-width:1200px;margin:35px auto;padding:0 20px;background:#f5f2e9;color:#173b38;font:17px/1.5 system-ui}h1{font:48px Georgia}button{padding:10px;margin:3px;border:1px solid #173b38;border-radius:7px;background:white;color:#173b38;cursor:pointer}button.active{background:#173b38;color:white}.views{display:grid;grid-template-columns:2fr 1fr;gap:20px}video,canvas{width:100%;background:white;border-radius:12px}.wrap{position:relative}.wrap canvas{position:absolute;inset:0;height:100%;background:transparent;pointer-events:none}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:8px;border-bottom:1px solid #ccc}.scroll{overflow:auto}.note{border-left:4px solid #a64239;padding:15px;background:white}@media(max-width:700px){.views{grid-template-columns:1fr}h1{font-size:34px}}</style><h1>Du passage au segment de lancer</h1><p id="summary"></p><div id="buttons"></div><h2 id="title"></h2><div class="views"><div><div class="wrap"><video id="v" controls preload="metadata" src="../throw-analysis/end3.mp4"></video><canvas id="overlay" width="1920" height="1080"></canvas></div><p><button id="start">Passage</button><button id="arrival">Arrivée</button><button id="settled">Stabilité candidate</button><label><input type="checkbox" id="stop" checked> Arrêter à la limite du segment</label></p><p id="clock"></p><p id="status"></p></div><canvas id="board" width="420" height="760"></canvas></div><p class="note">Les segments vont du passage à la ligne virtuelle jusqu’au passage suivant ; le dernier finit à la fin de l’extrait. Ce découpage inclut l’attente entre les lancers. Une stabilité visible pendant 2 secondes est un indice de fin, pas une preuve que toutes les pierres ont cessé de bouger. Les trajectoires sont partielles et l’association entre caméras reste provisoire.</p><p>Avant la ligne : aucune trajectoire inventée. Une droite pourrait être ajoutée comme hypothèse explicitement marquée, mais il manque une position de lâcher validée. La courbe ci-dessous utilise uniquement les observations de réception après le passage ; les lacunes supérieures à 0,75 seconde sont laissées vides.</p><div class="scroll"><table><thead><tr><th>Lancer</th><th>Passage → limite (source)</th><th>Arrivée associée</th><th>Stabilité visible candidate</th></tr></thead><tbody id="rows"></tbody></table></div><h2>Vérifier les fins candidates</h2><p>Pour chaque candidat : images à −2 s, à la confirmation et à +2 s. Ce sont des éléments à examiner, pas des références annotées de fin.</p><div id="endpointEvidence"></div><p><a href="../pre-gate-audit/index.html">Test de la droite avant la ligne</a> · <a href="../cross-view/index.html">Liaison entre les deux vues</a> · <a href="segments.csv">Segments CSV</a> · <a href="results.json">Résultats JSON</a> · <a href="../trajectory-accuracy/index.html">Audit manuel du lancer 11</a> · <a href="../throw-analysis/index.html">Évaluation des passages</a></p><script>const D=DATA,v=document.getElementById('v'),g=document.getElementById('board').getContext('2d'),og=document.getElementById('overlay').getContext('2d');let selected=0;function fmt(t){return Math.floor(t/60)+':'+(t%60).toFixed(1).padStart(4,'0')}function seek(t){v.pause();v.currentTime=t-1650}function choose(i){selected=i;const s=D.segments[i];document.getElementById('title').textContent=s.id+' · '+(s.colour==='red'?'rouge':'jaune');document.getElementById('status').textContent=s.outcome_status==='provisional_association'?'Arrivée associée provisoirement. Géométrie acceptée sur '+s.accepted_calibration_samples+'/'+s.analysis_sample_count+' observations.':'Arrivée non résolue : '+(s.candidate_tracks??0)+' pistes candidates. Aucune trajectoire attribuée.';document.getElementById('arrival').disabled=!s.arrival_trajectory.length;document.getElementById('settled').disabled=!s.settling.confirmed_at_s;document.querySelectorAll('#buttons button').forEach((b,j)=>b.classList.toggle('active',i===j));seek(s.start_s)}document.getElementById('summary').textContent=`${D.summary.review_segments} segments · ${D.summary.associated_arrivals} arrivées associées provisoirement · ${D.summary.visible_scene_settling_candidates} stabilités visibles candidates · aucune fin physique validée indépendamment.`;document.getElementById('buttons').innerHTML=D.segments.map((s,i)=>`<button onclick="choose(${i})">${s.id}</button>`).join('');document.getElementById('rows').innerHTML=D.segments.map(s=>`<tr><td>${s.id}</td><td>${fmt(s.start_s)} → ${fmt(s.end_s)}</td><td>${s.arrival_trajectory.length?'provisoire':'non résolue'}</td><td>${s.settling.confirmed_at_s?fmt(s.settling.confirmed_at_s):'non résolue'}</td></tr>`).join('');document.getElementById('start').onclick=()=>seek(D.segments[selected].start_s);document.getElementById('arrival').onclick=()=>seek(D.segments[selected].arrival_trajectory[0].time_s);document.getElementById('settled').onclick=()=>seek(D.segments[selected].settling.confirmed_at_s);document.getElementById('endpointEvidence').innerHTML=D.segments.filter(s=>s.settling.confirmed_at_s).map(s=>`<details><summary>${s.id} : stabilité visible candidate à ${fmt(s.settling.confirmed_at_s)}</summary><a href="${s.id}-endpoint.jpg"><img loading="lazy" style="width:100%" src="${s.id}-endpoint.jpg" alt="Trois images autour de la fin candidate ${s.id}"></a></details>`).join('');function xy(p){return [210+p[0]*65,150+p[1]*65]}function draw(){const s=D.segments[selected],t=v.currentTime+1650;if(document.getElementById('stop').checked&&!v.paused&&t>=s.end_s){v.pause();v.currentTime=s.end_s-1650}g.clearRect(0,0,420,760);for(const [r,col] of [[1.829,'#8cbacb'],[1.219,'white'],[.610,'#d99a92']]){g.fillStyle=col;g.beginPath();g.arc(210,150,r*65,0,7);g.fill()}g.strokeStyle='#bbb';g.beginPath();g.moveTo(210,0);g.lineTo(210,760);g.stroke();let prev=null;g.strokeStyle='#207c70';g.lineWidth=3;const end=s.settling.confirmed_at_s||s.analysis_interval_s[1];for(const p of s.arrival_trajectory.filter(p=>p.time_s>=s.start_s&&p.time_s<=Math.min(t,end))){if(!p.position_m){prev=null;continue}if(prev&&p.time_s-prev.time_s<=.75){g.beginPath();g.moveTo(...xy(prev.position_m));g.lineTo(...xy(p.position_m));g.stroke()}prev=p}if(prev&&Math.abs(t-prev.time_s)<=.51){g.fillStyle=s.colour==='yellow'?'#dab000':'#c84b3f';g.beginPath();g.arc(...xy(prev.position_m),10,0,7);g.fill()}g.fillStyle='#173b38';g.font='14px system-ui';g.fillText('Réception : coordonnées locales en mètres',12,25);g.fillText('Trajectoire partielle, sans liaison des caméras',12,740);og.clearRect(0,0,1920,1080);og.strokeStyle='#00e5d1';og.lineWidth=3;og.beginPath();og.moveTo(120,180);og.lineTo(840,180);og.stroke();let lastDeparture=null;og.strokeStyle='#00e5d1';for(const p of s.departure_trajectory.filter(p=>p.time_s>=s.start_s&&p.time_s<=t)){if(lastDeparture&&p.time_s-lastDeparture.time_s<.4){og.beginPath();og.moveTo(lastDeparture.pixel[0]*3,lastDeparture.pixel[1]*3);og.lineTo(p.pixel[0]*3,p.pixel[1]*3);og.stroke()}lastDeparture=p}const points=s.arrival_trajectory.filter(p=>Math.abs(p.time_s-t)<=.1&&p.time_s<=end);for(const p of points){og.strokeStyle='#ffe000';og.beginPath();og.arc(...p.pixel,20,0,7);og.stroke()}document.getElementById('clock').textContent='Source '+fmt(t)+' · segment '+fmt(s.start_s)+' → '+fmt(s.end_s);requestAnimationFrame(draw)}v.addEventListener('loadedmetadata',()=>choose(0),{once:true});choose(0);draw();</script></html>""".replace(
    "DATA", json.dumps(result)
)
def replace_viewer(old: str, new: str) -> None:
    global html
    if old not in html:
        raise RuntimeError(f"Missing viewer fragment: {old[:80]}")
    html = html.replace(old, new)


replace_viewer(
    '<button id="start">Passage</button>',
    '<button id="onset">Premier point suivi</button><button id="start">Passage</button>',
)
replace_viewer(
    '<p id="clock"></p><p id="status"></p>',
    '<p id="clock"></p><p id="onset-status"></p><p id="status"></p>',
)
replace_viewer(
    'Avant la ligne : aucune trajectoire inventée. Une droite pourrait être ajoutée comme hypothèse explicitement marquée, mais il manque une position de lâcher validée.',
    'Avant la ligne : les points suivis sont affichés à partir de leur première observation. Le lâcher physique reste inconnu quand le contact avec le dispositif de lancer est masqué.',
)
replace_viewer(
    "document.querySelectorAll('#buttons button').forEach((b,j)=>b.classList.toggle('active',i===j));seek(s.start_s)",
    "document.getElementById('onset-status').textContent='Premier point suivi : '+fmt(s.observed_motion_start_s)+' · passage : '+fmt(s.start_s)+' · lâcher physique : inconnu.';document.querySelectorAll('#buttons button').forEach((b,j)=>b.classList.toggle('active',i===j));seek(s.observed_motion_start_s)",
)
replace_viewer(
    "document.getElementById('start').onclick=()=>seek(D.segments[selected].start_s);",
    "document.getElementById('onset').onclick=()=>seek(D.segments[selected].observed_motion_start_s);document.getElementById('start').onclick=()=>seek(D.segments[selected].start_s);",
)
replace_viewer(
    's.departure_trajectory.filter(p=>p.time_s>=s.start_s&&p.time_s<=t)',
    's.departure_trajectory.filter(p=>p.time_s>=s.observed_motion_start_s&&p.time_s<=t)',
)
replace_viewer(
    '<th>Stabilité visible candidate</th>',
    '<th>Stabilité pierre livrée</th><th>Stabilité scène visible</th>',
)
replace_viewer(
    '${D.summary.visible_scene_settling_candidates} stabilités visibles candidates · aucune fin physique validée indépendamment.',
    '${D.summary.candidate_active_windows} fenêtres actives candidates · ${D.summary.visible_scene_settling_candidates} stabilités de scène visibles · aucune fin physique validée indépendamment.',
)
replace_viewer(
    "<td>${s.settling.confirmed_at_s?fmt(s.settling.confirmed_at_s):'non résolue'}</td>",
    "<td>${s.candidate_active_window.end_confirmation_s?fmt(s.candidate_active_window.end_confirmation_s):'non résolue'}</td><td>${s.settling.confirmed_at_s?fmt(s.settling.confirmed_at_s):'non résolue'}</td>",
)
replace_viewer(
    '<h2>Vérifier les fins candidates</h2>',
    '<p class="note">Fenêtre active candidate : du premier point suivi à la confirmation de stabilité de la pierre livrée, si elle existe. Le départ précède le passage ; la confirmation suit l’arrêt supposé d’au moins la fenêtre de stabilité. Ni l’un ni l’autre n’est un instant physique de lâcher ou de fin. La stabilité de toute la scène visible est indiquée séparément.</p><h2>Vérifier les fins candidates</h2>',
)
(out / "index.html").write_text(html)
print(summary)
