"""Compare visible tracked points to frozen source-object boxes at exact timestamps.

Measures point-on-labelled-object support only, never physical identity or metric
trajectory accuracy. Ignored regions and non-overlapping annotation times remain
explicit. No point interpolation or source-time offset is fitted.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from prototype.scripts.compare_stone_detectors import contains


def audit(result, protocol, annotations):
    samples=[]
    for frame,annotation in zip(protocol['frames'],annotations['rows']):
        assert frame['id']==annotation['frame_id']
        for event in result['events']:
            for segment in event['segments']:
                if segment.get('status')!='tracked' or segment.get('camera')!='right_split':continue
                times=segment['times_s']
                exact=[i for i,t in enumerate(times) if abs(t-frame['time_s'])<1e-6]
                if len(exact)!=1:continue
                i=exact[0]
                for q,(pixel,visible) in enumerate(zip(segment['tracks_px'][i],segment['point_visible'][i])):
                    matching=[j for j,b in enumerate(annotation['boxes_xyxy']) if contains(b,pixel)]
                    ignored=any(contains(b,pixel) for b in annotation.get('ignore_regions_xyxy',[]))
                    status='model_hidden' if not visible else 'on_annotated_stone' if matching else 'ignored_region' if ignored else 'outside_annotated_stones'
                    samples.append({'frame_id':frame['id'],'time_s':frame['time_s'],'segment':segment['segment_id'],
                                    'query':segment['point_names'][q],'pixel':pixel,'status':status,'matched_box_indices':matching})
    return {'scope':'Visible source-point support, NOT trajectory accuracy or physical identity. Annotation box indices are frame-local, not stone identities.',
            'annotation_provenance':annotations['annotator'],
            'counts':{k:sum(s['status']==k for s in samples) for k in ['model_hidden','on_annotated_stone','ignored_region','outside_annotated_stones']},'samples':samples}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--result',type=Path,required=True);p.add_argument('--annotations',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve existing audit')
    result=audit(json.loads(a.result.read_text()),json.loads(a.protocol.read_text()),json.loads(a.annotations.read_text()))
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result['counts']))

if __name__=='__main__':main()
