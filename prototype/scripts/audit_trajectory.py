"""Retrospective manual audit; shared calibration does not validate physical accuracy."""

from pathlib import Path
import sys, json, hashlib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from body_localization import transported_reference_camera, height_correct

out = ROOT / "trajectory-accuracy"
out.mkdir(exist_ok=True)
# Manual annotations are an input, never regenerated or silently re-frozen.
ref = json.loads((out / "reference.json").read_text())
expected = (out / "reference.sha256").read_text().strip()
if hashlib.sha256((out / "reference.json").read_bytes()).hexdigest() != expected:
    raise ValueError("Manual reference changed; create a new versioned audit explicitly.")
labels = [(r["time_s"], *r["pixel"]) for r in ref["labels"]]
timeline = json.loads((ROOT / "body-localization/video-timeline.json").read_text())
geom = json.loads((ROOT / "rectification/timeline.json").read_text())
cal = json.loads((ROOT / "rectification/calibration.json").read_text())
cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())
path = []
for r in timeline["records"]:
    for s in r["views"]["right"]["stones"]:
        if s.get("track_id") == 6 and s["colour"] == "yellow" and s.get("ground_position_m"):
            path.append(
                {
                    "time_s": r["time_s"],
                    "pixel": s["pixel_center"],
                    "position_m": s["ground_position_m"],
                }
            )
rows = []
for t, x, y in labels:
    p = next((p for p in path if p["time_s"] == t), None)
    H = np.array(geom["records"][round(t * 30)]["views"]["right"]["H"])
    prior = transported_reference_camera(
        np.array(cal["right"]["refined_H"]), H, cfg["views"]["right"]["region"]
    )
    q = height_correct(prior["camera"], [x, y], 0.136)
    rows.append(
        {
            "time_s": t,
            "reference_pixel": [x, y],
            "reference_position_m": q.tolist(),
            "prediction": p,
            "pixel_error": float(np.linalg.norm(np.array(p["pixel"]) - [x, y])) if p else None,
            "conditional_error_cm": float(100 * np.linalg.norm(np.array(p["position_m"]) - q))
            if p
            else None,
        }
    )


def stats(rs):
    a = [r for r in rs if r["prediction"]]
    return {
        "label_count": len(rs),
        "matched_count": len(a),
        "pixel_rmse": float(np.sqrt(np.mean([r["pixel_error"] ** 2 for r in a]))),
        "conditional_cm_rmse": float(np.sqrt(np.mean([r["conditional_error_cm"] ** 2 for r in a]))),
    }


result = {
    "scope": "T11 receiving-camera segment only; 2 Hz predictions, 1 Hz reference",
    "physical_accuracy_measured": False,
    "limitations": [
        "Same AI annotator, predictions previously inspected; not blind",
        "Shared homography and assumed 13.6 cm cap height; projection error is not measured",
        "Approximate manual readings, no independently measured label uncertainty",
        "No validation of unseen middle of throw, identity across cameras or other throws",
    ],
    "all_labels": stats(rows),
    "moving_labels": stats(rows[:4]),
    "rows": rows,
    "trajectory": path,
}
cue = json.loads((ROOT / "throw-analysis/target-analysis.json").read_text())["examples"][0][
    "broom_cue"
]
result["aiming_reference"] = cue
result["aiming_video_pixels"] = []
for r in timeline["records"]:
    h = geom["records"][r["frame"]]["views"]["right"]["H"]
    if h is not None:
        q = np.linalg.inv(np.array(h)) @ np.array([*cue["position_m_if_ice_contact"], 1.0])
        result["aiming_video_pixels"].append(
            {"time_s": r["time_s"], "pixel": (q[:2] / q[2]).tolist()}
        )
