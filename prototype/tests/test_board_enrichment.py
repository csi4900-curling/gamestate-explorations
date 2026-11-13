from copy import deepcopy
import json
import pytest
from prototype.board_enrichment import enrich_observation, select_snapshots, run


def test_snapshot_never_uses_future_or_previous_throw_observation():
    targets = [dict(start_s=5, end_s=9), dict(start_s=10, end_s=12), dict(start_s=20, end_s=21)]
    selected = select_snapshots([{'time_s': t} for t in [0, 8, 11, 13]], targets)
    assert [r['time_s'] if r else None for _, r in selected] == [8, 11, None]


def test_exact_endpoint_and_duplicate_target_times_are_retained():
    t = dict(start_s=0, end_s=10)
    assert [r['time_s'] for _, r in select_snapshots([{'time_s': 10}], [t, t])] == [10, 10]
    with pytest.raises(ValueError):
        select_snapshots([{'time_s': 10}, {'time_s': 9}], [t])


def test_enrichment_preserves_original_evidence_and_does_not_claim_team_or_score():
    class Ranker:
        def rank(self, image, box):
            return {'prediction': 'yellow', 'calibrated_confidence': False}
    row = dict(time_s=10, boards={'left': {'stones': [dict(bbox_xyxy=[1, 2, 3, 4],
               colour=None, team=None, physical_identity=None, height_adjusted_local_m=[0, 1])]},
               'right': {'stones': []}})
    original = deepcopy(row)
    out = enrich_observation(row, None, Ranker(), dict(house_radius_m=1.829, stone_radius_m=.142, groups=['red', 'yellow']))
    assert row == original
    assert out['boards']['left']['stones'][0]['colour'] is None
    assert out['boards']['left']['conditional_house_points']['conditional_points_by_group'] == {'red': 0, 'yellow': 1}
    assert out['current_points_from_stones'] is None
    assert out['team_mapping'] is None
    assert out['settled'] is None


def test_failed_receiving_produces_explicit_report_without_loading_model(tmp_path, monkeypatch):
    source = tmp_path/'run'
    (source/'two-view-tracking').mkdir(parents=True)
    (source/'events.json').write_text(json.dumps({'source_sha256': 'source'}))
    (source/'two-view-tracking/result.json').write_text(json.dumps({'source_sha256': 'source', 'events': []}))
    (source/'two-view-tracking/end-views.json').write_text(json.dumps([
        dict(candidate_id='failed', status='unavailable', reason='No analyzed receiving frames')]))
    (source/'match-observations.jsonl').write_text('')
    config = tmp_path/'config.json'
    config.write_text('{}')
    def forbidden(*args, **kwargs):
        raise AssertionError('No colour model needed for missing observations')
    monkeypatch.setattr('prototype.board_enrichment.ColourRanker', forbidden)
    out = tmp_path/'output'
    result = run(source, config, out, tmp_path/'cache')
    assert result['inference_performed'] is False
    assert result['snapshots'][0]['reason'] == 'No analyzed receiving frames'
    assert 'No analyzed receiving frames' in (out/'index.html').read_text()
    assert not list(out.glob('source-*.png'))


def test_mixed_source_run_rejected_before_inference(tmp_path):
    source = tmp_path/'run'
    (source/'two-view-tracking').mkdir(parents=True)
    (source/'events.json').write_text(json.dumps({'source_sha256': 'A'}))
    (source/'two-view-tracking/result.json').write_text(json.dumps({'source_sha256': 'B'}))
    config = tmp_path/'config.json'
    config.write_text('{}')
    with pytest.raises(ValueError, match='hashes differ'):
        run(source, config, tmp_path/'out', tmp_path/'cache')
