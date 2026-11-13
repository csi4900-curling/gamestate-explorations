/* One connected nominal rink, projected by a physically consistent pinhole camera. */
window.CalibrationTemplate=(()=>{
 const defaults=panel=>({camera_x_m:0,distance_m:panel==='left'?15:60,height_m:panel==='left'?5:7,focal_px:panel==='left'?2000:5000,yaw_deg:0,pitch_deg:0,roll_deg:0});
 const norm=a=>Math.hypot(...a),unit=a=>a.map(x=>x/norm(a)),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
 const mul=(A,B)=>A.map(row=>B[0].map((_,j)=>row.reduce((s,x,k)=>s+x*B[k][j],0)));
 function fromRecord(record,panel){
  if(record.template_parameters)return {...record.template_parameters};
  const model=record.camera_model;if(!model)throw Error('This older mapping has no physical camera. Start a new template alignment to edit it.');
  const C=model.camera_centre_m,f=model.focal_native_px,cx=panel==='left'?480:1440,P=model.projection_xyz_up_to_normalized_source;
  const R=[P[0].slice(0,3).map((x,j)=>(3*x-cx*P[2][j])/f),P[1].slice(0,3).map((x,j)=>(3*x-540*P[2][j])/f),P[2].slice(0,3)];
  const forward=unit(C.map(x=>-x)),right=unit([C[1],-C[0],0]),base=[right,cross(right,forward),forward],Q=mul(R,base[0].map((_,i)=>base.map(row=>row[i])));
  return {camera_x_m:C[0],distance_m:C[1],height_m:C[2],focal_px:f,yaw_deg:Math.atan2(-Q[2][0],Q[2][2])*180/Math.PI,pitch_deg:Math.asin(Math.max(-1,Math.min(1,Q[2][1])))*180/Math.PI,roll_deg:Math.atan2(-Q[0][1],Q[1][1])*180/Math.PI};
 }
 function camera(p,panel){
  const C=[p.camera_x_m,p.distance_m,p.height_m],forward=unit(C.map(v=>-v)),right=unit([C[1],-C[0],0]);let R=[right,cross(right,forward),forward];
  for(const [axis,key] of [['y','yaw_deg'],['x','pitch_deg'],['z','roll_deg']]){const a=p[key]*Math.PI/180,c=Math.cos(a),s=Math.sin(a),Q=axis==='x'?[[1,0,0],[0,c,-s],[0,s,c]]:axis==='y'?[[c,0,s],[0,1,0],[-s,0,c]]:[[c,-s,0],[s,c,0],[0,0,1]];R=mul(Q,R)}
  return world=>{const q=R.map(row=>row.reduce((sum,x,i)=>sum+x*(world[i]-C[i]),0));if(q[2]<=.0001)return null;return [(p.focal_px*q[0]/q[2]+(panel==='left'?480:1440))/1920,(p.focal_px*q[1]/q[2]+540)/1080]};
 }
 function lines(p,panel){const project=camera(p,panel),result=[],sign=panel==='left'?-1:1;
  for(const r of [1.829,1.219,.610])result.push(Array.from({length:181},(_,i)=>{const a=i*2*Math.PI/180;return project([r*Math.cos(a),r*Math.sin(a),0])}));
  for(const [a,b] of [[[-3,0,0],[3,0,0]],[[0,-sign*2,0],[0,sign*14,0]],[[-3,sign*6.401,0],[3,sign*6.401,0]]])result.push(Array.from({length:101},(_,i)=>project(a.map((v,j)=>v+(b[j]-v)*i/100))));
  return result;
 }
 const bounds={camera_x_m:[-30,30],distance_m:[2,150],height_m:[.5,30],focal_px:[200,50000],yaw_deg:[-45,45],pitch_deg:[-45,45],roll_deg:[-60,60]};
 const clamp=p=>Object.fromEntries(Object.entries(p).map(([k,v])=>[k,Math.max(bounds[k][0],Math.min(bounds[k][1],v))]));
 const pixel=(p,panel,q)=>{const v=camera(p,panel)(q);return v&&[v[0]*1920,v[1]*1080]};
 const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
 function solvePair(initial,keys,target,evaluate){
  let p={...initial},best=p,value=evaluate(p),cost=value?distance(value,target):Infinity;
  if(!value)return p;
  for(let iteration=0;iteration<10&&cost>.02;iteration++){
   const columns=keys.map(key=>{const step=Math.max(1,Math.abs(p[key]))*.0001,q={...p,[key]:p[key]+step},v=evaluate(q);return v&&[(v[0]-value[0])/step,(v[1]-value[1])/step]});
   if(columns.some(c=>!c))break;
   const [[a,c],[b,d]]=columns,det=a*d-b*c;if(Math.abs(det)<1e-12)break;
   const x=target[0]-value[0],y=target[1]-value[1],delta=[(d*x-b*y)/det,(-c*x+a*y)/det];let improved=false;
   for(const fraction of [1,.5,.25,.125,.0625]){const q=clamp({...p,[keys[0]]:p[keys[0]]+delta[0]*fraction,[keys[1]]:p[keys[1]]+delta[1]*fraction}),v=evaluate(q),next=v?distance(v,target):Infinity;if(next<cost){p=q;best=q;value=v;cost=next;improved=true;break}}
   if(!improved)break;
  }
  return best;
 }
 function pinCentre(p,panel,target){return solvePair(p,['yaw_deg','pitch_deg'],target,q=>pixel(q,panel,[0,0,0]))}
 function width(p,panel){const a=pixel(p,panel,[-1.829,0,0]),b=pixel(p,panel,[1.829,0,0]);return a&&b?distance(a,b):null}
 function anchor(p,panel,centre,diameter){
  p=pinCentre(p,panel,centre);
  for(let i=0;i<4;i++){const w=width(p,panel);if(!w)break;p=clamp({...p,focal_px:p.focal_px*diameter/w});p=pinCentre(p,panel,centre)}
  return p;
 }
 function handles(p,panel){
  const sign=panel==='left'?-1:1,tee=pixel(p,panel,[0,0,0]);
  const definitions=[['move','Move',[0,0,0]],['size-left','Size',[-1.829,0,0]],['size-right','Size',[1.829,0,0]],['shape-play','Perspective',[0,sign*1.829,0]],['shape-back','Perspective',[0,-sign*1.829,0]],['far','Far line',[0,sign*6.401,0]]];
  const result=definitions.map(([id,label,world])=>({id,label,world,pixel:pixel(p,panel,world)})).filter(h=>h.pixel);
  if(tee){const ring=result.filter(h=>h.id.startsWith('shape')).map(h=>Math.abs(h.pixel[1]-tee[1])),length=Math.max(90,...ring)+65,angle=p.roll_deg*Math.PI/180;result.push({id:'rotate',label:'Rotate',pixel:[tee[0]+Math.sin(angle)*length,tee[1]-Math.cos(angle)*length]})}
  return result;
 }
 function edit(original,panel,id,target){
  if(id==='far')throw Error('Use the constrained hog-line edit endpoint; the house must be protected.');
  const centre=pixel(original,panel,[0,0,0]),sign=panel==='left'?-1:1;let p={...original};
  if(id==='move')p=pinCentre(p,panel,target);
  else if(id==='rotate'){
   const start=handles(original,panel).find(h=>h.id===id).pixel,a=Math.atan2(start[1]-centre[1],start[0]-centre[0]),b=Math.atan2(target[1]-centre[1],target[0]-centre[0]);
   const turn=Math.atan2(Math.sin(b-a),Math.cos(b-a));p=pinCentre(clamp({...p,roll_deg:p.roll_deg+turn*180/Math.PI}),panel,centre);
  }else if(id.startsWith('size')){
   const world=[id==='size-left'?-1.829:1.829,0,0],wanted=Math.max(5,distance(target,centre));
   for(let i=0;i<8;i++){const point=pixel(p,panel,world);if(!point)break;p=pinCentre(clamp({...p,focal_px:p.focal_px*wanted/distance(point,centre)}),panel,centre)}
  }else{
   const diameter=width(original,panel),world=id==='far'?[0,sign*6.401,0]:[0,(id==='shape-play'?sign:-sign)*1.829,0],keys=id==='far'?['distance_m','camera_x_m']:['height_m','camera_x_m'];
   const evaluate=q=>pixel(anchor(q,panel,centre,diameter),panel,world);
   p=anchor(solvePair(p,keys,target,evaluate),panel,centre,diameter);
  }
  const point=handles(p,panel).find(h=>h.id===id)?.pixel;
  return {parameters:p,pointer_error_px:point?distance(point,target):Infinity};
 }
 function visibleHandles(p,panel,hogTarget){return handles(p,panel).map(h=>h.id==='far'&&hogTarget?{...h,pixel:hogTarget}:h)}
 function draw(ctx,p,panel,opacity,nativePerCss=1,selected='move',hogTarget=null,hogPlacing=false){ctx.save();ctx.globalAlpha=opacity;ctx.strokeStyle='#00ffff';ctx.lineWidth=4;ctx.shadowColor='#12313b';ctx.shadowBlur=2;
  const markings=lines(p,panel),far=handles(p,panel).find(h=>h.id==='far')?.pixel;
  for(const [index,line] of markings.entries()){if(index===5&&hogTarget&&hogPlacing)continue;if(index===5&&hogTarget)ctx.setLineDash([7*nativePerCss,5*nativePerCss]);ctx.beginPath();let started=false;for(const point of line){if(!point){started=false;continue}const x=(point[0]-(panel==='right'?.5:0))*1920,y=point[1]*1080;if(Math.abs(x)>1e5||Math.abs(y)>1e5){started=false;continue}ctx[started?'lineTo':'moveTo'](x,y);started=true}ctx.stroke();ctx.setLineDash([])}
  if(hogTarget&&far){ctx.strokeStyle='#ffac45';ctx.beginPath();let started=false;for(const point of markings[5]){if(!point){started=false;continue}const x=point[0]*1920-(panel==='right'?960:0)+hogTarget[0]-far[0],y=point[1]*1080+hogTarget[1]-far[1];ctx[started?'lineTo':'moveTo'](x,y);started=true}ctx.stroke()}
  ctx.shadowBlur=0;ctx.globalAlpha=1;
  for(const handle of visibleHandles(p,panel,hogTarget)){
   const [x,y]=[handle.pixel[0]-(panel==='right'?960:0),handle.pixel[1]],radius=7*nativePerCss;
   ctx.fillStyle=handle.id==='move'?'#ffdc5c':handle.id==='far'&&hogTarget?'#ffac45':handle.id.startsWith('shape')||handle.id==='far'?'#ff8cda':'#ffffff';ctx.strokeStyle=handle.id===selected?'#f6bf23':'#153943';ctx.lineWidth=(handle.id===selected?3:2)*nativePerCss;ctx.beginPath();
   if(handle.id.startsWith('shape')||handle.id==='far'){ctx.moveTo(x,y-radius*1.4);ctx.lineTo(x+radius*1.4,y);ctx.lineTo(x,y+radius*1.4);ctx.lineTo(x-radius*1.4,y);ctx.closePath()}else ctx.arc(x,y,radius,0,Math.PI*2);
   ctx.fill();ctx.stroke();ctx.font=`600 ${12*nativePerCss}px system-ui`;ctx.lineWidth=3*nativePerCss;ctx.strokeStyle='#16323d';const label=handle.id==='far'&&hogTarget?'Hog placement':handle.label,labelX=Math.min(x+12*nativePerCss,960-ctx.measureText(label).width-6*nativePerCss),labelY=Math.max(16*nativePerCss,y-10*nativePerCss);ctx.strokeText(label,labelX,labelY);ctx.fillStyle='#ffffff';ctx.fillText(label,labelX,labelY);
  }ctx.restore();
 }
 return {defaults,camera,lines,draw,fromRecord,handles,visibleHandles,edit};
})();
