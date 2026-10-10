(() => {
  const d = MATCH_DATA;
  const $ = id => document.getElementById(id);
  const video = $('video');
  const events = d.events;
  const states = d.official_post_shot_states;
  const stateIndex = new Map(states.map((s,i)=>[s.official_shot_id,i]));
  let selected = 0, officialSelected = 0, visible = events.map((_,i)=>i);
  const fmt = seconds => seconds == null ? 'inconnu' :
    `${Math.floor(seconds/3600)}:${String(Math.floor(seconds%3600/60)).padStart(2,'0')}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;
  const range = values => values ? `${fmt(values[0])} – ${fmt(values[1])}` : 'non observé';
  const escape = value => String(value ?? '').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  $('event-count').textContent=d.provisional_event_count;
  $('release-count').textContent=d.unique_release_cue_count;
  $('cross-count').textContent=d.cross_view_colour_agreement_count;
  $('weak-count').textContent=d.event_evidence_tiers.visual_window_only_unconfirmed;
  $('board-count').textContent=d.partial_board_link_count;
  $('official-count').textContent=states.length;
  $('official-state').innerHTML=states.map((s,i)=>`<option value="${i}">Fin ${s.end} · lancer ${s.shot_number}</option>`).join('');

  function board(canvas, stones, label){
    const c=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
    c.clearRect(0,0,w,h);c.fillStyle='#edf5f1';c.fillRect(0,0,w,h);
    c.fillStyle='#fff';c.fillRect(18,18,w-36,h-36);
    const extent=Math.max(1.65,...stones.map(s=>Math.max(Math.abs(s.position_house_radii[0]),Math.abs(s.position_house_radii[1]))+0.15));
    const scale=Math.min(107,145/extent),cx=w/2,cy=h/2;
    for(const [r,color] of [[1,'#4f91bf'],[2/3,'#fff'],[1/3,'#d6655c']]){
      c.beginPath();c.arc(cx,cy,r*scale,0,Math.PI*2);c.fillStyle=color;c.fill();
    }
    c.strokeStyle='#809e98';c.lineWidth=1;c.beginPath();c.moveTo(cx,18);c.lineTo(cx,h-18);c.moveTo(18,cy);c.lineTo(w-18,cy);c.stroke();
    for(const stone of stones){
      const [x,y]=stone.position_house_radii;
      c.beginPath();c.arc(cx+x*scale,cy+y*scale,8,0,Math.PI*2);
      c.fillStyle=stone.colour==='red'?'#ba4d3b':'#dfb51d';c.fill();
      c.strokeStyle='#fff';c.lineWidth=2;c.stroke();
    }
    c.fillStyle='#345a52';c.font='12px system-ui';c.fillText(label,12,20);
    c.fillText(`${stones.length} pierre${stones.length===1?'':'s'} représentée${stones.length===1?'':'s'}`,12,h-13);
  }

  function showOfficial(index){
    officialSelected=Math.max(0,Math.min(states.length-1,index));
    const state=states[officialSelected];
    $('official-state').value=String(officialSelected);
    const lateralSign=state.diagram_delivery_side==='bottom'?-1:1;
    const canonicalStones=state.stones.map(s=>({...s,position_house_radii:[
      lateralSign*s.position_house_radii[0],s.position_house_radii[1]]}));
    board($('official-board'),canonicalStones,'Référence PDF · repère latéral normalisé');
    const link=events[selected].official_reference_link;
    const linked=link?.official_shot_id===state.official_shot_id;
    const turn={clockwise:'horaire',counter_clockwise:'antihoraire'}[state.official_turn_direction]||'non renseigné';
    $('official-status').textContent=`Fin ${state.end}, lancer ${state.shot_number} · ${state.stones.length} symboles PDF. Sens de rotation consigné : ${turn} ; nombre de tours inconnu. ${linked?'Lien par compteur diffusé, identité physique non vérifiée.':'État parcouru indépendamment ; aucun lien avec la proposition sélectionnée.'}${state.review_flags.length?' Drapeaux du PDF : '+state.review_flags.join(', ')+'.':''}`;
  }

  function renderList(){
    const query=$('search').value.trim().toLowerCase();
    visible=events.map((_,i)=>i).filter(i=>{
      const e=events[i];
      return !query || [e.id,e.counter_id,...e.camera_shots].some(x=>String(x||'').toLowerCase().includes(query));
    });
    $('list-count').textContent=`${visible.length} / ${events.length}`;
    $('event-list').innerHTML=visible.map(i=>{
      const e=events[i],klass=e.colour==='red'?'red':e.colour==='yellow'?'yellow':'';
      const tier=e.event_evidence.tier==='visual_window_only_unconfirmed'?' · lancer non confirmé':
        e.event_evidence.tier==='two_view_release_without_counter'?' · deux vues concordantes':'';
      return `<button class="event-item ${i===selected?'active':''}" data-i="${i}"><strong><span class="dot ${klass}"></span>${escape(e.id)} · ${escape(e.counter_id||'sans compteur')}</strong><small>${escape(range(e.delivery_window_s))}${tier}${e.release_cue.time_s!=null?' · indice de départ':''}${e.partial_boards.length?' · plateau vidéo':''}</small></button>`;
    }).join('');
    $('event-list').querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>selectEvent(Number(button.dataset.i))));
  }

  function selectEvent(index){
    selected=Math.max(0,Math.min(events.length-1,index));
    const e=events[selected];
    $('event-title').textContent=`${e.id} · ${{red:'rouge',yellow:'jaune'}[e.colour]||'couleur inconnue'}`;
    $('event-time').textContent=range(e.review_window_s);
    $('review-window').textContent=range(e.review_window_s);
    $('evidence-tier').textContent={
      counter_backed_provisional:'Compteur diffusé lié ; identité et limites physiques encore provisoires.',
      two_view_release_without_counter:'Sans compteur : passage unique et couleur concordante en réception ; identité physique non vérifiée.',
      visual_window_only_unconfirmed:'Fenêtre visuelle seule ; lancer non confirmé.'
    }[e.event_evidence.tier];
    $('release-cue').textContent=e.release_cue.time_s==null?'Aucun indice unique':`${fmt(e.release_cue.time_s)} · ${e.release_cue.status.replaceAll('_',' ')}`;
    $('receiving').textContent=e.receiving_view.status.replaceAll('_',' ') +
      (e.receiving_view.motion_interval_s?' · '+range(e.receiving_view.motion_interval_s):'');
    const probe=e.counterless_motion_probe;
    $('motion-probe').textContent=!probe?'Sondage ciblé non effectué pour cette proposition.':
      probe.status==='no_supported_track_in_probe'?'Aucune piste de capuchon soutenue dans le sondage ; cela ne prouve pas l’absence de lancer.':
      probe.tracks.map(track=>`${track.colour==='red'?'rouge':'jaune'} ${fmt(track.first_seen_s)}–${fmt(track.last_seen_s)} (${track.span_px.toFixed(0)} px)`).join(' ; ')+
      '. Attribution au lancer non vérifiée.';
    $('camera-evidence').textContent=e.camera_shots.join(', ') +
      (e.possible_edit_times_s.length?' · coupure possible '+e.possible_edit_times_s.map(fmt).join(', '):'');
    $('spin').textContent=e.spin_observation.status==='unmeasured'?'Non mesurée : poignée à suivre dans les images':'Mesure disponible';
    video.pause();
    const seek=()=>{video.currentTime=e.review_window_s[0];};
    if(video.readyState>=1)seek();else video.addEventListener('loadedmetadata',seek,{once:true});
    if(e.official_reference_link)showOfficial(stateIndex.get(e.official_reference_link.official_shot_id));
    else showOfficial(officialSelected);
    if(e.partial_boards.length){
      const obs=e.partial_boards[0].observation;
      board($('video-board'),obs.stones,'Vidéo · coordonnées locales non métriques');
      $('video-board-status').textContent=`${range(obs.observation_interval_s)} · ${obs.stones.length} pierre(s) observée(s), complétude inconnue. Lien par compteur, pas identité de pierre vérifiée.`;
    }else{
      board($('video-board'),[],'Aucun plateau vidéo lié');
      $('video-board-status').textContent='Pas de plateau vidéo stable lié à cette proposition.';
    }
    renderList();drawTimeline();
  }

  function drawTimeline(){
    const canvas=$('timeline'),c=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
    c.clearRect(0,0,w,h);c.fillStyle='#f7faf7';c.fillRect(0,0,w,h);
    const start=d.source_interval_s[0],end=d.source_interval_s[1],left=42,right=w-25;
    const x=t=>left+(t-start)/(end-start)*(right-left);
    c.strokeStyle='#b8ccc3';c.lineWidth=2;c.beginPath();c.moveTo(left,76);c.lineTo(right,76);c.stroke();
    for(let t=0;t<=end;t+=1800){const px=x(t);c.strokeStyle='#b8ccc3';c.beginPath();c.moveTo(px,71);c.lineTo(px,82);c.stroke();c.fillStyle='#526b63';c.font='12px system-ui';c.fillText(fmt(t),px-13,100);}
    events.forEach((e,i)=>{
      const t=(e.evidence_core_s[0]+e.evidence_core_s[1])/2,px=x(t);
      c.strokeStyle=i===selected?'#302b61':e.event_evidence.tier==='visual_window_only_unconfirmed'?'#9ca3a3':
        e.partial_boards.length?'#72469e':e.release_cue.time_s!=null?'#08766e':'#c68925';
      c.lineWidth=i===selected?5:2;c.beginPath();c.moveTo(px,i===selected?15:32);c.lineTo(px,71);c.stroke();
    });
    const e=events[selected],px=x((e.evidence_core_s[0]+e.evidence_core_s[1])/2);
    c.fillStyle='#302b61';c.font='bold 13px system-ui';c.fillText(e.counter_id||e.id,Math.max(4,Math.min(px-20,w-90)),13);
  }

  $('timeline').addEventListener('click',event=>{
    const rect=event.currentTarget.getBoundingClientRect();
    const x=(event.clientX-rect.left)/rect.width*event.currentTarget.width;
    let best=0,distance=Infinity;
    events.forEach((e,i)=>{
      const t=(e.evidence_core_s[0]+e.evidence_core_s[1])/2;
      const px=42+(t-d.source_interval_s[0])/(d.source_interval_s[1]-d.source_interval_s[0])*(event.currentTarget.width-67);
      if(Math.abs(px-x)<distance){distance=Math.abs(px-x);best=i;}
    });selectEvent(best);
  });
  $('search').addEventListener('input',renderList);
  $('previous').onclick=()=>selectEvent(selected-1);
  $('next').onclick=()=>selectEvent(selected+1);
  $('play-window').onclick=()=>{video.currentTime=events[selected].review_window_s[0];video.play();};
  video.addEventListener('timeupdate',()=>{if($('stop-window').checked&&!video.paused&&video.currentTime>=events[selected].review_window_s[1])video.pause();});
  $('official-state').onchange=event=>showOfficial(Number(event.target.value));
  $('official-previous').onclick=()=>showOfficial(officialSelected-1);
  $('official-next').onclick=()=>showOfficial(officialSelected+1);
  selectEvent(0);
})();
