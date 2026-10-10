from pathlib import Path
import json, sys, hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cross_view import connect, TEE_DISTANCE_M, HOG_FROM_TEE_M

out = ROOT / "cross-view"
rows = []
for i in range(1, 17):
    name = f"T{i:02}"
    rows.append(
        connect(
            json.loads((ROOT / "throw-segments" / (name + ".json")).read_text()),
            json.loads((out / (name + "-departure.json")).read_text()),
        )
    )
config = {
    "tee_distance_m": TEE_DISTANCE_M,
    "hog_from_tee_m": HOG_FROM_TEE_M,
    "dimension_source": "../../feasibility/sources/Rules-2025.pdf, diagram on PDF page 5. Nominal dimensions, not a survey of this rink.",
    "global_axes": "Origin departure tee; +Y toward receiving tee; +X image-right in this source.",
    "departure_transform": "X=x_local; Y=-y_local",
    "receiving_transform": "X=x_local; Y=34.747-y_local",
    "orientation_status": "Source-specific orientation hypothesis from line layout and outgoing/incoming motion. Both panels treated as looking along +Y, with no broadcast mirroring. Not independently surveyed or solved from overlapping landmarks.",
    "time_offset_s": 0,
    "time_basis": "Both panels are decoded from the same composite video frame. No additional production delay between panels measured.",
    "height_model": "Existing conditional cap-height correction, 0.136 m; each view has its own registered calibration.",
    "association_rule": "Unique new same-colour receiving track within 35 s, crossing receiving hog line inward; positive time and forward rink displacement from departure observations. No ranking to force a match.",
    "development_status": "Rule developed on this end, including inspection of ambiguous T08. No held-out association accuracy claimed.",
}
summary = {
    "throws": len(rows),
    "provisional_links": sum(r["status"] == "provisional_link" for r in rows),
    "departure_positions": sum(len(r["departure"]) for r in rows),
    "departure_samples": sum(r["departure_samples"] for r in rows),
    "independently_verified_links": 0,
    "interpolated_gaps": 0,
}
result = {"configuration": config, "summary": summary, "throws": rows}
probe = json.loads((out / "T11-far-receiving-probe.json").read_text())
config["t11_provisional_receiving_bounds_m"] = probe["expanded_world_bounds_m"]
config["t11_provisional_receiving_status"] = probe["physical_accuracy_status"]
t11 = next(row for row in rows if row["id"] == "T11")
early = [
    {
        "time_s": 2260 + row["clip_time_s"],
        "pixel": row["candidates"][0]["pixel"],
        "local_m": row["candidates"][0]["ground_position_m"],
        "world_m": [
            row["candidates"][0]["ground_position_m"][0],
            TEE_DISTANCE_M - row["candidates"][0]["ground_position_m"][1],
        ],
        "scope": "range_expanded_diagnostic",
    }
    for row in probe["records"]
    if row["candidates"] and 2260 + row["clip_time_s"] < t11["arrival"][0]["time_s"] - 1e-6
]
assert early and abs(early[0]["time_s"] - t11["departure"][-1]["time_s"]) < 1e-6
t11["display_arrival"] = early + t11["arrival"]
left_end, right_start = t11["departure"][-1], early[0]
t11["expanded_handoff"] = {
    "time_s": right_start["time_s"],
    "sampled_gap_s": right_start["time_s"] - left_end["time_s"],
    "longitudinal_disagreement_m": right_start["world_m"][1] - left_end["world_m"][1],
    "lateral_disagreement_m": right_start["world_m"][0] - left_end["world_m"][0],
    "status": "provisional_far_geometry_and_identity",
    "source": "T11-far-receiving-probe.json",
}
(out / "results.json").write_text(json.dumps(result, indent=2))
(out / "configuration.json").write_text(json.dumps(config, indent=2))
print(summary)
html = r"""<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Deux vues, un lancer</title><style>body{max-width:1200px;margin:35px auto;padding:0 20px;background:#f5f2e9;color:#173b38;font:17px/1.5 system-ui}h1{font:46px Georgia}button{padding:10px;margin:3px;border:1px solid #173b38;background:white;color:#173b38;border-radius:7px;cursor:pointer}button.active{background:#173b38;color:white}.layout{display:grid;grid-template-columns:minmax(0,1fr) 270px;gap:24px}video,canvas{width:100%;border-radius:10px;background:white}.wrap{position:relative}.wrap canvas{position:absolute;inset:0;height:100%;background:transparent;pointer-events:none}.note{padding:16px;background:white;border-left:4px solid #a64239}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}.scroll{overflow:auto}a{color:#006f67}@media(max-width:700px){.layout{grid-template-columns:1fr}#rink{max-width:270px;margin:auto}h1{font-size:32px}}</style><h1>Deux vues, un lancer</h1><p id="summary"></p><div id="buttons"></div><h2 id="title"></h2><div class="layout"><div><div class="wrap"><video id="v" controls preload="metadata" src="../throw-analysis/end3.mp4"></video><canvas id="overlay" width="1920" height="1080"></canvas></div><p><button id="departure">Départ observé</button><button id="gate">Ligne virtuelle</button><button id="arrival">Arrivée observée</button><button id="show">Voir les deux traces</button></p><p id="clock"></p><p id="gap"></p><p id="coverage"></p><p class="note">Une calibration par caméra, puis deux transformations vers un repère commun. Pour T11, la zone de projection élargie montre aussi la caméra d’arrivée avant la hog line : les deux traces commencent à se chevaucher à 46,7 s. Leur écart au même instant est affiché, sans corriger arbitrairement la géométrie. Pour les autres lancers, les zones grises restent des lacunes du traitement borné. Les observations avant le début de la piste restent également inconnues.</p><p>Vert : départ. Orange : réception. Les traces disponibles sont affichées pour comparer les positions, jusqu’à la première stabilité candidate de la pierre lorsqu’elle est trouvée. Les observations brutes ultérieures restent dans le JSON ; les cercles indiquent uniquement une observation proche de l’instant vidéo, sans prédiction entre images.</p><details><summary>Hypothèses de géométrie et d’identité</summary><p>Origine : centre de la maison de départ. +Y vers la maison de réception ; +X vers la droite des images. Dans cette source, les deux panneaux sont traités comme regardant dans le même sens de piste, sans miroir. Cette orientation est une hypothèse explicite à valider indépendamment.</p><p>Départ : (x, −y). Réception : (x, 34,747 − y). Dimensions nominales du règlement ; distance réelle non mesurée. La projection de départ sort de la zone des cercles ayant servi à la calibration. Aucun chiffre de précision physique n’est établi ici.</p><p>Les deux panneaux partagent l’horloge du fichier, mais un éventuel décalage de production entre caméras n’a pas été mesuré. L’identité est proposée par couleur, ordre temporel et franchissement entrant de la hog line de réception. Elle n’est pas prouvée par une apparence unique de chaque pierre.</p><p>La règle a été développée sur cette manche, notamment après examen de T08. Le nombre de liens proposés n’est pas un score de précision sur des vidéos inédites.</p></details></div><canvas id="rink" width="270" height="1000"></canvas></div><h2>Associations proposées</h2><div class="scroll"><table><thead><tr><th>Lancer</th><th>Statut</th><th>Piste de réception</th><th>Intervalle du traitement initial</th><th>Déplacement longitudinal nominal</th></tr></thead><tbody id="rows"></tbody></table></div><h2>Preuves visuelles par lancer</h2><div id="evidence"></div><p><a href="results.json">Coordonnées et décisions</a> · <a href="configuration.json">Transformations et hypothèses</a> · <a href="../throw-segments/index.html">Segmentation et fins candidates</a> · <a href="../pre-gate-audit/index.html">Audit avant la ligne</a></p><script>const D=DATA,v=document.getElementById('v'),g=document.getElementById('rink').getContext('2d'),og=document.getElementById('overlay').getContext('2d');let selected=0;function fmt(t){return Math.floor(t/60)+':'+(t%60).toFixed(1).padStart(4,'0')}function seek(t){v.pause();v.currentTime=t-1650}function receive(r){return r.display_arrival||r.arrival}function choose(i){selected=i;const r=D.throws[i];document.getElementById('title').textContent=r.id+' · '+(r.colour==='red'?'rouge':'jaune');document.querySelectorAll('#buttons button').forEach((b,j)=>b.classList.toggle('active',i===j));document.getElementById('gap').textContent=r.expanded_handoff?`T11 : les deux caméras donnent une position à 46,7 s. Écart longitudinal nominal : ${r.expanded_handoff.longitudinal_disagreement_m.toFixed(2)} m ; latéral : ${Math.abs(r.expanded_handoff.lateral_disagreement_m).toFixed(2)} m. Le blanc de 5,8 s appartenait au filtre spatial initial ; identité et métrique restent provisoires.`:r.gap?`Lacune du traitement borné : ${r.gap.duration_s.toFixed(2)} s, déplacement longitudinal nominal ${r.gap.longitudinal_distance_m.toFixed(2)} m. Aucune interpolation.`:'Association non résolue.';document.getElementById('coverage').textContent=`Départ : ${r.departure.length}/${r.departure_samples} observations avec position conditionnelle. Réception : ${receive(r).length} observations attribuées provisoirement${r.display_arrival?" (dont points lointains expérimentaux)":""}.`;document.getElementById('arrival').disabled=!receive(r).length;seek(r.departure[0]?.time_s||r.gate_time_s)}document.getElementById('summary').textContent=`${D.summary.provisional_links}/${D.summary.throws} liens proposés entre vues. ${D.summary.departure_positions}/${D.summary.departure_samples} positions conditionnelles au départ. Aucun lien validé indépendamment ; aucun trajet inventé entre les vues.`;document.getElementById('buttons').innerHTML=D.throws.map((r,i)=>`<button onclick="choose(${i})">${r.id}</button>`).join('');document.getElementById('rows').innerHTML=D.throws.map(r=>`<tr><td>${r.id}</td><td>${r.status==='provisional_link'?'provisoire':'non résolu'}</td><td>${r.receiving_track_id??'?'}</td><td>${r.expanded_handoff?'0,0 s échantillonné (ancien : 5,8 s)':r.gap?r.gap.duration_s.toFixed(2)+' s':'?'}</td><td>${r.expanded_handoff?r.expanded_handoff.longitudinal_disagreement_m.toFixed(2)+' m écart':r.gap?r.gap.longitudinal_distance_m.toFixed(2)+' m':'?'}</td></tr>`).join('');document.getElementById('departure').onclick=()=>seek(D.throws[selected].departure[0]?.time_s||D.throws[selected].gate_time_s);document.getElementById('gate').onclick=()=>seek(D.throws[selected].gate_time_s);document.getElementById('arrival').onclick=()=>seek(receive(D.throws[selected])[0].time_s);document.getElementById('show').onclick=()=>seek(D.throws[selected].arrival.at(-1)?.time_s||D.throws[selected].gate_time_s);document.getElementById('evidence').innerHTML=D.throws.filter(r=>r.status==='provisional_link').map(r=>`<details><summary>${r.id} : départ et entrée dans la vue de réception</summary><a href="${r.id}-evidence.jpg"><img loading="lazy" style="width:100%" src="${r.id}-evidence.jpg" alt="Observations dans les deux vues pour ${r.id}"></a></details>`).join('');function xy(p){return [135+p[0]*24,920-p[1]*24]}function path(pts,col,maxGap){g.strokeStyle=col;g.lineWidth=3;let prev=null;for(const p of pts){const q=xy(p.world_m);if(prev&&p.time_s-prev.time_s<=maxGap){g.beginPath();g.moveTo(...xy(prev.world_m));g.lineTo(...q);g.stroke()}g.fillStyle=col;g.beginPath();g.arc(...q,2,0,7);g.fill();prev=p}}function draw(){const r=D.throws[selected],t=v.currentTime+1650;g.clearRect(0,0,270,1000);g.fillStyle='#fff';g.fillRect(0,0,270,1000);g.strokeStyle='#ccc';g.strokeRect(78,28,114,940);g.beginPath();g.moveTo(135,28);g.lineTo(135,968);g.stroke();for(const y of [0,D.configuration.tee_distance_m]){for(const [radius,col] of [[1.829,'#8cbacb'],[1.219,'white'],[.610,'#d99a92']]){g.fillStyle=col;g.beginPath();g.arc(...xy([0,y]),radius*24,0,7);g.fill()}}for(const y of [6.401,D.configuration.tee_distance_m-6.401]){g.strokeStyle='#5672a1';g.beginPath();g.moveTo(...xy([-2.375,y]));g.lineTo(...xy([2.375,y]));g.stroke()}if(r.gap&&!r.expanded_handoff){const ya=xy(r.departure.at(-1).world_m)[1],yb=xy(r.arrival[0].world_m)[1];g.fillStyle='#e9e7e1';g.fillRect(79,yb,112,ya-yb);g.fillStyle='#666';g.font='13px system-ui';g.fillText('Non observé',94,(ya+yb)/2)}path(r.departure,'#008578',.25);path(receive(r),'#c97815',.75);if(r.expanded_handoff){const a=xy(r.departure.at(-1).world_m),c=xy(receive(r)[0].world_m);g.setLineDash([4,3]);g.strokeStyle='#a43d3d';g.lineWidth=2;g.beginPath();g.moveTo(...a);g.lineTo(...c);g.stroke();g.setLineDash([]);g.fillStyle='#a43d3d';g.font='bold 12px system-ui';g.fillText('Δ 0,61 m',140,(a[1]+c[1])/2)}og.clearRect(0,0,1920,1080);for(const [pts,col,tol] of [[r.departure,'#00dcc4',.055],[receive(r),'#ffb300',.26]]){const p=pts.find(p=>Math.abs(p.time_s-t)<=tol);if(p){g.strokeStyle=col;g.lineWidth=3;g.beginPath();g.arc(...xy(p.world_m),7,0,7);g.stroke();og.strokeStyle=col;og.lineWidth=3;og.beginPath();og.arc(...p.pixel,16,0,7);og.stroke()}}g.fillStyle='#173b38';g.font='13px system-ui';g.fillText('Réception · Y = 34,747 m',45,18);g.fillText('Départ · Y = 0 m',74,990);document.getElementById('clock').textContent='Source '+fmt(t);requestAnimationFrame(draw)}v.addEventListener('loadedmetadata',()=>choose(10),{once:true});choose(10);draw();</script></html>""".replace(
    "DATA", json.dumps(result)
)
(out / "index.html").write_text(html)
(out / "provenance.json").write_text(
    json.dumps(
        {
            "sha256": {
                f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
                for f in [
                    "cross_view.py",
                    "body_localization.py",
                    "scripts/process_departure_geometry.py",
                    "scripts/probe_t11_far_receiving.py",
                    "rectification/calibration.json",
                    "throw-analysis/predictions.json",
                ]
            },
            "rules_pdf_sha256": hashlib.sha256(
                (ROOT.parent / "feasibility/sources/Rules-2025.pdf").read_bytes()
            ).hexdigest(),
        },
        indent=2,
    )
)

inputs = [
    *sorted((ROOT / "throw-segments").glob("T*.json")),
    *sorted(out.glob("T*-departure.json")),
    out / "T11-far-receiving-probe.json",
]
manifest = json.loads((out / "provenance.json").read_text())
manifest["observation_sha256"] = {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
}
(out / "provenance.json").write_text(json.dumps(manifest, indent=2))
