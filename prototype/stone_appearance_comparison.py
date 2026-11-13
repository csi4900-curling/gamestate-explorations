"""Development crop retrieval diagnostic using upstream OpenCLIP embeddings.

Reference local tracker IDs select source crops, not physical ground truth.
This does not alter tracking, associate cameras, or enable ReID in the pipeline.
"""
import argparse
import json
import math
from pathlib import Path
import time
from prototype.stone_colour_model import StoneColourModel, digest, torch_threads


def run(plan_path, output):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageOps
    plan_path, output = Path(plan_path), Path(output)
    if output.exists():
        raise ValueError('Preserve previous appearance comparison')
    plan = json.loads(plan_path.read_text())
    reference = Path(plan['reference'])
    events = json.loads((reference/'events.json').read_text())
    if digest(plan['video']) != events['source_sha256']:
        raise ValueError('Source hash mismatch')
    wanted = {round(t*events['source_fps']) for t in plan['times_s']}
    rows = {}
    with (reference/'observations.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['frame_index'] in wanted:
                rows[row['frame_index']] = row
    if set(rows) != wanted:
        raise ValueError('Requested source samples unavailable')
    output.mkdir(parents=True)
    (output/'plan.json').write_text(json.dumps(plan, indent=2))
    (output/'stone_appearance_comparison.py').write_bytes(Path(__file__).read_bytes())
    model = StoneColourModel(plan['model_config'])
    cap = cv2.VideoCapture(plan['video'])
    crops, embeddings = [], []
    sheet = Image.new('RGB', (240*len(plan['track_ids']), 190*len(wanted)), 'white')
    draw = ImageDraw.Draw(sheet)
    started = time.perf_counter()
    try:
        with torch_threads(model.torch, model.threads), model.torch.inference_mode():
            for i, frame_index in enumerate(sorted(rows)):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1 != frame_index:
                    raise ValueError('Exact source frame unavailable')
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                row = rows[frame_index]
                for j, identity in enumerate(plan['track_ids']):
                    found = [t for t in row['tracked_observations'] if t['track_id'] == identity]
                    if len(found) != 1:
                        raise ValueError('Requested local track has no unique observation')
                    track = found[0]
                    bounds = row['detections'][track['detection_index']]['bbox_xyxy']
                    x0, y0, x1, y1 = bounds
                    if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
                        raise ValueError('Invalid source crop')
                    crop = image.crop((math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1)))
                    feature = model.model.encode_image(model.transform(crop).unsqueeze(0))
                    feature = feature/feature.norm(dim=-1, keepdim=True)
                    embeddings.append(feature[0].cpu().numpy())
                    crops.append({'frame_index': frame_index, 'time_s': row['time_s'],
                                  'local_track_id': identity, 'bbox_xyxy': bounds})
                    sheet.paste(ImageOps.contain(crop, (230, 160)), (j*240, i*190+25))
                    draw.text((j*240+5, i*190+5), f"{row['time_s']} s / local ID {identity}", fill='black')
    finally:
        cap.release()
    embeddings = np.asarray(embeddings)
    similarities = embeddings@embeddings.T
    count = len(plan['track_ids'])
    comparisons = []
    for offset in range(count, len(crops), count):
        for query in range(count):
            rank = sorted(range(offset, offset+count), key=lambda k: float(similarities[query,k]), reverse=True)
            comparisons.append({'query_crop': query, 'gallery_time_s': crops[offset]['time_s'],
                                'ranked_gallery_crops': rank,
                                'cosines': [float(similarities[query,k]) for k in rank],
                                'top_rank_agrees_with_local_track': crops[query]['local_track_id'] == crops[rank[0]]['local_track_id']})
    result = {'development': True, 'physical_identity_accuracy': None,
              'model': model.provenance, 'crop_decode_and_embedding_wall_s': time.perf_counter()-started,
              'inputs': {str(p.resolve()): digest(p) for p in [plan_path, reference/'observations.jsonl', Path(__file__)]},
              'crops': crops, 'comparisons': comparisons,
              'scope': 'Image-embedding retrieval among selected source crops; local tracker labels are not independent physical identity ground truth.'}
    np.save(output/'embeddings.npy', embeddings)
    sheet.save(output/'source-crops.png')
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.plan, args.output)