(out / "results.json").write_text(json.dumps(result, indent=2))
print(json.dumps({k: result[k] for k in ["all_labels", "moving_labels"]}, indent=2))
html = """<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Trajectoire : première mesure</title><style>body{margin:32px auto;max-width:1100px;padding:0 20px;background:#f5f2e9;color:#173b38;font:17px system-ui}h1{font-size:42px}section{display:grid;grid-template-columns:2fr 1fr;gap:20px}video,canvas{width:100%;background:white;border-radius:14px}.video-wrap{position:relative}.video-wrap video{display:block}.video-wrap canvas{position:absolute;inset:0;width:100%;height:100%;background:transparent;pointer-events:none}p{line-height:1.5}table{width:100%;border-collapse:collapse}td,th{padding:9px;text-align:left;border-bottom:1px solid #ccc}button{padding:12px;background:#173b38;color:white;border:0;border-radius:8px}@media(max-width:650px){section{grid-template-columns:1fr}h1{font-size:30px}}</style><h1>Le lancer, vu du dessus</h1><p>Un premier segment mesuré : arrivée de la pierre jaune du lancer 11. La courbe utilise les positions enregistrées à 2 Hz. Les croix rouges sont des lectures manuelles à 1 Hz. Le repère violet indique la position du balai observée à 15 s, projetée sur la glace sous hypothèse de contact. Il reste affiché pendant le lancer : référence de visée, pas destination confirmée.</p><section><div><div class="video-wrap"><video id="v" controls src="../continuous/clip.mp4"></video><canvas id="overlay" width="1920" height="1080"></canvas></div><p><button onclick="v.currentTime=53;v.play()">Revoir l’arrivée</button> <button onclick="v.currentTime=15">Voir le balai</button> <span id="time"></span></p></div><canvas id="c" width="420" height="760"></canvas></section><h2>Vérifier les deux centres sur les images</h2><p>À gauche : image source sans marque. À droite : <strong style="color:#e02030">croix rouge = mon estimation manuelle (IA)</strong> ; <strong style="color:#007fff">cercle bleu = centre trouvé automatiquement par OpenCV</strong>. Les marques conservent leurs coordonnées exactes, même lorsqu’elles se chevauchent. Zoom ×6 sans lissage. Origine des coordonnées : coin supérieur gauche de l’image originale 1920 × 1080.</p><p>Ces estimations manuelles existaient avant cet affichage. Elles ne sont ni des annotations humaines indépendantes ni une vérité terrain. Précision de lecture estimée : environ 2 pixels, non mesurée.</p><div id="evidence"></div><h2>Ce que cette mesure dit</h2><p id="stats"></p><p><strong>Ce n’est pas une précision physique en centimètres.</strong> Les deux séries utilisent la même calibration et la même hauteur supposée. Cette comparaison mesure le désaccord de localisation, sous ces hypothèses. Les lectures manuelles sont approximatives, rétrospectives et réalisées par la même IA. Quatre points concernent le mouvement ; les six autres concernent la fin du mouvement et l’arrêt.</p><p>Le milieu du lancer n’est pas reconstruit. Une interruption de détection supérieure à 0,75 seconde coupe la courbe. Aucune interpolation entre caméras.</p><table><thead><tr><th>Temps du clip</th><th>Écart image</th><th>Écart métrique conditionnel</th></tr></thead><tbody id="rows"></tbody></table><p><a href="reference-sheet.jpg">Images de référence avec grille</a> · <a href="reference.json">Annotations</a> · <a href="results.json">Résultats et limites</a> · <a href="../throw-analysis/">Détection des lancers</a></p><script>const D=DATA;const v=document.getElementById('v'),c=document.getElementById('c'),g=c.getContext('2d');document.getElementById('stats').textContent=`Sur les 4 points de mouvement : RMSE ${D.moving_labels.pixel_rmse.toFixed(2)} pixels, soit ${D.moving_labels.conditional_cm_rmse.toFixed(2)} cm de désaccord conditionnel. Sur les 10 points : ${D.all_labels.pixel_rmse.toFixed(2)} pixels / ${D.all_labels.conditional_cm_rmse.toFixed(2)} cm.`;document.getElementById('rows').innerHTML=D.rows.map(r=>`<tr><td>${r.time_s} s</td><td>${r.pixel_error.toFixed(2)} px</td><td>${r.conditional_error_cm.toFixed(2)} cm</td></tr>`).join('');document.getElementById('evidence').innerHTML=D.rows.map((r,i)=>`<details ${i===0?'open':''}><summary>${r.time_s} s : manuel (${r.reference_pixel.join(', ')}) ; OpenCV (${r.prediction.pixel.map(x=>x.toFixed(4)).join(', ')}) ; écart ${r.pixel_error.toFixed(4)} px</summary><a href="comparison-${r.time_s}.png" target="_blank"><img style="width:100%" loading="lazy" src="comparison-${r.time_s}.png" alt="Source et comparaison des centres à ${r.time_s} secondes"></a><button onclick="v.pause();v.currentTime=${r.time_s};v.scrollIntoView({block:'center'})">Voir cette image dans la vidéo</button></details>`).join('');function xy(p){return [210+p[0]*78,180+p[1]*78]}const overlay=document.getElementById('overlay'),og=overlay.getContext('2d');
function mark(ctx,x,y,label,scale=1){ctx.save();ctx.strokeStyle='#a632d2';ctx.fillStyle='#a632d2';ctx.lineWidth=3*scale;ctx.beginPath();ctx.arc(x,y,11*scale,0,Math.PI*2);ctx.moveTo(x-18*scale,y);ctx.lineTo(x+18*scale,y);ctx.moveTo(x,y-18*scale);ctx.lineTo(x,y+18*scale);ctx.stroke();ctx.font=`${14*scale}px system-ui`;ctx.strokeStyle='white';ctx.lineWidth=4*scale;ctx.strokeText(label,x+22*scale,y-14*scale);ctx.fillText(label,x+22*scale,y-14*scale);ctx.restore()}
function draw(){g.clearRect(0,0,420,760);g.fillStyle='#fff';g.fillRect(0,0,420,760);for(const [r,col] of [[1.829,'#8cbacb'],[1.219,'white'],[.610,'#d99a92']]){g.beginPath();g.arc(210,180,r*78,0,7);g.fillStyle=col;g.fill()}g.strokeStyle='#ccc';g.beginPath();g.moveTo(210,0);g.lineTo(210,760);g.moveTo(0,180);g.lineTo(420,180);g.stroke();let prev=null;g.strokeStyle='#207c70';g.lineWidth=3;for(const p of D.trajectory.filter(p=>p.time_s<=v.currentTime)){const a=xy(p.position_m);if(prev&&p.time_s-prev.time_s<=.75){g.beginPath();g.moveTo(...xy(prev.position_m));g.lineTo(...a);g.stroke()}prev=p}g.strokeStyle='#a64239';for(const r of D.rows.filter(r=>r.time_s<=v.currentTime)){const [x,y]=xy(r.reference_position_m);g.beginPath();g.moveTo(x-5,y-5);g.lineTo(x+5,y+5);g.moveTo(x-5,y+5);g.lineTo(x+5,y-5);g.stroke()}if(prev&&v.currentTime-prev.time_s<=.75){g.fillStyle='#d5a600';g.beginPath();g.arc(...xy(prev.position_m),10,0,7);g.fill()}if(v.currentTime>=15){mark(g,...xy(D.aiming_reference.position_m_if_ice_contact),'Visée');}
og.clearRect(0,0,1920,1080);
const sample=D.trajectory.reduce((best,p)=>!best||Math.abs(p.time_s-v.currentTime)<Math.abs(best.time_s-v.currentTime)?p:best,null);
if(sample&&Math.abs(sample.time_s-v.currentTime)<=.1){og.strokeStyle='#ffe000';og.lineWidth=4;og.beginPath();og.arc(...sample.pixel,25,0,Math.PI*2);og.stroke();}
const manual=D.rows.find(r=>Math.abs(r.time_s-v.currentTime)<1/60);
if(manual){const [x,y]=manual.reference_pixel;const [ax,ay]=manual.prediction.pixel;og.strokeStyle='#e02030';og.lineWidth=2;og.beginPath();og.moveTo(x-10,y);og.lineTo(x+10,y);og.moveTo(x,y-10);og.lineTo(x,y+10);og.stroke();og.strokeStyle='#007fff';og.beginPath();og.arc(ax,ay,4,0,Math.PI*2);og.stroke();og.font='22px system-ui';og.fillStyle='white';og.fillRect(x+35,y-65,510,65);og.fillStyle='#e02030';og.fillText(`Manuel IA : (${x}, ${y})`,x+40,y-40);og.fillStyle='#007fff';og.fillText(`OpenCV : (${ax.toFixed(2)}, ${ay.toFixed(2)})`,x+40,y-12);}
const aim=D.aiming_video_pixels.reduce((best,p)=>!best||Math.abs(p.time_s-v.currentTime)<Math.abs(best.time_s-v.currentTime)?p:best,null);
if(v.currentTime>=15&&aim&&Math.abs(aim.time_s-v.currentTime)<=.26){mark(og,...aim.pixel,'Visée observée à 15 s',1.5);}
g.fillStyle='#173b38';g.font='14px system-ui';g.fillText('Repère local : origine au centre de la maison',12,25);g.fillText('Courbe : modèle · Croix : annotation',12,735);document.getElementById('time').textContent=v.currentTime.toFixed(1)+' s';requestAnimationFrame(draw)}v.currentTime=54;draw();</script></html>""".replace(
    "DATA", json.dumps(result)
)
(out / "index.html").write_text(html)
