"""Build a readable, source-linked page for the frozen Canada–USA transfer."""

from base64 import b64encode
from html import escape
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "RESULTS.html"


def main():
    frozen = json.loads((HERE / "frozen-first-score.json").read_text())
    sensitivity = json.loads((HERE / "postscore-one-second-tolerance.json").read_text())
    reference = json.loads((HERE / "blind-reference.json").read_text())
    confirmed = json.loads((HERE / "frozen-first-confirmed.json").read_text())
    first = frozen["score"]
    later = sensitivity["score"]
    event = next(item for item in confirmed["events"] if item["id"] == "S24")
    label = next(item for item in reference["events"] if item["id"] == "U14")
    assert frozen["source_id"] == reference["source_id"] == "Z1yEOv__bDc"
    assert frozen["source_interval_s"] == [1650, 2760]
    assert first["reference_count"] == first["prediction_count"] == 20
    assert (first["true_positives"], first["false_positives"],
            first["false_negatives"], first["f1"]) == (19, 1, 1, 0.95)
    assert first["colour_errors_among_matches"] == 0
    assert len(confirmed["events"]) == 20
    assert len(confirmed["withheld_events"]) == 19
    assert (later["true_positives"], later["false_positives"],
            later["false_negatives"]) == (20, 0, 0)
    assert label["delivery_interval_s"][0] == 2345
    assert abs(event["crossing_time_s"] - 2344.448) < 1e-6
    image = b64encode((HERE / "audit-u14.png").read_bytes()).decode("ascii")
    timing_delta = label["delivery_interval_s"][0] - event["crossing_time_s"]
    delta_fr = f"{timing_delta:.3f}".replace(".", ",")
    html = f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Canada–États-Unis 2024 · Résultat du détecteur de lancers</title>
