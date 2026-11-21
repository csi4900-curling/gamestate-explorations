"""OpenCLIP colour evidence for every saved tracker, not only event stones.

The event colour pass ranks only the delivered stone at its line crossing, so
other stones on a board have no colour. This pass samples full-body detector
boxes spread along each saved track and ranks them with the same upstream
component and prompts. A track gets a colour only when its samples agree. It
does not map colour to team, repair tracking or establish physical identity.
"""
import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path

import cv2

from prototype.detection_cache import digest

DEFAULTS = {'samples_per_track': 5, 'minimum_track_observations': 20,
            'provenance': 'Engineering defaults for a development replay; not validated.'}


def candidates(path, settings):
    """Evenly spaced full-body observations for each sufficiently long track."""
    tracks = {}
    with Path(path).open() as stream:
        for line in stream:
            row = json.loads(line)
            for panel, board in row['boards'].items():
                for stone in board['stones']:
                    if (stone.get('tracker_id') is not None and
                            stone['body_point_support']['status'] == 'full_body_box'):
                        tracks.setdefault((panel, stone['tracker_id']), []).append(
                            (row['frame_index'], row['time_s'], stone['bbox_xyxy']))
    chosen = {}
    for key, rows in tracks.items():
        if len(rows) < settings['minimum_track_observations']:
            continue
        count = settings['samples_per_track']
        chosen[key] = [rows[round(i*(len(rows)-1)/(count-1))] for i in range(count)]
    return chosen, len(tracks)


def read_sample(cap, frame_index):
    """Decode nearby samples in order, with exact-seek fallback for gaps or failures."""
    position = round(cap.get(cv2.CAP_PROP_POS_FRAMES))
    if 0 <= frame_index - position <= 30:
        if all(cap.grab() for _ in range(frame_index - position)):
            ok, image = cap.read()
            if ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES)) == frame_index + 1:
                return image
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, image = cap.read()
    if ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES)) == frame_index + 1:
        return image
    return None


def run(*, public_run, video, config_path, output, settings=None):
    from prototype.stone_colour_model import StoneColourModel
    public_run, output = Path(public_run), Path(output)
    if output.exists():
        raise ValueError('Output exists; preserve the previous run')
    protocol = json.loads((public_run/'protocol.json').read_text())
    if settings is None or 'minimum_track_observations' not in settings:
        eff_hz = float(protocol.get('effective_sample_hz') or 10.0)
        settings = {**DEFAULTS, 'minimum_track_observations': max(5, round(2.0 * eff_hz)), **(settings or {})}
    else:
        settings = {**DEFAULTS, **settings}
    if digest(video) != protocol['source_sha256']:
        raise ValueError('Video does not match public run')
    chosen, total = candidates(public_run/'match-observations.jsonl', settings)
    model = StoneColourModel(config_path)
    started = time.perf_counter()
    # One sequential decode in frame order avoids a seek per crop.
    wanted = {}
    for key, rows in chosen.items():
        for frame, time_s, box in rows:
            wanted.setdefault(frame, []).append((key, time_s, box))
    votes = {key: [] for key in chosen}
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError('Cannot open source video')
    try:
        batch_size = int(settings.get('batch_size', 64))
        use_batched = hasattr(model, 'classify_crops')
        pending_meta = []
        pending_crops = []

        def flush_batch():
            if not pending_meta:
                return
            results = model.classify_crops(pending_crops, batch_size=batch_size)
            for (key, time_s, frame_idx, box), result in zip(pending_meta, results):
                votes[key].append({'time_s': time_s, 'frame_index': frame_idx, 'bbox_xyxy': box,
                                   'status': result['status'], 'prediction': result['prediction'],
                                   'cosine_similarity': result.get('cosine_similarity')})
            pending_meta.clear()
            pending_crops.clear()

        for frame in sorted(wanted):
            image = read_sample(cap, frame)
            if image is None:
                for key, time_s, _ in wanted[frame]:
                    votes[key].append({'time_s': time_s, 'frame_index': frame, 'status': 'decode_failed', 'prediction': None})
                continue
            if use_batched:
                h, w = image.shape[:2]
                for key, time_s, box in wanted[frame]:
                    x0, y0, x1, y1 = box
                    if len(box) == 4 and all(math.isfinite(v) for v in box) and 0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h:
                        crop = image[math.floor(y0):math.ceil(y1), math.floor(x0):math.ceil(x1)].copy()
                    else:
                        crop = None
                    pending_meta.append((key, time_s, frame, box))
                    pending_crops.append(crop)
                    if len(pending_crops) >= batch_size:
                        flush_batch()
            else:
                results = model.classify(image, [{'bbox_xyxy': box} for _, _, box in wanted[frame]])
                for (key, time_s, box), result in zip(wanted[frame], results):
                    votes[key].append({'time_s': time_s, 'frame_index': frame, 'bbox_xyxy': box,
                                       'status': result['status'], 'prediction': result['prediction'],
                                       'cosine_similarity': result.get('cosine_similarity')})
        if use_batched:
            flush_batch()
    finally:
        cap.release()
    tracks = {}; evidence = {}
    for (panel, tracker_id), rows in votes.items():
        counts = Counter(r['prediction'] for r in rows if r['prediction'])
        answered = sum(counts.values())
        colour = next(iter(counts)) if len(counts) == 1 and answered == len(rows) else None
        tracks.setdefault(panel, {})[str(tracker_id)] = colour
        evidence.setdefault(panel, {})[str(tracker_id)] = {
            'colour': colour, 'votes': dict(counts), 'samples': rows,
            'status': ('sample_agreement' if colour else 'sample_disagreement' if len(counts) > 1
                       else 'unavailable')}
    result = {'schema_version': 'track-colour-development-v1', 'development': True,
              'source_sha256': protocol['source_sha256'], 'tracks': tracks, 'evidence': evidence,
              'summary': {'tracks_in_observations': total, 'tracks_sampled': len(votes),
                          'agreement': sum(v is not None for p in tracks.values() for v in p.values()),
                          'colours': dict(Counter(v for p in tracks.values() for v in p.values() if v)),
                          'wall_seconds': time.perf_counter()-started,
                          'calibrated_confidence': False, 'team_mapping_established': False,
                          'physical_identity_verified': False},
              'provenance': {'model': model.provenance, 'settings': settings, 'code_sha256': digest(__file__),
                             'observations_sha256': digest(public_run/'match-observations.jsonl'),
                             'limitations': ['Forced choice among configured prompts; occluded or mixed crops can be wrong.',
                                             'Agreement along one track is not independent evidence if the track switched stones.']}}
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('public-run', 'video', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--config', dest='config_path', required=True)
    print(json.dumps(run(**vars(parser.parse_args()))['summary']))
