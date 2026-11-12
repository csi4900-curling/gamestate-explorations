import json
from pathlib import Path
from prototype.spin.prepare_handle_dataset import prepare, git_blob


def test_pinned_inputs_reject_invalid_labels_and_keep_duplicates_together(tmp_path):
    metadata = tmp_path/'metadata'
    output = tmp_path/'dataset'
    metadata.mkdir()
    (metadata/'upstream.json').write_text(json.dumps({'repository':'https://github.com/example/data','commit':'fixed'}))
    trees = {'images':[], 'labels':[]}
    examples = [('image_1',b'same',True),('image_4001',b'same',True),
                ('image_2',b'other',True),('image_3',b'invalid',False)]
    for stem,image,valid in examples:
        label = b'0 0.1 0.2 0.5 0.2 0.5 0.4 0.1 0.4\n' if valid else b'0 -0.1 0.2 0.5 0.2 0.5 0.4 0.1 0.4\n'
        for kind,ext,data in [('images','jpg',image),('labels','txt',label)]:
            directory = output/'original'/kind
            directory.mkdir(parents=True,exist_ok=True)
            path = directory/f'{stem}.{ext}'
            path.write_bytes(data)
            trees[kind].append({'path':path.name,'sha':git_blob(data),'type':'blob'})
    for kind,tree in trees.items():
        (metadata/f'{kind}-tree.json').write_text(json.dumps({'tree':tree}))
    prepare(metadata,output,workers=1)
    split = json.loads((output/'split.json').read_text())['splits']
    assert split['train'] == ['image_2']
    assert set(split['val']) == {'image_1','image_4001'}
    assert not (output/'images/train/image_3.jpg').exists()
    assert (output/'original/labels/image_3.txt').read_bytes().startswith(b'0 -0.1')
    assert len(json.loads((output/'rejected-labels.json').read_text())['rejected']) == 1
    assert (output/'images/train/image_2.jpg').is_symlink()
