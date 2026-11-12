"""Development-only temporal scoreboard layout inference from observed OCR.

Raw observations stay unchanged. OpenCV fits a planar mapping between matching
TOTAL/team token boxes; previous observed row/column extents define score cells.
This is a programmed layout assumption, not learned team recognition or a
validated camera registration. No score is inferred from throw counts.
"""
import argparse
import hashlib
import json
from pathlib import Path


def unique(tokens, name):
    matches = [t for t in tokens if t['normalized'] == name.upper()]
    return matches[0] if len(matches) == 1 else None


def infer(rows, teams):
    import cv2
    import numpy as np
    reference = None
    previous_time = None
    for row in rows:
        if previous_time is not None and row['time_s'] <= previous_time:
            raise ValueError('Chronological OCR observations required')
        previous_time = row['time_s']
        tokens = row['tokens']
        anchors = {name: unique(tokens, name) for name in ['TOTAL', *teams]}
        result = {'time_s': row['time_s'], 'raw_totals': row['totals'],
                  'layout_inferred_totals': {team: {'value': None, 'status': 'unavailable'} for team in teams},
                  'physical_current_end': None, 'registration': None}
        if reference is not None:
            common = [name for name, token in anchors.items() if token is not None]
            if len(common) >= 2:
                source = np.asarray([point for name in common for point in reference['anchors'][name]['box']], dtype=float)
                target = np.asarray([point for name in common for point in anchors[name]['box']], dtype=float)
                matrix, _ = cv2.findHomography(source, target, method=0)
                if matrix is not None and np.isfinite(matrix).all():
                    mapped = cv2.perspectiveTransform(source.reshape(-1, 1, 2), matrix).reshape(-1, 2)
                    result['registration'] = {'method': 'OpenCV findHomography least squares on unique matching OCR token corners',
                        'reference_time_s': reference['time_s'], 'reference_age_s': row['time_s']-reference['time_s'],
                        'anchor_names': common, 'homography': matrix.tolist(),
                        'anchor_rmse_px': float(np.sqrt(np.mean(np.sum((mapped-target)**2, axis=1)))),
                        'accuracy_validated': False, 'quality_threshold_applied': False}
                    for team in teams:
                        polygon = cv2.perspectiveTransform(np.asarray(reference['cells'][team], dtype=float).reshape(-1, 1, 2), matrix).astype(np.float32)
                        if not np.isfinite(polygon).all() or not cv2.isContourConvex(polygon):
                            continue
                        candidates = []
                        for token in tokens:
                            # Preserve the baseline parser's numeric-token semantics.
                            if not token['normalized'].isdigit():
                                continue
                            x0, y0, x1, y1 = token['bounds']
                            if cv2.pointPolygonTest(polygon, ((x0+x1)/2, (y0+y1)/2), False) >= 0:
                                candidates.append({'value': int(token['normalized']), 'evidence': token})
                        result['layout_inferred_totals'][team] = {
                            'value': candidates[0]['value'] if len(candidates) == 1 else None,
                            'status': 'layout_inferred_unverified' if len(candidates) == 1 else 'unreadable_or_ambiguous',
                            'projected_cell': polygon.reshape(-1, 2).tolist(), 'candidates': candidates}
        # Refresh only after a frame with both directly observed totals and all
        # unique anchors; no inferred output feeds back as calibration evidence.
        if all(anchors.values()) and all(row['totals'][t]['value'] is not None for t in teams):
            hx0, _, hx1, _ = anchors['TOTAL']['bounds']
            cells = {}
            for team in teams:
                _, y0, _, y1 = anchors[team]['bounds']
                cells[team] = [[hx0, y0], [hx1, y0], [hx1, y1], [hx0, y1]]
            reference = {'time_s': row['time_s'], 'anchors': anchors, 'cells': cells}
        yield result


def chronological_layout_scores(layout_rows):
    """Compose existing chronology with explicit direct/layout input provenance."""
    from prototype.score_sequence import infer as chronological_infer
    evidence = []
    for row in layout_rows:
        totals = {}
        for team, direct in row['raw_totals'].items():
            inferred = row['layout_inferred_totals'][team]
            use_direct = direct['value'] is not None
            selected = direct if use_direct else inferred
            totals[team] = {'value': selected['value'],
                            'attribution': 'direct_ocr' if use_direct else 'temporal_layout_inference',
                            'evidence': selected}
            if selected['value'] is None:
                totals[team]['attribution'] = 'unknown'
        evidence.append({'time_s': row['time_s'], 'totals': totals})
    result = chronological_infer(evidence)
    result['sequence_input_semantics'] = 'Direct OCR takes precedence; otherwise use explicitly unverified layout-attributed current digits. Raw and layout observations are preserved separately.'
    result['sequence_inputs'] = evidence
    for row in result['timeline']:
        for team, value in row['totals'].items():
            if value['value'] is not None:
                origin = evidence[value['source_observation_index']]['totals'][team]
                value['source_attribution'] = origin['attribution']
                value['provenance'] = 'offline_chronological_inference_from_direct_and_layout_OCR'
    return result


def run(source, output, teams, *, chronological=False):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError('Preserve prior layout experiment')
    output.mkdir(parents=True)
    code = Path(__file__).read_bytes()
    (output/'score_layout_memory.py').write_bytes(code)
    with source.open() as stream:
        rows = [json.loads(line) for line in stream]
    results = list(infer(rows, teams))
    (output/'observations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results))
    if chronological:
        from prototype import score_sequence
        result = chronological_layout_scores(results)
        result['chronology_code_sha256'] = hashlib.sha256(Path(score_sequence.__file__).read_bytes()).hexdigest()
        (output/'score_sequence.py').write_bytes(Path(score_sequence.__file__).read_bytes())
        (output/'chronological-layout.json').write_text(json.dumps(result, indent=2)+'\n')
    summary = {'development': True, 'default_enabled': False, 'raw_observations_modified': False,
               'samples': len(rows), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'code_sha256': hashlib.sha256(code).hexdigest(), 'teams': teams,
               'additional_non_null_fields': sum(r['raw_totals'][t]['value'] is None and r['layout_inferred_totals'][t]['value'] is not None for r in results for t in teams),
               'conflicts_with_direct_observations': [
                   {'time_s': r['time_s'], 'team': t, 'direct': r['raw_totals'][t]['value'], 'inferred': r['layout_inferred_totals'][t]['value']}
                   for r in results for t in teams if r['raw_totals'][t]['value'] is not None and r['layout_inferred_totals'][t]['value'] is not None and r['raw_totals'][t]['value'] != r['layout_inferred_totals'][t]['value']],
               'physical_score_accuracy': None,
               'limitations': ['Two or more token boxes are only a layout hypothesis; OCR box changes and camera/layout changes can produce wrong mappings.',
                              'No calibrated confidence, scene-cut detection, replay detection or physical end assignment.',
                              'Additional outputs are inferred associations of current numeric tokens, not directly observed team-score pairs.']}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--teams', nargs=2, required=True)
    parser.add_argument('--chronological', action='store_true', help='Also apply existing offline chronological inference, preserving source attribution')
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output, args.teams, chronological=args.chronological), indent=2))
