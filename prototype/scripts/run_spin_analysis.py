"""Reusable development entry point for upstream point tracking and spin gaps."""
import argparse
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from prototype.spin.pipeline import run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--aggregate', type=Path)
    p.add_argument('--reuse-result', type=Path, help='Reuse hash-matched point predictions; recompute analysis and projection')
    p.add_argument('--expected-decoder-sha')
    p.add_argument('--mode', choices=['online','offline'], default='online')
    p.add_argument('--device', default='cpu')
    p.add_argument('--threads', type=int, default=4)
    a=p.parse_args()
    r=run(a.video,a.config,a.output,checkpoint=a.checkpoint,device=a.device,mode=a.mode,
          threads=a.threads,aggregate_path=a.aggregate,reuse_result=a.reuse_result,expected_decoder_sha=a.expected_decoder_sha)
    print(json.dumps({'report':str(a.output/'index.html'), 'model':r['model'],
                      'observed_orientation_frames':r['reconstruction']['observed_count'],
                      'estimated_frames':r['reconstruction']['estimated_count'],
                      'physical_revolutions':r['physical_revolutions']}))


if __name__=='__main__':main()
