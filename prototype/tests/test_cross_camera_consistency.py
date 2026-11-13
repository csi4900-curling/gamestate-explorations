from prototype.cross_camera_consistency import annotate


def sample(t, point, kind='height_adjusted_estimate'):
    return {'time_s': t, 'rink_position_m': point, 'rink_position_kind': kind}


def test_agreement_uses_exact_times_and_matching_measurement_semantics():
    aggregate = {'summary': {}, 'events': [{
        'segments': [
            {'segment_id': 'a', 'geometry_samples': [sample(1, [0, 2]), sample(2, [0, 3]), sample(3, [0, 4])]},
            {'segment_id': 'b', 'geometry_samples': [sample(1, [0, 4]), sample(2.01, [0, 3]), sample(3, [0, 5], 'ice_plane_unadjusted')]},
        ], 'cross_view_links': [{'departure_segment': 'a', 'receiving_segment': 'b'}],
    }]}
    result = annotate(aggregate)
    agreement = result['events'][0]['camera_consistency']
    assert agreement['paired_samples'] == 1
    assert agreement['median_m'] == agreement['maximum_m'] == 2.
    assert result['summary']['camera_consistency']['absolute_accuracy_verified'] is False


def test_absent_overlap_is_unknown_not_perfect_agreement():
    aggregate = {'summary': {}, 'events': [{'segments': [], 'cross_view_links': []}]}
    result = annotate(aggregate)
    assert result['summary']['camera_consistency']['paired_samples'] == 0
    assert result['summary']['camera_consistency']['median_m'] is None
