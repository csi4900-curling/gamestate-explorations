"""Conditional points lying from supplied stone geometry, not official end score.

World Curling July 2025 R12(b,d,f): touching house; nearest stone surface
to tee; strictly closer stones count. Dimensions are caller-supplied metres.
This calculation does not validate observations, completeness, identity or teams.
"""
import math


def points_lying(stones, *, house_radius_m, stone_radius_m, groups):
    if len(groups) != 2 or len(set(groups)) != 2:
        raise ValueError('Exactly two distinct groups required')
    if not all(math.isfinite(v) and v > 0 for v in [house_radius_m, stone_radius_m]):
        raise ValueError('Positive finite physical radii required')
    ids = [s['observation_id'] for s in stones]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate observation IDs; physical duplicates still require upstream resolution')
    rows = []
    unresolved = []
    distances = {g: [] for g in groups}
    for s in stones:
        p = s.get('position_m')
        row = {'observation_id': s['observation_id'], 'group': s.get('group'),
               'position_m': p, 'nearest_surface_distance_m': None, 'touches_house': None}
        if p is None:
            unresolved.append({'observation_id': s['observation_id'], 'reason': 'missing_geometry'})
        else:
            if len(p) != 2 or not all(math.isfinite(v) for v in p):
                raise ValueError('Finite two-dimensional positions required')
            radius = s.get('radius_m', stone_radius_m)
            if not math.isfinite(radius) or radius <= 0:
                raise ValueError('Positive finite stone radius required')
            distance = max(0., math.hypot(*p)-radius)
            inside = distance <= house_radius_m
            row.update(nearest_surface_distance_m=distance, touches_house=inside,
                       stone_radius_m=radius, house_boundary_margin_m=house_radius_m-distance)
            if inside:
                if s.get('group') not in distances:
                    unresolved.append({'observation_id': s['observation_id'], 'reason': 'unknown_group_in_house'})
                else:
                    distances[s['group']].append(distance)
        rows.append(row)
    points = None
    if not unresolved:
        points = {g: sum(d < min(distances[other], default=math.inf) for d in distances[g])
                  for g, other in [groups, groups[::-1]]}
    return {
        'conditional_points_by_group': points, 'observations': rows,
        'unresolved_observations': unresolved,
        'status': 'unresolved' if unresolved else 'conditional_on_supplied_observations',
        'house_radius_m': house_radius_m, 'default_stone_radius_m': stone_radius_m,
        'assumptions': ['Positions represent physical stone centres relative to the tee.',
                        'Every supplied item is one distinct in-play stone; no duplicates or stored stones.',
                        'No relevant stones are missing; group assignments and physical dimensions are correct.',
                        'Point estimates are used; geometric uncertainty has not been measured.'],
        'physical_board_verified': False, 'team_mapping_verified': False,
        'official_end_score': None,
        'rules': 'World Curling July 2025 R12(b,d,f), pages 18–19. Exact ties here use exact supplied distances, not an arbitrary tolerance.',
    }
