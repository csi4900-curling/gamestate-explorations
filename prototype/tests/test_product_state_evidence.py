import json
from prototype.scripts.build_state_timeline import observed_end,role_at,build


def test_observed_end_never_uses_future_marker_or_negative_age():
    rows=[{'time_s':10,'current_end':2},{'time_s':20,'current_end':3}]
    assert observed_end(rows,9) is None
    assert observed_end(rows,19) is None  # The closer future marker is unavailable.
    assert observed_end(rows,12)['age_s']==2
    assert observed_end(rows,20)['current_end']==3
    assert observed_end([{'time_s':10,'current_end':2},{'time_s':11,'current_end':None}],12) is None


def test_role_timeline_does_not_backfill_before_first_evidence():
    timeline={'left':[(10,'departure'),(20,'receiving')]}
    assert role_at(timeline,'left',9) is None
    assert role_at(timeline,'left',10)=='departure'
    assert role_at(timeline,'left',20)=='receiving'


def test_partial_recording_event_count_cannot_identify_absolute_game_end(tmp_path):
    events=tmp_path/'events.json';boards=tmp_path/'boards.jsonl';scores=tmp_path/'scores.jsonl'
    events.write_text(json.dumps({'source_interval_s':[600,610],'events':[{'id':'candidate','crossing_time_s':605,'direction':'negative','crossing_point_normalized':[.25,.2]}]}))
    boards.write_text(''.join(json.dumps({'time_s':t,'boards':{'left':{'stones':[]},'right':{'stones':[]}}})+'\n' for t in [600,604,605,610]))
    scores.write_text('')
    result=build(events,boards,scores)
    assert all(r['current_end'] is None for r in result['samples'])
    assert all(r['current_end_status']=='unknown_absolute_end' for r in result['samples'])
    assert result['samples'][-1]['relative_end_hypothesis']['current_end']==1
    assert result['samples'][-1]['deliveries_before']==1
    assert result['summary']['unknown_absolute_end_samples']==4
