"""Evaluate a frozen straight-path protocol against stored outgoing observations."""

from pathlib import Path
import json, sys, hashlib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pre_gate_geometry import audit_path

out = ROOT / "pre-gate-audit"
out.mkdir(exist_ok=True)
source = ROOT / "throw-analysis/predictions.json"
protocol = {
    "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "selection": "All detected throws, all saved observations at or before virtual gate crossing. No outlier removal.",
    "coordinate_system": "Original detector coordinates, full frame 640x360; display video 1920x1080 has a factor-three scale.",
    "feature": "Bounding-box-derived stone centre proxy with downward offset, not an independently verified physical centre.",
    "fit": "Orthogonal least-squares line by SVD; also compare with line through first and last observation.",
    "predictive_check": "For tracks with >=8 observations, fit first floor(2n/3), evaluate remaining points; no constant-speed assumption.",
    "physical_accuracy_measured": False,
    "limitations": [
        "Same detector supplies points and was developed on this recording.",
        "Before-first-detection interval and release location unknown.",
        "Sampling, quantisation, occlusion and changing feature shape confound curvature.",
        "No independent label uncertainty or physical position reference.",
        "Later-point holdout is within the same track, not an unseen-video evaluation.",
    ],
    "thresholds_px": [0.5, 1, 2],
}
(out / "protocol.json").write_text(json.dumps(protocol, indent=2))
(out / "protocol.sha256").write_text(
    hashlib.sha256((out / "protocol.json").read_bytes()).hexdigest() + "\n"
)
rows = []
for e in json.loads(source.read_text())["events"]:
    points = [p for p in e["trajectory"] if p["time_s"] <= e["crossing_time_s"]]
    a = np.array([p["pixel"] for p in points])
    audit = audit_path(a)
    rows.append(
        {
            "id": e["id"],
            "colour": e["colour"],
            "gate_time_s": e["crossing_time_s"],
            "duration_s": points[-1]["time_s"] - points[0]["time_s"],
            "first_observed_s": points[0]["time_s"],
            "last_observed_s": points[-1]["time_s"],
            "points": points,
            **audit,
        }
    )
