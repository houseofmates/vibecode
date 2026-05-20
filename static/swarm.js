// ── swarm.js — swarm panel for vibecode ────────────────────────────────────
// handles: toggleSwarmPanel, list view, detail view, coordination chat,
// agent sessions, starting new swarms, SSE polling. all text lowercase.

const SwarmApp=(function(){
 // ── state ───────────────────────────────────────────────────────────────────
 let swarms={};           // id -> swarm data
 let currentView='list';  // list | detail | new
 let currentSwarmId=null;
 let pollTimer=null;
 let sseConnected=false; // track SSE connection state
 let pollInterval=3000;   // 3s for live updates

 const COLORS=['#e94560','#ff6b35','#f6b012','#4ade80','#22d3ee','#6cb4ff','#a78bfa','#f472b6'];

 // ── init ─────────────────────────────────────────────────────────────────────
 function init(){
 // overlay removed — using panelSwarm sidebar
 // wire up panel buttons



   const _on=function(id,evt,fn){const el=$(id);if(el)el.addEventListener(evt,fn);};
   _on('btnCloseSwarmPanel','click',closePanel);
   _on('btnSwarmNew','click',showNewForm);
   _on('swarmBackBtn','click',showListView);
   _on('btnSwarmNewBack','click',showListView);
   _on('btnSwarmLaunch','click',launchSwarm);
   wireSwarmPanel();

   // Chat input
   const chatInput=$('swarmChatMsg');
   if(chatInput){
    chatInput.addEventListener('keydown',e=>{
     if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendChatMsg();}
    });
   }
   _on('btnSwarmChatSend','click',sendChatMsg);

   // Agent count buttons
   document.querySelectorAll('.sac-btn').forEach(btn=>{
    btn.addEventListener('click',()=>{
     document.querySelectorAll('.sac-btn').forEach(b=>b.classList.remove('active'));
     btn.classList.add('active');
    });
   });

   // Textarea auto-resize
   const ta=$('swarmChatMsg');
   if(ta){
    ta.addEventListener('input',()=>{ta.style.height='auto';ta.style.height=ta.scrollHeight+'px';});
   }

  // SSE subscription — listen for swarm events (primary transport)
  subscribeSSE();
  // Poll as fallback (SSE can miss on reconnect)
  startPoll();
  refresh();
  // Load templates for new form
  loadTemplates();
 }

 // ── panel open/close ────────────────────────────────────────────────────────
 function openPanel(){
  switchPanel('swarm');
  if(window._swarmList) refresh();
  startSSE();
 }

 function closePanel(){
  const panel=$('panelSwarm');
  if(panel) panel.classList.remove('active');
  const navBtn=document.getElementById('navSwarm');
  if(navBtn) navBtn.classList.remove('active');
  currentView='list';
  currentSwarmId=null;
  stopPoll(); stopContextPoll();
 }

 window.toggleSwarmPanel=function(){
  const panel=$('panelSwarm');
  if(panel && panel.classList.contains('active')) closePanel();
  else openPanel();
 };


 // ── view management ─────────────────────────────────────────────────────────
 function showListView(){
  stopContextPoll();
  currentView='list';
  currentSwarmId=null;
  try{
   const lv=$('swarmListView');if(lv) lv.style.display='block';
   const dv=$('swarmDetailView');if(dv) dv.style.display='none';
   const nv=$('swarmNewView');if(nv) nv.style.display='none';
   renderSwarmList();
  }catch(err){
   console.error('showListView error',err);
  }
 }

 function showDetail(swarmId){
  currentView='detail';
  currentSwarmId=swarmId;
  $('swarmListView').style.display='none';
  $('swarmDetailView').style.display='block';
  $('swarmNewView').style.display='none';
  renderSwarmDetail(swarmId);
  startCoordChatPoll(swarmId);
 }

 async function openOrchestrationChat(){
  if(typeof window.newSession !== 'function') return;
  try{
   const session=await window.newSession(false);
   if(session&&session.session_id){
    await api('/api/session/rename',{method:'POST',body:JSON.stringify({session_id:session.session_id,title:'orchestration'})});
    if(typeof renderSessionList==='function') renderSessionList();
    showToast('orchestration chat created',2800);
   }
  }catch(err){
   console.error('orchestration chat creation failed', err);
   showToast('failed to create orchestration chat',3000);
  }
 }

 function showNewForm(){
  currentView='new';
  $('swarmListView').style.display='none';
  $('swarmDetailView').style.display='none';
  $('swarmNewView').style.display='block';
  $('swarmNewTask').value='';
  $('swarmNewTask').focus();
 }

 // ── tab management ───────────────────────────────────────────────────────────
 function showTab(tabName){
  document.querySelectorAll('.sdt').forEach(t=>t.classList.toggle('active',t.dataset.tab===tabName));
  document.querySelectorAll('.swarm-tab-pane').forEach(p=>p.classList.toggle('active',p.id==='swarmTab'+capitalize(tabName)));
 }

 function capitalize(s){return s?s[0].toUpperCase()+s.slice(1):'';}

 // ── render list view ──────────────────────────────────────────────────────────
 function renderSwarmList(){
  const cards=$('swarmCards');
  const empty=$('swarmEmpty');
  const list=Object.values(swarms);
  list.sort((a,b)=>b.created_at-a.created_at);

  if(!list.length){
   cards.innerHTML='';
   empty.style.display='block';
   return;
  }
  empty.style.display='none';

  cards.innerHTML=list.map(s=>renderSwarmCard(s)).join('');

  // Bind card clicks
  cards.querySelectorAll('.swarm-card').forEach(card=>{
   card.addEventListener('click',()=>{
    const sid=card.dataset.swarm;
    showDetail(sid);
   });
  });

  // Bind cancel buttons
  cards.querySelectorAll('.swarm-cancel-btn').forEach(btn=>{
   btn.addEventListener('click',e=>{
    e.stopPropagation();
    cancelSwarm(btn.dataset.id);
   });
  });
 }

 function renderSwarmCard(s){
  const color=s.color||COLORS[Object.keys(swarms).indexOf(s.id)%COLORS.length];
  const statusMap={running:'running',completed:'done',cancelled:'cancelled',failed:'failed'};
  const status=s.status||'running';
  const lastMsg=s.last_coord_message;
  const workerCount=s.workers?s.workers.length:0;
  const runningCount=s.workers?s.workers.filter(w=>w.status==='running'||w.status==='pending').length:0;

  return `<div class="swarm-card" data-swarm="${s.id}" style="border-left:3px solid ${color}">
   <div class="sc-head">
    <div class="sc-color-dot" style="background:${color}"></div>
    <div class="sc-info">
     <div class="sc-task">${esc(s.task||'untitled')}</div>
     <div class="sc-meta">${workerCount} agents · ${runningCount} running${s.created_at?'<span class="sc-elapsed">'+((Date.now()/1000-s.created_at)>60?Math.floor((Date.now()/1000-s.created_at)/60)+"m":Math.floor(Date.now()/1000-s.created_at)+"s")+'</span>':''}</div>
    ${lastMsg&&lastMsg.content?'<div class="sc-last">'+esc(lastMsg.worker_name)+': '+esc(lastMsg.content)+'</div>':''}
    </div>
    <div class="sc-right">
     <span class="sc-status sc-status-${status}" style="color:${statusColor(status)}">${statusMap[status]||status}</span>
     ${status==='running'||status==='pending'
      ?`<button class="sc-cancel swarm-cancel-btn" data-id="${s.id}">×</button>`
      :''}
    </div>
   </div>
  </div>`;
 }

 function statusColor(s){
  if(s==='running'||s==='pending')return'var(--gold,#d4a74a)';
  if(s==='completed')return'var(--green,#4ade80)';
  if(s==='cancelled')return'var(--muted,#888)';
  if(s==='failed')return'var(--accent,#e94560)';
  return'var(--muted,#888)';
 }

 // ── render detail view ────────────────────────────────────────────────────────
 function renderSwarmDetail(swarmId){
  const s=swarms[swarmId];
  if(!s)return;

  // Header
  const workerCount=s.workers?s.workers.length:0;
  const running=s.workers?s.workers.filter(w=>w.status==='running'||w.status==='pending').length:0;
  const done=s.workers?s.workers.filter(w=>w.status==='done').length:0;
  $('swarmDetailHeader').innerHTML=`
   <div class="sd-task">${esc(s.task||'untitled')}</div>
   <div class="sd-meta">${workerCount} agents · ${running} active · ${done} done · ${s.model||'default'}
    ${(s.status==='completed'||s.status==='cancelled')?' <button class="btnInject" onclick="SwarmApp.injectResults(\''+swarmId+'\')">inject into chat</button>':''}
   </div>
  `;

  // Agents list
  if(s.workers){
   const agentList=$('swarmAgentsList');
   agentList.innerHTML=s.workers.map((w,i)=>{
    const color=w.color||COLORS[i%COLORS.length];
    const status=w.status||'pending';
    const icon=getStatusIcon(status);
    return `<div class="agent-card" data-worker="${w.worker_id}" onclick="SwarmApp.openWorkerSession('${swarmId}','${w.worker_id}')">
     <div class="ac-color" style="background:${color}"></div>
     <div class="ac-info">
      <div class="ac-name" style="color:${color}">${w.worker_name||w.worker_id?.slice(0,8)}</div>
      <div class="ac-task">${esc(w.task||'')}</div>
      <div class="ac-status ac-status-${status}">${icon} ${status}${w.duration?sprintf(' · %.1fs',w.duration):''}</div>
     </div>
     <div class="ac-actions">
      ${w.result&&status==='done'?'<button class="ac-result-btn" data-worker="'+w.worker_id+'" onclick="event.stopPropagation();SwarmApp.showWorkerResult(\''+swarmId+'\',\''+w.worker_id+'\')">view result</button>':''}
      ${(w.status==='running'||w.status==='pending')?'<button class="ac-kill-btn" data-worker="'+w.worker_id+'" onclick="event.stopPropagation();SwarmApp.killWorker(\''+swarmId+'\',\''+w.worker_id+'\')">✕ kill</button>':''}
      ${w.status==='error'?'<div class="ac-error">'+esc((w.result||'').slice(0,80))+'</div>':''}
     </div>
    </div>`;
   }).join('');

   // Show aggregate if completed
   if((s.status==='completed'||s.status==='cancelled')&&s.workers.length>1){
    const aggDiv=document.createElement('div');
    aggDiv.className='swarm-aggregate';
    aggDiv.innerHTML='<button class="btnAggregate" onclick="SwarmApp.loadAggregate(\''+swarmId+'\')"><svg class="swarm-icon" width="14" height="11" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg> view aggregate results</button>';
    agentList.appendChild(aggDiv);
   }
  }

  // Reset to coordination tab
  showTab('coord');
 }

 // ── coordination chat ───────────────────────────────────────────────────────
 let coordMsgs=[];
 let coordPollTimer=null;

 function startCoordChatPoll(swarmId){
  stopCoordChatPoll();
  function poll(){
   loadCoordMsgs(swarmId,(msgs)=>{
    coordMsgs=msgs||[];
    renderCoordChat(swarmId);
   });
   coordPollTimer=setTimeout(poll,pollInterval);
  }
  loadCoordMsgs(swarmId,(msgs)=>{
   coordMsgs=msgs||[];
   renderCoordChat(swarmId);
  });
  coordPollTimer=setTimeout(poll,pollInterval);
 }

 function stopCoordChatPoll(){
  if(coordPollTimer){clearTimeout(coordPollTimer);coordPollTimer=null;}
 }

 function renderCoordChat(swarmId){
  const chat=$('swarmCoordChat');
  if(!chat)return;
  const s=swarms[swarmId];

  if(!coordMsgs.length){
   chat.innerHTML='<div class="coord-placeholder">workers will post updates here as they work...</div>';
  }else{
  chat.innerHTML=coordMsgs.map(m=>{
   const color=m.worker_name&&s&&s.workers
    ?(s.workers.find(w=>w.worker_name===m.worker_name)||{}).color||'var(--blue)'
    :'var(--blue)';
   const typeClass=m.type==='system'?'coord-system':m.type==='error'?'coord-error':'coord-msg';
   const ts=m.timestamp?formatTs(m.timestamp):'';

   return `<div class="coord-msg ${typeClass}">
    ${m.worker_name&&m.role!=='system'?'<span class="cm-name" style="color:${color}">'+esc(m.worker_name)+'</span>':''}
    <span class="cm-content">${formatContent(m.content)}</span>
    <span class="cm-time">${ts}</span>
   </div>`;
  }).join('');
  }

  // Auto-scroll to bottom only if user is already near bottom
  const nearBottom=chat.scrollHeight-chat.scrollTop-chat.clientHeight<150;
  if(nearBottom)chat.scrollTop=chat.scrollHeight;
 }

 function formatContent(content){
  if(!content)return'';
  // Handle newlines
  let formatted=esc(content).replace(/\n/g,'<br>');
  // Highlight ✓ done
  formatted=formatted.replace(/✓\s*DONE/g,'<span class="coord-done">✓ DONE</span>');
  formatted=formatted.replace(/✓/g,'<span class="coord-check">✓</span>');
  formatted=formatted.replace(/✗/g,'<span class="coord-x">✗</span>');
  formatted=formatted.replace(/👋/g,'<span class="coord-hi">👋</span>');
  formatted=formatted.replace(/❌/g,'<span class="coord-cancel">❌</span>');
 formatted=formatted.split('<svg class="swarm-icon" width="14" height="11" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg>').join('<span class="coord-swarm"><svg class="swarm-icon" width="14" height="11" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg></span>');
  return formatted;
 }

 function sendChatMsg(){
  const input=$('swarmChatMsg');
  if(!input||!input.value.trim()||!currentSwarmId)return;
  const content=input.value.trim();
  input.value='';
  input.style.height='auto';

  fetch('/api/swarm/'+currentSwarmId+'/messages',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({content}),
  }).then(r=>r.json()).then(()=>{
   loadCoordMsgs(currentSwarmId,(msgs)=>{
    coordMsgs=msgs||[];
    renderCoordChat(currentSwarmId);
   });
  }).catch(e=>console.error('swarm chat error:',e));
 }

 // ── worker result viewer ───────────────────────────────────────────────────
 if(!window.SwarmApp) window.SwarmApp={};
 window.SwarmApp.showWorkerResult=function(swarmId,workerId){
  const s=swarms[swarmId];
  if(!s||!s.workers)return;
  const w=s.workers.find(w=>w.worker_id===workerId);
  if(!w||!w.result)return;

  const overlay=document.createElement('div');
  overlay.className='swarm-result-overlay';
  overlay.innerHTML=`
   <div class="sro-backdrop" onclick="this.parentElement.remove()"></div>
   <div class="sro-box">
    <div class="sro-header">
     <span>${esc(w.worker_name||workerId.slice(0,8))} · ${esc(w.task||'')}</span>
     <button class="sro-close" onclick="this.closest('.swarm-result-overlay').remove()">×</button>
    </div>
    <pre class="sro-content">${esc(w.result)}</pre>
   </div>
  `;
  document.body.appendChild(overlay);
 };

 // ── API calls ───────────────────────────────────────────────────────────────
 function swarmApi(path, opts={}){
  if(typeof window.api === 'function') return window.api(path, opts);
  return fetch(path, {credentials:'include', ...opts}).then(async res => {
   const text = await res.text();
   if(!res.ok) throw new Error(text || ('HTTP ' + res.status));
   return text ? JSON.parse(text) : {};
  });
 }

 function loadCoordMsgs(swarmId,cb){
  // Use the latest timestamp seen (or 0 for initial load)
  let after=0;
  if(coordMsgs.length){
   const timestamps=coordMsgs.map(m=>m.timestamp||0).filter(t=>t>0);
   after=timestamps.length?Math.max(...timestamps):0;
  }
  swarmApi('/api/swarm/'+swarmId+'/messages?after='+after)
   .then(d=>{
    const newMsgs=d.messages||[];
    // Merge: keep existing, append new ones (dedup by content+timestamp)
    const existingKeys=new Set(coordMsgs.map(m=>m.timestamp+':'+m.content.slice(0,30)));
    const uniqueNew=newMsgs.filter(m=>!existingKeys.has((m.timestamp||0)+':'+(m.content||'').slice(0,30)));
    cb([...coordMsgs,...uniqueNew]);
   })
   .catch(()=>cb(coordMsgs));
 }

 function refresh(){
  swarmApi('/api/swarm/list')
   .then(d=>{
    const list=d.swarms||[];
    list.forEach(s=>{
     // Preserve last coord message state
     const prev=swarms[s.id];
     swarms[s.id]={...prev,...s,last_coord_message:prev&&prev.last_coord_message||s.last_coord_message};
    });
    // Remove stale
    const ids=new Set(list.map(s=>s.id));
    Object.keys(swarms).forEach(k=>{if(!ids.has(k))delete swarms[k];});
    renderSwarmList();
    if(currentSwarmId&&swarms[currentSwarmId])renderSwarmDetail(currentSwarmId);
   }).catch(e=>console.error('swarm refresh error:', e && e.message ? e.message : e));
 }

 function cancelSwarm(id){
  swarmApi('/api/swarm/cancel',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({id:id}),
  }).then(()=>refresh()).catch(()=>refresh());
 }

 async function launchSwarm(){
  const task=$('swarmNewTask').value.trim();
  if(!task){$('swarmNewTask').focus();return;}

  const agentCount=parseInt(document.querySelector('.sac-btn.active')?.dataset?.count||'3');
  const model=$('swarmNewModel').value;

  const activeCountEl=$('swarmPanelSubtitle');
  if(activeCountEl)activeCountEl.textContent='launching...';

  // Get current session or create one if missing
  let sessionId=(window.S&&window.S.session&&window.S.session.session_id)||'';
  if(!sessionId && typeof window.newSession === 'function'){
   try{
    const s = await window.newSession(false);
    sessionId = s?.session_id || sessionId;
   }catch(err){ console.warn('failed to create orchestration session:', err); }
  }

  // Generate subtasks based on agent count
  const subtasks=[];
  const agentRoles=['primary','secondary','tertiary','quaternary','quinary','senary','septenary','octonary'];
  for(let i=0;i<agentCount;i++){
   subtasks.push({
    task:`${agentRoles[i]||'agent'} task ${i+1}: work on the swarm goal`,
    context:`You are agent ${i+1} (${agentRoles[i]||'agent'}) in this swarm. Take initiative and collaborate.`,
   });
  }

  swarmApi('/api/swarm/start',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({session_id:sessionId,task,subtasks,model}),
  }).then(data=>{
   if(data.error){alert('swarm error: '+data.error);return;}
   if(activeCountEl)activeCountEl.textContent='';
   showListView();
   refresh();
  }).catch(e=>{
   alert('swarm launch failed: '+e);
   if(activeCountEl)activeCountEl.textContent='';
  });
 }

 // ── SSE ──────────────────────────────────────────────────────────────────────
 function subscribeSSE(){
  const es=window._multiplexES||window._eventSource;
  if(!es){
   // SSE not available yet, retry once in 2s
   if(!_sseRetried){_sseRetried=true;setTimeout(()=>{_sseRetried=false;subscribeSSE();},2000);}
   return;
  }
  const events=['swarm.started','swarm.worker_started','swarm.worker_completed','swarm.worker_error',
                'swarm.completed','swarm.cancelled','swarm.worker_cancelled','swarm.stream_chunk'];
  events.forEach(ev=>{
   es.addEventListener(ev,e=>{
    try{const d=JSON.parse(e.data);onSwarmEvent(e.type,d);}catch(err){}
   });
  });
  // Track SSE disconnection — fall back to polling
 if(es.readyState===EventSource.CLOSED||es.readyState===EventSource.CONNECTING){
 sseConnected=false;
 if(!pollTimer&&document.getElementById('panelSwarm')?.classList.contains('active')){startPoll();}
 }
 es.addEventListener('error',()=>{
 sseConnected=false;
 if(!pollTimer){startPoll();}
 });
 }
 let _sseRetried=false;

 function onSwarmEvent(type,data){
  // For stream chunks, update coord chat immediately without full refresh
  if(type==='swarm.stream_chunk'&&data.text&&currentSwarmId&&currentView==='detail'){
   const sid=data.swarm_id||currentSwarmId;
   if(sid===currentSwarmId){
    // Append chunk to coord in real-time
    const chat=$('swarmCoordChat');
    if(chat&&coordMsgs.length){
     const lastIdx=coordMsgs.length-1;
     const last=coordMsgs[lastIdx];
     // Stream chunks come fast — aggregate them into the thinking message
     if(last&&last.type==='stream'&&last.worker_id===data.worker_id){
      last.content+=data.text;
      // Update last message in DOM
      const lastEl=chat.lastElementChild;
      if(lastEl&&lastEl.querySelector('.cm-content')){
       lastEl.querySelector('.cm-content').innerHTML=formatContent(last.content);
      }
     }
    }
    chat.scrollTop=chat.scrollHeight;
    return; // Don't do full refresh for every chunk
   }
  }
  refresh();
  // If this is the currently viewed swarm, reload coord chat
  if(currentSwarmId&&currentView==='detail'){
   loadCoordMsgs(currentSwarmId,(msgs)=>{
    coordMsgs=msgs||[];
    renderCoordChat(currentSwarmId);
   });
  }
 }

 // ── polling ──────────────────────────────────────────────────────────────────
 function startPoll(){
 if(sseConnected)return; // SSE is active, no need to poll
 stopPoll(); stopContextPoll();pollTimer=setInterval(refresh,pollInterval);
 }
 function stopPoll(){if(pollTimer){clearInterval(pollTimer);pollTimer=null;}}

 // ── helpers ─────────────────────────────────────────────────────────────────
 function esc(s){
  if(!s)return'';
  const d=document.createElement('div');d.textContent=s;return d.innerHTML;
 }
 function sprintf(fmt,...args){
  let i=0;
  return fmt.replace(/%[sdif]/g,()=>args[i++]??'');
 }


 function formatTs(ts){
  if(!ts)return'';
  const d=new Date(ts*1000);
  return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
 }

 function getStatusIcon(status){
  if(status==='done')return'✓';
  if(status==='error')return'✗';
  if(status==='cancelled')return'∅';
  if(status==='running'||status==='pending')return'◉';
  return'○';
 }


 // ── kill worker ────────────────────────────────────────────────────────────
 window.SwarmApp.killWorker=function(swarmId,workerId){
  if(!confirm('kill this worker?'))return;
  swarmApi('/api/swarm/'+swarmId+'/workers/'+workerId+'/kill',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:'{}',
  }).then(()=>refresh()).catch(e=>{console.error('kill worker err:',e);refresh();});
 };

 // ── inject results into parent session ─────────────────────────────────────
 window.SwarmApp.injectResults=function(swarmId){
  swarmApi('/api/swarm/'+swarmId+'/inject',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})
   .then(d=>{if(d.injected)alert('results injected into chat');})
   .catch(e=>alert('inject failed: '+e));
 };

 // ── aggregate results viewer ───────────────────────────────────────────────
 window.SwarmApp.loadAggregate=function(swarmId){
  swarmApi('/api/swarm/'+swarmId+'/aggregate')
   .then(d=>{
    if(d.error){alert(d.error);return;}
    showAggregateOverlay(swarmId,d);
   }).catch(e=>alert('aggregate error: '+e));
 };

 function showAggregateOverlay(swarmId,agg){
  const overlay=document.createElement('div');
  overlay.className='swarm-agg-overlay';
  let html=`
   <div class="sao-backdrop" onclick="this.parentElement.remove()"></div>
   <div class="sao-box">
    <div class="sao-header">
     <span><svg class="swarm-icon" width="14" height="11" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg> aggregate results: ${esc(agg.task||'')}</span>
     <button class="sao-close" onclick="this.closest('.swarm-agg-overlay').remove()">×</button>
    </div>
    <div class="sao-summary">
     done: ${agg.done} · failed: ${agg.failed} · cancelled: ${agg.cancelled} · total: ${agg.total}
    </div>`;

  if(agg.patterns&&Object.keys(agg.patterns).length){
   html+='<div class="sao-patterns">patterns: ';
   for(const [k,v] of Object.entries(agg.patterns)){
    html+=`<span class="sao-pattern">${k}: ${v}</span>`;
   }
   html+='</div>';
  }

  for(const r of (agg.results||[])){
   const icon=r.result?'✓':'✗';
   html+=`
    <div class="sao-result">
     <div class="sao-result-head"><span class="sao-result-icon">${icon}</span> ${esc(r.worker_name)} · ${esc(r.task||'')}${r.duration?` · ${r.duration}s`:''}</div>
     <pre class="sao-result-body">${esc(r.result||'(no output)')}</pre>
    </div>`;
  }

  html+='</div></div>';
  overlay.innerHTML=html;
  document.body.appendChild(overlay);
 }

 // ── templates ──────────────────────────────────────────────────────────────
 let _templates=[];

 function loadTemplates(){
  swarmApi('/api/swarm/templates')
   .then(d=>{_templates=d.templates||[];renderTemplates();})
   .catch(()=>{_templates=[];});
 }

 function renderTemplates(){
  const container=document.getElementById('swarmTemplates');
  if(!container||!_templates.length){if(container)container.innerHTML='';return;}
  container.innerHTML='<div class="stm-label">saved templates:</div>'+_templates.map(t=>`
   <div class="stm-chip" data-name="${esc(t.name)}" onclick="SwarmApp.loadTemplate('${esc(t.name)}')">
    <span><svg class="swarm-icon" width="14" height="11" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg> ${esc(t.name)}</span>
    <button class="stm-del" onclick="event.stopPropagation();SwarmApp.deleteTemplate('${esc(t.name)}')">×</button>
   </div>
  `).join('');
 }

 window.SwarmApp.loadTemplate=function(name){
  const tpl=_templates.find(t=>t.name===name);
  if(!tpl||!tpl.config)return;
  const cfg=tpl.config;
  if(cfg.task){$('swarmNewTask').value=cfg.task;}
  if(cfg.agentCount){
   const btn=document.querySelector('.sac-btn[data-count="'+cfg.agentCount+'"]');
   if(btn){
    document.querySelectorAll('.sac-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
   }
  }
  if(cfg.model){$('swarmNewModel').value=cfg.model;}
  showNewForm();
 };

 window.SwarmApp.saveTemplate=function(){
  const task=$('swarmNewTask').value.trim();
  const model=$('swarmNewModel').value;
  const agentCount=parseInt(document.querySelector('.sac-btn.active')?.dataset?.count||'3');
  const name=prompt('template name:',task?.slice(0,30)||'swarm template');
  if(!name)return;
  swarmApi('/api/swarm/templates/save',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({name,config:{task,agentCount,model}}),
  }).then(()=>loadTemplates()).catch(e=>alert('save failed: '+e));
 };

 window.SwarmApp.deleteTemplate=function(name){
  if(!confirm('delete template "'+name+'"?'))return;
  swarmApi('/api/swarm/templates/delete',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({name}),
  }).then(()=>loadTemplates()).catch(e=>alert('delete failed: '+e));
 };

 // ── shared context viewer ──────────────────────────────────────────────────
 let _contextPoll=null;

 function startContextPoll(swarmId){
  stopContextPoll();
  _contextPoll=setInterval(()=>{
   swarmApi('/api/swarm/'+swarmId+'/context')
    .then(d=>{renderContextPanel(swarmId,d.context||{});})
    .catch(()=>{});
  },5000);
  // Initial load
  swarmApi('/api/swarm/'+swarmId+'/context')
   .then(d=>{renderContextPanel(swarmId,d.context||{});})
   .catch(()=>{});
 }

 function stopContextPoll(){
  if(_contextPoll){clearInterval(_contextPoll);_contextPoll=null;}
 }

 function renderContextPanel(swarmId,ctx){
  const panel=$('swarmContextPanel');
  if(!panel)return;
  const keys=Object.keys(ctx);
  if(!keys.length){panel.innerHTML='<div class="sctx-empty">no shared context yet...</div>';return;}
  panel.innerHTML=keys.map(k=>{
   const entry=ctx[k];
   const val=typeof entry.value==='string'?entry.value:JSON.stringify(entry.value);
   return `<div class="sctx-entry">
    <div class="sctx-key">${esc(k)}</div>
    <div class="sctx-val">${esc(val.slice(0,300))||'(empty)'}</div>
   </div>`;
  }).join('');
 }

 function showView(view){
  if(view==='new') showNewForm();
  else if(view==='list') showListView();
  else if(view==='detail'&&currentSwarmId) showDetail(currentSwarmId);
  else showListView();
 }

 function openWorkerSession(swarmId, workerId){
  const swarm = swarms[swarmId];
  if(!swarm) return;
  const worker = swarm.workers?.find(w=>w.worker_id===workerId);
  if(!worker) return;
  if(worker.session_id && typeof window.loadSession === 'function'){
   loadSession(worker.session_id).then(()=>{ if(typeof switchPanel === 'function') switchPanel('chat'); });
   return;
  }
  alert('No worker chat session available for this agent yet.');
 }

 function startSSE(){ subscribeSSE(); startPoll(); }

 // ── public ───────────────────────────────────────────────────────────────────
 const swarmPublic = {
  showTab,
  showView,
  refresh,
  startSSE,
  launchSwarm,
  sendChatMsg,
  openOrchestrationChat,
  openWorkerSession,
  killWorker: window.SwarmApp?.killWorker || null,
  injectResults: window.SwarmApp?.injectResults || null,
  loadAggregate: window.SwarmApp?.loadAggregate || null,
  showWorkerResult: window.SwarmApp?.showWorkerResult || null,
  loadTemplate: window.SwarmApp?.loadTemplate || null,
  saveTemplate: window.SwarmApp?.saveTemplate || null,
  deleteTemplate: window.SwarmApp?.deleteTemplate || null,
  toggle: toggleSwarmPanel,
 };
 window.SwarmApp = Object.assign(window.SwarmApp || {}, swarmPublic);
 return window.SwarmApp;
})();

