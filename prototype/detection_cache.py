"""Strict reuse of immutable detector observations; tracking is replayed normally."""
import hashlib
import json
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def verify_committed_prefix(folder):
    """Verify the atomic progress boundary, excluding any uncommitted tail."""
    folder=Path(folder)
    protocol=json.loads((folder/'protocol.json').read_text())
    progress=json.loads((folder/'progress.json').read_text())
    count=progress['samples'];fps=protocol['source_fps']
    if not isinstance(count,int) or count<=0 or fps<=0:
        raise ValueError('Invalid committed detector prefix')
    first=round(protocol['source_interval_s'][0]*fps);step=protocol['sample_step_frames']
    if not isinstance(step,int) or step<=0:raise ValueError('Invalid sampling grid')
    with (folder/'observations.jsonl').open() as stream:
        for i in range(count):
            line=stream.readline()
            if not line:raise ValueError('Incomplete committed detector prefix')
            row=json.loads(line);expected=first+i*step
            if row['frame_index']!=expected or abs(row['time_s']-expected/fps)>1e-9:
                raise ValueError('Invalid committed detector sampling grid')
            if not isinstance(row['detections'],list):raise ValueError('Invalid saved detections')
    if abs(row['time_s']-progress['source_time_s'])>1e-9:
        raise ValueError('Committed detector prefix differs from progress time')
    if row['time_s']>=protocol['source_interval_s'][1]:
        raise ValueError('Committed detector prefix exceeds requested interval')
    return {'verified_sampled_frames':count,'first_frame_index':first,
            'last_frame_index':row['frame_index'],'last_source_time_s':row['time_s'],
            'complete_requested_scan':False,'scope':'Atomic committed prefix only; ignore uncommitted tail and detect remaining frames afresh.'}


class DetectionCache:
    def __init__(self,folder,*,source_sha256,model,confidence,decoder_sha256,prefix_samples=None):
        folder=Path(folder);self.path=folder/'observations.jsonl'
        protocol=json.loads((folder/'protocol.json').read_text());config=json.loads((folder/'config.json').read_text())
        canonical=lambda x:json.dumps(x,sort_keys=True)
        if protocol['source_sha256']!=source_sha256:raise ValueError('Detection cache source mismatch')
        if canonical(protocol['model'])!=canonical(model):raise ValueError('Detection cache model/runtime mismatch')
        if config['detector_confidence']!=confidence:raise ValueError('Detection cache confidence mismatch')
        if protocol.get('opencv_build_sha256')!=decoder_sha256:raise ValueError('Detection cache decoder mismatch')
        if protocol['code_sha256']['stone_detector.py']!=digest(Path(__file__).with_name('stone_detector.py')):
            raise ValueError('Detection cache adapter changed')
        self.provenance={'path':str(folder.resolve()),'observations_sha256':digest(self.path),'protocol_sha256':digest(folder/'protocol.json'),
                         'policy':'Exact source/model/runtime/decoder/adapter/confidence match. Replay tracker state from detections; never reuse track IDs as physical identity.'}
        self.limit=prefix_samples;self.read_count=0
        if prefix_samples is not None:
            verified=verify_committed_prefix(folder)
            if verified['verified_sampled_frames']!=prefix_samples:raise ValueError('Committed detector prefix changed')
            self.provenance['committed_prefix']=verified
        self.stream=self.path.open();self.pending=None;self.last_read=-1;self.last_requested=-1;self.reused=0;self.prior_detector_seconds=0.
        self._advance()

    def _advance(self):
        if self.limit is not None and self.read_count>=self.limit:self.pending=None;return
        line=self.stream.readline()
        if not line:self.pending=None;return
        row=json.loads(line)
        if not isinstance(row['frame_index'],int) or row['frame_index']<=self.last_read:
            raise ValueError('Detection cache must have strictly increasing source frames')
        self.last_read=row['frame_index'];self.pending=row;self.read_count+=1

    def get(self,frame_index):
        if frame_index<=self.last_requested:raise ValueError('Detection cache requests must advance')
        self.last_requested=frame_index
        while self.pending is not None and self.pending['frame_index']<frame_index:self._advance()
        if self.pending is None or self.pending['frame_index']!=frame_index:return None
        row=self.pending;self.reused+=1
        original_seconds=row.get('detector_wall_seconds',0.)+(row.get('prior_detector_wall_seconds') or 0.)
        self.prior_detector_seconds+=original_seconds
        self._advance()
        return {'detections':row['detections'],'wall_seconds':0.,'upstream_speed_ms':row.get('upstream_speed_ms'),
                'reused_from_cache':True,'prior_detector_wall_seconds':original_seconds}

    def close(self):
        self.stream.close()
        if digest(self.path)!=self.provenance['observations_sha256']:raise ValueError('Detection cache changed during run')
