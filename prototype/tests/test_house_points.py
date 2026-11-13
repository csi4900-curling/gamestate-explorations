import pytest
from prototype.house_points import points_lying


def score(stones):
    return points_lying(stones, house_radius_m=1.8, stone_radius_m=.15, groups=['red', 'yellow'])


def stone(i, x, group, **extra):
    return dict(observation_id=i, position_m=[x, 0], group=group, **extra)


def test_only_closer_stones_count_and_guards_do_not():
    r = score([stone('a', .2, 'red'), stone('b', .5, 'red'), stone('c', 1, 'yellow'), stone('d', 3, 'red')])
    assert r['conditional_points_by_group'] == {'red': 2, 'yellow': 0}
    assert r['official_end_score'] is None
    assert r['physical_board_verified'] is False


def test_touching_house_counts_using_stone_radius():
    r = score([stone('a', 1.9, 'red')])
    assert r['conditional_points_by_group']['red'] == 1
    assert r['observations'][0]['touches_house'] is True


def test_exact_tie_does_not_invent_a_winner_or_additional_point():
    assert score([stone('a', 1, 'red'), stone('b', 1, 'yellow')])['conditional_points_by_group'] == {'red': 0, 'yellow': 0}
    assert score([stone('a', .5, 'red'), stone('b', 1, 'red'), stone('c', 1, 'yellow')])['conditional_points_by_group'] == {'red': 1, 'yellow': 0}


def test_nearest_surface_not_just_centre_distance():
    r = score([stone('a', 1, 'red', radius_m=.14), stone('b', 1.005, 'yellow', radius_m=.15)])
    assert r['conditional_points_by_group'] == {'red': 0, 'yellow': 1}


def test_missing_geometry_or_group_is_not_a_zero_score():
    assert score([dict(observation_id='a', position_m=None, group='red')])['conditional_points_by_group'] is None
    assert score([stone('a', 1, None)])['conditional_points_by_group'] is None
    assert score([stone('a', 3, None)])['conditional_points_by_group'] == {'red': 0, 'yellow': 0}


def test_invalid_and_duplicate_inputs_rejected():
    with pytest.raises(ValueError):
        score([stone('a', 1, 'red'), stone('a', 2, 'red')])
    with pytest.raises(ValueError):
        score([stone('a', float('nan'), 'red')])
