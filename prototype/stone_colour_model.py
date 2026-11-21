"""Optional upstream OpenCLIP crop-colour evidence; never a verified team label.

Uses configured text prompts without HSV thresholds. A ranked colour is a forced
choice among those prompts; mixed, occluded and non-stone crops can be wrong.
"""
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import time


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@contextmanager
def torch_threads(torch, count):
    previous = torch.get_num_threads()
    torch.set_num_threads(count)
    try:
        yield
    finally:
        torch.set_num_threads(previous)


class StoneColourModel:
    def __init__(self, config_path):
        import open_clip
        import torch
        self.config = json.loads(Path(config_path).read_text())
        config = self.config
        self.names = list(config['prompts'])
        if len(self.names) < 2 or any(not isinstance(v, str) or not v.strip() for v in config['prompts'].values()):
            raise ValueError('At least two explicit nonempty colour prompts required')
        self.threads = config['threads']
        if type(self.threads) is not int or self.threads < 1:
            raise ValueError('Positive integer thread setting required')
        self.torch = torch
        started = time.perf_counter()
        with torch_threads(torch, self.threads):
            pretrained = open_clip.get_pretrained_cfg(config['model'], config['pretrained'])
            if not pretrained:
                raise ValueError('Unknown upstream pretrained configuration')
            weights = open_clip.download_pretrained(pretrained, cache_dir=config['cache_dir'])
            self.model, _, self.transform = open_clip.create_model_and_transforms(
                config['model'], pretrained=config['pretrained'], device='cpu', cache_dir=config['cache_dir'])
            self.model.eval()
            tokenizer = open_clip.get_tokenizer(config['model'])
            with torch.inference_mode():
                features = self.model.encode_text(tokenizer(list(config['prompts'].values())))
                self.features = features/features.norm(dim=-1, keepdim=True)
        self.provenance = {'backend': 'upstream OpenCLIP image/text cosine similarity',
                           'model': config['model'], 'pretrained': config['pretrained'],
                           'prompts': config['prompts'], 'device': 'cpu', 'threads': self.threads,
                           'config_sha256': digest(config_path), 'weights_sha256': digest(weights),
                           'code_sha256': digest(__file__), 'open_clip_version': open_clip.__version__,
                           'torch_version': str(torch.__version__),
                           'load_and_text_encoding_wall_s': time.perf_counter()-started,
                           'calibrated_confidence': False, 'physical_identity_verified': False,
                           'team_mapping_verified': False}

    def classify_crops(self, crops_bgr, *, batch_size=64):
        """Encode pre-extracted BGR stone crops in batches using the same OpenCLIP transform."""
        from PIL import Image
        if not crops_bgr:
            return []
        rows = [None] * len(crops_bgr)
        valid_indices = []
        tensors = []
        for index, crop_bgr in enumerate(crops_bgr):
            if crop_bgr is None or getattr(crop_bgr, 'size', 0) == 0:
                rows[index] = {'detection_index': index, 'status': 'unavailable_invalid_crop', 'prediction': None}
                continue
            valid_indices.append(index)
            tensors.append(self.transform(Image.fromarray(crop_bgr[:, :, ::-1])))
        if tensors:
            with torch_threads(self.torch, self.threads), self.torch.inference_mode():
                for start in range(0, len(tensors), batch_size):
                    started = time.perf_counter()
                    chunk = tensors[start:start + batch_size]
                    chunk_indices = valid_indices[start:start + batch_size]
                    batch = self.torch.stack(chunk)
                    embeddings = self.model.encode_image(batch)
                    embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
                    similarities = (embeddings @ self.features.T).tolist()
                    per_crop_s = (time.perf_counter() - started) / len(chunk)
                    for idx, similarity in zip(chunk_indices, similarities):
                        rows[idx] = {
                            'detection_index': idx,
                            'status': 'unverified_colour_ranking',
                            'prediction': self.names[max(range(len(self.names)), key=similarity.__getitem__)],
                            'cosine_similarity': dict(zip(self.names, similarity)),
                            'calibrated_confidence': False,
                            'wall_seconds': per_crop_s,
                            'single_stone_extent_verified': False,
                            'team': None,
                        }
        return rows

    def classify(self, frame_bgr, detections):
        height, width = frame_bgr.shape[:2]
        crops = []
        for detection in detections:
            bounds = detection['bbox_xyxy']
            if len(bounds) != 4 or not all(math.isfinite(v) for v in bounds):
                raise ValueError('Finite crop bounds required')
            x0, y0, x1, y1 = bounds
            if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
                crops.append(None)
                continue
            crops.append(frame_bgr[math.floor(y0):math.ceil(y1), math.floor(x0):math.ceil(x1)])
        return self.classify_crops(crops)
