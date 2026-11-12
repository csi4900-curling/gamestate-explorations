"""Reusable development postprocessing of public post-throw board observations.

Preserves the source run. Uses saved detections/geometry, upstream OpenCLIP colour
ranking and explicit-dimension house calculations. Does not certify game state.
"""
import argparse
import copy
import hashlib
import html
import json
import math
from pathlib import Path
import time

from prototype.house_points import points_lying


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def select_snapshots(rows, targets):
    """Latest observed board at/before each endpoint, never before its interval."""
    ordered = sorted(targets, key=lambda t: t['end_s'])
    selected = []
    last = None
    index = 0
    previous = None
    for row in rows:
        t = row['time_s']
        if previous is not None and t <= previous:
            raise ValueError('Board stream must be strictly chronological')
        previous = t
        while index < len(ordered) and ordered[index]['end_s'] < t:
            target = ordered[index]
            selected.append((target, last if last and last['time_s'] >= target['start_s'] else None))
            index += 1
        last = row
    for target in ordered[index:]:
        selected.append((target, last if last and target['start_s'] <= last['time_s'] <= target['end_s'] else None))
    return selected


class ColourRanker:
    def __init__(self, config, cache_dir):
        import open_clip
        import torch
        self.torch = torch
        torch.set_num_threads(config['threads'])
        started = time.perf_counter()
        self.model, _, self.transform = open_clip.create_model_and_transforms(
            config['model'], pretrained=config['pretrained'], device='cpu', cache_dir=str(cache_dir))
        self.model.eval()
        self.names = list(config['prompts'])
        with torch.inference_mode():
            text = open_clip.get_tokenizer(config['model'])(list(config['prompts'].values()))
            features = self.model.encode_text(text)
            self.features = features/features.norm(dim=-1, keepdim=True)
        self.metadata = dict(open_clip_version=open_clip.__version__, torch_version=torch.__version__,
                             config=config, device='cpu', load_and_text_wall_s=time.perf_counter()-started)

    def rank(self, image, box):
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
            raise ValueError('Detector box outside source image')
        crop = image.crop((math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1)))
        started = time.perf_counter()
        with self.torch.inference_mode():
            features = self.model.encode_image(self.transform(crop).unsqueeze(0))
            features = features/features.norm(dim=-1, keepdim=True)
            similarity = (features@self.features.T)[0].tolist()
        return dict(prediction=self.names[max(range(len(self.names)), key=similarity.__getitem__)],
                    cosine_similarity=dict(zip(self.names, similarity)),
                    inference_wall_s=time.perf_counter()-started,
                    calibrated_confidence=False,
                    status='forced_text_ranking_not_verified_stone_colour')


def enrich_observation(observation, image, ranker, dimensions):
    row = copy.deepcopy(observation)
    for panel, board in row['boards'].items():
        inputs = []
        for i, stone in enumerate(board['stones']):
            stone['colour_ranking'] = ranker.rank(image, stone['bbox_xyxy'])
            # Keep original colour/team/identity fields; predictions have separate provenance.
            inputs.append(dict(observation_id=f'{panel}:{i}', group=stone['colour_ranking']['prediction'],
                               position_m=stone.get('height_adjusted_local_m')))
        board['conditional_house_points'] = points_lying(inputs, **dimensions)
        board['complete_board_verified'] = False
    row['current_points_from_stones'] = None
    row['team_mapping'] = None
    row['settled'] = None
    row['status'] = 'development_enriched_observation_not_verified_match_state'
    return row


