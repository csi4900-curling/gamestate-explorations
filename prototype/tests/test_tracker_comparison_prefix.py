import pytest
from prototype.tracker_component_comparison import comparison_coverage, compare_assignments


def test_prefix_requires_opt_in_and_does_not_claim_full_scan():
    events = {'status': 'partial_development_snapshot_not_completed_match',
              'source_sha256': 'source', 'source_fps': 30,
              'source_interval_s': [0, .2], 'sample_step_frames': 3,
              'sampled_frames': 2, 'events': []}
    protocol = {'source_sha256': 'source', 'source_interval_s': [0, 100]}
    rows = [{'time_s': 0, 'frame_index': 0}, {'time_s': .1, 'frame_index': 3}]
    progress = {'samples': 2, 'source_time_s': .1, 'events_so_far': []}
    with pytest.raises(ValueError, match='opt-in'):
        comparison_coverage(events, protocol, rows)
    result = comparison_coverage(events, protocol, rows, allow_partial=True, progress=progress)
    assert result['complete_requested_scan'] is False
    assert result['complete_declared_prefix'] is True
    assert events['status'] == 'partial_development_snapshot_not_completed_match'
    with pytest.raises(ValueError, match='boundary'):
        comparison_coverage(events, protocol, rows, allow_partial=True,
                            progress={**progress, 'source_time_s': .2})
    with pytest.raises(ValueError, match='Missing'):
        comparison_coverage(events, protocol, [{**rows[0], 'frame_index': 1}, rows[1]],
                            allow_partial=True, progress=progress)


def test_comparison_preserves_missing_multiple_and_rejects_changed_inputs():
    row = {'frame_index': 3, 'time_s': .1, 'detections': [{'pixel': [4, 5]}],
           'tracked_observations': [{'track_id': 7, 'detection_index': 0}]}
    missing = {**row, 'tracked_observations': []}
    assert compare_assignments([row], [missing], [7])['summary']['7']['missing_candidate_observations'] == 1
    duplicate = {**row, 'tracked_observations': [{'track_id': i, 'detection_index': 0} for i in [8, 9]]}
    result = compare_assignments([row], [duplicate], [7])
    assert result['summary']['7']['multiple_candidate_observations'] == 1
    assert result['summary']['7']['unique_candidate_ids'] == [8, 9]
    with pytest.raises(ValueError, match='inputs differ'):
        compare_assignments([row], [{**row, 'detections': [{'pixel': [4, 6]}]}], [7])
    with pytest.raises(ValueError, match='lengths differ'):
        compare_assignments([row], [], [7])
