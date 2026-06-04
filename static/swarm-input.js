// ── swarm-input.js — "run as swarm" trigger for vibecode ──────────────────
// adds swarm button to the composer footer. clicking opens a modal where
// the user defines the main task + subtasks, then starts a swarm.

const SwarmInput=(function(){
 // ── state ────────────────────────────────────────────────────────────
 let modal=null;
 let isOpen=false;

 // ── build trigger button ─────────────────────────────────────────────
 function addTrigger(){
  const footer=document.querySelector('.composer-right');
  if(!footer||document.getElementById('swarmTriggerBtn'))return;

  const btn=document.createElement('button');
  btn.id='swarmTriggerBtn';
  btn.className='swarm-trigger-btn';
  btn.type='button';
  btn.title='run as swarm';
 btn.innerHTML='<svg class="swarm-icon" width="16" height="13" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg>';
  btn.addEventListener('click',e=>{e.preventDefault();openModal();});

  // insert before the send button
  const sendBtn=document.getElementById('btnSend');
  if(sendBtn){
   footer.insertBefore(btn,sendBtn);
  }else{
   footer.appendChild(btn);
  }
 }

 // ── build modal ──────────────────────────────────────────────────────
 function buildModal(){
  if(modal)return;
  modal=document.createElement('div');
  modal.id='swarmModal';
  modal.className='swarm-modal';
  modal.innerHTML=`
   <div class="swarm-modal-backdrop" data-close="1"></div>
   <div class="swarm-modal-box">
    <div class="swarm-modal-header">
<span class="swarm-modal-icon"><svg class="swarm-icon" width="18" height="14" viewBox="0 0 1800 1434" fill="currentColor" aria-hidden="true"><use href="#swarm"/></svg></span>
     <span class="swarm-modal-title">swarm</span>
     <button class="swarm-modal-close" data-close="1">×</button>
    </div>
    <div class="swarm-modal-body">
     <label class="swarm-label">task</label>
     <textarea id="swarmTask" class="swarm-textarea" rows="2" placeholder="what should the swarm accomplish?"></textarea>
     <label class="swarm-label">subtasks <span class="swarm-hint">(one per line)</span></label>
     <textarea id="swarmSubtasks" class="swarm-textarea" rows="5" placeholder="research the codebase\nwrite unit tests\ncheck for edge cases"></textarea>
     <div class="swarm-options">
      <label class="swarm-opt-label">model</label>
      <select id="swarmModel" class="swarm-select">
       <option value="">default</option>
        <option value="@nvidia:deepseek-ai/deepseek-v4-pro">deepseek</option>
        <option value="@nvidia:z-ai/glm-5.1">glm</option>
        <option value="@nvidia:minimaxai/minimax-m2.7">minimax</option>
        <option value="@nvidia:mistralai/mistral-medium-3.5-128b">mistral</option>
      </select>
     </div>
    </div>
    <div class="swarm-modal-footer">
     <button class="swarm-btn swarm-btn-cancel" data-close="1">cancel</button>
     <button class="swarm-btn swarm-btn-go" id="swarmLaunchBtn">launch swarm</button>
    </div>
   </div>
  `;
  document.body.appendChild(modal);

  // close handlers
  modal.querySelectorAll('[data-close]').forEach(el=>{
   el.addEventListener('click',closeModal);
  });

  // launch handler
  document.getElementById('swarmLaunchBtn').addEventListener('click',launchSwarm);

  // esc to close
  document.addEventListener('keydown',e=>{
   if(e.key==='Escape'&&isOpen)closeModal();
  });
 }

 function openModal(){
  buildModal();
  // prefill task from composer if there's text
  const msg=document.getElementById('msg');
  const taskEl=document.getElementById('swarmTask');
  if(msg&&msg.value.trim()&&taskEl&&!taskEl.value){
   taskEl.value=msg.value.trim();
  }
  modal.classList.add('open');
  isOpen=true;
  document.getElementById('swarmTask').focus();
 }

 function closeModal(){
  if(!modal)return;
  modal.classList.remove('open');
  isOpen=false;
 }

 // ── launch swarm ─────────────────────────────────────────────────────
 async function launchSwarm(){
  const task=document.getElementById('swarmTask').value.trim();
  const subtaskText=document.getElementById('swarmSubtasks').value.trim();
  const model=document.getElementById('swarmModel').value;

  if(!task){document.getElementById('swarmTask').focus();return;}
  if(!subtaskText){document.getElementById('swarmSubtasks').focus();return;}

  const subtasks=subtaskText.split('\n').map(s=>s.trim()).filter(Boolean);
  if(!subtasks.length){document.getElementById('swarmSubtasks').focus();return;}

  const btn=document.getElementById('swarmLaunchBtn');
  btn.disabled=true;
  btn.textContent='launching…';

  // get current session id
  const sessionId=(window.S&&window.S.session&&window.S.session.session_id)
   ||document.getElementById('sessionSelect')?.value
   ||document.querySelector('[data-session-id]')?.dataset?.sessionId;

  if(!sessionId){
   btn.disabled=false;
   btn.textContent='launch swarm';
   alert('no active session — start a conversation first');
   return;
  }

  try{
   const body={session_id:sessionId,task,subtasks};
   if(model)body.model=model;

   const resp=await fetch('/api/swarm/start',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)
   });

   if(!resp.ok){
    const err=await resp.json().catch(()=>({error:resp.statusText}));
    throw new Error(err.error||err.message||'swarm start failed');
   }

   const data=await resp.json();

   // clear the composer message since we're running as swarm instead
   const msg=document.getElementById('msg');
   if(msg)msg.value='';

   closeModal();

   // open the swarm panel if available
   if(window.SwarmUI&&SwarmUI.showPanel)SwarmUI.showPanel();

  }catch(e){
   alert('swarm error: '+e.message);
  }finally{
   btn.disabled=false;
   btn.textContent='launch swarm';
  }
 }

 // ── init ─────────────────────────────────────────────────────────────
 function init(){
  addTrigger();
  // retry in case composer wasn't ready yet
  if(!document.getElementById('swarmTriggerBtn')){
   setTimeout(addTrigger,1000);
   setTimeout(addTrigger,3000);
  }
 }

 return {init,openModal,closeModal};
})();

// auto-init when DOM is ready
if(document.readyState==='loading'){
 document.addEventListener('DOMContentLoaded',SwarmInput.init);
}else{
 SwarmInput.init();
}