def render(result, output):
    sections = []
    for snapshot in result['snapshots']:
        if snapshot['status'] != 'observed':
            sections.append('<p>'+html.escape(str(snapshot))+'</p>')
            continue
        row = snapshot['observation']
        panels = []
        all_positions = [s['height_adjusted_local_m'] for b in row['boards'].values()
                         for s in b['stones'] if s.get('height_adjusted_local_m') is not None]
        extent = max([2.375]+[abs(v) for p in all_positions for v in p])
        scale = 210/extent
        for panel, board in row['boards'].items():
            points = board['conditional_house_points']
            svg = '<svg viewBox="0 0 480 480" width="400" role="img" aria-label="Positions locales conditionnelles"><rect width="480" height="480" fill="#f4f8fa"/>'
            for radius in [points['house_radius_m'], 1.219, .610]:
                svg += f'<circle cx="240" cy="240" r="{radius*scale}" fill="none" stroke="#a6bec8"/>'
            for i, stone in enumerate(board['stones']):
                p = stone.get('height_adjusted_local_m')
                if p is None:
                    continue
                colour = '#bf2535' if stone['colour_ranking']['prediction'] == 'red' else '#e6c000'
                x, y = 240+p[0]*scale, 240-p[1]*scale
                svg += f'<circle cx="{x}" cy="{y}" r="{points["default_stone_radius_m"]*scale}" fill="{colour}" stroke="#243540"/><text x="{x+5}" y="{y-5}" font-size="10">{i}</text>'
            svg += '</svg><p>Coordonnées locales : x vers la droite, y vers le haut. Même échelle pour les deux panneaux ; numéros d’observation, pas identités physiques.</p>'
            panels.append('<h3>'+html.escape(panel)+'</h3><pre>'+html.escape(json.dumps({
                'points_conditionnels_par_couleur': points['conditional_points_by_group'],
                'observations_sans_geometrie_ou_couleur': points['unresolved_observations'],
                'pierres_detectees': len(board['stones']),
                'plateau_complet_verifie': False}, indent=2))+'</pre>'+svg)
        sections.append(f'<section><h2>{html.escape(snapshot["candidate_id"])}</h2><p>Image source : {row["time_s"]:.3f} s ; fin analysée : {snapshot["analysis_end_s"]:.3f} s ; écart : {snapshot["age_s"]:.3f} s.</p>'
                        f'<img src="{snapshot["image"]}" alt="Deux vues source"><div class="panels">'+''.join('<div>'+p+'</div>' for p in panels)+'</div></section>')
    content='<!doctype html><meta charset="utf-8"><title>État observé après les lancers — développement</title><style>body{font:16px system-ui;max-width:1300px;margin:30px auto;padding:20px}img{width:100%}.panels{display:flex;gap:40px}pre{white-space:pre-wrap}section{border-top:1px solid #ccc;margin-top:25px}</style><h1>État observé après les lancers</h1><p>Développement : couleurs prédites par OpenCLIP ; géométrie et détections conservées du traitement public. Les points conditionnels supposent des pierres distinctes, en jeu, correctement localisées et un plateau complet. Ces conditions ne sont pas vérifiées. Équipes, identité physique, arrêt des pierres et score officiel restent inconnus.</p>'+''.join(sections)+'<p><a href="result.json">Observations, positions et provenance complètes</a></p>'
    (output/'index.html').write_text(content)


