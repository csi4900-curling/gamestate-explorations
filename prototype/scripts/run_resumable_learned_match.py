"""Restart a public learned-match run after interruption, preserving every attempt.

Only immutable learned detections are replayed; tracker and geometry state are
rebuilt by the unchanged public pipeline. This does not claim dense-stage resume.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def main(config_path):
    config_path=Path(config_path).resolve();cfg=json.loads(config_path.read_text());root=Path(cfg['attempt_root']);root.mkdir(parents=True,exist_ok=True)
    if (root/'finished.json').exists():return
    for path,expected in cfg['code_sha256'].items():
        if digest(path)!=expected:raise ValueError(f'Frozen code/config changed: {path}')
    previous=sorted(root.glob('attempt-*'));cache=cfg.get('initial_detection_cache')
    for folder in reversed(previous):
        if all((folder/name).exists() for name in ['protocol.json','config.json','observations.jsonl']):
            # A truncated record must not be silently omitted or accepted.
            with (folder/'observations.jsonl').open() as stream:
                for line in stream:json.loads(line)
            cache=str(folder);break
    attempt_number=len(list(root.glob('launch-*.json')))
    output=root/f'attempt-{attempt_number:04d}'
    command=[*cfg['command'],'--output-dir',str(output)]
    if cache:command+=['--detection-cache',cache]
    manifest={'command':command,'job_config_sha256':digest(config_path),'detection_cache':cache,
              'recovery_policy':'Fresh public run, exact-contract detector replay; no restored tracker IDs or hidden geometry state'}
    (root/f'launch-{attempt_number:04d}.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'launch':command}),flush=True)
    code=subprocess.call(command,cwd=cfg['working_directory'])
    if code==0:(root/'finished.json').write_text(json.dumps({'output':str(output),'public_process_returncode':code,'quality_acceptance_verified':False},indent=2)+'\n')
    sys.exit(code)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--job-config',required=True);a=p.parse_args();main(a.job_config)
