from prototype.detected_throw_score import DeliveryEndContext, build_match_ledger
from prototype.scripts.build_state_timeline import infer_end


def events():
    return [{'candidate_id': str(i), 'event_prediction': {'crossing_time_s': float(i)}}
            for i in range(1, 6)]


def proposals(missing=None):
    rows = []
    for i in range(1, 6):
        score = {'A': i % 2, 'B': (i + 1) % 2}
        state = {'end_context': {'current_end': (i - 1) // 2 + 1},
                 'boards': {'right': {'detected_throw_score': {
                     'estimated_points': score, 'status': 'conditional_on_current_associations',
                     'stale_event_ids': []}}}}
        rows.append({'event_id': str(i), 'proposal': {'panel': 'right', 'time_s': i + .5},
                     'state': None if i == missing else state})
    return rows


def test_last_throw_remains_in_its_end_until_next_end_first_crossing():
    context = DeliveryEndContext(events(), end_size=2, start_s=0)
    for time in (2, 2.1, 2.99):
        assert context.at(time)['current_end'] == 1
        assert infer_end([1, 2, 3, 4, 5], time, end_size=2)['current_end'] == 1
    assert context.at(3)['current_end'] == 2
    assert context.at(3)['epoch_start_s'] == 3
    assert context.at(4.9)['current_end'] == 2
    assert context.at(5)['current_end'] == 3


def test_points_awarded_once_per_end_not_per_throw_and_never_early():
    result = build_match_ledger(events(), proposals(), end_size=2, teams=['A', 'B'], start_s=0)
    assert result['timeline'] == [
        {'time_s': 0, 'known_subtotal': {'A': 0, 'B': 0}, 'estimated_total': {'A': 0, 'B': 0},
         'unresolved_end_numbers': [], 'completed_end_numbers': []},
        {'time_s': 3., 'known_subtotal': {'A': 0, 'B': 1}, 'estimated_total': {'A': 0, 'B': 1},
         'unresolved_end_numbers': [], 'completed_end_numbers': [1]},
        {'time_s': 5., 'known_subtotal': {'A': 0, 'B': 2}, 'estimated_total': {'A': 0, 'B': 2},
         'unresolved_end_numbers': [], 'completed_end_numbers': [1, 2]},
    ]
    assert result['ends'][-1]['status'] == 'open_end_not_awarded'
    assert result['ends'][-1]['estimated_end_points'] == {'A': 1, 'B': 0}


def test_missing_final_result_does_not_use_earlier_throw_or_zero():
    result = build_match_ledger(events(), proposals(missing=2), end_size=2, teams=['A', 'B'], start_s=0)
    assert result['ends'][0]['status'] == 'unresolved_end'
    assert result['ends'][0]['estimated_end_points'] is None
    assert result['timeline'][-1]['known_subtotal'] == {'A': 0, 'B': 1}
    assert result['timeline'][-1]['estimated_total'] is None
    assert result['timeline'][-1]['unresolved_end_numbers'] == [1]
