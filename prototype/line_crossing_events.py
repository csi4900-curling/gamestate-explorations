"""Configured finite-line crossings of observed stone detections.

Only event geometry is implemented here. Association belongs to upstream ByteTrack.
A crossing is a candidate delivery, not verified physical identity or game context.
"""
import math


def validate_config(config):
    allowed={'schema_version','sample_hz','detector_confidence','tracker_config','lines','source_sha256'}
    if set(config)-allowed:raise ValueError('Unknown line-event configuration fields')
    if config.get('schema_version')!='stone-line-events-v1':raise ValueError('Unsupported line-event schema')
    hz=config.get('sample_hz');confidence=config.get('detector_confidence')
    if not isinstance(hz,(float,int)) or isinstance(hz,bool) or not math.isfinite(hz) or hz<=0:raise ValueError('sample_hz must be positive')
    if not isinstance(confidence,(float,int)) or isinstance(confidence,bool) or not math.isfinite(confidence) or not 0<=confidence<=1:raise ValueError('Invalid detector confidence')
    if not config.get('tracker_config'):raise ValueError('An explicit upstream tracker configuration is required')
    lines=config.get('lines')
    if not isinstance(lines,list) or not lines:raise ValueError('Configure at least one line')
    ids=set()
    for line in lines:
        if set(line)-{'id','endpoints_normalized','direction','deadband_normalized'}:raise ValueError('Unknown line settings')
        if not isinstance(line.get('id'),str) or not line['id'] or line['id'] in ids:raise ValueError('Line IDs must be unique')
        ids.add(line['id'])
        points=line.get('endpoints_normalized')
        if not isinstance(points,list) or len(points)!=2 or any(not isinstance(p,list) or len(p)!=2 for p in points):raise ValueError('Each line requires two endpoints')
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=1 for p in points for x in p):raise ValueError('Endpoints must be normalized source coordinates in [0,1]')
        if points[0]==points[1]:raise ValueError('Line endpoints must differ')
        if line.get('direction') not in ('both','positive','negative'):raise ValueError('Invalid crossing direction')
        d=line.get('deadband_normalized',0)
        if isinstance(d,bool) or not isinstance(d,(int,float)) or not math.isfinite(d) or d<0:raise ValueError('Deadband must be finite and nonnegative')
    return config


class LineCrossings:
    def __init__(self,config):
        self.config=validate_config(config);self.previous={};self.emitted=set();self.events=[];self.last_time=None

    def update(self,observations,time_s):
        if self.last_time is not None and time_s<=self.last_time:raise ValueError('Observation times must increase')
        self.last_time=time_s
        ids=[o['track_id'] for o in observations]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate tracker ID in frame')
        active=set(ids)
        # Never infer a crossing across a model/detection visibility gap.
        self.previous={key:value for key,value in self.previous.items() if key[1] in active}
        new=[]
        for line in self.config['lines']:
            a,b=line['endpoints_normalized'];dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            for obs in observations:
                key=(line['id'],obs['track_id']);x,y=obs['point_normalized']
                distance=(dx*(y-a[1])-dy*(x-a[0]))/length
                if abs(distance)<=line.get('deadband_normalized',0):continue
                current={'time_s':time_s,'distance':distance,**obs}
                prev=self.previous.get(key);self.previous[key]=current
                if prev is None or key in self.emitted or prev['distance']*distance>=0:continue
                direction='positive' if distance>0 else 'negative'
                if line['direction'] not in ('both',direction):continue
                fraction=prev['distance']/(prev['distance']-distance)
                p=prev['point_normalized'];cross=[p[0]+fraction*(x-p[0]),p[1]+fraction*(y-p[1])]
                along=((cross[0]-a[0])*dx+(cross[1]-a[1])*dy)/(length*length)
                if not 0<=along<=1:continue
                self.emitted.add(key)
                event={'id':f'L{len(self.events)+1:05d}','line_id':line['id'],'track_id':obs['track_id'],
                       'crossing_time_s':prev['time_s']+fraction*(time_s-prev['time_s']),
                       'observed_bracket_s':[prev['time_s'],time_s],'confirmed_at_s':time_s,
                       'crossing_point_normalized':cross,'direction':direction,
                       'time_semantics':'linear_estimate_between_observed_stone_box_centres',
                       'release_time_s':None,'point_kind':'body_box_center','colour':None,
                       'physical_identity_verified':False,'status':'stone_line_crossing_candidate',
                       'observations':[prev,current]}
                self.events.append(event);new.append(event)
        return new