def run(public_run, config_path, output, cache_dir):
    import cv2
    from PIL import Image
    public_run, config_path, output = map(Path, (public_run, config_path, output))
    if output.exists():
        raise ValueError('Preserve previous outputs')
    config = json.loads(config_path.read_text())
    dense = json.loads((public_run/'two-view-tracking/result.json').read_text())
    event_data = json.loads((public_run/'events.json').read_text())
    if event_data['source_sha256'] != dense['source_sha256']:
        raise ValueError('Event and tracking source hashes differ')
    ending = json.loads((public_run/'two-view-tracking/end-views.json').read_text())
    events = {e['candidate_id']: e for e in dense['events']}
    targets = []
    unavailable = []
    for end in ending:
        if end['status'] != 'observed':
            unavailable.append(dict(candidate_id=end['candidate_id'], status='unavailable', reason=end.get('reason')))
            continue
        event = events[end['candidate_id']]
        starts = [s['times_s'][0] for s in event['segments'] if s['status'] == 'tracked' and s['times_s']]
        targets.append(dict(candidate_id=end['candidate_id'], start_s=min(starts), end_s=end['time_s']))
    board_path = public_run/'match-observations.jsonl'
    with board_path.open() as stream:
        selected = select_snapshots((json.loads(line) for line in stream), targets)
    if not any(row is not None for _, row in selected):
        output.mkdir(parents=True)
        (output/'code.py').write_bytes(Path(__file__).read_bytes())
        (output/'house_points.py').write_bytes(Path(__file__).with_name('house_points.py').read_bytes())
        snapshots = unavailable+[dict(candidate_id=t['candidate_id'], status='unavailable',
                                     reason='No board observation inside tracked interval before endpoint')
                                 for t, _ in selected]
        result = dict(development=True, source_sha256=dense['source_sha256'], snapshots=snapshots,
                      config=config, model=None, inference_performed=False,
                      source_video_bytes_verified=False,
                      input_sha256={str(p):sha(p) for p in [config_path, board_path, public_run/'events.json', public_run/'two-view-tracking/result.json', public_run/'two-view-tracking/end-views.json']},
                      public_run_modified=False, complete_match_state_verified=False,
                      status='no_eligible_board_observations')
        (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        render(result, output)
        return result
    # Read source from saved segment provenance; match its bytes before processing.
    source = None
    for event in dense['events']:
        for s in event['segments']:
            if s['status'] == 'tracked':
                saved = json.loads((public_run/'two-view-tracking'/s['result']).read_text())
                source = Path(saved['provenance']['video_path'])
                break
        if source is not None:
            break
    if source is None or sha(source) != dense['source_sha256']:
        raise ValueError('Source unavailable or differs from public run')
    output.mkdir(parents=True)
    (output/'code.py').write_bytes(Path(__file__).read_bytes())
    (output/'house_points.py').write_bytes(Path(__file__).with_name('house_points.py').read_bytes())
    started = time.perf_counter()
    ranker = ColourRanker(config['colour'], cache_dir)
    cap = cv2.VideoCapture(str(source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    snapshots = list(unavailable)
    try:
        for i, (target, row) in enumerate(selected):
            if row is None:
                snapshots.append(dict(candidate_id=target['candidate_id'], status='unavailable', reason='No board observation inside tracked interval before endpoint'))
                continue
            frame = round(row['time_s']*fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, bgr = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1 != frame:
                raise ValueError('Could not seek exact source frame')
            image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            image_name = f'source-{i:05d}.png'
            image.save(output/image_name)
            enriched = enrich_observation(row, image, ranker, config['dimensions'])
            snapshots.append(dict(candidate_id=target['candidate_id'], status='observed',
                                  analysis_end_s=target['end_s'], age_s=target['end_s']-row['time_s'],
                                  source_frame_index=frame, image=image_name, observation=enriched))
    finally:
        cap.release()
    result = dict(development=True, source_sha256=dense['source_sha256'], snapshots=snapshots,
                  config=config, model=ranker.metadata, wall_seconds=time.perf_counter()-started,
                  runtime_scope='Model initialization, source-frame decoding, colour inference and house calculation. Excludes input verification, final cache hashing and report serialization; not whole-process runtime.',
                  input_sha256={str(p):sha(p) for p in [config_path, board_path, public_run/'two-view-tracking/result.json', public_run/'two-view-tracking/end-views.json']},
                  cache_sha256={str(p):sha(p) for p in Path(cache_dir).rglob('*') if p.is_file()},
                  source_video_bytes_verified=True, inference_performed=True,
                  public_run_modified=False, complete_match_state_verified=False)
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    render(result, output)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['run', 'config', 'output', 'cache-dir']:
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    r = run(a.run, a.config, a.output, a.cache_dir)
    print(json.dumps(dict(snapshots=len(r['snapshots']), inference_performed=r['inference_performed'], wall_seconds=r.get('wall_seconds'))))
