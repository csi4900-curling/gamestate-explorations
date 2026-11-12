"""Audit a finalized public event scan against timestamped source references.

Checks every expected sampled frame. Unmatched crossings remain review items,
not automatically false positives when the reference footage is non-exhaustive.
"""
import argparse
import hashlib
import json
from pathlib import Path

from prototype.throw_event_benchmark import evaluate_events


def verified_candidate_precision(scored, references):
    """Known positive references can verify precision without exhaustive recall labels.

    Unmatched candidates remain unclassified rather than being called false
    positives. This measure is conditional on the recorded source reviewer.
    """
    known = {r['id'] for r in references if r.get('physical_delivery_observed') is True}
    verified = sum(m['reference_id'] in known for m in scored['matches'])
    total = scored['prediction_count']
    all_verified = total > 0 and verified == total
    return {'value': verified/total if all_verified else None,
            'verified_positive_candidates': verified, 'candidate_count': total,
            'unclassified_candidates': total-verified,
            'status': 'all_candidates_match_source_verified_deliveries' if all_verified else 'candidate_review_incomplete_or_no_candidates',
            'scope': 'Source-review-conditioned candidate precision in the evaluated interval; not independent ground truth or full-match recall.'}


def verify_scan(events, observations):
    if events['status'] != 'development_complete_event_stage':
        raise ValueError('Event stage is not finalized')
    fps = events['source_fps']
    first, stop = [round(t*fps) for t in events['source_interval_s']]
    expected = range(first, stop, events['sample_step_frames'])
    count = 0
    for row in observations:
        if count >= len(expected) or row['frame_index'] != expected[count]:
            raise ValueError('Missing, duplicated or out-of-order sampled frame')
        if abs(row['time_s']-row['frame_index']/fps) > 1e-9:
            raise ValueError('Source time does not match frame index')
        count += 1
    if count != len(expected) or count != events['sampled_frames']:
        raise ValueError('Incomplete scan: saved frame coverage differs from requested interval')
    return dict(expected_sampled_frames=len(expected), verified_sampled_frames=count,
                source_interval_s=events['source_interval_s'], complete_requested_scan=True)


def audit_prefix(protocol, progress, observations, references):
    """Audit an immutable progress snapshot, never certify the unfinished scan.

    Read only the number of rows committed by that snapshot. A later append is
    irrelevant; a missing row or a crossing beyond the snapshot is an error.
    """
    if protocol['source_sha256'] != references['source_sha256']:
        raise ValueError('Source hashes differ')
    if protocol['config_sha256'] != references['line_config_sha256']:
        raise ValueError('Reference crossing line differs')
    count = progress['samples']
    if count <= 0:
        raise ValueError('No committed samples')
    fps = protocol['source_fps']
    first = round(protocol['source_interval_s'][0]*fps)
    iterator = iter(observations)
    for i in range(count):
        row = next(iterator, None)
        if row is None or row['frame_index'] != first+i*protocol['sample_step_frames']:
            raise ValueError('Incomplete or invalid sampled prefix')
        if abs(row['time_s']-row['frame_index']/fps) > 1e-9:
            raise ValueError('Source time does not match frame index')
    stop = row['time_s']
    if abs(stop-progress['source_time_s']) > 1e-9:
        raise ValueError('Progress time differs from committed prefix')
    predictions = progress['events_so_far']
    if len(predictions) != progress['crossings'] or any(e['confirmed_at_s'] > stop for e in predictions):
        raise ValueError('Crossings inconsistent with progress snapshot')
    lo = protocol['source_interval_s'][0]
    refs = [r for r in references['events'] if lo <= r['delivery_interval_s'][0] and r['delivery_interval_s'][1] <= stop]
    scored = evaluate_events(predictions, refs, (lo, stop), tolerance_s=0, evaluate_colour=False)
    return dict(partial_run=True, complete_requested_scan=False,
                source_sha256=protocol['source_sha256'], verified_sampled_frames=count,
                evaluated_interval_s=[lo, stop], requested_interval_s=protocol['source_interval_s'],
                matched_known_throws=scored['true_positives'], reference_count=len(refs),
                missed_known_throw_ids=scored['missed_reference_ids'], matches=scored['matches'],
                unmatched_prediction_ids=scored['extra_prediction_ids'],
                precision_evidence=verified_candidate_precision(scored, refs),
                full_match_recall_verified=False,
                reference_reviewer=references.get('reviewer'),
                independent_ground_truth=references.get('independent_ground_truth', False))


def audit(public_run, reference_path):
    public_run, reference_path = Path(public_run), Path(reference_path)
    events = json.loads((public_run/'events.json').read_text())
    references = json.loads(reference_path.read_text())
    if events['source_sha256'] != references['source_sha256']:
        raise ValueError('Source hashes differ')
    if events['config_sha256'] != references['line_config_sha256']:
        raise ValueError('Reference crossing line differs from evaluated configuration')
    with (public_run/'observations.jsonl').open() as stream:
        coverage = verify_scan(events, (json.loads(line) for line in stream))
    lo, hi = events['source_interval_s']
    refs = [r for r in references['events'] if lo <= r['delivery_interval_s'][0] and r['delivery_interval_s'][1] <= hi]
    scored = evaluate_events(events['events'], refs, (lo, hi), tolerance_s=0, evaluate_colour=False)
    precision = verified_candidate_precision(scored, refs)
    extras = set(scored['extra_prediction_ids'])
    queue = [dict(prediction_id=e['id'], crossing_time_s=e['crossing_time_s'],
                  direction=e.get('direction'), status='requires_source_review')
             for e in events['events'] if e['id'] in extras]
    def sha(path):
        h = hashlib.sha256()
        with Path(path).open('rb') as f:
            for block in iter(lambda: f.read(1024*1024), b''):
                h.update(block)
        return h.hexdigest()
    return dict(coverage=coverage, source_sha256=events['source_sha256'],
                reference_count=len(refs), prediction_count=len(events['events']),
                matched_known_throws=scored['true_positives'],
                missed_known_throw_ids=scored['missed_reference_ids'],
                recall_of_known_reference_throws=scored['recall'],
                matches=scored['matches'], unmatched_prediction_review_queue=queue,
                actual_event_precision=precision['value'],
                precision_status=precision['status'],
                precision_evidence=precision,
                full_match_recall_verified=False,
                annotation_provenance=dict(reviewer=references.get('reviewer'),
                    independent_ground_truth=references.get('independent_ground_truth', False),
                    exhaustive_intervening_footage_review=references.get('exhaustive_intervening_footage_review', False)),
                interpretation='Zero added timing tolerance; source crossing brackets, not release-time accuracy. This audit covers the event stage only.',
                evidence_sha256={str(p):sha(p) for p in [reference_path, public_run/'events.json', public_run/'observations.jsonl', Path(__file__)]})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['run', 'reference', 'output']:
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    result = audit(a.run, a.reference)
    with Path(a.output).open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
