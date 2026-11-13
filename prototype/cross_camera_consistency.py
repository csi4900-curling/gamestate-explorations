"""Conditional same-timestamp camera agreement, never absolute trajectory accuracy."""
import math
import statistics


def annotate(aggregate):
    all_distances = []
    paired_links = 0
    for event in aggregate['events']:
        by_id = {s['segment_id']: s for s in event['segments']}
        links = []
        for link in event.get('cross_view_links', []):
            departure = by_id[link['departure_segment']]
            receiving = by_id[link['receiving_segment']]
            a = {p['time_s']: p for p in departure.get('geometry_samples', [])
                 if p.get('rink_position_m') is not None}
            b = {p['time_s']: p for p in receiving.get('geometry_samples', [])
                 if p.get('rink_position_m') is not None}
            pairs = []
            for t in sorted(a.keys() & b.keys()):
                # A raw ice-plane projection and a height-corrected estimate are
                # different measurement semantics; do not silently compare them.
                if a[t].get('rink_position_kind') != b[t].get('rink_position_kind'):
                    continue
                x, y = a[t]['rink_position_m'], b[t]['rink_position_m']
                if not all(math.isfinite(v) for v in [*x, *y]):
                    continue
                pairs.append({'time_s': t, 'departure_rink_m': x, 'receiving_rink_m': y,
                              'distance_m': math.dist(x, y)})
            distances = [p['distance_m'] for p in pairs]
            all_distances.extend(distances)
            paired_links += bool(pairs)
            links.append({'departure_segment': departure['segment_id'],
                          'receiving_segment': receiving['segment_id'],
                          'paired_samples': len(pairs),
                          'median_m': statistics.median(distances) if distances else None,
                          'maximum_m': max(distances) if distances else None,
                          'samples': pairs,
                          'status': 'conditional_camera_disagreement' if pairs else 'no_comparable_overlap',
                          'physical_identity_verified': False})
        distances = [p['distance_m'] for link in links for p in link['samples']]
        event['camera_consistency'] = {
            'paired_samples': len(distances),
            'median_m': statistics.median(distances) if distances else None,
            'maximum_m': max(distances) if distances else None,
            'links': links,
            'scope': 'Matching composite-source timestamps and comparable coordinate semantics; conditional on provisional stone association. Not absolute error or measured feed synchronization.',
        }
    aggregate['summary']['camera_consistency'] = {
        'paired_samples': len(all_distances), 'links_with_overlap': paired_links,
        'median_m': statistics.median(all_distances) if all_distances else None,
        'maximum_m': max(all_distances) if all_distances else None,
        'absolute_accuracy_verified': False, 'camera_feed_synchronization_verified': False,
    }
    return aggregate
