"""One configurable spin experiment entry point, using upstream point tracking.

Seed locations and crops are explicitly supplied initialization data. Automatic
handle identification and physical orientation validation are not implemented.
"""
from dataclasses import asdict
import json
import hashlib
from pathlib import Path
import time
import tempfile

import numpy as np

from .gaps import GapConfig, reconstruct, evaluate_hidden_intervals
from .point_tracking import digest, read_clip, track_points, pair_angles, decoder_identity
from .report import write_report
from .projection import project_existing
from .episodes import receiving_episode_interval, receiving_scene_seeds, learned_scene_seeds


def candidate_config(video, aggregate_path, segment_id, *, receiving_scene=False):
    """Seed the existing normalized split-pipeline observation in native pixels.

    No manual landmark or new calibration. Only the split pipeline's documented
    640x360 observation coordinates are supported; other adapters must not enter.
    """
    import cv2
    aggregate = json.loads(Path(aggregate_path).read_text())
    if aggregate['context']['source_sha256'] != digest(video):
        raise ValueError('Aggregate source differs from video')
    found = [(e, s) for e in aggregate['events'] for s in e['segments'] if s['segment_id'] == segment_id]
    if len(found) != 1:
        raise ValueError('Requested segment must exist exactly once')
    event, segment = found[0]
    if segment['camera'] not in ('left_split', 'right_split') or not segment['pixel_points']:
        raise ValueError('Automatic seeding requires a nonempty split-camera segment')
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError('Cannot open source video')
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps, count = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    points = sorted(segment['pixel_points'], key=lambda p: p['time_s'])
    point_kind=segment.get('point_kind','cap_with_body_support')
    if point_kind not in ('cap_with_body_support','body_box_center'):
        raise ValueError('Unsupported segment point semantics')
    config = {
        'source_sha256': aggregate['context']['source_sha256'],
        'expected_decoder': decoder_identity(),
        'candidate_id': event['candidate_id'], 'segment_id': segment_id,
        'interval_s': [points[0]['time_s'], min(count/fps, points[-1]['time_s'] + 1/fps)],
        'crop_px': [0,0,width//2,height] if segment['camera']=='left_split' else [width//2,0,width,height],
        'seed_from_segment': True, 'segment_to_source_scale': [width/640, height/360],
        'orientation_pair': None, 'evaluation_masks_s': [],
        'known_breaks_s': segment.get('camera_cut_times_s', []),
        'initialization_method': 'first existing cap observation; fixed split-panel crop; native-coordinate rescaling',
    }
    if point_kind!='cap_with_body_support':
        config['segment_point_kind']=point_kind
        config['frame_storage']='memmap'
        config['initialization_method']='first existing learned body-box observation; fixed split-panel crop; native-coordinate rescaling'
    if receiving_scene and segment.get('role')=='receiving' and segment['camera']=='right_split':
        if point_kind=='body_box_center':
            config.update(receiving_scene=False,episode_policy={'end_reason':'observed_learned_track_extent',
                          'physical_stop_detected':False,'legacy_cap_episode_budget_applied':False})
            return config
        interval,diagnostic=receiving_episode_interval(aggregate,event,segment,count/fps)
        config.update(interval_s=interval,receiving_scene=True,episode_policy=diagnostic,
                      scene_seed_detector="existing_right_caps")
    return config


def run(video, config_path, output, *, checkpoint, device='cpu', mode='online', threads=4,
        aggregate_path=None, reuse_result=None, expected_decoder_sha=None, stone_detector=None):
    started = time.perf_counter()
    video, config_path, output = Path(video), Path(config_path), Path(output)
    config = json.loads(config_path.read_text())
    decoder=decoder_identity()
    if ((expected_decoder_sha is not None and decoder['build_sha256']!=expected_decoder_sha)
        or (config.get('expected_decoder') is not None and config['expected_decoder']!=decoder)):
        raise ValueError('Decoder differs from initialization/main pipeline; align OpenCV environments before inference')
    source_hash = digest(video)
    if config.get('source_sha256') != source_hash:
        raise ValueError('Initialization config does not match source video hash')
    if output.exists():
        raise ValueError('Output already exists; preserve previous runs')
    start, end = config['interval_s']
    seeds = config.get('points', [])
    pair = config.get('orientation_pair')
    if aggregate_path is not None:
        aggregate = json.loads(Path(aggregate_path).read_text())
        if aggregate['context']['source_sha256'] != source_hash:
            raise ValueError('Aggregate source differs from spin source')
        event = next((e for e in aggregate['events'] if e['candidate_id'] == config.get('candidate_id')), None)
        if event is None:
            raise ValueError('Spin config candidate is absent from aggregate')
        segment = next((s for s in event['segments'] if s['segment_id'] == config.get('segment_id')), None)
        if segment is None or not segment['pixel_points']:
            raise ValueError('Spin config segment has no source observations')
        observed_times = [p['time_s'] for p in segment['pixel_points']]
        if end < min(observed_times) or start > max(observed_times):
            raise ValueError('Spin interval does not overlap candidate track')
        if config.get('seed_from_segment'):
            matches = [p for p in segment['pixel_points'] if abs(p['time_s']-start) < 1e-6]
            if len(matches) != 1:
                raise ValueError('Automatic segment seeding requires start at an existing observation timestamp')
            scale = config.get('segment_to_source_scale', [1, 1])
            kind=config.get('segment_point_kind','cap_with_body_support')
            if kind not in ('cap_with_body_support','body_box_center'):
                raise ValueError('Unsupported segment point semantics')
            if segment.get('point_kind','cap_with_body_support')!=kind:
                raise ValueError('Segment/config point semantics disagree')
            seed={'name':'candidate_cap_point' if kind=='cap_with_body_support' else 'candidate_body_box_center',
                  'pixel':[p*s for p,s in zip(matches[0]['pixel'],scale)]}
            if kind!='cap_with_body_support':seed['point_kind']=kind
            seeds=[seed]
            config['seed_provenance'] = ('Existing pipeline cap observation; automatic seed, not a handle landmark or verified physical identity' if kind=='cap_with_body_support' else
                                         'Existing pipeline learned body-box observation; automatic seed, not a handle landmark or verified physical identity')
            if stone_detector is not None:
                additional, diagnostic=learned_scene_seeds(video,start,seeds[0]['pixel'],config['crop_px'],stone_detector)
                seeds.extend(additional)
                config['scene_initialization']=diagnostic
                config['seed_provenance'] += '; learned body-box scene queries, no colour filters; existing event anchor retained'
            elif config.get('receiving_scene'):
                additional,diagnostic=receiving_scene_seeds(video,start,seeds[0]['pixel'],segment['colour'],
                                                               detector=config.get('scene_seed_detector','existing_right_caps'))
                seeds.extend(additional)
                config['scene_initialization']=diagnostic
                config['seed_provenance'] += '; additional first-frame cap proposals from unchanged detector; query IDs are not verified physical identities'

    elif config.get('seed_from_segment'):
        raise ValueError('Automatic segment seeding needs an aggregate')
    if not seeds or not config.get('seed_provenance'):
        raise ValueError('Need named point seeds and explicit initialization provenance')
    if len(set(p['name'] for p in seeds)) != len(seeds):
        raise ValueError('Point names must be unique')
    if pair is not None and (len(pair) != 2 or len(set(pair)) != 2 or any(i < 0 or i >= len(seeds) for i in pair)):
        raise ValueError('orientation_pair must identify two different seed indices')
    gap_cfg = GapConfig(**config.get('gap_model', {}))
    gap_cfg.validate()
    output.mkdir(parents=True)
    (output/'input-config.json').write_bytes(config_path.read_bytes())
    code_bytes = {p.name: p.read_bytes() for p in Path(__file__).parent.glob('*.py')}
    (output/'code-snapshot').mkdir()
    for name, content in code_bytes.items():
        (output/'code-snapshot'/name).write_bytes(content)
    frame_storage=config.get('frame_storage','memory')
    if frame_storage not in ('memory','memmap'):raise ValueError('Unknown decoded frame storage')
    with tempfile.TemporaryDirectory(prefix='decoded-',dir=output) as temporary:
        storage_path=Path(temporary)/'frames.npy' if frame_storage=='memmap' else None
        frames=None
        try:
            frames, times, indices, fps, crop = read_clip(video, start, end, config.get('crop_px'), storage_path=storage_path,
                                                        frame_step=config.get('frame_step',1))
            decode_finished = time.perf_counter()
            queries = [[0, p['pixel'][0]-crop[0], p['pixel'][1]-crop[1]] for p in seeds]
            decoded_input={'decoder':decoder,'shape':list(frames.shape),
                           'rgb_uint8_sha256':hashlib.sha256(frames).hexdigest()}
            query_input=np.asarray(queries,dtype=np.float32).tolist()
            if reuse_result is None:
                tracks, visible, model = track_points(frames, queries, checkpoint, device=device, threads=threads,
                                                    mode=mode, progress_directory=config.get('tracking_progress_directory'),
                                                    decoded_sha256=decoded_input['rgb_uint8_sha256'],
                                                    progress=lambda a,b: print(f'CoTracker: {a}/{b} frames', flush=True))
                tracks += np.asarray(crop[:2])
            else:
                cached_path = Path(reuse_result)
                cached = json.loads(cached_path.read_text())
                raw_path = cached_path.parent/'point-tracks.npz'
                if (cached['provenance'].get('decoded_input') != decoded_input
                    or cached['provenance'].get('query_input') != query_input
                    or cached['point_names'] != [p['name'] for p in seeds]
                    or cached['provenance']['source_sha256'] != source_hash
                    or cached['provenance']['config_sha256'] != digest(config_path)
                    or cached['model']['checkpoint_sha256'] != digest(checkpoint)
                    or cached['model']['mode'] != mode
                    or cached['provenance']['point_tracks_sha256'] != digest(raw_path)
                    or cached['provenance']['code_sha256']['point_tracking.py'] != digest(Path(__file__).parent/'point_tracking.py')):
                    raise ValueError('Cached point predictions do not match source/config/weights/mode/adapter')
                with np.load(raw_path) as raw:
                    if not np.allclose(raw['times'],times) or raw['frame_indices'].tolist()!=indices:
                        raise ValueError('Cached frame timestamps differ from source decode')
                    tracks, visible = raw['tracks'].copy(), raw['visible'].copy()
                model = {**cached['model'], 'reused_result_sha256': digest(cached_path),
                         'runtime_note': 'Inference time belongs to preserved original run; neural inference was not repeated'}
        finally:
            if isinstance(frames,np.memmap):frames._mmap.close()
    np.savez_compressed(output/'point-tracks.npz', tracks=tracks, visible=visible, times=times, frame_indices=indices)
    # H is an explicitly supplied, existing camera mapping, never fitted per clip here.
    H = config.get('image_to_plane_homography')
    if H is not None and not config.get('geometry_provenance'):
        raise ValueError('Existing homography requires explicit provenance')
    if pair is None:
        angles, observed = np.full(len(times), np.nan), np.zeros(len(times), dtype=bool)
    else:
        angles, observed = pair_angles(tracks, visible, pair, H,
                                      min_separation_px=config.get('min_pair_separation_px', 4.0))
    breaks = config.get('known_breaks_s', [])
    rec = reconstruct(times, angles, observed, gap_cfg, breaks=breaks)
    evaluation = evaluate_hidden_intervals(times, angles, observed, config.get('evaluation_masks_s', []),
                                          gap_cfg, breaks=breaks)
    coordinate_system = 'supplied plane coordinates (unvalidated)' if H is not None else 'image coordinates'
    result = {
        'schema_version': 'spin-development-v1', 'status': 'development_point_tracking_and_gap_model',
        'candidate_id': config.get('candidate_id'), 'segment_id': config.get('segment_id'),
        'interval_s': [start, end], 'fps': fps, 'crop_px': crop,
        'sampling': {'source_fps':fps,'frame_step':config.get('frame_step',1),
                     'nominal_sample_hz':fps/config.get('frame_step',1),
                     'timestamps':'Source presentation times, no interpolation of skipped frames'},
        'frame_indices': indices, 'times_s': times.tolist(),
        'point_names': [p['name'] for p in seeds], 'point_kinds':[p.get('point_kind','cap_with_body_support') for p in seeds], 'tracks_px': tracks.tolist(), 'point_visible': visible.tolist(),
        'seed_provenance': config['seed_provenance'],
        'angle_coordinate_system': coordinate_system,
        'orientation_scope': 'Development: model point-pair orientation in '+coordinate_system+'. '
                             'Point identity and physical stone spin are not validated. No physical revolution count is claimed.',
        'physical_revolutions': None,
        'reconstruction': rec,
        'masked_evaluation': evaluation,
        'evaluation_scope': 'Masked-model consistency check against withheld CoTracker-derived angles; '
                            'not independent physical-angle or revolution accuracy. Hidden angles are excluded from fitting.',
        'config': {**config, 'gap_model': asdict(gap_cfg)}, 'model': model,
        'provenance': {
            'video_path': str(video.resolve()), 'source_sha256': source_hash,
            'config_sha256': digest(config_path), 'checkpoint_sha256': digest(checkpoint),
            'decoded_input':decoded_input,'query_input':query_input,
            'aggregate_sha256': digest(aggregate_path) if aggregate_path else None,
            'point_tracks_sha256': digest(output/'point-tracks.npz'),
            'code_sha256': {name: digest(output/'code-snapshot'/name) for name in code_bytes},
            'decode_and_preparation_wall_s': decode_finished-started,
            'total_wall_s_before_report': time.perf_counter()-started,
        },
    }
    if pair is None:
        result['orientation_scope'] = 'Development: dense tracking of the candidate query and any scene queries, with feature types recorded in point_kinds. No handle orientation or physical revolutions are inferred.'
    if aggregate_path is not None and config.get('seed_from_segment'):
        result['projection'] = project_existing(video, aggregate_path, config['segment_id'], times, tracks, visible, point_kinds=result['point_kinds'], **({'heights_m': config['feature_heights_m']} if 'feature_heights_m' in config else {}))
    result['provenance']['total_wall_s_before_report'] = time.perf_counter()-started
    (output/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    write_report(result, output, video)
    return result
