"""Run upstream SAM2 video tracking on the exact source/queries of a CoTracker run.

This is a component comparison, not a replacement pipeline. The adapter exports
native lossless frames, preserves upstream object slots (including empty masks),
and records mask geometry without claiming physical identity or stone centres.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path


def run(video, reference_result, checkpoint, output, *, max_frames=None, threads=4):
    import cv2
    import numpy as np
    import torch
    import ultralytics
    from ultralytics.models.sam.predict import SAM2VideoPredictor
    from ultralytics.utils import ops
    from prototype.detection_cache import digest
    video,reference_result,checkpoint,output=map(Path,(video,reference_result,checkpoint,output))
    if output.exists():raise ValueError('Preserve prior comparison')
    ref=json.loads(reference_result.read_text())
    if digest(video)!=ref['provenance']['source_sha256']:raise ValueError('Source differs from reference tracker run')
    cfg=json.loads((reference_result.parent/'input-config.json').read_text())
    frames=ref['frame_indices'][:max_frames];times=ref['times_s'][:max_frames]
    if not frames or frames!=list(range(frames[0],frames[-1]+1)):raise ValueError('Comparison requires contiguous native frames')
    output.mkdir(parents=True);(output/'masks').mkdir()
    clip=output/'native-crop.avi';x0,y0,x1,y1=cfg['crop_px'];fps=ref['fps']
    cap=cv2.VideoCapture(str(video));cap.set(cv2.CAP_PROP_POS_FRAMES,frames[0])
    writer=cv2.VideoWriter(str(clip),cv2.VideoWriter_fourcc(*'FFV1'),fps,(x1-x0,y1-y0))
    if not writer.isOpened():raise ValueError('Cannot encode lossless comparison input')
    expected=hashlib.sha256();rgb=hashlib.sha256()
    try:
        for idx in frames:
            ok,frame=cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=idx:raise ValueError('Source frame mismatch')
            crop=np.ascontiguousarray(frame[y0:y1,x0:x1]);writer.write(crop);expected.update(crop);rgb.update(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB))
    finally:writer.release();cap.release()
    cap=cv2.VideoCapture(str(clip));actual=hashlib.sha256();count=0
    while True:
        ok,frame=cap.read()
        if not ok:break
        actual.update(frame);count+=1
    cap.release()
    if actual.digest()!=expected.digest() or count!=len(frames):raise ValueError('Lossless export verification failed')
    if max_frames is None and rgb.hexdigest()!=ref['provenance']['decoded_input']['rgb_uint8_sha256']:
        raise ValueError('Decoded pixels differ from CoTracker input')
    queries=ref['provenance']['query_input'];points=[[[q[1],q[2]]] for q in queries]
    torch.set_num_threads(threads)
    predictor=SAM2VideoPredictor(overrides={'model':str(checkpoint),'device':'cpu','imgsz':1024,'verbose':False,'save':False,'show':False})
    protocol={'development':True,'upstream':'ultralytics.models.sam.predict.SAM2VideoPredictor','ultralytics':ultralytics.__version__,
              'source_sha256':ref['provenance']['source_sha256'],'reference_result_sha256':digest(reference_result),
              'checkpoint_sha256':digest(checkpoint),'adapter_sha256':digest(__file__),'crop_px':cfg['crop_px'],
              'source_frame_indices':frames,'times_s':times,'query_input':queries,'point_names':ref['point_names'],
              'native_bgr_input_sha256':actual.hexdigest(),'native_rgb_input_sha256':rgb.hexdigest(),
              'input_pixels_match_reference_full_sequence':max_frames is None,'native_frame_rate':fps,'imgsz':1024,'threads':threads,
              'mask_point_semantics':'Mask centroid/bounding-box centre, not tracked feature or verified contact point',
              'identity_verified':False,'max_frames':max_frames,'upstream_default_non_overlap_masks':predictor.non_overlap_masks}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n');(output/'adapter.py').write_bytes(Path(__file__).read_bytes())
    started=time.perf_counter();n=0
    with (output/'observations.jsonl').open('w') as stream:
        for result in predictor(source=str(clip),points=points,labels=[[1]]*len(points),stream=True):
            state=predictor.inference_state;key=predictor.dataset.frame
            current=state['output_dict']['cond_frame_outputs'].get(key)
            if current is None:current=state['output_dict']['non_cond_frame_outputs'][key]
            logits=current['pred_masks'].flatten(0,1)
            # Upstream public results drop empty slots. Read the preserved internal
            # slots and use upstream scaling/non-overlap operations without renumbering.
            masks=ops.scale_masks(logits[None].float(),(y1-y0,x1-x0),padding=False)[0]
            masks=predictor.model._apply_non_overlapping_constraints(masks.unsqueeze(0))[0]
            masks=(masks>predictor.model.mask_threshold).cpu().numpy()
            ids=state['obj_ids'];objects=[]
            if len(ids)!=len(masks):raise ValueError('Object slots and masks differ')
            for j,mask in zip(ids,masks):
                yy,xx=np.nonzero(mask)
                objects.append({'query_index':j,'mask_pixels':int(len(xx)),
                    'centroid_full_source_px':[float(xx.mean()+x0),float(yy.mean()+y0)] if len(xx) else None,
                    'bbox_full_source_xyxy':[int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0),int(yy.max()+y0)] if len(xx) else None})
            np.savez_compressed(output/'masks'/f'{n:06}.npz',packed_masks=np.packbits(masks,axis=2),shape=masks.shape,obj_ids=ids)
            row={'frame_index':frames[n],'time_s':times[n],'objects':objects,'wall_seconds_so_far':time.perf_counter()-started}
            stream.write(json.dumps(row)+'\n');stream.flush();n+=1
            if n%10==0:print(json.dumps({'frames':n,'of':len(frames),'wall_seconds':time.perf_counter()-started}),flush=True)
    if n!=len(frames):raise ValueError('Incomplete SAM video output')
    (output/'summary.json').write_text(json.dumps({'frames':n,'wall_seconds':time.perf_counter()-started,'physical_identity_verified':False},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--video',required=True);p.add_argument('--reference-result',required=True);p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True);p.add_argument('--max-frames',type=int)
    a=p.parse_args();run(a.video,a.reference_result,a.checkpoint,a.output,max_frames=a.max_frames)
