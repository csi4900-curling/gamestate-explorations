"""Attach timestamped state evidence to an unchanged public trajectory viewer.

Development presentation only: no new score, geometry or identity inference.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path


def build(public_run, state, output):
    public_run, state, output = map(Path, (public_run, state, output))
    manifest = json.loads((state / 'manifest.json').read_text())
    events = json.loads((public_run / 'events.json').read_text())
    if manifest['source_sha256'] != events['source_sha256']:
        raise ValueError('Source hashes differ')
    board_path = public_run / 'match-observations.jsonl'
    expected = manifest['inputs'].get(str(board_path.resolve()))
    if expected != hashlib.file_digest(board_path.open('rb'), 'sha256').hexdigest():
        raise ValueError('State evidence does not belong to this public run')
    viewer = public_run / 'two-view-tracking/index.html'
    if not viewer.is_file():
        raise ValueError('Public trajectory viewer missing')
    if output.exists():
        raise ValueError('Preserve previous viewer outputs')
    rows = []
    with (state / 'timeline.jsonl').open() as stream:
        for line in stream:
            r = json.loads(line)
            rows.append({k: v for k, v in r.items() if k not in ['boards', 'latest_scoreboard_parse']})
    if not rows or any(b['time_s'] <= a['time_s'] for a, b in zip(rows, rows[1:])):
        raise ValueError('State timeline must be nonempty and strictly chronological')
    output.mkdir(parents=True)
    times = [r['time_s'] for r in rows]
    # Chunking is a storage choice, not an inference parameter.
    size = 256
    for start in range(0, len(rows), size):
        (output / f'state-{start // size}.js').write_text(
            f'window.receiveState({start // size},' + json.dumps(rows[start:start+size]) + ');\n')
    page = '''<!doctype html><meta charset="utf-8"><title>Trajectoires et état du match — développement</title>
<style>body{font:16px system-ui;margin:16px;color:#213545}iframe{width:100%;height:850px;border:1px solid #ccd5da}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccd5da}pre{white-space:pre-wrap}#state{padding:12px;background:#f0f5f7}</style>
<h1>Trajectoires et état du match</h1>
<p>Résultat de développement. Identités physiques et état complet du match non validés. Les deux vues de trajectoire ci-dessous conservent leurs résultats et leurs lacunes.</p>
<section id="state" aria-live="polite"><span id="status">Chargement…</span><div id="score"></div><p id="context"></p><details><summary>Provenance exacte des observations</summary><pre id="evidence"></pre></details></section>
<iframe id="trajectory" title="Vidéo et trajectoires synchronisées" src="__VIEWER__"></iframe>
<script>
const times=__TIMES__,chunkSize=256,cache=new Map(),loading=new Set();let currentIndex=-2;
const frame=document.getElementById('trajectory'),status=document.getElementById('status');
const known=v=>v===null||v===undefined?'inconnu':String(v);
function cell(tr,value){const td=document.createElement('td');td.textContent=value;tr.append(td);}
function show(r,t){
 window.displayedState={time_s:r.time_s,video_time_s:t,index:currentIndex};
 status.textContent=`Vidéo ${t.toFixed(2)} s · observation ${r.time_s.toFixed(2)} s · âge ${(t-r.time_s).toFixed(2)} s`;
 const target=document.getElementById('score');target.replaceChildren();const table=document.createElement('table');
 const head=document.createElement('tr');['Équipe','OCR externe : dernière lecture','Inférence hors ligne (observations futures)','OCR du traitement public : à cet instant','Fond du tableau : hypothèse de couleur'].forEach(s=>cell(head,s));table.append(head);
 for(const [team,s] of Object.entries(r.cumulative_match_score)){
  const tr=document.createElement('tr');cell(tr,team);
  const reading=s.last_reading;cell(tr,reading?`${reading.value} · lu à ${reading.observed_at_s}s · âge ${(t-reading.observed_at_s).toFixed(1)}s`:'inconnu');
  cell(tr,known(s.offline_inferred?.value));
  cell(tr,known(r.public_run_score_evidence?.observation?.totals?.[team]?.value));
  const c=r.scoreboard_team_colour_evidence?.[team], o=c?.last_observation;
  cell(tr,!o?'inconnu':`${c.status==='conflicting_observations'?'contradiction : '+c.observed_colours.join(', '):c.background_colour_hypothesis} · dernière lecture ${o.time_s}s · âge ${(t-o.time_s).toFixed(1)}s · attribution aux pierres non vérifiée`);table.append(tr);
 }target.append(table);
 document.getElementById('context').textContent=`End observé : ${known(r.current_end)}. Points courants dans la maison : ${known(r.current_points_in_house)}. Les panneaux caméra ne constituent pas des identifiants d’extrémités physiques.`;
 document.getElementById('evidence').textContent=JSON.stringify(r,null,2);
}
window.receiveState=(key,rows)=>{cache.set(key,rows);loading.delete(key);tick();};
function tick(){
 let v;try{v=frame.contentDocument?.querySelector('video');}catch(e){status.textContent='Servir ce dossier par HTTP pour synchroniser les vues.';return;}
 if(!v||v.readyState<1)return;
 const t=v.currentTime;let lo=0,hi=times.length;while(lo<hi){let m=(lo+hi)>>1;if(times[m]<=t)lo=m+1;else hi=m;}
 const index=lo-1;currentIndex=index;
 if(index<0||t>times[times.length-1]+0.000001){window.displayedState=null;status.textContent='Hors de l’intervalle des observations : état inconnu';document.getElementById('score').replaceChildren();document.getElementById('context').textContent='';document.getElementById('evidence').textContent='';return;}
 const key=Math.floor(index/chunkSize);
 if(cache.has(key)){show(cache.get(key)[index%chunkSize],t);return;}
 window.displayedState=null;status.textContent='Chargement de l’observation…';document.getElementById('score').replaceChildren();document.getElementById('context').textContent='';document.getElementById('evidence').textContent='';
 if(!loading.has(key)){loading.add(key);const script=document.createElement('script');script.src=`state-${key}.js`;script.onerror=()=>{status.textContent='Observation indisponible';loading.delete(key);};document.body.append(script);}
}
setInterval(tick,150);
</script>'''
    page = page.replace('__VIEWER__', html.escape(os.path.relpath(viewer.resolve(), output.resolve()), quote=True))
    page = page.replace('__TIMES__', json.dumps(times))
    (output / 'index.html').write_text(page)
    evidence = {'development': True, 'samples': len(rows), 'source_sha256': events['source_sha256'],
                'inference_modified': False, 'physical_identity_verified': False,
                'inputs': {str(p.resolve()): hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
                           for p in [viewer, state/'timeline.jsonl', state/'manifest.json', Path(__file__)]}}
    (output / 'manifest.json').write_text(json.dumps(evidence, indent=2))
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--state', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.run, args.state, args.output)))
