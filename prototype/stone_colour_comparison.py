"""Development crop-colour comparison using upstream OpenCLIP, without HSV gates.

Ranks configured text descriptions. Similarities are not calibrated confidence;
two-colour ranking does not establish stone existence, team, or physical identity.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def compare(inputs, labels, output, cache_dir):
    import open_clip
    import torch
    from PIL import Image
    inputs, labels, output = map(Path, (inputs, labels, output))
    config = json.loads(inputs.read_text())
    reference = json.loads(labels.read_text())
    if output.exists():
        raise ValueError('Preserve previous comparison')
    output.mkdir(parents=True)
    # Freeze the planned experiment and labels before any model output.
    protocol = dict(inputs_sha256=sha(inputs), labels_sha256=sha(labels),
                    code_sha256=sha(__file__), config=config,
                    upstream='https://github.com/mlfoundations/open_clip',
                    open_clip_version=open_clip.__version__, torch_version=torch.__version__,
                    device='cpu', threads=1, model_changed=False,
                    scope='Development component comparison on supplied crops; not complete stone/colour detection accuracy.')
    (output/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    torch.set_num_threads(1)
    started = time.perf_counter()
    model, _, transform = open_clip.create_model_and_transforms(
        config['model'], pretrained=config['pretrained'], device='cpu', cache_dir=str(cache_dir))
    model.eval()
    load_s = time.perf_counter()-started
    tokenizer = open_clip.get_tokenizer(config['model'])
    names = list(config['prompts'])
    with torch.inference_mode():
        features = model.encode_text(tokenizer([config['prompts'][name] for name in names]))
        features = features/features.norm(dim=-1, keepdim=True)
        rows = []
        for item in config['items']:
            if sha(item['image']) != item['image_sha256']:
                raise ValueError('Source image changed')
            x0, y0, x1, y1 = item['bbox_xyxy']
            with Image.open(item['image']) as image:
                crop = image.convert('RGB').crop((math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1)))
                tensor = transform(crop).unsqueeze(0)
            clock = time.perf_counter()
            embedding = model.encode_image(tensor)
            embedding = embedding/embedding.norm(dim=-1, keepdim=True)
            similarity = (embedding@features.T)[0].tolist()
            predicted = names[max(range(len(names)), key=similarity.__getitem__)]
            actual = reference['labels'].get(item['id'])
            rows.append(dict(id=item['id'], prediction=predicted, reference=actual,
                             correct=predicted == actual if actual is not None else None,
                             cosine_similarity=dict(zip(names, similarity)),
                             inference_wall_s=time.perf_counter()-clock))
            (output/'progress.json').write_text(json.dumps(rows, indent=2)+'\n')
    known = [r for r in rows if r['reference'] is not None]
    result = dict(protocol=protocol, rows=rows, model_load_and_download_wall_s=load_s,
                  labelled_crops=len(known), correct=sum(r['correct'] for r in known),
                  independent_ground_truth=reference.get('independent_ground_truth', False),
                  calibrated_confidence=False, colour_to_team_mapping_established=False,
                  cache_files={str(p):sha(p) for p in Path(cache_dir).rglob('*') if p.is_file()},
                  limitations=['Supplied crop locations may be manual; classification is conditional on these crops.',
                               'Repeated appearances are not independent stone identities.',
                               'Two descriptions force a choice even on unrecognizable or non-stone inputs.',
                               'No production integration or generalization claim.'])
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['inputs', 'labels', 'output', 'cache-dir']:
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    r = compare(a.inputs, a.labels, a.output, a.cache_dir)
    print(json.dumps({k:r[k] for k in ['labelled_crops', 'correct', 'model_load_and_download_wall_s']}))
