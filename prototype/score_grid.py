"""Read individual end-score cells from observed OCR header and team rows.

No fixed board coordinates or configured end count. Merged tokens remain
unresolved rather than being split into guessed digits. These are unverified
OCR observations, not the current end or a completed-game assertion.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def parse_end_cells(tokens, team_labels):
    anchors=[t for t in tokens if t['normalized']=='END']
    columns={}
    for anchor in anchors:
        ax0,ay0,ax1,ay1=anchor['bounds']
        numbered=[]
        for token in tokens:
            x0,y0,x1,y1=token['bounds']
            text=token['text'].strip()
            if text.isdecimal() and int(text)>0 and x0>ax1 and ay0<=(y0+y1)/2<=ay1:
                numbered.append(token)
        numbered.sort(key=lambda t:t['bounds'][0])
        for i,token in enumerate(numbered):
            value=int(token['text'].strip())
            # Adjacent sequential labels provide grid evidence. This rejects
            # merged headers such as "3456" without imposing an end count.
            supported=(i>0 and int(numbered[i-1]['text'].strip())==value-1) or (i+1<len(numbered) and int(numbered[i+1]['text'].strip())==value+1)
            if supported:columns.setdefault(value,[]).append(token)
    result={}
    for end,headers in sorted(columns.items()):
        result[str(end)]={}
        for team in team_labels:
            candidates=[]
            if len(headers)==1:
                header=headers[0];hx0,hy0,hx1,hy1=header['bounds']
                labels=[t for t in tokens if t['normalized']==team.upper() and t['bounds'][2]<hx0 and t['bounds'][1]>hy1]
                for label in labels:
                    _,ly0,_,ly1=label['bounds']
                    for token in tokens:
                        x0,y0,x1,y1=token['bounds'];text=token['text'].strip()
                        # Entire glyph must overlap this observed header and its centre
                        # must lie within it. Multi-digit/merged end-score OCR is ambiguous.
                        if len(text)==1 and text.isdecimal() and hx0<=(x0+x1)/2<=hx1 and ly0<=(y0+y1)/2<=ly1:
                            candidates.append({'value':int(text),'evidence':[header,label,token]})
            if len(candidates)==1:
                result[str(end)][team]={**candidates[0],'status':'ocr_observed_unverified'}
            else:
                result[str(end)][team]={'value':None,'status':'unreadable_or_ambiguous','candidates':candidates}
    marker_candidates=[]
    for team in team_labels:
        labels=[t for t in tokens if t['normalized']==team.upper()]
        for token in tokens:
            text=token['text'].replace(' ','')
            if not re.fullmatch(r'[0-9]*>',text):continue
            x0,y0,x1,y1=token['bounds']
            # A merged score-row token uses one printed glyph per end cell.
            # This is an explicit typography assumption, not character detection.
            marker_x=x1-(x1-x0)/(2*len(text))
            for label in labels:
                lx0,ly0,lx1,ly1=label['bounds']
                if lx1>=x0 or not ly0<=(y0+y1)/2<=ly1:continue
                for end,headers in columns.items():
                    if len(headers)!=1:continue
                    hx0,hy0,hx1,hy1=headers[0]['bounds']
                    if hx0<=marker_x<=hx1 and y0>hy1:
                        marker_candidates.append({'end':end,'team_row':team,'evidence':[headers[0],label,token],
                            'marker_x_estimate_px':marker_x,'glyph_localization':'Equal-width glyphs within merged OCR token' if len(text)>1 else 'Single OCR glyph centre'})
    marker=marker_candidates[0] if len(marker_candidates)==1 else None
    return {'end_score_cells':result,'current_end':marker['end'] if marker else None,
            'current_end_status':'scoreboard_marker_observed_unverified' if marker else 'unreadable_or_ambiguous',
            'current_end_evidence':marker,'current_end_candidates':marker_candidates,
            'end_interpretation':'Displayed active-end marker, not a verified physical end boundary or game-completion state',
            'method':'Observed END header row, adjacent sequential numbered headers and configured team rows; merged digits unresolved'}


def derive(source, output, team_labels):
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('Preserve previous derived results')
    output.mkdir(parents=True)
    samples=0;readable=0;both=0;markers=0
    with source.open() as inp,(output/'observations.jsonl').open('w') as out:
        for line in inp:
            row=json.loads(line);parsed=parse_end_cells(row['tokens'],team_labels)
            parsed['time_s']=row['time_s'];parsed['frame_index']=row['frame_index']
            out.write(json.dumps(parsed)+'\n');samples+=1
            cells=parsed['end_score_cells']
            markers+=parsed['current_end'] is not None
            readable+=sum(s['value'] is not None for cell in cells.values() for s in cell.values())
            both+=sum(all(s['value'] is not None for s in cell.values()) for cell in cells.values())
    code=Path(__file__).read_bytes();(output/'parser.py').write_bytes(code)
    summary={'development':True,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
             'code_sha256':hashlib.sha256(code).hexdigest(),'team_labels':team_labels,'samples':samples,
             'non_null_team_cells':readable,'both_team_cells':both,'accuracy_evaluated':False,
             'active_end_marker_observation_count':markers,'current_end_extraction_complete':False}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--observations',required=True);p.add_argument('--output',required=True);p.add_argument('--teams',nargs=2,required=True)
    a=p.parse_args();print(json.dumps(derive(a.observations,a.output,a.teams)))
