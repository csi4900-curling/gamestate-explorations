(() => {
  const d=MATCH_DATA,$=id=>document.getElementById(id),canvas=$('rink'),ctx=canvas.getContext('2d');
  const tee=34.747,houseRadius=1.829,halfWidth=2.375,hog=6.401;
  const videoRows=d.events.filter(e=>e.partial_boards.length);
  const experimental=EXPERIMENTAL_VIDEO_STATES;
  if(experimental.recording_code!==d.recording_code || experimental.source_video_sha256!==d.source_video_sha256 ||
     experimental.event_count!==d.events.length || experimental.rows.length!==d.events.length ||
     experimental.rows.some((row,i)=>row.event_id!==d.events[i].id)){
    throw new Error('La provenance ou l’ordre des événements vidéo expérimentaux ne correspond pas à la démo.');
  }
  let mode='official',view='house',index=0,timer=null;
  const rowsForMode=()=>mode==='official'?d.official_post_shot_states:mode==='video'?videoRows:experimental.rows;
  const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0);
  const norm=a=>{const l=Math.hypot(...a);return a.map(x=>x/l);};
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  function camera(){
    const position=view==='wide'?[0,-6,9]:[0,15,7];
    const target=view==='wide'?[0,20,0]:[0,35,0];
    const forward=norm(target.map((v,i)=>v-position[i]));
    const right=norm(cross(forward,[0,0,1]));
    const up=cross(right,forward);
    return {position,forward,right,up,focal:view==='wide'?540:2200};
  }
  function project(world,cam){
    const relative=world.map((v,i)=>v-cam.position[i]),depth=dot(relative,cam.forward);
    if(depth<=0.1)return null;
    return [canvas.width/2+cam.focal*dot(relative,cam.right)/depth,
            canvas.height/2-cam.focal*dot(relative,cam.up)/depth];
  }
  function polygon(points,fill,stroke,lineWidth=1){
    if(points.some(p=>!p))return;
    ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.closePath();
    if(fill){ctx.fillStyle=fill;ctx.fill();}
    if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke();}
  }
  function line(a,b,color,width=2){
    if(!a||!b)return;ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);
    ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();
  }
  function ring(cx,cy,r,color,cam){
    const points=[];
    for(let i=0;i<72;i++){const a=2*Math.PI*i/72;points.push(project([cx+r*Math.cos(a),cy+r*Math.sin(a),0.003],cam));}
    polygon(points,color,null);
  }
  function stone(x,y,colour,cam){
    const radius=0.145,z=0.12,top=[],bottom=[];
    for(let i=0;i<24;i++){
      const a=2*Math.PI*i/24,dx=radius*Math.cos(a),dy=radius*Math.sin(a);
      top.push(project([x+dx,y+dy,z],cam));bottom.push(project([x+dx,y+dy,0.025],cam));
    }
    if(top.some(p=>!p)||bottom.some(p=>!p))return;
    polygon([...bottom.slice(0,13),...top.slice(0,13).reverse()],'#87938e','#66756e',1);
    polygon(top,colour==='red'?'#bf5346':'#e0b427','#f8f5dc',1.5);
    const handle=project([x,y,z+0.07],cam),base=project([x,y,z],cam);
    line(handle,base,colour==='red'?'#8d302c':'#aa7d11',3);
  }
  function selectedRow(){return rowsForMode()[index];}
  function selectedStones(){
    if(mode==='official'){
      const state=selectedRow(),sign=state.diagram_delivery_side==='bottom'?-1:1;
      return state.stones.map(s=>({colour:s.colour,
        x:sign*s.position_house_radii[0]*houseRadius,
        y:tee+s.position_house_radii[1]*houseRadius}));
    }
    const stones=mode==='video'?selectedRow().partial_boards[0].observation.stones:selectedRow().stones;
    return stones.map(s=>({colour:s.colour,
      x:s.position_house_radii[0]*houseRadius,y:tee+s.position_house_radii[1]*houseRadius}));
  }
  function draw(){
    const cam=camera();ctx.clearRect(0,0,canvas.width,canvas.height);
    const sky=ctx.createLinearGradient(0,0,0,760);sky.addColorStop(0,'#b8d6e1');sky.addColorStop(1,'#eaf4f3');ctx.fillStyle=sky;ctx.fillRect(0,0,1200,760);
    polygon([[ -halfWidth,0,0],[halfWidth,0,0],[halfWidth,tee,0],[-halfWidth,tee,0]].map(p=>project(p,cam)),
      '#f8fcfb','#799ca6',2);
    for(const y of [0,tee]){
      ring(0,y,1.829,'#4b93c3',cam);ring(0,y,1.219,'#fff',cam);ring(0,y,.610,'#d9685e',cam);
    }
    line(project([0,0,.008],cam),project([0,tee,.008],cam),'#9db9bd',2);
    for(const y of [hog,tee-hog])line(project([-halfWidth,y,.01],cam),project([halfWidth,y,.01],cam),'#405eb4',3);
    line(project([-halfWidth,0,.01],cam),project([-halfWidth,tee,.01],cam),'#638c98',2);
    line(project([halfWidth,0,.01],cam),project([halfWidth,tee,.01],cam),'#638c98',2);
    for(const s of selectedStones().sort((a,b)=>b.y-a.y))stone(s.x,s.y,s.colour,cam);
    ctx.fillStyle='#173b38';ctx.font='bold 21px system-ui';
    ctx.fillText(mode==='official'?'Référence PDF · état après lancer':
      mode==='video'?'Observation vidéo · plateau partiel':'Vidéo expérimentale · observation partielle',28,42);
    ctx.font='15px system-ui';ctx.fillText('Positions discrètes · aucune trajectoire interpolée',28,69);
  }
  function setIndex(value){
    const rows=rowsForMode();
    index=Math.max(0,Math.min(rows.length-1,value));$('state').value=String(index);
    const row=selectedRow();
    if(mode==='official'){
      $('status').textContent=`Référence officielle : fin ${row.end}, lancer ${row.shot_number} · ${row.stones.length} pierres représentées. Rotation consignée : ${{clockwise:'horaire',counter_clockwise:'antihoraire'}[row.official_turn_direction]||'inconnue'} ; nombre de tours inconnu.`;
    }else if(mode==='video'){
      $('status').textContent=`Vidéo de la démo : ${row.id} · ${row.partial_boards[0].observation.stones.length} pierres observées. Plateau partiel ; état complet et échelle métrique inconnus.`;
    }else{
      const coverage=row.image_coverage;
      const colour={red:'rouge',yellow:'jaune'}[row.throw_colour]||'inconnue';
      const eventKind=row.event_evidence.tier==='visual_window_only_unconfirmed'?'fenêtre visuelle, lancer non confirmé':
        row.event_evidence.tier==='two_view_release_without_counter'?'passage et réception concordants, sans compteur':'compteur diffusé lié';
      const colourNote=row.throw_colour_provenance?.status==='source_two_view_colour_corrected'? ' · couleur corrigée par deux vues source':
        row.throw_colour_provenance?.status==='source_two_view_colour_filled'?' · couleur établie par deux vues source':'';
      $('status').textContent=row.stones.length?
        `Vidéo expérimentale : ${row.event_id} (${row.counter_id||'sans compteur'}) · ${eventKind} · couleur ${colour}${colourNote} · ${row.stones.length} pierre(s) observée(s) entre ${row.observation_interval_s[0].toFixed(1)} et ${row.observation_interval_s[1].toFixed(1)} s. Maison entière dans l’image : ${coverage.image_bound_house_envelope_seen?'oui':'non'} ; zone étendue : ${coverage.image_bound_extended_envelope_seen?'oui':'non'}. Présence en jeu, plateau complet et arrêt physique non vérifiés.`:
        `Vidéo expérimentale : ${row.event_id} (${row.counter_id||'sans compteur'}) · ${eventKind} · couleur ${colour}${colourNote} · aucun plateau stable observé. Aucune position de pierre n’est inférée pour cette proposition.`;
    }
    draw();
  }
  function setMode(value){
    mode=value;index=0;$('official-mode').classList.toggle('active',mode==='official');
    $('video-mode').classList.toggle('active',mode==='video');
    $('experimental-mode').classList.toggle('active',mode==='experimental');
    $('state').innerHTML=rowsForMode().map((row,i)=>
      `<option value="${i}">${mode==='official'?`Fin ${row.end} · lancer ${row.shot_number}`:mode==='video'?row.id:`${row.event_id} · ${row.stones.length?'plateau partiel':'aucun plateau'}`}</option>`).join('');
    setIndex(0);
  }
  $('official-mode').onclick=()=>setMode('official');$('video-mode').onclick=()=>setMode('video');
  $('experimental-mode').onclick=()=>setMode('experimental');
  $('wide-view').onclick=()=>{view='wide';$('wide-view').classList.add('active');$('house-view').classList.remove('active');draw();};
  $('house-view').onclick=()=>{view='house';$('house-view').classList.add('active');$('wide-view').classList.remove('active');draw();};
  $('state').onchange=e=>setIndex(Number(e.target.value));
  $('previous').onclick=()=>setIndex(index-1);$('next').onclick=()=>setIndex(index+1);
  $('autoplay').onclick=()=>{
    if(timer){clearInterval(timer);timer=null;$('autoplay').textContent='Défiler les états';return;}
    $('autoplay').textContent='Arrêter';
    timer=setInterval(()=>{
      const count=rowsForMode().length;
      setIndex((index+1)%count);
    },1300);
  };
  setMode('official');setIndex(111);
})();