held = [r["held_out_later_points"] for r in rows if r["held_out_later_points"]]
summary = {
    "throws": len(rows),
    "duration_range_s": [min(r["duration_s"] for r in rows), max(r["duration_s"] for r in rows)],
    "duration_median_s": float(np.median([r["duration_s"] for r in rows])),
    "best_line_rms_median_px": float(np.median([r["best_fit"]["rms_px"] for r in rows])),
    "endpoint_line_max_median_px": float(np.median([r["endpoint_line"]["max_px"] for r in rows])),
    "endpoint_line_worst_max_px": max(r["endpoint_line"]["max_px"] for r in rows),
    "endpoint_line_within_px": {
        str(t): sum(r["endpoint_line"]["max_px"] <= t for r in rows)
        for t in protocol["thresholds_px"]
    },
    "held_out_tracks": len(held),
    "held_out_rms_median_px": float(np.median([h["rms_px"] for h in held])),
    "held_out_worst_max_px": max(h["max_px"] for h in held),
}
result = {"protocol": protocol, "summary": summary, "throws": rows}
(out / "results.json").write_text(json.dumps(result, indent=2))
print(json.dumps(summary, indent=2))
html = r"""<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Avant la ligne : tester une droite</title><style>body{max-width:1100px;margin:40px auto;padding:0 20px;background:#f5f2e9;color:#173b38;font:17px/1.5 system-ui}h1{font:44px Georgia}article{background:white;border:1px solid #ccd8d0;padding:20px;margin:20px 0;border-radius:12px}canvas{width:100%;max-width:600px;background:#f8faf9}img{width:100%}table{border-collapse:collapse;width:100%}td,th{padding:8px;text-align:left;border-bottom:1px solid #ccc}.scroll{overflow:auto}.note{border-left:4px solid #a64239;padding:15px}a{color:#006f67}button{padding:10px;background:#173b38;color:white;border:0;border-radius:6px}</style><h1>Avant la ligne : une droite suffit-elle ?</h1><p id="summary"></p><p class="note"><strong>Conclusion limitée au court segment visible.</strong> Nous mesurons l’écart entre les observations du détecteur et une droite, pas l’erreur physique de trajectoire. Le lâcher et le trajet avant la première détection restent inconnus. Aucune valeur en centimètres n’est revendiquée ici.</p><p>Les pixels ci-dessous sont ceux du détecteur 640 × 360. Sur la vidéo 1920 × 1080, multiplier par trois. Une homographie préserve les droites : la perspective seule ne transforme pas une ligne droite du plan en courbe. Les distances en pixels ne sont cependant pas des distances sur la glace.</p><p id="holdout"></p><p>Vert : observations détectées. Rouge : droite reliant les première et dernière observations. Une droite ajustée à toutes les observations minimise l’écart ; son résultat est donc plus optimiste. Les points ne sont pas une vérité terrain, et les déplacements du centre apparent peuvent venir de la détection.</p><div class="scroll"><table><thead><tr><th>Lancer</th><th>Durée visible</th><th>Points</th><th>Écart max à la droite entre extrémités</th><th>RMSE sur points ultérieurs réservés</th></tr></thead><tbody id="rows"></tbody></table></div><h2>Inspecter les observations</h2><div id="plots"></div><h2>Pourquoi le segment est court</h2><p>À −4, −2, −1 et 0 seconde du passage, sur quatre lancers : les joueurs et fauteuils masquent souvent les positions précédentes. Ces images fournissent le contexte ; elles n’annotent pas l’instant du lâcher.</p><a href="context.jpg"><img src="context.jpg" alt="Contexte avant le passage"></a><p><a href="results.json">Observations et résultats</a> · <a href="protocol.json">Protocole</a> · <a href="../throw-segments/index.html">Segments et trajectoires</a></p><script>const D=DATA,S=D.summary;document.getElementById('summary').textContent=`${S.throws} lancers. Seulement ${S.duration_range_s[0].toFixed(1)} à ${S.duration_range_s[1].toFixed(1)} s observée avant la ligne. ${S.endpoint_line_within_px['1']}/16 trajectoires restent à moins de 1 pixel de la droite entre leurs extrémités ; ${S.endpoint_line_within_px['2']}/16 à moins de 2 pixels. Écart maximal observé : ${S.endpoint_line_worst_max_px.toFixed(2)} pixels.`;document.getElementById('holdout').textContent=`Vérification prédictive sur ${S.held_out_tracks} pistes suffisamment longues : droite ajustée sur les deux premiers tiers, puis comparaison avec le dernier tiers. RMSE médiane par piste : ${S.held_out_rms_median_px.toFixed(2)} pixels ; écart maximal : ${S.held_out_worst_max_px.toFixed(2)} pixels. Ce test ne valide ni le trajet masqué avant la première détection ni une autre vidéo.`;document.getElementById('rows').innerHTML=D.throws.map(r=>`<tr><td><a href="#${r.id}">${r.id}</a></td><td>${r.duration_s.toFixed(1)} s</td><td>${r.points.length}</td><td>${r.endpoint_line.max_px.toFixed(2)} px</td><td>${r.held_out_later_points?r.held_out_later_points.rms_px.toFixed(2)+' px':'trop peu de points'}</td></tr>`).join('');document.getElementById('plots').innerHTML=D.throws.map(r=>`<article id="${r.id}"><h3>${r.id} : ${r.points.length} observations</h3><canvas id="plot-${r.id}" width="600" height="360"></canvas><p>Axes image, même échelle horizontale et verticale. Horodatages source : ${r.first_observed_s.toFixed(1)} à ${r.last_observed_s.toFixed(1)} s.</p><details><summary>Images source et marque détectée</summary><img loading="lazy" src="${r.id}-source.jpg" alt="Première, milieu et dernière observation ${r.id}"></details><details><summary>Coordonnées originales</summary><pre>${r.points.map(p=>p.time_s.toFixed(1)+' s : ('+p.pixel.join(', ')+')').join('\n')}</pre></details></article>`).join('');for(const r of D.throws){const g=document.getElementById('plot-'+r.id).getContext('2d'),pts=r.points.map(p=>p.pixel),xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]),cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2,scale=Math.min(500/(Math.max(...xs)-Math.min(...xs)+4),260/(Math.max(...ys)-Math.min(...ys)+4)),xy=p=>[300+(p[0]-cx)*scale,180+(p[1]-cy)*scale];g.strokeStyle='#c33';g.lineWidth=2;g.beginPath();g.moveTo(...xy(pts[0]));g.lineTo(...xy(pts.at(-1)));g.stroke();g.fillStyle='#006f67';for(const p of pts){g.beginPath();g.arc(...xy(p),4,0,7);g.fill()}g.fillStyle='#173b38';g.font='14px system-ui';g.fillText('1 pixel détecteur = '+scale.toFixed(1)+' pixels du graphique',15,25);g.fillText('Début',xy(pts[0])[0]+12,xy(pts[0])[1]);g.fillText('Vers la ligne',xy(pts.at(-1))[0]+12,xy(pts.at(-1))[1]);}</script></html>""".replace(
    "DATA", json.dumps(result)
)
(out / "index.html").write_text(html)
