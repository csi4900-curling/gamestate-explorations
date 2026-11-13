import json
import pytest
from prototype.scripts import run_resumable_learned_match as runner


def config(tmp_path):
    root=tmp_path/'attempts';p=tmp_path/'job.json'
    p.write_text(json.dumps({'attempt_root':str(root),'working_directory':str(tmp_path),'command':['public-pipeline'],'code_sha256':{}}))
    return p,root


def test_failure_before_output_creation_keeps_distinct_launch_records(tmp_path,monkeypatch):
    p,root=config(tmp_path);calls=[]
    monkeypatch.setattr(runner.subprocess,'call',lambda command,**kw:calls.append(command) or 1)
    for _ in range(2):
        with pytest.raises(SystemExit) as exc:runner.main(p)
        assert exc.value.code==1
    assert (root/'launch-0000.json').exists() and (root/'launch-0001.json').exists()
    assert calls[0][-1]!=calls[1][-1]
    assert not (root/'finished.json').exists()


def test_recovery_replays_saved_detections_without_resuming_tracker_state(tmp_path,monkeypatch):
    p,root=config(tmp_path);old=root/'attempt-0000';old.mkdir(parents=True)
    for name in ['protocol.json','config.json']:(old/name).write_text('{}')
    (old/'observations.jsonl').write_text('{"frame_index":0}\n')
    (root/'launch-0000.json').write_text('{}');calls=[]
    monkeypatch.setattr(runner.subprocess,'call',lambda command,**kw:calls.append(command) or 0)
    with pytest.raises(SystemExit) as exc:runner.main(p)
    assert exc.value.code==0
    assert calls[0][-2:]==['--detection-cache',str(old)]
    assert json.loads((root/'finished.json').read_text())['quality_acceptance_verified'] is False
    runner.main(p)
    assert len(calls)==1
