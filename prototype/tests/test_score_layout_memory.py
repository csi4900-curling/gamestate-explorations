from copy import deepcopy
from prototype.scoreboard_observation import parse_totals
from prototype.score_layout_memory import infer, chronological_layout_scores


def row(time, texts, positions):
    boxes = [[[x, y], [x+20, y], [x+20, y+20], [x, y+20]] for x, y in positions]
    return {'time_s': time, **parse_totals(texts, [.99]*len(texts), boxes, ['CAN', 'SWE'])}


def reference():
    return row(0, ['TOTAL', 'CAN', 'SWE', '0', '0'], [(100,0), (0,30), (0,60), (100,30), (100,60)])


def test_current_digit_with_missing_label_is_inferred_and_raw_unchanged():
    current = row(1, ['TOTAL','CAN','0','1'], [(110,10), (10,40), (110,40), (110,70)])
    before = deepcopy(current)
    result = list(infer([reference(), current], ['CAN','SWE']))[-1]
    assert current == before
    assert result['raw_totals']['SWE']['value'] is None
    assert result['layout_inferred_totals']['SWE']['value'] == 1
    assert result['layout_inferred_totals']['SWE']['status'] == 'layout_inferred_unverified'
    assert result['physical_current_end'] is None


def test_insufficient_anchors_and_ambiguous_digits_remain_unknown():
    current = row(1, ['TOTAL','1'], [(100,0), (100,60)])
    result = list(infer([reference(), current], ['CAN','SWE']))[-1]
    assert result['registration'] is None
    assert result['layout_inferred_totals']['SWE']['value'] is None
    ambiguous = row(2, ['TOTAL','CAN','1','2'], [(100,0), (0,30), (100,60), (100,60)])
    result = list(infer([reference(), ambiguous], ['CAN','SWE']))[-1]
    assert result['layout_inferred_totals']['SWE']['value'] is None
    assert len(result['layout_inferred_totals']['SWE']['candidates']) == 2


def test_inferred_rows_never_refresh_reference():
    first = row(1, ['TOTAL','CAN','0','1'], [(100,0), (0,30), (100,30), (100,60)])
    second = {**first, 'time_s': 2}
    result = list(infer([reference(), first, second], ['CAN','SWE']))[-1]
    assert result['registration']['reference_time_s'] == 0


def test_chronology_keeps_raw_and_layout_provenance_and_rejects_isolated_spike():
    rows = []
    for time, direct, inferred in [(0,6,None),(1,None,9),(2,None,6),(3,6,None)]:
        rows.append({'time_s':time,'raw_totals':{'A':{'value':direct}},
                     'layout_inferred_totals':{'A':{'value':inferred}}})
    original = deepcopy(rows)
    result = chronological_layout_scores(rows)
    assert rows == original
    assert result['sequence_inputs'][1]['totals']['A']['value'] == 9
    assert result['analyses']['A']['observations'][1]['status'] == 'conflicts_with_maximum_support_chronology'
    assert result['timeline'][1]['totals']['A']['value'] == 6
    assert result['timeline'][1]['totals']['A']['source_attribution'] == 'direct_ocr'
    assert result['timeline'][2]['totals']['A']['source_attribution'] == 'temporal_layout_inference'
    assert all(r['future_observations_used_for_sequence_selection'] for r in result['timeline'])
