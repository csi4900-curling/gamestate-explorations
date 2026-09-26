"""Fixed-view outgoing-stone passage baseline. Never reads event labels or shot counts."""
from dataclasses import dataclass,field
import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment
VERSION='stone-passage-v2'
@dataclass
class PassageConfig:
    # Coordinates refer to a normalized 640x360 full frame, left panel only.
    roi: tuple=(40,4,280,116)
    gate_y: float=60.
    min_span_px: float=24.
    min_observations: int=6
    max_gap_s: float=.55
    association_px: float=13.
    min_speed_px_s: float=8.
    max_speed_px_s: float=65.

def stone_candidates(frame,config):
    im=cv2.resize(frame,(640,360),interpolation=cv2.INTER_AREA)
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);x0,y0,x1,y1=config.roi
    crop=hsv[y0:y1,x0:x1];h,s,v=cv2.split(crop)
    candidates=[]
    for colour,mask in [('red',((h<12)|(h>160))&(s>50)&(v>35)),('yellow',(h>16)&(h<43)&(s>70)&(v>65))]:
        contours,_=cv2.findContours(mask.astype('uint8')*255,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x,y,w,hh=cv2.boundingRect(cnt);area=cv2.contourArea(cnt)
            if not(2<=area<=100 and 3<=w<=22 and 1<=hh<=13 and .7<=w/hh<=5):continue
            x+=x0;y+=y0
            # A stone cap should have neutral granite directly underneath.
            band=hsv[min(359,y+hh):min(360,y+hh+max(2,round(w*.45))),x:x+w]
            if not band.size:continue
            neutral=(band[:,:,1]<95)&(band[:,:,2]>35)&(band[:,:,2]<220)
            support=float(np.mean(neutral))
            if support<.25:continue
            candidates.append({'colour':colour,'pixel':[x+w/2,y+hh/2+max(1,w*.12)],'bbox':[x,y,w,hh+max(2,round(w*.45))],'body_support':support})
    return candidates

@dataclass
class Track:
    id:int
    colour:str
    points:list=field(default_factory=list)
    emitted:bool=False

class PassageDetector:
    def __init__(self,config=None):
        self.config=config or PassageConfig();self.tracks=[];self.next_id=1;self.events=[];self.finished=[]
    def update(self,candidates,t):
        c=self.config
        alive=[]
        for track in self.tracks:
            if t-track.points[-1]['time_s']>c.max_gap_s:
                if track.emitted:self.finished.append(track)
            else:alive.append(track)
        self.tracks=alive;matched=set()
        if self.tracks and candidates:
            cost=np.full((len(self.tracks),len(candidates)),1e6)
            for i,tr in enumerate(self.tracks):
                p=tr.points[-1];pred=np.array(p['pixel'],float)
                if len(tr.points)>=3:
                    q=tr.points[-3];dt=p['time_s']-q['time_s']
                    if dt>0:pred+=(pred-np.array(q['pixel']))/dt*(t-p['time_s'])
                for j,obs in enumerate(candidates):
                    distance=np.linalg.norm(pred-obs['pixel'])
                    if tr.colour==obs['colour'] and distance<c.association_px:cost[i,j]=distance
            ii,jj=linear_sum_assignment(cost)
            for i,j in zip(ii,jj):
                if cost[i,j]>=1e6:continue
                self.tracks[i].points.append(dict(candidates[j],time_s=float(t)));matched.add(j)
        for j,obs in enumerate(candidates):
            if j not in matched:
                self.tracks.append(Track(self.next_id,obs['colour'],[dict(obs,time_s=float(t))]));self.next_id+=1
        new=[]
        for tr in self.tracks:
            # A bounded history prevents long stationary observations creating a fake motion event.
            recent=[p for p in tr.points if t-p['time_s']<=4]
            if tr.emitted or len(recent)<c.min_observations:continue
            xy=np.array([p['pixel'] for p in recent]);tt=np.array([p['time_s'] for p in recent]);dy=xy[0,1]-xy[-1,1]
            if dy<c.min_span_px or not(xy[0,1]>c.gate_y+5 and xy[-1,1]<c.gate_y-5):continue
            vx,vy=np.polyfit(tt-tt[0],xy,1)[0];duration=tt[-1]-tt[0]
            if not(-c.max_speed_px_s<vy<-c.min_speed_px_s) or abs(vx)>abs(vy)*.8:continue
            monotonic=float(np.mean(np.diff(xy[:,1])<1))
            if monotonic<.85:continue
            cross=None
            for a,b in zip(recent,recent[1:]):
                if a['pixel'][1]>=c.gate_y>b['pixel'][1]:
                    alpha=(a['pixel'][1]-c.gate_y)/(a['pixel'][1]-b['pixel'][1]);cross=a['time_s']+alpha*(b['time_s']-a['time_s']);break
            if cross is None:continue
            tr.emitted=True
            # Deduplicate fragmented observations of the same crossing, not entire delivery cycles.
            if any(abs(e['crossing_time_s']-cross)<1.5 and e['colour']==tr.colour for e in self.events):continue
            e={'id':f'T{len(self.events)+1:02}','track_id':tr.id,'colour':tr.colour,'crossing_time_s':round(cross,3),'confirmed_at_s':round(t,3),'first_observed_s':tr.points[0]['time_s'],'evidence_kind':'outgoing_stone_passage','release_time_s':None,'gate_y_px':c.gate_y,'velocity_px_s':[float(vx),float(vy)],'observations_at_confirmation':len(recent),'direction_consistency':monotonic}
            self.events.append(e);new.append(e)
        return new
    def trajectories(self):
        return {tr.id:tr.points for tr in self.finished+self.tracks if tr.emitted}
