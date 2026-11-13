"""Train a handle OBB development baseline using maintained Ultralytics training.

This command never changes the workbench profile or installs new dependencies.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def train(config_path):
    import torch
    import ultralytics
    from ultralytics import YOLO
    config_path = Path(config_path)
    config = json.loads(config_path.read_text())
    output = Path(config['project'])/config['name']
    if output.exists():
        raise ValueError('Output exists; preserve prior training attempt')
    torch.set_num_threads(config['threads'])
    model = YOLO(config['model'])
    # Resolve/download pretrained input before capturing the actual model hash.
    model_path = Path(model.ckpt_path)
    manifest = {'development':True,'config':config,'torch':torch.__version__,
                'ultralytics':ultralytics.__version__,
                'pretrained_model_sha256':digest(model_path),
                'trainer_adapter_sha256':digest(__file__),
                'training_config_sha256':digest(config_path),
                'data_yaml_sha256':digest(config['data']),
                'split_sha256':digest(Path(config['data']).with_name('split.json')),
                'dataset_manifest_sha256':digest(Path(config['data']).with_name('download-manifest.json')),
                'validation_scope':'Internal image-block development validation. Upstream source-video group IDs unavailable. No main-project recording is training data. No independent accuracy claim.'}
    protocol = config_path.with_name(config_path.stem+'-resolved-inputs.json')
    if protocol.exists():
        raise ValueError('Resolved training protocol exists; preserve it')
    protocol.write_text(json.dumps(manifest,indent=2)+'\n')
    started = time.perf_counter()
    options = {k:v for k,v in config.items() if k not in ['model','threads']}
    model.train(**options)
    manifest.update(wall_s=time.perf_counter()-started,
                    best_sha256=digest(output/'weights/best.pt'),
                    last_sha256=digest(output/'weights/last.pt'),
                    results_csv_sha256=digest(output/'results.csv'))
    (output/'training-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'wall_s':manifest['wall_s'],'best_sha256':manifest['best_sha256']}),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    args = parser.parse_args()
    train(args.config)
