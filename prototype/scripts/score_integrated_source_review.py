"""Score frozen aggregate outputs against exhaustive source-point adjudications."""
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'prototype'))
from cache_contract import file_sha256
from aggregate_evaluation import has_top_view


def score(folder):
    result = {}
    for name, reference_count in [('sweden22', 125), ('sweden24', 143)]:
        path = folder / name / 'aggregate.json'
        data = json.loads(path.read_text())
        review_paths = sorted((ROOT / 'validation/integrated-pipeline-v2' / name).glob('point-review-*/adjudication.json'))
        review_paths += sorted((folder / name).glob('*point-review/adjudication.json'))
        labels = {}
        for review_path in review_paths:
            review = json.loads(review_path.read_text())
            assert review['source_sha256'] == data['context']['source_sha256']
            for r in review['rows']:
                key = (r['candidate_id'], r['time_s'], tuple(r['pixel']))
                assert type(r['correct_stone_at_pixel']) is bool
                if key in labels:
                    assert labels[key] == r['correct_stone_at_pixel'], key
                labels[key] = r['correct_stone_at_pixel']
        csv_path = (folder / name / 'event-audit/candidate-review.csv' if name == 'sweden24' else ROOT / 'validation/fresh-same-format-transfer-2026-10-21/sweden22/source-reviewed-event-score.csv')
        events = {r['candidate_id']: r['verdict'] for r in csv.DictReader(csv_path.open())}
        assert set(events) == {e['candidate_id'] for e in data['events']}
        assert all(v in ('TP', 'FP') for v in events.values())
        rows = []
        for event in data['events']:
            key = event['candidate_id']
            checks = []
            segment_checks = []
            for segment in event['segments']:
                projected = [p for p in segment['geometry_samples'] if p['top_view_m'] is not None]
                verdicts = [labels[(key, p['time_s'], tuple(p['pixel']))] for p in projected]
                checks += verdicts
                segment_checks.append({'segment_id': segment['segment_id'], 'projected_points': len(verdicts), 'stone_points': sum(verdicts), 'all_projected_samples_on_stone': bool(verdicts) and all(verdicts)})
            # Strict candidate pass: a true delivery, two consecutive projected observations,
            # and every projected sample lands on a source-visible stone.
            usable = has_top_view(event)
            passed = events[key] == 'TP' and usable and all(checks)
            rows.append({'candidate_id': key, 'event_verdict': events[key], 'has_projected_segment': usable, 'projected_points': len(checks), 'stone_points': sum(checks), 'strict_source_point_pass': passed, 'has_cross_view_link': bool(event.get('cross_view_links')), 'segments': segment_checks})
        emitted = [r for r in rows if r['has_projected_segment']]
        passed = sum(r['strict_source_point_pass'] for r in rows)
        points = sum(r['projected_points'] for r in rows)
        correct = sum(r['stone_points'] for r in rows)
        linked = [r for r in rows if r['has_cross_view_link']]
        result[name] = {
            'aggregate_sha256': file_sha256(path),
            'event_review_sha256': file_sha256(csv_path),
            'review_sha256': {str(p.relative_to(ROOT)): file_sha256(p) for p in review_paths},
            'reference_deliveries': reference_count,
            'event_TP': sum(v == 'TP' for v in events.values()),
            'event_FP': sum(v == 'FP' for v in events.values()),
            'event_FN': reference_count - sum(v == 'TP' for v in events.values()),
            'projected_samples_reviewed': points, 'samples_on_visible_stone': correct,
            'source_point_precision': correct / points if points else None,
            'candidates_with_projected_segment': len(emitted),
            'strict_source_point_passes': passed,
            'strict_source_point_precision': passed / len(emitted) if emitted else None,
            'strict_source_point_recall': passed / reference_count,
            'cross_view_links': len(linked),
            'cross_view_links_passing_all_source_points': sum(r['strict_source_point_pass'] for r in linked),
            'definition': 'Joint delivery detection + emitted homography + exhaustive projected-source-point object check. Strict pass requires a TP delivery, two consecutive projected samples in a segment and no non-stone projected sample anywhere in its output. Not a metre-accuracy or continuous physical-identity score; same-colour collision switches can pass.',
            'rows': rows,
        }
    (folder / 'source-review-score.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: {a: b for a, b in v.items() if a not in ('rows', 'review_sha256')} for k, v in result.items()}, indent=2))
    return result


if __name__ == '__main__':
    score(Path(sys.argv[1]).resolve())
