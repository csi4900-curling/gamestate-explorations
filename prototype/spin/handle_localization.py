"""Isolated upstream Florence-2 referring-segmentation component experiment.

Polygons are unverified handle hypotheses, not landmarks or angular velocity.
This component is not used to alter event detection, identity or trajectories.
"""
import argparse
import json
from pathlib import Path
import time

from PIL import Image, ImageDraw

from prototype.detection_cache import digest


def run(evidence_path, config_path, output):
    import torch
    import transformers
    from huggingface_hub import HfApi, snapshot_download
    from transformers import AutoProcessor, Florence2ForConditionalGeneration

    evidence_path,config_path,output=map(Path,(evidence_path,config_path,output))
    if output.exists():raise ValueError('Preserve existing handle experiment')
    config=json.loads(config_path.read_text());evidence=json.loads(evidence_path.read_text())
    output.mkdir(parents=True)
    plan={'development':True,'config':config,'evidence_sha256':digest(evidence_path),
          'adapter_sha256':digest(__file__),
          'selection':'First preselected moving-source review sample of each requested event; no prompt tuning after outputs.',
          'physical_revolutions':None}
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    torch.set_num_threads(config['threads'])
    revision=HfApi().model_info(config['model'],revision=config.get('revision','main')).sha
    (output/'resolved-revision.json').write_text(json.dumps({'model':config['model'],'revision':revision})+'\n')
    model_path=Path(snapshot_download(config['model'],revision=revision,cache_dir=config['cache_dir'],
                   allow_patterns=['*.json','*.safetensors','*.txt','*.model']))
    started=time.perf_counter()
    model=Florence2ForConditionalGeneration.from_pretrained(model_path,torch_dtype=torch.float32,
                                                           attn_implementation='eager').eval()
    processor=AutoProcessor.from_pretrained(model_path)
    load_wall=time.perf_counter()-started;rows=[]
    for event in evidence['events']:
        samples=event.get('review_samples',[])
        if not samples:continue
        sample=samples[0];image_path=evidence_path.parent/sample['crop']
        image=Image.open(image_path).convert('RGB')
        for prompt_index,text in enumerate(config['prompts']):
            started=time.perf_counter();task='<REFERRING_EXPRESSION_SEGMENTATION>'
            inputs=processor(text=task+text,images=image,return_tensors='pt')
            with torch.inference_mode():
                ids=model.generate(**inputs,max_new_tokens=config['max_new_tokens'],
                                   num_beams=config['num_beams'],do_sample=False)
            raw=processor.batch_decode(ids,skip_special_tokens=False)[0]
            parsed=processor.post_process_generation(raw,task=task,image_size=image.size)
            row={'event_id':event['event_id'],'time_s':sample['time_s'],'frame_index':sample['frame_index'],
                 'source_crop':str(image_path.resolve()),'source_crop_sha256':digest(image_path),
                 'crop_source_bounds':sample['crop_source_bounds'],'prompt':text,
                 'raw_generation':raw,'parsed':parsed,'wall_s':time.perf_counter()-started,
                 'generated_tokens':int(ids.shape[-1]),
                 'generation_budget_reached':int(ids.shape[-1])>=config['max_new_tokens'],
                 'physical_orientation':None,'status':'unverified_referring_segmentation'}
            filename=f"{event['event_id']}-prompt-{prompt_index}.json"
            (output/filename).write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
            overlay=image.copy();draw=ImageDraw.Draw(overlay)
            for group in parsed.get(task,{}).get('polygons',[]):
                # Upstream segmentation represents each instance as a list of polygons.
                for polygon in group:
                    xy=list(zip(polygon[::2],polygon[1::2]))
                    if len(xy)>=3:draw.line(xy+[xy[0]],fill='blue',width=2)
            overlay.resize((image.width*3,image.height*3),Image.Resampling.NEAREST).save(output/filename.replace('.json','.png'))
            print(event['event_id'],prompt_index,round(row['wall_s'],2),'s',flush=True)
    manifest={**plan,'model_revision':revision,'transformers':transformers.__version__,
              'torch':str(torch.__version__),'model_load_wall_s':load_wall,
              'model_sha256':{str(p.relative_to(model_path)):digest(p) for p in model_path.rglob('*') if p.is_file()},
              'results':rows,'adopted_into_match_pipeline':False,
              'scope':'Learned handle-mask hypotheses only; no endpoint tracking, calibrated angular velocity or revolution count.'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['evidence','config','output']:parser.add_argument('--'+name,required=True)
    a=parser.parse_args();run(a.evidence,a.config,a.output)
