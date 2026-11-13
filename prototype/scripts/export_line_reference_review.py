"""Export source-only contact sheets for manual event-reference review.

Historical timestamps select frames; they are not new line-crossing labels.
No detector predictions are loaded. This tool never changes inference rules.
"""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
from PIL import Image, ImageDraw


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def run(video, reference, line_config, output, end_number, crop, offsets):
    output=Path(output)
    if output.exists():raise ValueError('Preserve previous review export')
    config=json.loads(Path(line_config).read_text())
    selected=[r for r in json.loads(Path(reference).read_text())['throws'] if r['end']==end_number]
    if not selected:raise ValueError('No reference timestamps for this end')
    cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS)
    if fps<=0:raise ValueError('Unreadable video')
    output.mkdir(parents=True);samples=[]
    try:
        for page,start in enumerate(range(0,len(selected),4)):
            group=selected[start:start+4]
            canvas=Image.new('RGB',(480*len(offsets),300*len(group)),'white');draw=ImageDraw.Draw(canvas)
            for row,entry in enumerate(group):
                for col,offset in enumerate(offsets):
                    index=round((entry['time_s']+offset)*fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES,index);ok,frame=cap.read()
                    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=index:raise ValueError('Source seek mismatch')
                    height,width=frame.shape[:2]
                    for line in config['lines']:
                        a,b=[(round(x*width),round(y*height)) for x,y in line['endpoints_normalized']]
                        cv2.line(frame,a,b,(0,200,0),2)
                    x0,y0,x1,y1=[round(v*s) for v,s in zip(crop,[width,height,width,height])]
                    tile=Image.fromarray(cv2.cvtColor(frame[y0:y1,x0:x1],cv2.COLOR_BGR2RGB)).resize((480,270))
                    canvas.paste(tile,(480*col,300*row+30))
                    draw.text((480*col+5,300*row+5),f"{entry['reference_shot_id']} {index/fps:.3f}s",fill='black')
                    samples.append({'id':entry['reference_shot_id'],'frame_index':index,'time_s':index/fps,'page':page,'row':row,'column':col})
            canvas.save(output/f'page-{page}.png')
    finally:cap.release()
    (output/'protocol.json').write_text(json.dumps({'source_sha256':sha(video),'historical_reference_sha256':sha(reference),
        'line_config_sha256':sha(line_config),'code_sha256':sha(__file__),'end':end_number,'source_crop_normalized':crop,
        'offsets_s':offsets,'samples':samples,'predictions_loaded':False,
        'purpose':'Source-only evidence export, not annotations or an exhaustive throw count',
        'selection_bias':'Historical assistant-reviewed throws select timestamps; this is not independent ground truth.'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['video','reference','line-config','output']:p.add_argument('--'+name,required=True)
    p.add_argument('--end',type=int,required=True);p.add_argument('--crop',type=float,nargs=4,required=True)
    p.add_argument('--offsets',type=float,nargs='+',required=True)
    a=p.parse_args();run(a.video,a.reference,a.line_config,a.output,a.end,a.crop,a.offsets)