<style>
:root{{--ink:#142d38;--muted:#53676c;--teal:#126c78;--red:#aa4f42;--paper:#fffefa;--wash:#f4f5f0;--line:#d8e3e0}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.62 system-ui,-apple-system,"Segoe UI",sans-serif}}
a{{color:var(--teal);text-underline-offset:3px}}a:focus-visible,button:focus-visible{{outline:3px solid #d9aa43;outline-offset:3px}}
.top{{background:#102c36;color:#deeeee;padding:12px 5vw;display:flex;gap:24px;align-items:center;justify-content:space-between;font-size:13px}}
.top a{{color:#d3eceb}}.wrap{{max-width:1100px;margin:auto;padding:0 28px}}header{{padding:65px 0 42px}}.eyebrow{{color:var(--teal);font-size:12px;letter-spacing:.13em;text-transform:uppercase;font-weight:800}}h1,h2{{font-family:Georgia,serif;font-weight:400;line-height:1.1}}h1{{font-size:clamp(43px,6vw,76px);letter-spacing:-.04em;margin:15px 0 20px}}h2{{font-size:36px;margin:12px 0 20px}}h3{{font-size:18px;margin:0 0 8px}}p{{margin:0 0 16px}}.lead{{font-size:20px;color:#405a62;max-width:860px}}.chips{{display:flex;gap:8px;flex-wrap:wrap;margin-top:25px}}.chip{{border:1px solid #cddfdd;background:#eaf3f1;border-radius:100px;padding:6px 11px;font-size:12px;font-weight:750}}.chip.warn{{background:#f8e9e4;border-color:#efd1ca;color:#844238}}
.section{{border-top:1px solid var(--line);padding:50px 0}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.metric,.card{{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:22px}}.metric strong{{display:block;font:46px Georgia,serif;color:var(--teal);line-height:1.1}}.metric span{{display:block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:800;color:var(--muted);margin-top:8px}}.card p:last-child{{margin:0}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:15px}}.note{{background:#e6f0ef;border-left:4px solid var(--teal);padding:18px 22px;border-radius:0 9px 9px 0;margin-top:18px}}.warning{{background:#fbede8;border-left-color:var(--red)}}.note p:last-child{{margin:0}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:12px;background:var(--paper)}}table{{width:100%;border-collapse:collapse;min-width:660px}}td,th{{text-align:left;padding:14px 16px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);background:#edf3f1}}tr:last-child td{{border:0}}.main-score{{font-weight:800;color:#145f65}}.small{{font-size:13px;color:var(--muted)}}.timeline{{position:relative;display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:24px 0}}.timepoint{{padding:16px;background:white;border:1px solid var(--line);border-radius:10px}}.timepoint b{{display:block;font-size:22px}}.timepoint span{{font-size:13px;color:var(--muted)}}figure{{margin:24px 0 0;background:white;border:1px solid var(--line);padding:14px;border-radius:12px}}figure img{{display:block;width:100%;height:auto}}figcaption{{font-size:13px;color:var(--muted);padding:12px 4px 0}}ol{{padding-left:23px}}li{{padding-left:5px;margin-bottom:10px}}.links{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.links a{{display:block;background:white;border:1px solid var(--line);border-radius:9px;padding:14px;text-decoration:none;font-size:14px;font-weight:700}}.links a:hover{{border-color:var(--teal);background:#f0f7f5}}footer{{padding:35px 0 70px;color:var(--muted);font-size:13px}}
@media(max-width:750px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.grid,.links{{grid-template-columns:1fr}}header{{padding-top:40px}}}}
@media print{{body{{background:white}}.top{{display:none}}.section{{break-inside:avoid}}figure{{break-inside:avoid}}a{{color:inherit}}}}
</style></head><body>
<nav class="top"><span>Projet curling · validation des événements</span><a href="../../../supervisor-progress-2026-10-09.html">← Rapport de la réunion</a></nav>
<main class="wrap"><header><div class="eyebrow">Essai figé · Canada–États-Unis 2024</div>
<h1>Un bon résultat sur 18,5 minutes.<br>Pas encore une validation sur une partie entière.</h1>
<p class="lead">Le détecteur retrouve 19 des 20 fenêtres de lancer approximatives préparées avant son exécution, avec un candidat supplémentaire. L’unique désaccord porte sur une pierre jaune détectée {delta_fr} s avant le début de sa fenêtre de référence.</p>
<div class="chips"><span class="chip">Même type de diffusion 2024</span><span class="chip">Règles et référence figées avant inférence</span><span class="chip warn">Référence préparée par l’agent, non indépendante</span></div></header>

<section class="section" id="resultat"><div class="eyebrow">01 · Résultat principal</div><h2>Le premier score figé</h2>
<div class="metrics"><div class="metric"><strong>19</strong><span>Lancers appariés · VP</span></div><div class="metric"><strong>1</strong><span>Candidat en plus · FP</span></div><div class="metric"><strong>1</strong><span>Lancer manqué · FN</span></div><div class="metric"><strong>0,950</strong><span>F1 temporel</span></div></div>
<div class="note"><p><b>Précision : 0,950 · Rappel : 0,950.</b> Les 19 appariements ont la bonne couleur. Le score porte sur la concordance entre des instants de passage détectés et des fenêtres temporelles grossières, avec zéro marge ajoutée. Il ne mesure ni l’instant physique du lâcher ni la précision de la trajectoire.</p></div>
<p class="small" style="margin-top:16px">VP : un candidat apparié à une fenêtre ; FP : candidat sans fenêtre ; FN : fenêtre sans candidat. Le score est calculé événement par événement, avec association un à un.</p></section>

<section class="section" id="comparaison"><div class="eyebrow">02 · Comment lire les deux chiffres</div><h2>La vérification après score ne remplace pas le score initial.</h2>
<div class="table-wrap"><table><thead><tr><th>Calcul</th><th>VP / FP / FN</th><th>Précision</th><th>Rappel</th><th>F1</th><th>Statut</th></tr></thead><tbody>
<tr class="main-score"><td>Premier passage, tolérance supplémentaire nulle</td><td>19 / 1 / 1</td><td>0,950</td><td>0,950</td><td>0,950</td><td>Résultat de transfert à conserver</td></tr>
<tr><td>Après examen, tolérance de 1 s</td><td>20 / 0 / 0</td><td>1,000</td><td>1,000</td><td>1,000</td><td>Sensibilité à la limite de fenêtre, non validation</td></tr>
</tbody></table></div>
<p class="small" style="margin-top:13px">Les mêmes prédictions et la même référence sont utilisées dans les deux lignes ; seule la tolérance change. La seconde ligne a été calculée après avoir vu le premier score.</p></section>

<section class="section" id="cas"><div class="eyebrow">03 · Le seul désaccord</div><h2>Une pierre jaune à la limite de la fenêtre U14.</h2>
<div class="timeline"><div class="timepoint"><span>Détection S24 · milieu du suivi observé</span><b>2 344,448 s</b></div><div class="timepoint"><span>Début de la fenêtre U14 · référence grossière</span><b>2 345,000 s</b></div></div>
<p>Les images source entre 2 339 et 2 350 s montrent le lancer jaune correspondant. La détection arrive {delta_fr} s avant la borne de la fenêtre. Sous la règle figée à tolérance zéro, S24 compte donc comme un candidat supplémentaire et U14 comme un lancer manqué. Une tolérance d’une seconde les apparie, mais cette modification a été envisagée <em>après</em> le score.</p>
<figure><img src="data:image/png;base64,{image}" alt="Images source successives de 2339 à 2350 secondes autour du lancer jaune U14 et de la détection S24."><figcaption>Examen rétrospectif des images source. Il explique le désaccord de frontière ; il ne change pas le résultat figé. <a href="audit-u14.png">Ouvrir l’image originale</a>.</figcaption></figure></section>

<section class="section" id="methode"><div class="eyebrow">04 · Ce qui a été testé</div><h2>Un transfert contrôlé, dans une seule famille de vidéos.</h2>
<div class="grid"><div class="card"><h3>Avant l’inférence</h3><p>Un intervalle continu de 1 650 à 2 760 s de la vidéo Canada–États-Unis a été choisi. Vingt fenêtres de lancer ont été préparées à partir d’images source seulement, puis la référence, les règles et les empreintes des fichiers ont été figées. <a href="SELECTION.md">Lire le protocole préalable</a>.</p></div>
<div class="card"><h3>Détecteur figé</h3><p>Il suit le mouvement d’une pierre dans la vue précoce de lancer, recherche une progression cohérente et examine le changement visuel local. Il produit un instant au milieu d’un suivi observé. Sur cet extrait, 39 candidats de mouvement ont été examinés : 20 confirmés, 19 écartés avec leur raison enregistrée.</p></div></div>
<div class="note warning"><p><b>Limites de la référence.</b> Les fenêtres ont été préparées par le même agent qui développe le détecteur ; elles ne sont pas des annotations humaines indépendantes. Hors d’un changement de manche échantillonné plus finement, les planches d’images espacées de cinq secondes peuvent manquer un lancer bref. L’intervalle ne couvre pas une partie entière.</p></div></section>

<section class="section" id="suite"><div class="eyebrow">05 · Interprétation</div><h2>Ce résultat justifie la suite, pas une revendication de robustesse.</h2>
<p>Il montre que la règle préparée à partir d’autres vidéos 2024 fonctionne bien sur cet extrait du même type de diffusion. Pour démontrer un détecteur robuste, il faut encore évaluer des parties complètes, d’autres configurations de caméra, les périodes sans lancer et une référence exhaustive établie indépendamment. Le seuil visé est une précision et un rappel d’au moins 0,95 sur chaque vidéo complète tenue à l’écart.</p>
<div class="links"><a href="frozen-first-score.json">Premier score figé →</a><a href="blind-reference.json">Fenêtres de référence →</a><a href="frozen-first-confirmed.json">Candidats confirmés et écartés →</a><a href="postscore-one-second-tolerance.json">Sensibilité après score →</a><a href="RESULTS.md">Note technique d’origine →</a><a href="../README.md">Protocole du benchmark →</a></div></section>
<footer>Source vidéo : <a href="https://www.youtube.com/watch?v=Z1yEOv__bDc">Canada–États-Unis 2024</a> · Référence SHA-256 : <code>{escape(frozen['reference_sha256'][:16])}…</code> · Rapport généré depuis les résultats figés.</footer></main></body></html>'''
    OUTPUT.write_text(html)
    print(f"Wrote {OUTPUT} ({len(html):,} characters)")


if __name__ == "__main__":
    main()
