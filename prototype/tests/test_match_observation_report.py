import json
import pytest
from prototype.match_observation_report import render


def fixture(tmp_path, source='same'):
    events=[{'id':'a','crossing_time_s':1.}]
    (tmp_path/'events.json').write_text(json.dumps({'events':events,'source_sha256':'same','source_interval_s':[0,2], 'status':'partial_development_snapshot_not_completed_match'}))
    (tmp_path/'match-observations.jsonl').write_text(json.dumps({'time_s':1.,'boards':{},'last_observed_totals':{}})+'\n')
    (tmp_path/'aggregate.json').write_text(json.dumps({'context':{'source_sha256':source},'events':[{'candidate_id':'a','segments':[{'camera':'left_split','tracker_id':2},{'camera':'right_split','tracker_id':7},{'camera':'right_split','tracker_id':9}], 'handoff_hypothesis':{'status':'ambiguous'}}]}))
    return events


def test_event_groups_preserve_multiple_candidates_and_partial_boundary(tmp_path):
    render(tmp_path,tmp_path/'video.mp4',fixture(tmp_path))
    m=json.loads((tmp_path/'match-view-data/manifest.json').read_text())
    assert m['event_track_groups']['a']=={'left':[2],'right':[7,9],'status':'ambiguous','observed_interval_s':None}
    assert m['right_censored_event_id']=='a'


def test_other_video_aggregate_rejected(tmp_path):
    with pytest.raises(ValueError,match='source mismatch'):
        render(tmp_path,tmp_path/'video.mp4',fixture(tmp_path,'other'))


def test_optional_state_requires_exact_source_and_frames(tmp_path):
    events=fixture(tmp_path)
    state=tmp_path/'match-state';state.mkdir()
    (state/'manifest.json').write_text(json.dumps({'source_sha256':'different'}))
    row={'time_s':1.,'cumulative_match_score':{},'current_end':None,'current_points_in_house':None}
    (state/'timeline.jsonl').write_text(json.dumps(row)+'\n')
    with pytest.raises(ValueError,match='State/video'):
        render(tmp_path,tmp_path/'video.mp4',events)
    (state/'manifest.json').write_text(json.dumps({'source_sha256':'same'}))
    (state/'timeline.jsonl').write_text(json.dumps({**row,'time_s':2})+'\n')
    with pytest.raises(ValueError,match='source frames'):
        render(tmp_path,tmp_path/'video.mp4',events)
    (state/'timeline.jsonl').write_text(json.dumps(row)+'\n')
    render(tmp_path,tmp_path/'video.mp4',events)
    assert '"state"' in (tmp_path/'match-view-data/0.js').read_text()
