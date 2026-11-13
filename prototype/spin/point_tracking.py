"""Thin adapter around the unmodified upstream CoTracker3 online predictor."""
from pathlib import Path
import hashlib
import time

import cv2
import numpy as np

UPSTREAM_COMMIT = '82e02e8029753ad4ef13cf06be7f4fc5facdda4d'


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def decoder_identity():
    return {'opencv_version':cv2.__version__,
            'build_sha256':hashlib.sha256(cv2.getBuildInformation().encode()).hexdigest()}


def read_clip(video, start, end, crop=None, *, storage_path=None, frame_step=1):
    if isinstance(frame_step, bool) or not isinstance(frame_step, int) or frame_step < 1:
        raise ValueError('frame_step must be a positive integer')
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError(f'Cannot open {video}')
    fps = cap.get(cv2.CAP_PROP_FPS)
    first = round(start * fps)
    last = round(end * fps)
    if first < 0 or last <= first or last > int(cap.get(cv2.CAP_PROP_FRAME_COUNT)):
        raise ValueError('Invalid source interval')
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    crop = list(crop or [0, 0, width, height])
    x0, y0, x1, y1 = crop
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError('Crop outside source frame')
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    frames, indices, times = [], [], []
    mapped=None
    if storage_path is not None:
        mapped=np.lib.format.open_memmap(storage_path,mode='w+',dtype=np.uint8,
                                        shape=(len(range(first,last,frame_step)),y1-y0,x1-x0,3))
    try:
        for expected in range(first, last):
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f'Decode failed at frame {expected}')
            decoded = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if decoded != expected:
                raise ValueError(f'Seek mismatch: expected {expected}, decoded {decoded}')
            if (expected-first) % frame_step:
                continue
            # Decoder timestamps support variable presentation spacing where available.
            pts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if times and pts <= times[-1]:
                raise ValueError('Decoder did not return increasing presentation timestamps')
            rgb=cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
            if mapped is None:frames.append(rgb)
            else:mapped[len(indices)]=rgb
            indices.append(decoded)
            times.append(pts)
    finally:
        cap.release()
    if mapped is not None:mapped.flush()
    return mapped if mapped is not None else np.asarray(frames), np.asarray(times), indices, fps, crop


