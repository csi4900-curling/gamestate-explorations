"""Conservative image-space association; missing tracks are never board observations."""
import math
class Tracker:
 def __init__(self):
  self.tracks={};self.serial=0
 def update(self,detections,t):
  self.tracks={k:v for k,v in self.tracks.items() if t-v['last']<=1.5}
  pairs=[]
  for i,d in enumerate(detections):
   for k,v in self.tracks.items():
    distance=math.dist(d['pixel_center'],v['point'])
    if d['colour']==v['colour'] and distance<=70:pairs.append((distance,i,k))
  assignments={};used=set()
  for _,i,k in sorted(pairs):
   if i not in assignments and k not in used:assignments[i]=k;used.add(k)
  output=[]
  for i,d in enumerate(detections):
   k=assignments.get(i)
   if k is None:
    self.serial+=1;k=self.serial
    self.tracks[k]={'colour':d['colour'],'history':[],'first':t}
   tr=self.tracks[k];tr.update(point=d['pixel_center'],last=t)
   tr['history']=[p for p in tr['history'] if t-p[0]<=3]+[(t,d['pixel_center'])]
   h=tr['history'];stable=len(h)>=5 and t-h[0][0]>=2 and max(math.dist(p,h[-1][1]) for _,p in h)<5
   output.append(dict(d,track_id=k,track_status='persistent' if len(h)>=3 else 'tentative',motion_status='visually_stable' if stable else 'moving_or_insufficient_history'))
  return output
