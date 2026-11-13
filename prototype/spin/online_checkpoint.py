"""Persist the unmodified pinned CoTracker3 online predictor's temporal state.

No tracking decisions are made here. Callers must supply an exact input/runtime
contract and save only after a successful upstream window computation.
"""
import hashlib
import json
import os
from pathlib import Path


ONLINE_FIELDS = ('online_ind', 'online_track_feat', 'online_track_support',
                 'online_coords_predicted', 'online_vis_predicted', 'online_conf_predicted')


def contract_key(contract):
    return hashlib.sha256(json.dumps(contract, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _move(value, device):
    import torch
    if isinstance(value, torch.Tensor):
        return value.detach().to(device).clone()
    if isinstance(value, list):
        return [_move(x, device) for x in value]
    if isinstance(value, dict):
        return {k: _move(v, device) for k, v in value.items()}
    if value is None or isinstance(value, (int, float, bool, str)):
        return value
    raise TypeError(f'Unsupported checkpoint state type: {type(value)}')


def save(path, predictor, contract, next_offset, tracks, visible):
    import torch
    path = Path(path)
    if next_offset != predictor.model.online_ind:
        raise ValueError('Window cursor differs from upstream online state')
    state = {name: _move(getattr(predictor.model, name), 'cpu') for name in ONLINE_FIELDS}
    # Library version strings may be str subclasses (TorchVersion). Store only
    # JSON primitives so weights_only loading never needs custom pickle globals.
    plain_contract = json.loads(json.dumps(contract, sort_keys=True, allow_nan=False))
    payload = dict(schema='cotracker3-online-progress-v1', contract=plain_contract,
                   contract_sha256=contract_key(contract), next_offset=next_offset,
                   predictor=dict(N=predictor.N, queries=_move(predictor.queries, 'cpu')),
                   online_state=state, tracks=_move(tracks, 'cpu'), visible=_move(visible, 'cpu'))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('wb') as stream:
        torch.save(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    # Persist the rename as well as the checkpoint contents across host restarts.
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def restore(path, predictor, contract, device):
    import torch
    payload = torch.load(path, map_location='cpu', weights_only=True)
    if payload.get('schema') != 'cotracker3-online-progress-v1':
        raise ValueError('Unknown online checkpoint schema')
    plain_contract = json.loads(json.dumps(contract, sort_keys=True, allow_nan=False))
    if payload['contract_sha256'] != contract_key(contract) or payload['contract'] != plain_contract:
        raise ValueError('Online checkpoint input/runtime contract differs')
    state = payload['online_state']
    if set(state) != set(ONLINE_FIELDS):
        raise ValueError('Incomplete upstream online state')
    if payload['next_offset'] != state['online_ind'] or payload['next_offset'] % predictor.step:
        raise ValueError('Invalid online window cursor')
    for name, value in state.items():
        setattr(predictor.model, name, _move(value, device))
    predictor.N = payload['predictor']['N']
    predictor.queries = _move(payload['predictor']['queries'], device)
    return payload['next_offset'], _move(payload['tracks'], device), _move(payload['visible'], device)