def track_points(frames, queries, checkpoint, *, device='cpu', threads=4, progress=None, mode='online', progress_directory=None, decoded_sha256=None):
    import torch
    from cotracker.predictor import CoTrackerOnlinePredictor, CoTrackerPredictor

    if len(frames) < 2:
        raise ValueError('Need at least two frames')
    torch.set_num_threads(threads)
    started = time.perf_counter()
    if mode not in ('online', 'offline'):
        raise ValueError('mode must be online or offline')
    cls = CoTrackerOnlinePredictor if mode == 'online' else CoTrackerPredictor
    model = cls(checkpoint=str(checkpoint)).to(device).eval()
    loaded = time.perf_counter()
    queries = np.asarray(queries, dtype=np.float32)
    if queries.ndim != 2 or queries.shape[1] != 3 or not np.isfinite(queries).all():
        raise ValueError('Queries must be finite [frame_index, x, y] rows')
    if np.any(queries[:, 0] != 0):
        raise ValueError('This adapter seeds all queries in the first clip frame')
    h, w = frames.shape[1:3]
    if np.any(queries[:, 1:] < 0) or np.any(queries[:, 1] >= w) or np.any(queries[:, 2] >= h):
        raise ValueError('Seed outside crop')

    def tensor(part):
        return torch.from_numpy(np.ascontiguousarray(part)).permute(0, 3, 1, 2)[None].float().to(device)

    progress_path = None
    resumed_offset = 0
    saved_windows = 0
    checkpoint_write_s = 0.
    if progress_directory is not None:
        if mode != 'online' or device != 'cpu':
            raise ValueError('Progress checkpoints currently require online CPU tracking')
        import cotracker
        from .online_checkpoint import contract_key, save, restore
        package = Path(cotracker.__file__).parent
        contract = dict(decoded_sha256=decoded_sha256 or hashlib.sha256(frames).hexdigest(),
                        shape=list(frames.shape), dtype=str(frames.dtype), queries=queries.tolist(),
                        checkpoint_sha256=digest(checkpoint), torch_version=str(torch.__version__),
                        torch_build=torch.__config__.show(), threads=threads, device=device,
                        support_grid=True, mode=mode, upstream_commit=UPSTREAM_COMMIT,
                        upstream_code={str(p.relative_to(package)):digest(p) for p in sorted(package.rglob('*.py'))},
                        adapter_sha256=digest(Path(__file__)),
                        checkpoint_adapter_sha256=digest(Path(__file__).with_name('online_checkpoint.py')))
        progress_path = Path(progress_directory)/(contract_key(contract)+'.pt')
    with torch.inference_mode():
        if mode == 'offline':
            tracks, visible = model(tensor(frames), queries=torch.as_tensor(queries, device=device)[None])
            if progress:
                progress(len(frames), len(frames))
        else:
            step = model.step
            model(tensor(frames[:step * 2]), is_first_step=True,
                  queries=torch.as_tensor(queries, device=device)[None], add_support_grid=True)
            if progress_path is not None and progress_path.exists():
                resumed_offset, tracks, visible = restore(progress_path, model, contract, device)
            # Upstream online windows overlap by model.step; each call advances one step.
            for offset in range(resumed_offset, max(1, len(frames) - step), step):
                tracks, visible = model(tensor(frames[offset:offset + 2 * step]), add_support_grid=True)
                if progress_path is not None:
                    checkpoint_started = time.perf_counter()
                    save(progress_path, model, contract, offset+step, tracks, visible)
                    checkpoint_write_s += time.perf_counter()-checkpoint_started
                    saved_windows += 1
                if progress:
                    progress(min(offset + 2 * step, len(frames)), len(frames))
        tracks = tracks[0, :len(frames)].cpu().numpy()
        visible = visible[0, :len(frames)].cpu().numpy()
    if len(tracks) != len(frames):
        raise RuntimeError('Upstream output length does not match source frames')
    return tracks, visible, {
        'model_load_wall_s': loaded - started,
        'inference_wall_s': time.perf_counter() - loaded,
        'device': device, 'threads': threads, 'torch_version': torch.__version__, 'mode': mode,
        'upstream_commit': UPSTREAM_COMMIT,
        'checkpoint_sha256': digest(checkpoint),
        'visibility_semantics': 'Upstream visibility decision; not calibrated accuracy probability',
        'support_grid': True, 'native_frame_count': len(frames),
        'progress_checkpoint': {'enabled': progress_path is not None,
                                'path': str(progress_path) if progress_path is not None else None,
                                'resumed_window_offset': resumed_offset, 'windows_saved': saved_windows,
                                'write_wall_s': checkpoint_write_s},
    }


def pair_angles(tracks, visible, pair, homography=None, min_separation_px=4.):
    a, b = pair
    delta = tracks[:, b] - tracks[:, a]
    valid = visible[:, a] & visible[:, b] & (np.linalg.norm(delta, axis=1) >= min_separation_px)
    xy = tracks[:, [a, b]]
    if homography is not None:
        H = np.asarray(homography, dtype=float)
        if H.shape != (3, 3) or not np.isfinite(H).all() or np.linalg.matrix_rank(H) != 3:
            raise ValueError('Homography must be finite and nonsingular')
        p = np.concatenate([xy, np.ones((*xy.shape[:2], 1))], axis=2) @ H.T
        valid &= np.all(np.abs(p[:, :, 2]) > 1e-8, axis=1)
        xy = p[:, :, :2] / np.where(np.abs(p[:, :, 2:]) > 1e-8, p[:, :, 2:], np.nan)
    delta = xy[:, 1] - xy[:, 0]
    angles = np.arctan2(delta[:, 1], delta[:, 0])
    valid &= np.isfinite(angles)
    return angles, valid
