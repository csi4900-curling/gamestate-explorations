"""Observable broom cues and receiving-view outcomes, not automatic tactical intent."""
import cv2
import numpy as np

def broom_candidates(frame):
    """Source-specific orange upright broom-head proposals; lower edge is a contact proxy."""
    hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV);h,s,v=cv2.split(hsv)
    mask=((h>12)&(h<42)&(s>120)&(v>110)).astype('uint8')*255
    # Existing 1080p right panel. This is explicit source setup, not automatic skip recognition.
    mask[:320]=0;mask[630:]=0;mask[:,:1080]=0;mask[:,1800:]=0
    cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);out=[]
    for cnt in cs:
        x,y,w,hh=cv2.boundingRect(cnt);area=cv2.contourArea(cnt)
        if not(7<=w<=45 and 25<=hh<=90 and 1.4<=hh/w<=5 and 150<=area<=3000):continue
        bottom=cnt.reshape(-1,2);bottom=bottom[bottom[:,1]>=y+hh-3]
        px=[float(np.median(bottom[:,0])),float(y+hh-1)]
        out.append({'pixel':px,'bbox':[x,y,w,hh],'kind':'upright_broom_head_candidate','contact_assumption':'Visible lower edge treated as ice contact; not independently verified.'})
    return out

def stable_broom(records,throw_time,window_s=30):
    usable=[r for r in records if throw_time-window_s<=r['source_time_s']<=throw_time-2 and len(r['candidates'])==1]
    if len(usable)<8:return {'status':'unavailable','reason':'Insufficient unambiguous pre-throw broom observations.'}
    xy=np.array([r['candidates'][0]['pixel'] for r in usable]);centre=np.median(xy,axis=0);dist=np.linalg.norm(xy-centre,axis=1)
    keep=[r for r,d in zip(usable,dist) if d<=10]
    if len(keep)<8 or keep[-1]['source_time_s']-keep[0]['source_time_s']<3:return {'status':'unavailable','reason':'No sufficiently stable cue.'}
    best=min(keep,key=lambda r:np.linalg.norm(np.array(r['candidates'][0]['pixel'])-centre));cue=best['candidates'][0]
    return {'status':'candidate','kind':'aiming_broom_candidate','evidence_time_s':best['source_time_s'],'pixel':cue['pixel'],'bbox':cue['bbox'],'position_m_if_ice_contact':cue.get('position_m_if_ice_contact'),'stable_observations':len(keep),'span_s':[keep[0]['source_time_s'],keep[-1]['source_time_s']],'pixel_spread_p95':float(np.percentile([np.linalg.norm(np.array(r['candidates'][0]['pixel'])-centre) for r in keep],95)),'intended_destination_m':None,'semantic_review_required':True,'uncertainty_m':None}

def receiving_outcome(timeline,event):
    start=timeline['source_start_s'];tracks={}
    for row in timeline['records']:
        t=start+row['time_s']
        for s in row['views']['right']['stones']:
            key=(s['colour'],s['track_id']);tracks.setdefault(key,[]).append({'time_s':t,'pixel':s['pixel_center'],'position_m':s['ground_position_m']})
    eligible=[]
    for (colour,tid),pts in tracks.items():
        if colour!=event['colour'] or not(event['crossing_time_s']<pts[0]['time_s']<event['crossing_time_s']+35):continue
        early=[p for p in pts if p['time_s']<=pts[0]['time_s']+6]
        if len(early)<4 or early[0]['pixel'][1]-min(p['pixel'][1] for p in early)<35:continue
        eligible.append((tid,pts))
    if len(eligible)!=1:return {'status':'unavailable','reason':'Receiving-track association absent or ambiguous.','candidate_tracks':len(eligible)}
    tid,pts=eligible[0];settled=None
    for i,p in enumerate(pts):
        win=[q for q in pts[:i+1] if p['time_s']-q['time_s']<=2]
        if len(win)<5 or p['time_s']-win[0]['time_s']<2:continue
        xy=np.array([q['pixel'] for q in win]);spread=float(np.max(np.linalg.norm(xy-np.median(xy,axis=0),axis=1)))
        if spread>3 or abs(xy[-1,1]-xy[0,1])>2:continue
        metric=[q['position_m'] for q in win if q['position_m'] is not None]
        if len(metric)<5:continue
        settled={'time_s':p['time_s'],'position_m':np.median(metric,axis=0).tolist(),'pixel':np.median(xy,axis=0).tolist(),'window_s':[win[0]['time_s'],p['time_s']],'pixel_spread_max':spread};break
    interactions=[]
    for (colour,other_id),other in tracks.items():
        if other_id==tid and colour==event['colour']:continue
        for a,b in zip(other,other[1:]):
            if settled and a['time_s']>settled['time_s']:continue
            if b['time_s']-a['time_s']>1.1 or a['position_m'] is None or b['position_m'] is None:continue
            if np.linalg.norm(np.array(b['position_m'])-a['position_m'])<.15:continue
            nearby=[p for p in pts if a['time_s']<=p['time_s']<=b['time_s'] and p['position_m'] is not None]
            if nearby and min(np.linalg.norm(np.array(p['position_m'])-a['position_m']) for p in nearby)<.55:
                interactions.append({'time_s':a['time_s'],'other_colour':colour,'other_track_id':other_id,'kind':'proximity_and_motion_change_candidate'});break
    return {'status':'provisional_association','track_id':tid,'association_basis':'Unique same-colour newly appearing receiving track with sustained inward motion in the following 35 seconds; cameras not fused.','trajectory':pts,'settled':settled,'interaction_candidates':interactions,'physical_accuracy_measured':False}
