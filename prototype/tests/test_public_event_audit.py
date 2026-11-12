import pytest
from prototype.public_event_audit import verify_scan


def events():
    return dict(status='development_complete_event_stage', source_fps=30,
                source_interval_s=[10, 10.3], sample_step_frames=3, sampled_frames=3)


def rows(frames):
    return [dict(frame_index=f, time_s=f/30) for f in frames]


def test_verifies_entire_requested_sampling_grid():
    assert verify_scan(events(), rows([300, 303, 306]))['complete_requested_scan']


@pytest.mark.parametrize('frames', [[300, 303], [300, 300, 306], [300, 306, 303], [300, 303, 306, 309]])
def test_rejects_truncated_duplicate_reordered_or_extra_rows(frames):
    with pytest.raises(ValueError):
        verify_scan(events(), rows(frames))


def test_final_status_and_timestamps_are_not_blindly_trusted():
    bad = events()
    bad['status'] = 'running'
    with pytest.raises(ValueError):
        verify_scan(bad, rows([300, 303, 306]))
    data = rows([300, 303, 306])
    data[-1]['time_s'] = 0
    with pytest.raises(ValueError):
        verify_scan(events(), data)


def test_precision_can_be_verified_without_exhaustive_recall_labels():
    from prototype.public_event_audit import verified_candidate_precision
    scored = {'prediction_count': 1, 'matches': [{'reference_id': 'r', 'prediction_id': 'p'}]}
    result = verified_candidate_precision(scored, [{'id':'r', 'physical_delivery_observed':True}])
    assert result['value'] == 1
    assert result['unclassified_candidates'] == 0


def test_unmatched_prediction_is_not_assumed_false_positive():
    from prototype.public_event_audit import verified_candidate_precision
    scored = {'prediction_count': 2, 'matches': [{'reference_id': 'r', 'prediction_id': 'p'}]}
    result = verified_candidate_precision(scored, [{'id':'r', 'physical_delivery_observed':True}])
    assert result['value'] is None
    assert result['unclassified_candidates'] == 1


def test_no_predictions_does_not_mean_perfect_precision():
    from prototype.public_event_audit import verified_candidate_precision
    assert verified_candidate_precision({'prediction_count':0, 'matches':[]}, [])['value'] is None


def test_prefix_ignores_later_append_but_never_claims_complete():
    from prototype.public_event_audit import audit_prefix
    protocol = {**events(), 'source_sha256': 'a', 'config_sha256': 'b'}
    progress = dict(samples=2, source_time_s=10.1, crossings=0, events_so_far=[])
    refs = dict(source_sha256='a', line_config_sha256='b', events=[])
    result = audit_prefix(protocol, progress, rows([300, 303, 306]), refs)
    assert result['verified_sampled_frames'] == 2
    assert result['complete_requested_scan'] is False
    assert result['evaluated_interval_s'] == [10, 10.1]
    with pytest.raises(ValueError, match='prefix'):
        audit_prefix(protocol, progress, rows([300]), refs)
    with pytest.raises(ValueError, match='Progress time'):
        audit_prefix(protocol, {**progress, 'source_time_s': 10.2}, rows([300, 303]), refs)
