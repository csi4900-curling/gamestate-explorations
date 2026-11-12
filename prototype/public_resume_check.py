"""Exercise real public CLI interruption/recovery against a continuous control.

The supplied plan contains the same reusable public command and input interval;
this harness makes no detection, tracking, association, or geometry decisions.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def run(plan_path):
    plan = json.loads(Path(plan_path).read_text())
    root = Path(plan['output_root'])
    root.mkdir(parents=True, exist_ok=False)
    progress = root/'progress'
    (root/'plan.json').write_text(json.dumps(plan, indent=2))

    def start(name, resumable):
        command = [*plan['command'], '--output-dir', str(root/name)]
        if resumable:
            command += ['--tracking-progress-dir', str(progress)]
        log = (root/(name+'.log')).open('w')
        process = subprocess.Popen(command, cwd=plan['working_directory'], stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        (root/(name+'-launch.json')).write_text(json.dumps(dict(command=command, pid=process.pid), indent=2))
        return process, log

    process, log = start('interrupted', True)
    deadline = time.monotonic()+plan.get('timeout_s', 900)
    try:
        while not list(progress.glob('*.pt')):
            if process.poll() is not None:
                raise RuntimeError(f'Public run exited before checkpoint: {process.returncode}')
            if time.monotonic() >= deadline:
                raise TimeoutError('No committed checkpoint before test timeout')
            time.sleep(.25)
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=30)
        (root/'interruption.json').write_text(json.dumps(dict(
            signal='SIGTERM to the dedicated test process group', returncode=process.returncode,
            committed_checkpoints=[str(p) for p in progress.glob('*.pt')]), indent=2))
        print('Public process interrupted after committed checkpoint', flush=True)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        log.close()

    for name, resumable in [('resumed', True), ('continuous', False)]:
        process, log = start(name, resumable)
        try:
            code = process.wait(timeout=plan.get('timeout_s', 900))
            if code:
                raise RuntimeError(f'{name} public process failed: {code}')
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            log.close()
        print(name+' public run finished', flush=True)

    return compare_outputs(root, plan['scope'])


def compare_outputs(root, scope):
    """Recheck preserved outputs without paying for inference again."""
    root = Path(root)
    records = [json.loads((root/name/'two-view-tracking/result.json').read_text())
               for name in ['resumed', 'continuous']]
    reports = []
    for name, record in zip(['resumed', 'continuous'], records):
        segments = {}
        for event in record['events']:
            for segment in event['segments']:
                if segment['status'] != 'tracked':
                    raise ValueError('A requested segment failed in the public test')
                saved = json.loads((root/name/'two-view-tracking'/segment['result']).read_text())
                segments[segment['segment_id']] = saved
        reports.append(segments)
    if not reports[0] or reports[0].keys() != reports[1].keys():
        raise ValueError('Nonempty identical segment set required')
    comparison = []
    for key, resumed in reports[0].items():
        control = reports[1][key]
        comparison.append(dict(segment_id=key,
            frame_indices_equal=resumed['frame_indices']==control['frame_indices'],
            times_equal=resumed['times_s']==control['times_s'],
            tracks_bitwise_equal=resumed['tracks_px']==control['tracks_px'],
            visibility_equal=resumed['point_visible']==control['point_visible'],
            checkpoint=resumed['model'].get('progress_checkpoint')))
    checks = ['frame_indices_equal', 'times_equal', 'tracks_bitwise_equal', 'visibility_equal']
    resumed_work = any((row['checkpoint'] or {}).get('resumed_window_offset', 0) > 0
                       for row in comparison)
    passed = resumed_work and all(row[key] for row in comparison for key in checks)
    result = dict(nonempty_tracked_outputs=True, segments=comparison,
                  checkpoint_actually_resumed=resumed_work, all_checks_passed=passed,
                  scope=scope, full_match_complete=False)
    (root/'output-comparison.json').write_text(json.dumps(result, indent=2))
    if not passed:
        raise ValueError('Public checkpoint comparison failed; see output-comparison.json')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--compare-only', action='store_true')
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text())
    result = (compare_outputs(plan['output_root'], plan['scope']) if args.compare_only
              else run(args.plan))
    print(json.dumps(result), flush=True)
