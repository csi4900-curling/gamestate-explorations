"""Acquire a pinned upstream handle OBB dataset with Git blob verification.

The internal validation partition is not a recording-disjoint accuracy claim:
upstream filenames do not provide source-video group IDs. Exact duplicates are
kept in one partition. A separate recording is required for transfer evaluation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
import threading
import requests


def git_blob(data):
    return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()


def prepare(metadata, output, workers=4):
    metadata, output = Path(metadata), Path(output)
    upstream = json.loads((metadata/'upstream.json').read_text())
    commit = upstream['commit']
    repository = upstream['repository'].removeprefix('https://github.com/')
    directory = 'curling_dataset/curling_obb_dataset'
    trees = {kind:json.loads((metadata/f'{kind}-tree.json').read_text())['tree']
             for kind in ['images','labels']}
    output.mkdir(exist_ok=True)
    for kind in trees:
        (output/'original'/kind).mkdir(parents=True,exist_ok=True)
    started = time.perf_counter()
    sessions = threading.local()
    def fetch(kind, entry):
        name = entry['path']
        if Path(name).name != name:
            raise ValueError('Expected flat upstream file list')
        path = output/'original'/kind/name
        data = path.read_bytes() if path.exists() else None
        if data is not None and git_blob(data) != entry['sha']:
            raise ValueError(f'Existing input changed: {path}')
        if data is None:
            url = f'https://raw.githubusercontent.com/{repository}/{commit}/{directory}/{kind}/{name}'
            for attempt in range(3):
                try:
                    if not hasattr(sessions,'http'):
                        sessions.http = requests.Session()
                    response = sessions.http.get(url,timeout=30)
                    response.raise_for_status()
                    data = response.content
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(attempt+1)
            if git_blob(data) != entry['sha']:
                raise ValueError(f'Git hash mismatch: {name}')
            tmp = path.with_suffix(path.suffix+'.partial')
            tmp.write_bytes(data)
            tmp.replace(path)
        return {'path':str(path),'git_blob_sha1':entry['sha'],
                'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    verified, failures = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch,kind,e):(kind,e['path'])
                   for kind,tree in trees.items() for e in tree if e['type']=='blob'}
        for i,future in enumerate(as_completed(futures),1):
            try:
                verified.append(future.result())
            except Exception as exc:
                failures.append({'input':futures[future],'error':str(exc)})
            if i % 500 == 0:
                print(f'{i}/{len(futures)} files verified; failures={len(failures)}',flush=True)
    manifest = {'repository':upstream['repository'],'commit':commit,
                'files':sorted(verified,key=lambda r:r['path']),'failures':failures,
                'wall_s':time.perf_counter()-started,'preparation_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output/'download-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if failures:
        raise ValueError('Incomplete download; verified prefix retained for resume')
    images = {Path(r['path']).stem:r for r in verified if '/images/' in r['path']}
    labels = {Path(r['path']).stem:r for r in verified if '/labels/' in r['path']}
    if images.keys() != labels.keys():
        raise ValueError('Image/label pairs differ')
    duplicate_groups, rejected = {}, []
    for stem,row in images.items():
        valid = True
        for line in Path(labels[stem]['path']).read_text().splitlines():
            values = line.split()
            if len(values) != 9 or values[0] not in ('0','1') or not all(0<=float(x)<=1 for x in values[1:]):
                rejected.append({'image':stem,'reason':'Malformed or out-of-image normalized OBB coordinates','original_label':line})
                valid = False
        if valid:
            duplicate_groups.setdefault(row['sha256'],[]).append(stem)
    (output/'rejected-labels.json').write_text(json.dumps({'policy':'Exclude image/label pair when OBB coordinates are invalid; no clipping, relabeling or negative-image conversion. Originals preserved.','rejected':rejected},indent=2)+'\n')
    split = {'train':[],'val':[]}
    for group in duplicate_groups.values():
        # Numeric block split fixed before training; duplicates cannot straddle.
        partition = 'val' if any(int(x.rsplit('_',1)[1])>4000 for x in group) else 'train'
        for stem in sorted(group):
            split[partition].append(stem)
    for partition,stems in split.items():
        for kind in ['images','labels']:
            target = output/kind/partition
            target.mkdir(parents=True,exist_ok=True)
            lookup = images if kind=='images' else labels
            for stem in stems:
                source = Path(lookup[stem]['path']).resolve()
                link = target/source.name
                if not link.exists():
                    link.symlink_to(source)
    (output/'data.yaml').write_text(f'path: {output.resolve()}\ntrain: images/train\nval: images/val\nnames:\n  0: red_handle\n  1: yellow_handle\n')
    (output/'split.json').write_text(json.dumps({'policy':'Numeric blocks1-4000train,4001-5000val; exact duplicate groups moved together toval','source_video_groups_available':False,'independent_recording_validation':False,'splits':split,'unique_image_sha256':len(duplicate_groups)},indent=2)+'\n')
    print(json.dumps({'train':len(split['train']),'val':len(split['val']),'rejected':len(rejected),'unique_images':len(duplicate_groups),'wall_s':time.perf_counter()-started}),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--workers',type=int,default=4)
    args = parser.parse_args()
    prepare(args.metadata,args.output,args.workers)
