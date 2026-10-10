"""Audit proposal recall and confirmation precision on frozen development runs.

This reads immutable first-pass artifacts; it does not refit a threshold or
claim independent full-match validation.
"""

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from throw_event_benchmark import evaluate_events
from two_stage_throw_triage import triage_candidates


RUNS = {
    "canada-china-2024": ["frozen-first-corridor.json"],
    "canada-estonia-2024": ["frozen-first-corridor.json", "frozen-first-confirmed.json"],
    "canada-usa-2024": ["frozen-first-confirmed.json"],
}
OUT = ROOT / "validation/two-stage-throw-audit"


def audit_run(name, stages):
    base = ROOT / "validation/throw-event-benchmark" / name
    raw_path = base / "frozen-first-raw.json"
    ref_path = base / "blind-reference.json"
    raw = json.loads(raw_path.read_text())
    reference = json.loads(ref_path.read_text())
    previous_path = raw_path
    stage_inputs = []
    for path_name in stages:
        path = base / path_name
        artifact = json.loads(path.read_text())
        for key in ("source_id", "source_sha256", "source_interval_s"):
            if artifact[key] != raw[key]:
                raise ValueError(f"Mismatched {key}: {path}")
        if artifact["input_sha256"] != file_sha256(previous_path):
            raise ValueError(f"Stage input fingerprint mismatch: {path}")
        stage_inputs.append((path_name.removesuffix(".json"), artifact))
        previous_path = path
    if reference["source_sha256"] != raw["source_sha256"]:
        raise ValueError(f"Reference source mismatch: {name}")
    result = triage_candidates(raw["events"], stage_inputs)
    pool = evaluate_events(raw["events"], reference["events"], reference["source_interval_s"])
    confirmed = evaluate_events(
        result["auto_confirmed_events"], reference["events"], reference["source_interval_s"]
    )
    unified_path = OUT / f"{name}-unified-gate.json"
    unified = json.loads(unified_path.read_text())
    if (unified["source_sha256"] != raw["source_sha256"] or
            unified["proposal_sha256"] != file_sha256(raw_path) or
            unified["source_interval_s"] != raw["source_interval_s"]):
        raise ValueError(f"Unified gate input mismatch: {unified_path}")
    unified_score = evaluate_events(
        unified["events"], reference["events"], reference["source_interval_s"]
    )
    confirmed_refs = {row["reference_id"] for row in confirmed["matches"]}
    review_ids = {row["id"] for row in result["review_events"]}
    review_matches = [
        row for row in pool["matches"]
        if row["prediction_id"] in review_ids and row["reference_id"] not in confirmed_refs
    ]
    unified_refs = {row["reference_id"] for row in unified_score["matches"]}
    unified_review_ids = {row["id"] for row in unified["review_events"]}
    unified_review_matches = [
        row for row in pool["matches"]
        if row["prediction_id"] in unified_review_ids and row["reference_id"] not in unified_refs
    ]
    return {
        "recording": name,
        "reference_method": reference["reference_method"],
        "scope": "frozen partial-interval development diagnostic",
        "source_sha256": raw["source_sha256"],
        "source_interval_s": raw["source_interval_s"],
        "input_sha256": {"raw": file_sha256(raw_path), "reference": file_sha256(ref_path),
                         **{path: file_sha256(base / path) for path in stages}},
        "stages": stages,
        "historical_counts": result["counts"],
        "unified_counts": unified["counts"],
        "proposal_pool_score": pool,
        "historical_confirmed_score": confirmed,
        "historical_reference_matches_in_review": review_matches,
        "unified_confirmed_score": unified_score,
        "unified_reference_matches_in_review": unified_review_matches,
        "historical_proposals": result["proposals"],
        "proposals": unified["proposals"],
        "unified_gate_sha256": file_sha256(unified_path),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runs = [audit_run(name, stages) for name, stages in RUNS.items()]
    document = {
        "status": "development_audit_not_independent_validation",
        "method": "All raw proposals are retained. Historical frozen gates and one unified image-context gate are compared; withheld candidates stay in review.",
        "runs": runs,
        "limitations": [
            "References are same-agent coarse intervals on partial recordings, not independent exhaustive labels.",
            "Historical stage rules differ between these previously exposed recordings. The unified rule is post-score development on China and Estonia; the USA result reproduces its frozen first score.",
            "A review candidate is not a confirmed event; automated end-to-end high precision and recall remain unproven.",
            "No exact physical release time or persistent stone identity is inferred.",
        ],
    }
    (OUT / "results.json").write_text(json.dumps(document, indent=2) + "\n")
    lines = [
        "# Two-stage throw-event development audit", "",
        "Raw proposals are kept for recall. One image-context gate now runs over",
        "all three frozen raw candidate lists; every withheld proposal remains reviewable.",
        "China and Estonia were already exposed, so their new scores are post-score",
        "development diagnostics. USA reproduces the frozen first transfer result.", "",
        "| Recording | Proposal pool TP/FP/FN | Historical gate TP/FP/FN | Unified gate TP/FP/FN | Labelled throws in unified review |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for run in runs:
        a, b, c = (run["proposal_pool_score"], run["historical_confirmed_score"],
                   run["unified_confirmed_score"])
        fmt = lambda s: f"{s['true_positives']}/{s['false_positives']}/{s['false_negatives']}"
        lines.append(f"| {run['recording']} | {fmt(a)} | {fmt(b)} | {fmt(c)} | {len(run['unified_reference_matches_in_review'])} |")
    lines.extend([
        "", "On Estonia, the spatial gate retained 16 reference matches, but the later",
        "image-speed gate withheld three of them. The unified context gate restores",
        "those three to the automated candidate set on this exposed excerpt. The raw",
        "pool still misses one labelled delivery; a filter cannot",
        "recover a throw that the proposal stage never produced.", "",
        "The same context rule removes 19 unmatched USA raw proposals while retaining",
        "its 19 temporal matches. On China it removes eight raw proposals, leaving",
        "17 matches and one extra. These are exposed, partial-interval checks with",
        "agent-made labels; they do not establish general precision or recall.", "",
        "Next: broaden the proposal routes for occluded/cut deliveries, then freeze a",
        "single confirmation policy and score it on independently labelled full videos.", "",
        "Machine-readable candidate-level decisions: [results.json](results.json).", "",
    ])
    (OUT / "README.md").write_text("\n".join(lines))
    table_rows = []
    detail_rows = []
    for run in runs:
        pool = run["proposal_pool_score"]
        historical = run["historical_confirmed_score"]
        unified = run["unified_confirmed_score"]
        short = run["recording"].removeprefix("canada-").removesuffix("-2024").title()
        table_rows.append(
            f"<tr><th>{escape(short)}</th><td>{run['unified_counts']['proposed']}</td>"
            f"<td>{pool['true_positives']}/{pool['false_positives']}/{pool['false_negatives']}</td>"
            f"<td>{historical['true_positives']}/{historical['false_positives']}/{historical['false_negatives']}</td>"
            f"<td>{unified['true_positives']}/{unified['false_positives']}/{unified['false_negatives']}</td>"
            f"<td>{len(run['unified_reference_matches_in_review'])}</td></tr>"
        )
        matches = run["historical_reference_matches_in_review"]
        if matches:
            cases = ", ".join(
                f"{escape(row['prediction_id'])} ↔ {escape(row['reference_id'])}" for row in matches
            )
            detail_rows.append(f"<li><strong>{escape(short)} :</strong> {cases}</li>")
    review_data = [
        {
            "recording": run["recording"],
            "events": [row for row in run["proposals"] if row["disposition"] == "needs_review"],
        }
        for run in runs
    ]
    review_json = json.dumps(review_data, ensure_ascii=False).replace("<", "\\u003c")
    html = f'''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Deux étapes pour détecter les lancers</title><style>
    :root{{--ink:#173d3a;--teal:#087c76;--paper:#f6f3eb;--warn:#a44b31}}
    body{{max-width:1040px;margin:0 auto;padding:42px 24px;background:var(--paper);color:var(--ink);font:18px/1.52 system-ui}}
    h1{{font:clamp(34px,5vw,58px)/1.08 Georgia,serif;max-width:800px;margin:0 0 20px}}
    h2{{font:30px Georgia,serif;margin:0 0 12px}}p{{max-width:78ch}}.eyebrow{{color:var(--teal);font-weight:700;letter-spacing:.12em;text-transform:uppercase;font-size:13px}}
    .lead{{font-size:23px;max-width:760px}}.card{{background:white;border:1px solid #d9e4df;border-radius:14px;padding:24px;margin:22px 0}}
    .flow{{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:14px;align-items:center;margin:30px 0}}.step{{background:white;border:1px solid #d9e4df;padding:18px;border-radius:12px;height:100%;box-sizing:border-box}}.step b{{display:block;font-size:21px}}.arrow{{font-size:30px;color:var(--teal)}}
    table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:13px 10px;border-bottom:1px solid #d9e4df;text-align:left}}thead th{{font-size:14px;background:#e5efeb}}.scroll{{overflow:auto}}.note{{border-left:5px solid var(--warn);padding:12px 20px;background:white}}a{{color:#087078}}small{{font-size:14px;color:#4c625e}}video{{display:block;width:100%;max-width:760px;background:#122;border-radius:10px;margin:18px 0}}select,button{{padding:10px;font:inherit;border:1px solid #8caaa2;border-radius:7px;background:white;color:var(--ink)}}button{{cursor:pointer}}.queue{{display:flex;flex-wrap:wrap;gap:7px;margin:15px 0}}button.active{{background:var(--ink);color:white}}@media(max-width:700px){{.flow{{display:block}}.step{{margin:10px 0}}.arrow{{display:none}}}}
    </style><p class="eyebrow">Prototype · audit de développement</p><h1>Proposer largement, confirmer prudemment.</h1>
    <p class="lead">Chaque indice de lancer reste traçable. Le filtre confirme les cas soutenus par l'image et envoie les autres en vérification, sans effacer les propositions.</p>
    <div class="flow"><div class="step"><b>1 · Proposer</b>Mouvement de pierre possible dans la vidéo ; on privilégie le rappel.</div><div class="arrow">→</div><div class="step"><b>2 · Examiner les indices</b>Position sur la glace, cohérence du mouvement et contexte du plan.</div><div class="arrow">→</div><div class="step"><b>3 · Décider</b>Candidat confirmé automatiquement ou cas à vérifier.</div></div>
    <section class="card"><h2>Ce que montrent trois extraits déjà étudiés</h2><p>VP/FP/FN : passages appariés / candidats supplémentaires / passages manqués par rapport aux fenêtres de référence. « Ancien » conserve le premier résultat figé ; « commun » applique la même règle de contexte aux trois listes brutes.</p><div class="scroll"><table><thead><tr><th>Vidéo</th><th>Propositions</th><th>Brut<br>VP/FP/FN</th><th>Ancien filtre<br>VP/FP/FN</th><th>Filtre commun<br>VP/FP/FN</th><th>Lancers dans<br>la vérification</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div></section>
    <section class="card"><h2>Le cas décisif : Estonie</h2><p>La règle spatiale conservait 16 passages appariés. L'ancien seuil de vitesse en retirait trois :</p><ul>{''.join(detail_rows)}</ul><p>Le filtre commun retrouve ces trois propositions sur cet extrait déjà étudié. Un passage demeure manqué par toutes les propositions : aucun filtre ne peut retrouver un événement jamais proposé.</p></section>
    <section class="card"><h2>Ouvrir la file de vérification</h2><p>Chaque proposition incertaine reste liée à sa vidéo et aux raisons données par les filtres. Les images ne sont pas des annotations de référence.</p><label>Vidéo <select id="recording"></select></label><div class="queue" id="queue"></div><p id="decision"></p><video id="source" controls preload="metadata"></video><small id="source-time"></small></section>
    <p class="note"><strong>À ne pas surinterpréter.</strong> Chine et Estonie sont des essais rétrospectifs sur des sources déjà étudiées. Le résultat USA reproduit le premier score figé. Les références sont des fenêtres approximatives préparées par l'agent, et les extraits ne couvrent pas des parties entières. Les trois cas estoniens ont été identifiés rétrospectivement grâce à la référence ; leur récupération sur cette source n'est pas une preuve de généralisation. La précision et le rappel finaux restent à mesurer sur des vidéos complètes annotées indépendamment.</p>
    <p><a href="results.json">Décisions et scores par candidat (JSON)</a> · <a href="README.md">Note technique</a> · <a href="../throw-event-benchmark/README.md">Protocole d'évaluation</a></p>
    <script>const DATA=__REVIEW_DATA__,selector=document.getElementById('recording'),queue=document.getElementById('queue'),video=document.getElementById('source');
    selector.innerHTML=DATA.map((run,i)=>`<option value="${{i}}">${{run.recording}} · ${{run.events.length}} cas</option>`).join('');selector.value='1';
    function show(runIndex,eventIndex){{const run=DATA[runIndex],event=run.events[eventIndex];if(!event)return;document.querySelectorAll('#queue button').forEach((b,i)=>b.classList.toggle('active',i===eventIndex));const reasons=event.stage_evidence.map(e=>`${{e.stage}} : ${{e.reason||e.decision}}`).join(' · ');document.getElementById('decision').textContent=`${{event.id}} · ${{event.colour}} · ${{reasons}}`;document.getElementById('source-time').textContent=`Temps source : ${{event.crossing_time_s.toFixed(3)}} s. Fenêtre de vérification : quelques secondes avant et après.`;const src=`../throw-event-benchmark/${{run.recording}}/source.mp4`;if(video.getAttribute('src')!==src){{video.src=src;video.addEventListener('loadedmetadata',()=>{{video.currentTime=Math.max(0,event.crossing_time_s-4)}},{{once:true}})}}else{{video.currentTime=Math.max(0,event.crossing_time_s-4)}}}}
    function render(){{const runIndex=Number(selector.value),events=DATA[runIndex].events;queue.innerHTML=events.map((e,i)=>`<button type="button" data-index="${{i}}">${{e.id}} · ${{e.crossing_time_s.toFixed(1)}} s</button>`).join('');queue.querySelectorAll('button').forEach(b=>b.onclick=()=>show(runIndex,Number(b.dataset.index)));show(runIndex,0)}}selector.onchange=render;render();</script></html>'''.replace('__REVIEW_DATA__', review_json)
    (OUT / "index.html").write_text(html)
    print("\n".join(lines[:11]))


if __name__ == "__main__":
    main()