// ── switchPanel integration ────────────────────────────────────────────
const _origSwarmSwitchPanel = window.switchPanel;
window.switchPanel = function(name){
  if(_origSwarmSwitchPanel) _origSwarmSwitchPanel(name);
  if(name === 'swarm'){
    const p = $('panelSwarm');
    if(p && !p.dataset.init){
      p.dataset.init = '1';
      // panelSwarm already has the HTML from index.html
      // just wire up the event listeners
      wireSwarmPanel();
    }
    if(window._swarmList === undefined) SwarmApp.refresh();
    if(typeof SwarmApp.startSSE === 'function'){
      SwarmApp.startSSE();
    } else {
      console.warn('SwarmApp.startSSE not available; skipping SSE startup.');
    }
  }
};

function wireSwarmPanel(){
  const btnNew = $('btnSwarmNew');
  const btnNewChat = $('btnSwarmNewChat');
  const btnBack = $('swarmBackBtn');
  const btnLaunch = $('btnSwarmLaunch');
  const btnChatSend = $('btnSwarmChatSend');
  if(btnNewChat) btnNewChat.onclick = ()=>SwarmApp.openOrchestrationChat();
  if(btnNew) btnNew.onclick = ()=>SwarmApp.showView('new');
  if(btnBack) btnBack.onclick = ()=>SwarmApp.showView('list');
  if(btnLaunch) btnLaunch.onclick = ()=>SwarmApp.launchSwarm();
  if(btnChatSend) btnChatSend.onclick = ()=>SwarmApp.sendChatMsg();
}

