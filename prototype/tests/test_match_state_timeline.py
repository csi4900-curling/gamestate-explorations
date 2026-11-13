import json
import pytest

from prototype.match_state_timeline import assemble, run


def score(t, a, b):
    return {'time_s': t, 'totals': {'A': {'value': a}, 'B': {'value': b}}, 'tokens': []}


def board(t):
    return {'time_s': t, 'boards': {'left': {'stones': [], 'end_identity': None},
                                   'right': {'stones': [], 'end_identity': None}}}


def test_optional_layout_is_not_reported_as_direct_or_current_when_stale():
    from prototype.tests.test_score_layout_memory import reference, row
    scores = [reference(), row(1, ['TOTAL','CAN','0','1'], [(100,0),(0,30),(100,30),(100,60)])]
    boards = [board(1), board(1.5)]
    default = list(assemble(boards, scores, ['CAN','SWE']))
    enriched = list(assemble(boards, scores, ['CAN','SWE'], score_layout_memory=True))
    assert default[0]['cumulative_match_score']['SWE']['offline_inferred']['value'] == 0
    value = enriched[0]['cumulative_match_score']['SWE']
    assert value['observed_at_this_time'] is None
    assert value['last_reading']['value'] == 0
    assert value['layout_inferred_at_this_time']['value'] == 1
    assert value['offline_inferred']['source_attribution'] == 'temporal_layout_inference'
    assert enriched[1]['cumulative_match_score']['SWE']['layout_inferred_at_this_time'] is None
    assert enriched[1]['cumulative_match_score']['SWE']['offline_inferred']['age_s'] == .5
    assert enriched[0]['boards'] == default[0]['boards']


def test_no_future_observation_and_no_unknown_zero():
    rows = list(assemble([board(0), board(10), board(15)], [score(10, 0, 1)], ['A', 'B']))
    assert rows[0]['cumulative_match_score']['A']['last_reading'] is None
    assert rows[0]['cumulative_match_score']['A']['offline_inferred'] is None
    assert rows[1]['cumulative_match_score']['A']['observed_at_this_time'] == 0
    later = rows[2]['cumulative_match_score']['A']
    assert later['observed_at_this_time'] is None
    assert later['last_reading']['age_s'] == 5
    assert later['offline_inferred']['age_s'] == 5
    assert later['offline_inferred']['future_observations_used'] is True
    assert rows[2]['current_points_in_house'] is None
    assert rows[2]['current_end'] is None
    assert rows[2]['boards'] == board(15)['boards']


def test_contradictory_ocr_is_retained_separately_from_inference():
    scores = [score(0, 0, 0), score(10, 4, 0), score(20, 1, 0), score(30, 1, 0)]
    row = list(assemble([board(10)], scores, ['A', 'B']))[0]
    assert row['cumulative_match_score']['A']['observed_at_this_time'] == 4
    assert row['cumulative_match_score']['A']['last_reading']['value'] == 4
    assert row['cumulative_match_score']['A']['offline_inferred']['value'] == 0
    assert row['complete_match_state_verified'] is False


def test_unreadable_latest_does_not_erase_last_reading_or_reset_age():
    row = list(assemble([board(20)], [score(0, 2, 3), score(10, None, None)], ['A', 'B']))[0]
    assert row['latest_score_observation_age_s'] == 10
    assert row['cumulative_match_score']['A']['last_reading']['age_s'] == 20
    assert row['cumulative_match_score']['A']['last_reading']['value'] == 2


def test_rejects_out_of_order_streams():
    with pytest.raises(ValueError, match='chronological'):
        list(assemble([board(10), board(5)], [score(0, 0, 0)], ['A', 'B']))
    with pytest.raises(ValueError, match='chronological'):
        list(assemble([board(10)], [score(5, 0, 0), score(0, 0, 0)], ['A', 'B']))


def test_prior_end_marker_is_evidence_not_current_end():
    row = score(10, 0, 1)
    row['tokens'] = [dict(text=s, normalized=s, bounds=b) for s, b in [
        ('END', [0, 0, 10, 10]), ('1', [20, 0, 30, 10]),
        ('2', [40, 0, 50, 10]), ('A', [0, 20, 10, 30]),
        ('0>', [15, 20, 55, 30])]]
    observed, later = list(assemble([board(10), board(11)], [row], ['A', 'B']))
    assert observed['current_end'] is None
    assert observed['displayed_end_evidence']['value'] == 2
    assert observed['displayed_end_evidence']['age_s'] == 0
    assert observed['displayed_end_evidence']['observed_at_this_time'] is True
    assert later['displayed_end_evidence']['value'] == 2
    assert later['displayed_end_evidence']['age_s'] == 1
    assert later['displayed_end_evidence']['observed_at_this_time'] is False
    assert later['current_end'] is None
    assert later['latest_scoreboard_parse']['current_end'] == 2
    assert later['latest_score_observation_age_s'] == 1


def test_other_score_stream_is_not_discarded_or_silently_overwritten():
    source = board(20)
    source['last_observed_totals'] = {'A': {'value': 3, 'observed_at_s': 19}}
    row = list(assemble([source], [score(10, 2, 1)], ['A', 'B']))[0]
    assert row['public_run_score_evidence']['last_observed_totals'] == source['last_observed_totals']
    assert row['cumulative_match_score']['A']['last_reading']['value'] == 2


def test_colour_evidence_is_past_only_and_conflicts_not_overwritten():
    colours = [dict(team='A', time_s=t, predicted_background_colour=c)
               for t, c in [(10, 'red'), (20, 'yellow'), (30, 'red')]]
    rows = list(assemble([board(t) for t in [0, 15, 25, 35]],
                         [score(0, 0, 0)], ['A', 'B'], colours))
    evidence = [r['scoreboard_team_colour_evidence']['A'] for r in rows]
    assert evidence[0]['status'] == 'unknown'
    assert evidence[1]['background_colour_hypothesis'] == 'red'
    assert evidence[1]['last_observation']['age_s'] == 5
    for e in evidence[2:]:
        assert e['status'] == 'conflicting_observations'
        assert e['background_colour_hypothesis'] is None
        assert e['observed_colours'] == ['red', 'yellow']
    assert all(e['stone_team_mapping_verified'] is False for e in evidence)
    assert all(r['boards'] == board(0)['boards'] for r in rows)


def test_rejects_out_of_order_colour_evidence():
    with pytest.raises(ValueError, match='chronological'):
        list(assemble([board(20)], [score(0, 0, 0)], ['A', 'B'],
                      [dict(team='A', time_s=t, predicted_background_colour='red')
                       for t in [20, 10]]))


def test_colour_source_mismatch_rejected_before_output_creation(tmp_path):
    public = tmp_path/'public'
    public.mkdir()
    (public/'events.json').write_text(json.dumps({'source_sha256': 'match-a'}))
    (tmp_path/'protocol.json').write_text(json.dumps({'source_sha256': 'match-a'}))
    colour = tmp_path/'colour.json'
    colour.write_text(json.dumps({'source_sha256': 'match-b', 'observations': []}))
    output = tmp_path/'output'
    with pytest.raises(ValueError, match='Colour and board source hashes differ'):
        run(public, tmp_path/'scores.jsonl', output, ['A', 'B'], colour)
    assert not output.exists()
