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

    def classify(self, frame_bgr, detections):
        from PIL import Image
        image = Image.fromarray(frame_bgr[:, :, ::-1])
        rows = []
        with torch_threads(self.torch, self.threads), self.torch.inference_mode():
            for index, detection in enumerate(detections):
                started = time.perf_counter()
                bounds = detection['bbox_xyxy']
                if len(bounds) != 4 or not all(math.isfinite(v) for v in bounds):
                    raise ValueError('Finite crop bounds required')
                x0, y0, x1, y1 = bounds
                if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
                    rows.append({'detection_index': index, 'status': 'unavailable_invalid_crop', 'prediction': None})
                    continue
                crop = image.crop((math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1)))
                embedding = self.model.encode_image(self.transform(crop).unsqueeze(0))
                embedding = embedding/embedding.norm(dim=-1, keepdim=True)
                similarity = (embedding@self.features.T)[0].tolist()
                rows.append({'detection_index': index, 'status': 'unverified_colour_ranking',
                             'prediction': self.names[max(range(len(self.names)), key=similarity.__getitem__)],
                             'cosine_similarity': dict(zip(self.names, similarity)),
                             'calibrated_confidence': False, 'wall_seconds': time.perf_counter()-started,
                             'single_stone_extent_verified': False, 'team': None})
        return rows