if(document.readyState==='loading'){
 document.addEventListener('DOMContentLoaded',SwarmApp.init);
}else{
 SwarmApp.init();
}


// ── Aggregate view (S3) ──────────────────────────────────────────────────────
 let _aggregateCache={};
 async function loadAggregate(swarmId){
  const data=await api(`/api/swarm/${swarmId}/aggregate`);
  _aggregateCache[swarmId]=data;
  return data;
 }
 function renderAggregate(swarmId){
  const data=_aggregateCache[swarmId];
  if(!data)return;
  const container=$('swarmAggregate');
  if(!container)return;
  let h='';
  // Summary header
  h+=`<div style="padding:12px;background:var(--panel-bg);border-radius:8px;margin-bottom:12px">`;
  h+=`<div style="font-size:13px;color:var(--muted);margin-bottom:6px"><svg class="swarm-icon" width="14" height="11" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg> results for: <b>${esc(data.task||'')}</b></div>`;
  h+=`<div style="display:flex;gap:12px;font-size:11px">`;
  h+=`<span style="color:#4ade80">✓ ${data.completed||0} done</span>`;
  h+=`<span style="color:#e94560">✗ ${data.failed||0} failed</span>`;
  h+=`<span style="color:var(--muted)">❌ ${data.cancelled||0} cancelled</span>`;
  h+=`</div></div>`;
  // Consensus
  if(data.consensus&&data.consensus.length>0){
   h+=`<div style="padding:8px;background:rgba(246,176,18,.1);border-left:3px solid #f6b012;border-radius:4px;margin-bottom:12px;font-size:11px">`;
   h+=`<b>consensus:</b> `;
   data.consensus.forEach(c=>{h+=`<span style="margin-right:8px">📁 ${esc(c.file||'')} (${c.mentioned_by} workers)</span>`;});
   h+=`</div>`;
  }
  // Worker cards
  if(data.results){
   data.results.forEach((r,i)=>{
    const color=COLORS[i%8];
    const icon=r.status==='done'?'✓':r.status==='error'?'✗':'∅';
    h+=`<div class="swarm-worker-card" style="border-left:3px solid ${color};margin-bottom:8px;padding:8px 10px;background:var(--msg-bg);border-radius:4px;cursor:pointer" onclick="SwarmApp.showWorkerAggregate('${esc(r.worker_id)}','${esc(swarmId)}')">`;
    h+=`<div style="font-size:12px;font-weight:600"><span style="color:${color}">${icon}</span> ${esc(r.worker_name)} <span style="color:var(--muted);font-weight:400">${esc(r.task||'').substring(0,60)}</span></div>`;
    if(r.result){
     const preview = r.result.substring(0,200);
     h+=`<div style="font-size:11px;color:var(--muted);margin-top:4px;white-space:pre-wrap;max-height:60px;overflow:hidden">${esc(preview)}...</div>`;
    }
    if(r.duration!=null)h+=`<div style="font-size:10px;color:var(--muted);margin-top:2px">${r.duration}s</div>`;
    if(r.code_blocks)h+=`<div style="font-size:10px;color:#22d3ee;margin-top:2px">📎 ${r.code_blocks} code block(s)</div>`;
    h+=`</div>`;
   });
  }
  container.innerHTML=h;
 }
 function showWorkerAggregate(workerId,swarmId){
  const data=_aggregateCache[swarmId];
  if(!data||!data.results)return;
  const r=data.results.find(w=>w.worker_id===workerId);
  if(!r)return;
  const modal=document.getElementById('swarm-worker-modal');
  const overlay=document.getElementById('swarm-worker-overlay');
  if(!modal||!overlay)return;
  modal.innerHTML=`
   <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span style="font-size:14px;font-weight:600"><svg class="swarm-icon" width="14" height="11" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg> ${esc(r.worker_name)}: ${esc(r.task||'')}</span>
    <button onclick="this.closest('.swarm-modal-overlay').style.display='none'" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:18px">×</button>
   </div>
   <div style="font-size:11px;color:var(--muted);margin-bottom:8px">status: ${r.status} | duration: ${r.duration||'?'}s</div>
   <pre style="background:var(--panel-bg);padding:12px;border-radius:8px;font-size:11px;white-space:pre-wrap;max-height:60vh;overflow-y:auto">${esc(r.result_full||r.result||'')}</pre>
  `;
  overlay.style.display='flex';
 }

 // ── Templates (S8) ──────────────────────────────────────────────────────────
 const TEMPLATE_KEY='hermes-swarm-templates';
 function saveTemplate(){
  const name = prompt('template name:');
  if(!name)return;
  let templates=[];
  try{templates=JSON.parse(localStorage.getItem(TEMPLATE_KEY)||'[]');}catch(e){}
  const tpl={
   name,
   numAgents: parseInt(document.getElementById('swarmAgentCount')?.value||'3'),
   model: document.getElementById('swarmAgentModel')?.value||'(auto)',
   mode: document.getElementById('swarmAgentMode')?.value||'auto',
   systemPrompt: document.getElementById('swarmSystemPrompt')?.value||'',
   task: document.getElementById('swarmTask')?.value||'',
  };
  templates.push(tpl);
  localStorage.setItem(TEMPLATE_KEY,JSON.stringify(templates));
  renderTemplates();
  alert('template saved: '+name);
 }
 function loadTemplate(idx){
  let templates=[];
  try{templates=JSON.parse(localStorage.getItem(TEMPLATE_KEY)||'[]');}catch(e){}
  const tpl=templates[idx];
  if(!tpl)return;
  if(document.getElementById('swarmAgentCount'))document.getElementById('swarmAgentCount').value=tpl.numAgents||3;
  if(document.getElementById('swarmAgentModel'))document.getElementById('swarmAgentModel').value=tpl.model||'';
  if(document.getElementById('swarmAgentMode'))document.getElementById('swarmAgentMode').value=tpl.mode||'auto';
  if(document.getElementById('swarmSystemPrompt'))document.getElementById('swarmSystemPrompt').value=tpl.systemPrompt||'';
  if(document.getElementById('swarmTask'))document.getElementById('swarmTask').value=tpl.task||'';
  alert('loaded template: '+tpl.name);
 }
 function deleteTemplate(idx){
  if(!confirm('delete this template?'))return;
  let templates=[];
  try{templates=JSON.parse(localStorage.getItem(TEMPLATE_KEY)||'[]');}catch(e){}
  templates.splice(idx,1);
  localStorage.setItem(TEMPLATE_KEY,JSON.stringify(templates));
  renderTemplates();
 }
 function renderTemplates(){
  const el=document.getElementById('swarmTemplates');
  if(!el)return;
  let templates=[];
  try{templates=JSON.parse(localStorage.getItem(TEMPLATE_KEY)||'[]');}catch(e){}
  if(!templates.length){el.innerHTML='';return;}
  let h='<div style="font-size:11px;color:var(--muted);margin:4px 0 2px">templates:</div>';
  templates.forEach((t,i)=>{
   h+=`<span style="display:inline-block;padding:2px 8px;margin:2px 4px 2px 0;background:var(--panel-bg);border-radius:12px;font-size:10px;cursor:pointer" onclick="SwarmApp.loadTemplate(${i})" title="click to load, right-click to delete" oncontextmenu="event.preventDefault();SwarmApp.deleteTemplate(${i})"><svg width=10 height=8 viewBox=0 0 1800 1434 fill=currentColor style=vertical-align:-1px><use href=#swarm/></svg> ${esc(t.name)}</span>`;
  });
  el.innerHTML=h;
 }

 // ── Extend public API ──
 window.SwarmApp.loadAggregate=loadAggregate;
 window.SwarmApp.renderAggregate=renderAggregate;
 window.SwarmApp.showWorkerAggregate=showWorkerAggregate;
 window.SwarmApp.saveTemplate=saveTemplate;
 window.SwarmApp.loadTemplate=loadTemplate;
 window.SwarmApp.deleteTemplate=deleteTemplate;
 window.SwarmApp.renderTemplates=renderTemplates;
 
// Alias for messages.js compatibility (it calls SwarmUI[handler] and SwarmUI.init())
window.SwarmUI = window.SwarmApp;
