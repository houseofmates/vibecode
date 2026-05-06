let _currentPanel = 'chat';
let _skillsData = null; // cached skills list

async function switchPanel(name) {
  // Terminal now lives in a bottom panel, not the sidebar
  if (name === 'terminal') {
    const bottomPanel = $('bottomPanel');
    const panelTerminal = $('panelTerminal');
    if (bottomPanel && panelTerminal) {
      const isActive = bottomPanel.classList.contains('active');
      if (isActive) {
        bottomPanel.classList.remove('active');
        panelTerminal.classList.remove('active');
        if (typeof onTerminalPanelHide === 'function') onTerminalPanelHide();
      } else {
        // Defensive: clear any stuck inline styles from old cached code
        bottomPanel.style.display = '';
        bottomPanel.style.opacity = '';
        bottomPanel.style.visibility = '';
        bottomPanel.style.pointerEvents = '';
        panelTerminal.style.display = '';
        panelTerminal.style.opacity = '';
        panelTerminal.style.visibility = '';
        panelTerminal.style.pointerEvents = '';
        bottomPanel.classList.add('active');
        panelTerminal.classList.add('active');
        if (typeof initTerminalPanel === 'function') initTerminalPanel();
        if (typeof onTerminalPanelShow === 'function') onTerminalPanelShow();
      }
    }
    const tt = $('btnTerminalPanelToggle');
    if (tt) tt.classList.toggle('active', bottomPanel?.classList.contains('active'));
    return;
  }

  _currentPanel = name;
  // Update nav tabs
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.panel === name));
  // Update panel views
  document.querySelectorAll('.panel-view').forEach(p => p.classList.remove('active'));
  const panelEl = $('panel' + name.charAt(0).toUpperCase() + name.slice(1));
  if (panelEl) panelEl.classList.add('active');
  // Hide bottom panel when switching to a non-terminal sidebar panel
  const bottomPanel = $('bottomPanel');
  if (bottomPanel) {
    bottomPanel.classList.remove('active');
    const panelTerminal = $('panelTerminal');
    if (panelTerminal) panelTerminal.classList.remove('active');
    if (typeof onTerminalPanelHide === 'function') onTerminalPanelHide();
  }
  const tt = $('btnTerminalPanelToggle');
  if (tt) tt.classList.remove('active');
  // Refresh sessions whenever the chat panel becomes active.
  if (name === 'chat') {
    if (typeof renderSessionList === 'function') {
      await renderSessionList();
    } else if (typeof renderSessionListFromCache === 'function') {
      renderSessionListFromCache();
    }
  }
  // Lazy-load panel data
  if (name === 'tasks') await loadCrons();
  if (name === 'skills') await loadSkills();
  if (name === 'memory') await loadMemory();
  if (name === 'workspaces') await loadWorkspacesPanel();
  if (name === 'todos') loadTodos();
}

// ── Cron panel ──
let _cronsCache = null;

async function loadCrons() {
  const box = $('cronList');
  // Show cached crons instantly while fetching fresh data
  if (!_cronsCache) {
    let cached = null;
    try { cached = localStorage.getItem('hermes-crons-cache'); } catch (e) {}
    if (cached) {
      try {
        _cronsCache = JSON.parse(cached);
        _renderCrons(_cronsCache);
      } catch (e) { /* ignore parse errors */ }
    }
  }
  try {
    const data = await api('/api/crons');
    _cronsCache = data;
    // Cache for instant load next time
    try { localStorage.setItem('hermes-crons-cache', JSON.stringify(data)); } catch (e) {}
    _renderCrons(data);
  } catch(e) { box.innerHTML = `<div style="padding:12px;color:var(--accent);font-size:12px">${esc(t('error_prefix'))}${esc(e.message)}</div>`; }
}

function _renderCrons(data) {
  const box = $('cronList');
  if (!data.jobs || !data.jobs.length) {
    box.innerHTML = `<div style="padding:16px;color:var(--muted);font-size:12px">${esc(t('cron_no_jobs'))}</div>`;
    return;
  }
  box.innerHTML = '';
  for (const job of data.jobs) {
    const item = document.createElement('div');
    item.className = 'cron-item';
    item.id = 'cron-' + job.id;
    const statusClass = job.enabled === false ? 'disabled' : job.state === 'paused' ? 'paused' : job.last_status === 'error' ? 'error' : 'active';
    const statusLabel = job.enabled === false ? t('cron_status_off') : job.state === 'paused' ? t('cron_status_paused') : job.last_status === 'error' ? t('cron_status_error') : t('cron_status_active');
    const nextRun = job.next_run_at ? new Date(job.next_run_at).toLocaleString() : t('not_available');
    const lastRun = job.last_run_at ? new Date(job.last_run_at).toLocaleString() : t('never');
    item.innerHTML = `
      <div class="cron-header" onclick="toggleCron('${job.id}')">
        <span class="cron-name" title="${esc(job.name)}">${esc(job.name)}</span>
        <span class="cron-status ${statusClass}">${statusLabel}</span>
      </div>
      <div class="cron-body" id="cron-body-${job.id}">
        <div class="cron-schedule">${li('clock',12)} ${esc(job.schedule_display || job.schedule?.expression || '')} &nbsp;|&nbsp; ${esc(t('cron_next'))}: ${esc(nextRun)} &nbsp;|&nbsp; ${esc(t('cron_last'))}: ${esc(lastRun)}</div>
        <div class="cron-prompt">${esc((job.prompt||'').slice(0,300))}${(job.prompt||'').length>300?'…':''}</div>
        <div class="cron-actions">
          <button class="cron-btn run" onclick="cronRun('${job.id}')">${li('play',12)} ${esc(t('cron_run_now'))}</button>
          ${job.state==='paused'
            ? `<button class="cron-btn" onclick="cronResume('${job.id}')">${li('play',12)} ${esc(t('cron_resume'))}</button>`
            : `<button class="cron-btn pause" onclick="cronPause('${job.id}')">${li('pause',12)} ${esc(t('cron_pause'))}</button>`}
          <button class="cron-btn" onclick="cronEditOpen('${job.id}',${JSON.stringify(job).replace(/"/g,'&quot;')})">${li('pencil',12)} ${esc(t('edit'))}</button>
          <button class="cron-btn" style="border-color:rgba(201,168,76,.3);color:var(--accent)" onclick="cronDelete('${job.id}')">${li('trash-2',12)} ${esc(t('delete_title'))}</button>
        </div>
        <!-- Inline edit form, hidden by default -->
        <div id="cron-edit-${job.id}" style="display:none;margin-top:8px;border-top:1px solid var(--border);padding-top:8px">
          <input id="cron-edit-name-${job.id}" placeholder="${esc(t('cron_job_name_placeholder'))}" style="width:100%;background:rgba(255,255,255,.05);border:1px solid var(--border2);border-radius:6px;color:var(--text);padding:5px 8px;font-size:12px;outline:none;margin-bottom:5px;box-sizing:border-box">
          <input id="cron-edit-schedule-${job.id}" placeholder="${esc(t('cron_schedule_placeholder'))}" style="width:100%;background:rgba(255,255,255,.05);border:1px solid var(--border2);border-radius:6px;color:var(--text);padding:5px 8px;font-size:12px;outline:none;margin-bottom:5px;box-sizing:border-box">
          <textarea id="cron-edit-prompt-${job.id}" rows="3" placeholder="${esc(t('cron_prompt_placeholder'))}" style="width:100%;background:rgba(255,255,255,.05);border:1px solid var(--border2);border-radius:6px;color:var(--text);padding:5px 8px;font-size:12px;outline:none;resize:none;font-family:inherit;margin-bottom:5px;box-sizing:border-box"></textarea>
          <div id="cron-edit-err-${job.id}" style="font-size:11px;color:var(--accent);display:none;margin-bottom:5px"></div>
          <div style="display:flex;gap:6px">
            <button class="cron-btn run" style="flex:1" onclick="cronEditSave('${job.id}')">${esc(t('save'))}</button>
            <button class="cron-btn" style="flex:1" onclick="cronEditClose('${job.id}')">${esc(t('cancel'))}</button>
          </div>
        </div>
        <div id="cron-output-${job.id}">
          <div class="cron-last-header" style="display:flex;align-items:center;justify-content:space-between">
            <span>${esc(t('cron_last_output'))}</span>
            <button class="cron-btn" style="padding:1px 8px;font-size:10px" onclick="loadCronHistory('${job.id}',this)">${esc(t('cron_all_runs'))}</button>
          </div>
          <div class="cron-last" id="cron-out-text-${job.id}" style="color:var(--muted);font-size:11px">${esc(t('loading'))}</div>
          <div id="cron-history-${job.id}" style="display:none"></div>
        </div>
      </div>`;
    box.appendChild(item);
    // Eagerly load last output for visible items
    loadCronOutput(job.id);
  }
}

let _cronSelectedSkills=[];
let _cronSkillsCache=null;

function toggleCronForm(){
  const form=$('cronCreateForm');
  if(!form)return;
  const open=form.style.display!=='none';
  form.style.display=open?'none':'';
  if(!open){
    $('cronFormName').value='';
    $('cronFormSchedule').value='';
    $('cronFormPrompt').value='';
    $('cronFormDeliver').value='local';
    $('cronFormError').style.display='none';
    _cronSelectedSkills=[];
    _renderCronSkillTags();
    const search=$('cronFormSkillSearch');
    if(search)search.value='';
    // Always re-fetch skills to avoid stale cache
    _cronSkillsCache=null;
    api('/api/skills').then(d=>{_cronSkillsCache=d.skills||[];}).catch(()=>{});
    $('cronFormName').focus();
  }
}

function _renderCronSkillTags(){
  const wrap=$('cronFormSkillTags');
  if(!wrap)return;
  wrap.innerHTML='';
  for(const name of _cronSelectedSkills){
    const tag=document.createElement('span');
    tag.className='skill-tag';
    tag.dataset.skill=name;
    const rm=document.createElement('span');
    rm.className='remove-tag';rm.textContent='×';
    rm.onclick=()=>{_cronSelectedSkills=_cronSelectedSkills.filter(s=>s!==name);tag.remove();};
    tag.appendChild(document.createTextNode(name));
    tag.appendChild(rm);
    wrap.appendChild(tag);
  }
}

// Skill search input handler
(function(){
  const setup=()=>{
    const search=$('cronFormSkillSearch');
    const dropdown=$('cronFormSkillDropdown');
    if(!search||!dropdown)return;
    search.oninput=()=>{
      const q=search.value.trim().toLowerCase();
      if(!q||!_cronSkillsCache){dropdown.style.display='none';return;}
      const matches=_cronSkillsCache.filter(s=>
        !_cronSelectedSkills.includes(s.name)&&
        (s.name.toLowerCase().includes(q)||(s.category||'').toLowerCase().includes(q))
      ).slice(0,8);
      if(!matches.length){dropdown.style.display='none';return;}
      dropdown.innerHTML='';
      for(const s of matches){
        const opt=document.createElement('div');
        opt.className='skill-opt';
        opt.textContent=s.name+(s.category?' ('+s.category+')':'');
        opt.onclick=()=>{
          _cronSelectedSkills.push(s.name);
          _renderCronSkillTags();
          search.value='';
          dropdown.style.display='none';
        };
        dropdown.appendChild(opt);
      }
      dropdown.style.display='';
    };
    search.onblur=()=>setTimeout(()=>{dropdown.style.display='none';},150);
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup);
  else setTimeout(setup,0);
})();

async function submitCronCreate(){
  const name=$('cronFormName').value.trim();
  const schedule=$('cronFormSchedule').value.trim();
  const prompt=$('cronFormPrompt').value.trim();
  const deliver=$('cronFormDeliver').value;
  const errEl=$('cronFormError');
  errEl.style.display='none';
  if(!schedule){errEl.textContent=t('cron_schedule_required_example');errEl.style.display='';return;}
  if(!prompt){errEl.textContent=t('cron_prompt_required');errEl.style.display='';return;}
  try{
    const body={schedule,prompt,deliver};
    if(name)body.name=name;
    if(_cronSelectedSkills.length)body.skills=_cronSelectedSkills;
    await api('/api/crons/create',{method:'POST',body:JSON.stringify(body)});
    toggleCronForm();
    showToast(t('cron_job_created'));
    await loadCrons();
  }catch(e){
    errEl.textContent=t('error_prefix')+e.message;errEl.style.display='';
  }
}

function _cronOutputSnippet(content) {
  // Extract the response body from a cron output .md file
  const lines = content.split('\n');
  const responseIdx = lines.findIndex(l => l.startsWith('## Response') || l.startsWith('# Response'));
  const body = (responseIdx >= 0 ? lines.slice(responseIdx + 1) : lines).join('\n').trim();
  return body.slice(0, 600) || '(empty)';
}

async function loadCronOutput(jobId) {
  try {
    const data = await api(`/api/crons/output?job_id=${encodeURIComponent(jobId)}&limit=1`);
    const el = $('cron-out-text-' + jobId);
    if (!el) return;
    if (!data.outputs || !data.outputs.length) { el.textContent = t('cron_no_runs_yet'); return; }
    const out = data.outputs[0];
    const ts = out.filename.replace('.md','').replace(/_/g,' ');
    el.textContent = ts + '\n\n' + _cronOutputSnippet(out.content);
  } catch(e) { /* ignore */ }
}

async function loadCronHistory(jobId, btn) {
  const histEl = $('cron-history-' + jobId);
  if (!histEl) return;
  // Toggle: if already open, close it
  if (histEl.style.display !== 'none') {
    histEl.style.display = 'none';
    if (btn) btn.textContent = t('cron_all_runs');
    return;
  }
  if (btn) btn.textContent = t('loading');
  try {
    const data = await api(`/api/crons/output?job_id=${encodeURIComponent(jobId)}&limit=20`);
    if (!data.outputs || !data.outputs.length) {
      histEl.innerHTML = `<div style="font-size:11px;color:var(--muted);padding:4px 0">${esc(t('cron_no_runs_yet'))}</div>`;
    } else {
      histEl.innerHTML = data.outputs.map((out, i) => {
        const ts = out.filename.replace('.md','').replace(/_/g,' ');
        const snippet = _cronOutputSnippet(out.content);
        const id = `cron-hist-run-${jobId}-${i}`;
        return `<div style="border-top:1px solid var(--border);padding:6px 0">
          <div style="display:flex;align-items:center;justify-content:space-between;cursor:pointer" onclick="document.getElementById('${id}').style.display=document.getElementById('${id}').style.display==='none'?'':'none'">
            <span style="font-size:11px;font-weight:600;color:var(--muted)">${esc(ts)}</span>
            <span style="font-size:10px;color:var(--muted);opacity:.6">▸</span>
          </div>
          <div id="${id}" style="display:none;font-size:11px;color:var(--muted);white-space:pre-wrap;line-height:1.5;margin-top:4px;max-height:200px;overflow-y:auto">${esc(snippet)}</div>
        </div>`;
      }).join('');
    }
    histEl.style.display = '';
    if (btn) btn.textContent = t('cron_hide_runs');
  } catch(e) {
    if (btn) btn.textContent = t('cron_all_runs');
  }
}

function toggleCron(id) {
  const body = $('cron-body-' + id);
  if (body) body.classList.toggle('open');
}

async function cronRun(id) {
  try {
    await api('/api/crons/run', {method:'POST', body: JSON.stringify({job_id: id})});
    showToast(t('cron_job_triggered'));
    setTimeout(() => loadCronOutput(id), 5000);
  } catch(e) { showToast(t('failed_colon') + e.message, 4000); }
}

async function cronPause(id) {
  try {
    await api('/api/crons/pause', {method:'POST', body: JSON.stringify({job_id: id})});
    showToast(t('cron_job_paused'));
    await loadCrons();
  } catch(e) { showToast(t('failed_colon') + e.message, 4000); }
}

async function cronResume(id) {
  try {
    await api('/api/crons/resume', {method:'POST', body: JSON.stringify({job_id: id})});
    showToast(t('cron_job_resumed'));
    await loadCrons();
  } catch(e) { showToast(t('failed_colon') + e.message, 4000); }
}

function cronEditOpen(id, job) {
  const form = $('cron-edit-' + id);
  if (!form) return;
  $('cron-edit-name-' + id).value = job.name || '';
  $('cron-edit-schedule-' + id).value = job.schedule_display || (job.schedule && job.schedule.expression) || job.schedule || '';
  $('cron-edit-prompt-' + id).value = job.prompt || '';
  const errEl = $('cron-edit-err-' + id);
  if (errEl) errEl.style.display = 'none';
  form.style.display = '';
}

function cronEditClose(id) {
  const form = $('cron-edit-' + id);
  if (form) form.style.display = 'none';
}

async function cronEditSave(id) {
  const name = $('cron-edit-name-' + id).value.trim();
  const schedule = $('cron-edit-schedule-' + id).value.trim();
  const prompt = $('cron-edit-prompt-' + id).value.trim();
  const errEl = $('cron-edit-err-' + id);
  if (!schedule) { errEl.textContent = t('cron_schedule_required'); errEl.style.display = ''; return; }
  if (!prompt) { errEl.textContent = t('cron_prompt_required'); errEl.style.display = ''; return; }
  try {
    const updates = {job_id: id, schedule, prompt};
    if (name) updates.name = name;
    await api('/api/crons/update', {method:'POST', body: JSON.stringify(updates)});
    showToast(t('cron_job_updated'));
    await loadCrons();
  } catch(e) { errEl.textContent = t('error_prefix') + e.message; errEl.style.display = ''; }
}

async function cronDelete(id) {
  const _delCron=await showConfirmDialog({title:t('cron_delete_confirm_title'),message:t('cron_delete_confirm_message'),confirmLabel:t('delete_title'),danger:true,focusCancel:true});
  if(!_delCron) return;
  try {
    await api('/api/crons/delete', {method:'POST', body: JSON.stringify({job_id: id})});
    showToast(t('cron_job_deleted'));
    await loadCrons();
  } catch(e) { showToast(t('delete_failed') + e.message, 4000); }
}

function loadTodos() {
  const panel = $('todoPanel');
  if (!panel) return;
  const sourceMessages = (S.session && Array.isArray(S.session.messages) && S.session.messages.length) ? S.session.messages : S.messages;
  // Parse the most recent todo state from message history
  let todos = [];
  for (let i = sourceMessages.length - 1; i >= 0; i--) {
    const m = sourceMessages[i];
    if (m && m.role === 'tool') {
      try {
        const d = JSON.parse(typeof m.content === 'string' ? m.content : JSON.stringify(m.content));
        if (d && Array.isArray(d.todos) && d.todos.length) {
          todos = d.todos;
          break;
        }
      } catch(e) {}
    }
  }
  if (!todos.length) {
    panel.innerHTML = `<div style="color:var(--muted);font-size:12px;padding:4px 0">${esc(t('todos_no_active'))}</div>`;
    return;
  }
  const statusIcon = {pending:li('square',14), in_progress:li('loader',14), completed:li('check',14), cancelled:li('x',14)};
  const statusColor = {pending:'var(--muted)', in_progress:'var(--blue)', completed:'rgba(100,200,100,.8)', cancelled:'rgba(200,100,100,.5)'};
  panel.innerHTML = todos.map(t => `
    <div style="display:flex;align-items:flex-start;gap:10px;padding:6px 0;border-bottom:1px solid var(--border);">
      <span style="font-size:14px;display:inline-flex;align-items:center;flex-shrink:0;margin-top:1px;color:${statusColor[t.status]||'var(--muted)'}">${statusIcon[t.status]||li('square',14)}</span>
      <div style="flex:1;min-width:0">
        <div style="font-size:13px;color:${t.status==='completed'?'var(--muted)':t.status==='in_progress'?'var(--text)':'var(--text)'};${t.status==='completed'?'text-decoration:line-through;opacity:.5':''};line-height:1.4">${esc(t.content)}</div>
        <div style="font-size:10px;color:var(--muted);margin-top:2px;opacity:.6">${esc(t.id)} · ${esc(t.status)}</div>
      </div>
    </div>`).join('');
}

async function clearConversation() {
  if(!S.session) return;
  const _clrMsg=await showConfirmDialog({title:t('clear_conversation_title'),message:t('clear_conversation_message'),confirmLabel:t('clear'),danger:true,focusCancel:true});
  if(!_clrMsg) return;
  try {
    const data = await api('/api/session/clear', {method:'POST',
      body: JSON.stringify({session_id: S.session.session_id})});
    S.session = data.session;
    S.messages = [];
    S.toolCalls = [];
    syncTopbar();
    renderMessages();
    showToast(t('conversation_cleared'));
  } catch(e) { setStatus(t('clear_failed') + e.message);}
}

// ── Skills panel ──
async function loadSkills() {
  const box = $('skillsList');
  // Show cached skills instantly while fetching fresh data
  if (!_skillsData) {
    let cached = null;
    try { cached = localStorage.getItem('hermes-skills-cache'); } catch (e) {}
    if (cached) {
      try {
        _skillsData = JSON.parse(cached);
        renderSkills(_skillsData);
      } catch (e) { /* ignore parse errors */ }
    }
  }
  if (_skillsData) { renderSkills(_skillsData); }
  try {
    const data = await api('/api/skills');
    _skillsData = data.skills || [];
    // Cache for instant load next time
    try { localStorage.setItem('hermes-skills-cache', JSON.stringify(_skillsData)); } catch (e) {}
    renderSkills(_skillsData);
  } catch(e) { if (!box.innerHTML || box.innerHTML.includes('loading')) box.innerHTML = `<div style="padding:12px;color:var(--accent);font-size:12px">Error: ${esc(e.message)}</div>`; }
}

function renderSkills(skills) {
  const query = ($('skillsSearch').value || '').toLowerCase();
  const filtered = query ? skills.filter(s =>
    (s.name||'').toLowerCase().includes(query) ||
    (s.description||'').toLowerCase().includes(query) ||
    (s.category||'').toLowerCase().includes(query)
  ) : skills;
  // Group by category
  const cats = {};
  for (const s of filtered) {
    const cat = s.category || '(general)';
    if (!cats[cat]) cats[cat] = [];
    cats[cat].push(s);
  }
  const box = $('skillsList');
  box.innerHTML = '';
  if (!filtered.length) { box.innerHTML = `<div style="padding:12px;color:var(--muted);font-size:12px">${esc(t('skills_no_match'))}</div>`; return; }
  for (const [cat, items] of Object.entries(cats).sort()) {
    const sec = document.createElement('div');
    sec.className = 'skills-category';
    const header = document.createElement('div');
    header.className = 'skills-cat-header';
    header.innerHTML = `<span class="skills-cat-toggle">${li('chevron-right',12)}</span> ${li('folder',12)} ${esc(cat)} <span style="opacity:.5">(${items.length})</span>`;
    header.onclick = () => {
      header.classList.toggle('collapsed');
      header.querySelector('.skills-cat-toggle').innerHTML = li(header.classList.contains('collapsed') ? 'chevron-right' : 'chevron-down', 12);
      Array.from(sec.children).slice(1).forEach(el => el.style.display = header.classList.contains('collapsed') ? 'none' : '');
    };
    sec.appendChild(header);
    for (const skill of items.sort((a,b) => a.name.localeCompare(b.name))) {
      const el = document.createElement('div');
      el.className = 'skill-item';
      el.dataset.skillName = skill.name;
      el.innerHTML = `<span class="skill-name">${esc(skill.name)}</span><span class="skill-desc">${esc(skill.description||'')}</span>`;
      el.onclick = () => openSkillEditor(skill.name, el);
      el.oncontextmenu = (e) => showSkillContextMenu(e, skill.name, el);
      sec.appendChild(el);
    }
    box.appendChild(sec);
  }
}

function filterSkills() {
  if (_skillsData) renderSkills(_skillsData);
}

// ── Skill WYSIWYG Editor ──
let _currentEditingSkill = null;

async function openSkillEditor(name, el) {
  // Highlight active skill
  document.querySelectorAll('.skill-item').forEach(e => e.classList.remove('active'));
  if (el) el.classList.add('active');
  _currentEditingSkill = name;
  
  try {
    const data = await api(`/api/skills/content?name=${encodeURIComponent(name)}`);
    $('skillEditorName').textContent = name + '.md';
    $('skillEditorContent').value = data.content || '';
    $('skillEditorError').style.display = 'none';
    
    // Show editor at bottom of skills panel
    $('skillEditor').style.display = 'flex';
    // Reduce skills list height to accommodate editor
    $('skillsList').style.flex = '0 0 50%';
  } catch(e) { 
    showToast(t('skill_load_failed') + e.message, 4000);
  }
}

function closeSkillEditor() {
  $('skillEditor').style.display = 'none';
  $('skillsList').style.flex = '1';
  document.querySelectorAll('.skill-item').forEach(e => e.classList.remove('active'));
  _currentEditingSkill = null;
}

async function saveSkillEditor() {
  if (!_currentEditingSkill) return;
  const content = $('skillEditorContent').value;
  const errEl = $('skillEditorError');
  errEl.style.display = 'none';
  
  try {
    // Fetch current skill to preserve category
    const current = await api(`/api/skills/content?name=${encodeURIComponent(_currentEditingSkill)}`);
    await api('/api/skills/save', {
      method: 'POST', 
      body: JSON.stringify({
        name: _currentEditingSkill, 
        category: current.category, 
        content
      })
    });
    showToast(t('skill_updated'));
    _skillsData = null;
    _cronSkillsCache = null;
  } catch(e) { 
    errEl.textContent = t('error_prefix') + e.message; 
    errEl.style.display = ''; 
  }
}

function formatSkillText(format) {
  const textarea = $('skillEditorContent');
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selected = textarea.value.substring(start, end);
  let replacement = selected;
  
  switch(format) {
    case 'bold': replacement = `**${selected || 'bold text'}**`; break;
    case 'italic': replacement = `*${selected || 'italic text'}*`; break;
    case 'h1': replacement = `# ${selected || 'heading'}`; break;
    case 'h2': replacement = `## ${selected || 'heading'}`; break;
    case 'ul': replacement = selected ? selected.split('\n').map(l => `- ${l}`).join('\n') : '- list item'; break;
    case 'ol': replacement = selected ? selected.split('\n').map((l, i) => `${i+1}. ${l}`).join('\n') : '1. list item'; break;
    case 'code': replacement = `\`\`\`\n${selected || 'code block'}\n\`\`\``; break;
    case 'link': replacement = `[${selected || 'link text'}](url)`; break;
  }
  
  textarea.setRangeText(replacement, start, end, 'select');
  textarea.focus();
}

// ── Skill Context Menu ──
let _skillContextMenu = null;

function showSkillContextMenu(e, skillName, el) {
  e.preventDefault();
  e.stopPropagation();
  
  // Remove any existing context menu
  hideSkillContextMenu();
  
  // Create context menu
  const menu = document.createElement('div');
  menu.className = 'skill-context-menu';
  
  // Estimate menu height (~110px for 3 items with divider)
  const menuHeight = 110;
  const menuWidth = 140;
  
  // Adjust position to stay within viewport
  let x = e.clientX;
  let y = e.clientY;
  
  if (y + menuHeight > window.innerHeight) {
    y = Math.max(10, y - menuHeight);
  }
  if (x + menuWidth > window.innerWidth) {
    x = Math.max(10, x - menuWidth);
  }
  
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';
  
  menu.innerHTML = `
    <div class="skill-context-item" onclick="openSkillEditor('${esc(skillName)}', document.querySelector('.skill-item[data-skill-name=\\'${esc(skillName)}\\']'))">
      ${li('pencil', 14)} edit
    </div>
    <div class="skill-context-item" onclick="renameSkill('${esc(skillName)}')">
      ${li('settings', 14)} rename
    </div>
    <div class="skill-context-divider"></div>
    <div class="skill-context-item delete" onclick="deleteSkill('${esc(skillName)}')">
      ${li('trash-2', 14)} delete
    </div>
  `;
  
  document.body.appendChild(menu);
  _skillContextMenu = menu;
  
  // Close on click outside
  setTimeout(() => {
    document.addEventListener('click', hideSkillContextMenu, { once: true });
    document.addEventListener('contextmenu', hideSkillContextMenu, { once: true });
  }, 10);
}

function hideSkillContextMenu() {
  if (_skillContextMenu) {
    _skillContextMenu.remove();
    _skillContextMenu = null;
  }
}

async function renameSkill(oldName) {
  hideSkillContextMenu();
  const newName = prompt('new skill name:', oldName);
  if (!newName || newName === oldName) return;
  
  const cleanName = newName.trim().toLowerCase().replace(/\s+/g, '-');
  if (!cleanName) return;
  
  try {
    // Get current content
    const data = await api(`/api/skills/content?name=${encodeURIComponent(oldName)}`);
    // Save with new name
    await api('/api/skills/save', {
      method: 'POST',
      body: JSON.stringify({
        name: cleanName,
        category: data.category,
        content: data.content
      })
    });
    // Delete old
    await api('/api/skills/delete', {
      method: 'POST',
      body: JSON.stringify({ name: oldName })
    });
    showToast(t('skill_renamed'));
    _skillsData = null;
    _cronSkillsCache = null;
    await loadSkills();
  } catch(e) {
    showToast(t('error_prefix') + e.message, 4000);
  }
}

async function deleteSkill(name) {
  hideSkillContextMenu();
  const confirmed = await showConfirmDialog({
    title: 'delete skill',
    message: `delete "${name}"?`,
    confirmLabel: 'delete',
    danger: true,
    focusCancel: true
  });
  if (!confirmed) return;
  
  try {
    await api('/api/skills/delete', {
      method: 'POST',
      body: JSON.stringify({ name })
    });
    showToast(t('skill_deleted'));
    _skillsData = null;
    _cronSkillsCache = null;
    // Close editor if open for this skill
    if (_currentEditingSkill === name) closeSkillEditor();
    await loadSkills();
  } catch(e) {
    showToast(t('delete_failed') + e.message, 4000);
  }
}

// ── Workspace management ──
let _workspaceList = [];  // cached from /api/workspaces

function getWorkspaceFriendlyName(path){
  // Look up the friendly name from the workspace list cache, fallback to last path segment
  if(_workspaceList && _workspaceList.length){
    const match=_workspaceList.find(w=>w.path===path);
    if(match && match.name) return match.name;
  }
  return path.split('/').filter(Boolean).pop()||path;
}

function syncWorkspaceDisplays(){
  const hasSession=!!(S.session&&S.session.workspace);
  const ws=hasSession?S.session.workspace:'';
  const label=hasSession?getWorkspaceFriendlyName(ws):t('no_workspace');

  const sidebarName=$('sidebarWsName');
  const sidebarPath=$('sidebarWsPath');
  if(sidebarName) sidebarName.textContent=label;
  if(sidebarPath) sidebarPath.textContent=ws;

  const composerChip=$('composerWorkspaceChip');
  const composerLabel=$('composerWorkspaceLabel');
  const composerDropdown=$('composerWsDropdown');
  if(!hasSession && composerDropdown) composerDropdown.classList.remove('open');
  if(composerLabel) composerLabel.textContent=label;
  if(composerChip){
    // Always enable workspace selector (allow switching even without session workspace)
    composerChip.disabled=false;
    composerChip.title=hasSession?ws:t('no_workspace');
    composerChip.classList.toggle('active',!!(composerDropdown&&composerDropdown.classList.contains('open')));
  }
}

let _workspaceListCache = null;

async function loadWorkspaceList(){
  // Clear cache to ensure fresh data
  _workspaceListCache = null;
  localStorage.removeItem('hermes-workspaces-cache');
  try{
    const data = await api('/api/workspaces');
    _workspaceList = data.workspaces || [];
    _workspaceListCache = data.workspaces || [];
    // Cache for instant load next time
    try { localStorage.setItem('hermes-workspaces-cache', JSON.stringify(_workspaceListCache)); } catch (e) {}
    syncWorkspaceDisplays();
    return data;
  }catch(e){
    // Return cached data on error if available
    if (_workspaceListCache) return {workspaces: _workspaceListCache, last:''};
    return {workspaces:[], last:''};
  }
}

function _renderWorkspaceAction(label, meta, iconSvg, onClick){
  const opt=document.createElement('div');
  opt.className='ws-opt ws-opt-action';
  opt.innerHTML=`<span class="ws-opt-icon">${iconSvg}</span><span><span class="ws-opt-name">${esc(label)}</span>${meta?`<span class="ws-opt-meta">${esc(meta)}</span>`:''}</span>`;
  opt.onclick=onClick;
  return opt;
}

function _positionComposerWsDropdown(){
  const dd=$('composerWsDropdown');
  const chip=$('composerWorkspaceChip');
  const footer=document.querySelector('.composer-footer');
  if(!dd||!chip||!footer){
    console.error('[Workspace] Positioning failed - missing element:', {dd:!!dd, chip:!!chip, footer:!!footer});
    return;
  }
  const chipRect=chip.getBoundingClientRect();
  const footerRect=footer.getBoundingClientRect();
  const viewportHeight=window.innerHeight;
  
  // Get actual dropdown height now that it's rendered
  const ddHeight=dd.offsetHeight || 300;
  
  // Position dropdown above the chip by default
  let bottom=footerRect.height - (chipRect.top - footerRect.top) + 8;
  let left=chipRect.left - footerRect.left;
  
  // Check available space
  const spaceAbove=chipRect.top;
  const spaceBelow=viewportHeight - chipRect.bottom;
  
  // // console.log('[Workspace] Positioning:', {spaceAbove, spaceBelow, ddHeight, chipTop: chipRect.top, footerBottom: footerRect.top});
  
  // If not enough space above but enough below, position below
  if(spaceAbove < ddHeight + 20 && spaceBelow > ddHeight + 20){
    // // console.log('[Workspace] Positioning BELOW chip');
    bottom = -(ddHeight + 8 + (chipRect.bottom - footerRect.top));
  } else {
    // // console.log('[Workspace] Positioning ABOVE chip');
  }
  
  const maxLeft=Math.max(0, footer.clientWidth - dd.offsetWidth);
  left=Math.max(0, Math.min(left, maxLeft));
  
  dd.style.bottom=`${bottom}px`;
  dd.style.left=`${left}px`;
  
  // // console.log('[Workspace] Final position:', {bottom, left, ddHeight: dd.offsetHeight});
}

function renderWorkspaceDropdownInto(dd, workspaces, currentWs){
  if(!dd)return;
  dd.innerHTML='';

  // Add default /home/house workspaces for each machine at the top
  const machineDefaults = [
    { name: 'ubuntu', path: '/home/house', _machine: 'ubuntu' },
    { name: 'pop! os', path: '/home/house', _machine: 'popos' }
  ];

  for (const m of machineDefaults) {
    const opt = document.createElement('div');
    // Include machine in active check to distinguish between same path on different machines
    const isActive = m.path === currentWs && S.session && S.session.machine_id === m._machine;
    opt.className = 'ws-opt' + (isActive ? ' active' : '');
    opt.style.pointerEvents = 'auto';
    opt.style.cursor = 'pointer';
    // Directory name as main text, computer name colored in subtext
    const dirName = m.path.split('/').filter(Boolean).pop() || m.path;
    const machineColor = m._machine === 'ubuntu' ? '#3b82f6' : '#f4ae11';
    const machineLabel = m._machine === 'ubuntu' ? 'ubuntu' : "pop! os";
    opt.innerHTML = `<span class="ws-opt-name">${esc(dirName)}</span><span class="ws-opt-path" style="color:${machineColor}">${esc(machineLabel)}</span>`;
    opt.addEventListener('click', async function(e){
      console.log('[Workspace] Machine default clicked:', m.path, m.name, m._machine);
      e.stopPropagation();
      console.log('[Workspace] Calling switchToWorkspace with machine:', m._machine);
      await window.switchToWorkspace(m.path, m.name, m._machine);
      console.log('[Workspace] switchToWorkspace completed, closing dropdown...');
      closeWsDropdown();
    });
    dd.appendChild(opt);
  }

  // Add separator after machine defaults
  const machineDiv = document.createElement('div');
  machineDiv.className = 'ws-divider';
  dd.appendChild(machineDiv);

  // Add remote paths from localStorage (paths added to each machine)
  const remotePaths = _getRemotePaths();
  for (const computer of REMOTE_COMPUTERS) {
    const computerPaths = remotePaths[computer.id] || [];
    for (const p of computerPaths) {
      // Skip paths that are already the machine home
      if (p === computer.home) continue;
      const opt = document.createElement('div');
      opt.className = 'ws-opt' + (p === currentWs ? ' active' : '');
      opt.style.pointerEvents = 'auto';
      opt.style.cursor = 'pointer';
      const pathName = p.split('/').filter(Boolean).pop() || p;
      // Color: blue for ubuntu, yellow for pop! os
      const machineColor = computer.id === 'ubuntu' ? '#3b82f6' : '#f4ae11';
      const machineLabel = computer.id === 'ubuntu' ? 'ubuntu' : "pop! os";
      opt.innerHTML = `<span class="ws-opt-name">${esc(pathName)}</span><span class="ws-opt-path" style="color:${machineColor}">${esc(machineLabel)}</span>`;
      opt.addEventListener('click', async function(e){
        e.stopPropagation();
        await window.switchToWorkspace(p, computer.name, computer.id);
        closeWsDropdown();
      });
      dd.appendChild(opt);
    }
  }

  // Add another separator if there are remote paths
  const hasRemotePaths = REMOTE_COMPUTERS.some(c => (remotePaths[c.id] || []).length > 0);
  if (hasRemotePaths) {
    const remoteDiv = document.createElement('div');
    remoteDiv.className = 'ws-divider';
    dd.appendChild(remoteDiv);
  }

  // Add existing workspaces (excluding /home/house since it's shown as machine default)
  for(const w of workspaces){
    if (w.path === '/home/house') continue;

    const opt=document.createElement('div');
    opt.className='ws-opt'+(w.path===currentWs?' active':'');
    opt.style.pointerEvents='auto';
    opt.style.cursor='pointer';
    // Directory name as main text, computer name colored in subtext
    const machineColor = w._machine === 'ubuntu' ? '#3b82f6' : (w._machine === 'popos' ? '#f4ae11' : 'var(--muted)');
    const machineLabel = w._machine === 'ubuntu' ? 'ubuntu' : (w._machine === 'popos' ? "pop! os" : w._machine);
    const subtext = w._machine ? `<span class="ws-opt-path" style="color:${machineColor}">${esc(machineLabel)}</span>` : `<span class="ws-opt-path">${esc(w.path)}</span>`;
    opt.innerHTML=`<span class="ws-opt-name">${esc(w.name)}</span>${subtext}`;
    opt.addEventListener('click', async function(e){
      console.log('[Workspace] Option clicked:', w.path, w.name);
      e.stopPropagation();
      console.log('[Workspace] Calling switchToWorkspace...');
      await window.switchToWorkspace(w.path, w.name, w._machine);
      console.log('[Workspace] switchToWorkspace completed, closing dropdown...');
      closeWsDropdown();
    });
    dd.appendChild(opt);
  }
  dd.appendChild(document.createElement('div')).className='ws-divider';
  dd.appendChild(_renderWorkspaceAction(
    t('workspace_choose_path'),
    t('workspace_choose_path_meta'),
    li('folder',12),
    ()=>{promptWorkspacePath();}
  ));
  const div=document.createElement('div');div.className='ws-divider';dd.appendChild(div);
  dd.appendChild(_renderWorkspaceAction(
    t('workspace_manage'),
    t('workspace_manage_meta'),
    GEAR_ICON_SVG,
    ()=>{closeWsDropdown();mobileSwitchPanel('workspaces');}
  ));
}

function toggleWsDropdown(){
  const dd=$('wsDropdown');
  if(!dd)return;
  const open=dd.classList.contains('open');
  if(open){closeWsDropdown();}
  else{
    closeProfileDropdown(); // close profile dropdown if open
    loadWorkspaceList().then(data=>{
      renderWorkspaceDropdownInto(dd, data.workspaces, S.session?S.session.workspace:'');
      dd.classList.add('open');
    });
  }
}

function toggleComposerWsDropdown(){
  const dd=$('composerWsDropdown');
  const chip=$('composerWorkspaceChip');
  if(!dd||!chip){
    console.error('[Workspace] Dropdown or chip not found:', {dd:!!dd, chip:!!chip});
    return;
  }
  const open=dd.classList.contains('open');
  if(open){
    closeWsDropdown();
  } else{
    closeProfileDropdown();
    if(typeof closeModelDropdown==='function') closeModelDropdown();
    loadWorkspaceList().then(data=>{
      renderWorkspaceDropdownInto(dd, data.workspaces, S.session?S.session.workspace:'');
      dd.classList.add('open');
      _positionComposerWsDropdown();
      chip.classList.add('active');
    }).catch(e=>{
      console.error('[Workspace] Failed to load workspaces:', e);
    });
  }
}

// Expose globally
window.toggleComposerWsDropdown = toggleComposerWsDropdown;

function closeWsDropdown(){
  const dd=$('wsDropdown');
  const composerDd=$('composerWsDropdown');
  const composerChip=$('composerWorkspaceChip');
  if(dd)dd.classList.remove('open');
  if(composerDd)composerDd.classList.remove('open');
  if(composerChip)composerChip.classList.remove('active');
}
document.addEventListener('click',e=>{
  if(
    !e.target.closest('#composerWorkspaceChip') &&
    !e.target.closest('#composerWsDropdown')
  ) closeWsDropdown();
});
window.addEventListener('resize',()=>{
  const dd=$('composerWsDropdown');
  if(dd&&dd.classList.contains('open')) _positionComposerWsDropdown();
});

async function loadWorkspacesPanel(){
  const panel=$('workspacesPanel');
  console.log('[loadWorkspacesPanel] Panel element:', panel);
  if(!panel){
    console.error('[loadWorkspacesPanel] Panel element not found!');
    return;
  }
  // Clear cache to ensure fresh data
  try { localStorage.removeItem('hermes-workspaces-cache'); } catch (e) {}
  // Sync remote paths from server so Tauri/browser share paths
  await _syncRemotePathsFromServer();
  console.log('[loadWorkspacesPanel] Loading workspace list...');
  const data=await loadWorkspaceList();
  console.log('[loadWorkspacesPanel] Data received:', data);
  console.log('[loadWorkspacesPanel] Workspaces count:', data.workspaces ? data.workspaces.length : 0);
  renderWorkspacesPanel(data.workspaces);
}

// ── Remote computer cards ───────────────────────────────────────────────
const REMOTE_COMPUTERS=[
  {id:'ubuntu',name:'ubuntu home',color:'rgba(59,130,246,0.08)',border:'rgba(59,130,246,0.3)',ip:'192.168.4.250',home:'/home/house'},
  {id:'popos',name:'pop! os home',color:'rgba(244,174,17,0.08)',border:'rgba(244,174,17,0.3)',ip:'192.168.4.233',home:'/home/house'},
];

// Gear icon SVG (matches the profile dropdown "manage profiles" icon)
const GEAR_ICON_SVG = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`;

function _getRemotePaths(){
  try{
    const raw=localStorage.getItem('hermes-remote-paths');
    return raw?JSON.parse(raw):{};
  }catch(e){return {};}
}

async function _syncRemotePathsFromServer(){
  try{
    let localPaths=_getRemotePaths();
    // Pull from server first (server is source of truth)
    const data=await api('/api/remote_paths');
    const serverPaths=data.paths||{};
    let merged=false;
    for(const key of ['ubuntu','popos',...Object.keys(serverPaths)]){
      const serverList=serverPaths[key]||[];
      const localList=localPaths[key]||[];
      const combined=[...new Set([...localList,...serverList])];
      if(JSON.stringify(combined)!==JSON.stringify(localPaths[key]||[])){
        localPaths[key]=combined;
        merged=true;
      }
    }
    if(merged || Object.keys(localPaths).length===0){
      _saveRemotePaths(localPaths,false);
    }
    // Push merged data back so other clients stay in sync
    try{
      await api('/api/remote_paths',{method:'POST',body:JSON.stringify({paths:localPaths})});
    }catch(e){
      console.warn('[remote_paths] Failed to push merged paths to server:',e);
    }
  }catch(e){
    console.warn('[remote_paths] Failed to sync from server:',e);
  }
}

function _seedRemotePathsIfEmpty(){
  // Try to sync from server on startup so Tauri/browser share paths
  _syncRemotePathsFromServer();
}

function _saveRemotePaths(data, syncToServer=true){
  try{
    localStorage.setItem('hermes-remote-paths',JSON.stringify(data));
  }catch(e){}
  if(syncToServer){
    api('/api/remote_paths',{method:'POST',body:JSON.stringify({paths:data})}).catch(e=>{
      console.warn('[remote_paths] Failed to sync to server:',e);
    });
  }
}

function _normalizePath(path){
  if(!path) return '';
  return path.trim().replace(/\/$/,'');
}

function _addRemotePath(computerId,path){
  const data=_getRemotePaths();
  if(!data[computerId]) data[computerId]=[];
  const normalized=_normalizePath(path);
  if(!normalized) return;
  const existing=data[computerId].map(_normalizePath);
  if(!existing.includes(normalized)){
    data[computerId].push(normalized);
    _saveRemotePaths(data);
  }
}

function _removeRemotePath(computerId,path){
  const data=_getRemotePaths();
  if(!data[computerId]) return;
  const normalized=_normalizePath(path);
  data[computerId]=data[computerId].filter(p=>_normalizePath(p)!==normalized);
  _saveRemotePaths(data);
}

function _showRemotePathModal(computerId){
  const computer=REMOTE_COMPUTERS.find(c=>c.id===computerId);
  if(!computer) return;
  showPromptDialog({
    title:'Add path for '+computer.name,
    message:'Enter the path to add:',
    confirmLabel:'Add',
    cancelLabel:'Cancel',
    placeholder:'/path/to/workspace',
    value:''
  }).then(async (path)=>{
    if(!path||!path.trim()) return;
    path=path.trim();
    try{
      const data=await api('/api/workspaces/add',{method:'POST',body:JSON.stringify({path})});
      _workspaceList=data.workspaces;
      _addRemotePath(computerId,path);
      loadWorkspacesPanel();
    }catch(e){
      setStatus('Failed to add: '+e.message);
    }
  });
}

function _showRemotePathContextMenu(event,computerId,path){
  event.preventDefault();
  event.stopPropagation();
  const computer=REMOTE_COMPUTERS.find(c=>c.id===computerId);
  if(!computer) return;

  const menu=document.createElement('div');
  menu.className='machine-context-menu';
  menu.style.cssText='position:fixed;background:#0a0a0a;border:1px solid rgba(255,255,255,0.1);border-radius:8px;box-shadow:0 4px 24px rgba(0,0,0,.6);z-index:1000;min-width:160px;overflow:hidden;';
  
  // Estimate menu height (2 items ~70px)
  const menuHeight = 70;
  const menuWidth = 160;
  
  // Adjust position to stay within viewport
  let x = event.clientX;
  let y = event.clientY;
  
  if (y + menuHeight > window.innerHeight) {
    y = Math.max(10, y - menuHeight);
  }
  if (x + menuWidth > window.innerWidth) {
    x = Math.max(10, x - menuWidth);
  }
  
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';

  // Rename option
  const renameOpt=document.createElement('div');
  renameOpt.style.cssText='padding:8px 14px;font-size:12px;color:var(--text);cursor:pointer;transition:background .12s;text-transform:lowercase;';
  renameOpt.textContent='rename';
  renameOpt.onmouseover=()=>renameOpt.style.background='rgba(255,255,255,.05)';
  renameOpt.onmouseout=()=>renameOpt.style.background='';
  renameOpt.onclick=()=>{
    _showRenamePathModal(computerId,path);
    document.body.removeChild(menu);
  };

  // Remove option
  const deleteOpt=document.createElement('div');
  deleteOpt.style.cssText='padding:8px 14px;font-size:12px;color:#f87171;cursor:pointer;transition:background .12s;text-transform:lowercase;border-top:1px solid rgba(255,255,255,0.05);';
  deleteOpt.textContent='remove';
  deleteOpt.onmouseover=()=>deleteOpt.style.background='rgba(248,113,113,.08)';
  deleteOpt.onmouseout=()=>deleteOpt.style.background='';
  deleteOpt.onclick=()=>{
    _removeRemotePath(computerId,path);
    loadWorkspacesPanel();
    document.body.removeChild(menu);
  };

  menu.appendChild(renameOpt);
  menu.appendChild(deleteOpt);
  document.body.appendChild(menu);

  const closeMenu=()=>{if(menu.parentNode) document.body.removeChild(menu);};
  const handleClickOutside=(e)=>{if(!menu.contains(e.target)) closeMenu(); document.removeEventListener('click',handleClickOutside);};
  setTimeout(()=>document.addEventListener('click',handleClickOutside),10);
}

function _showRenamePathModal(computerId,oldPath){
  const computer=REMOTE_COMPUTERS.find(c=>c.id===computerId);
  if(!computer) return;
  showPromptDialog({
    title:'rename path',
    message:'enter new path:',
    confirmLabel:'rename',
    cancelLabel:'cancel',
    placeholder:oldPath,
    value:oldPath
  }).then((newPath)=>{
    if(!newPath||!newPath.trim()||newPath.trim()===oldPath) return;
    newPath=newPath.trim();
    // Remove old path and add new one
    _removeRemotePath(computerId,oldPath);
    _addRemotePath(computerId,newPath);
    loadWorkspacesPanel();
  });
}

function _showLocalWorkspaceContextMenu(event,path,name){
  event.preventDefault();
  event.stopPropagation();

  const menu=document.createElement('div');
  menu.className='machine-context-menu';
  menu.style.cssText='position:fixed;background:#0a0a0a;border:1px solid rgba(255,255,255,0.1);border-radius:8px;box-shadow:0 4px 24px rgba(0,0,0,.6);z-index:1000;min-width:160px;overflow:hidden;';
  menu.style.left=event.clientX+'px';
  menu.style.top=event.clientY+'px';

  // Switch option
  const switchOpt=document.createElement('div');
  switchOpt.style.cssText='padding:8px 14px;font-size:12px;color:var(--text);cursor:pointer;transition:background .12s;text-transform:lowercase;';
  switchOpt.textContent='switch to workspace';
  switchOpt.onmouseover=()=>switchOpt.style.background='rgba(255,255,255,.05)';
  switchOpt.onmouseout=()=>switchOpt.style.background='transparent';
  switchOpt.onclick=()=>{
    document.body.removeChild(menu);
    switchToWorkspace(path,name);
  };

  // Remove option (with confirmation dialog - but we can make it a simpler inline confirm)
  const removeOpt=document.createElement('div');
  removeOpt.style.cssText='padding:8px 14px;font-size:12px;color:#f87171;cursor:pointer;transition:background .12s;text-transform:lowercase;border-top:1px solid rgba(255,255,255,0.05);';
  removeOpt.textContent='remove';
  removeOpt.onmouseover=()=>removeOpt.style.background='rgba(248,113,113,.08)';
  removeOpt.onmouseout=()=>removeOpt.style.background='transparent';
  removeOpt.onclick=()=>{
    document.body.removeChild(menu);
    _removeLocalWorkspace(path);
  };

  menu.appendChild(switchOpt);
  menu.appendChild(removeOpt);
  document.body.appendChild(menu);

  const closeMenu=()=>{if(menu.parentNode) document.body.removeChild(menu);};
  const handleClickOutside=(e)=>{if(!menu.contains(e.target)) closeMenu(); document.removeEventListener('click',handleClickOutside);};
  setTimeout(()=>document.addEventListener('click',handleClickOutside),10);
}

async function _removeLocalWorkspace(path){
  try{
    const data=await api('/api/workspaces/remove',{method:'POST',body:JSON.stringify({path})});
    _workspaceList=data.workspaces;
    renderWorkspacesPanel(data.workspaces);
  }catch(e){setStatus(t('remove_failed')+e.message);}
}

function _renderComputerCard(computer){
  const paths=_getRemotePaths();
  const computerPaths=paths[computer.id]||[];

  const card=document.createElement('div');
  card.className='ws-machine-card';
  card.style.cssText='margin-bottom:12px;border:1px solid '+computer.border+';border-radius:12px;background:'+computer.color+';overflow:hidden;';
  
  const header=document.createElement('div');
  header.style.cssText='padding:12px 14px;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:10px;transition:background .12s;border-radius:12px 12px 0 0;';
  header.onmouseenter=()=>header.style.background='rgba(255,255,255,.04)';
  header.onmouseleave=()=>header.style.background='transparent';
  header.title='Click to open ' + computer.home + ' on ' + computer.name;
  header.onclick=(e)=>{
    if(e.button===2) return;
    console.log('[CardHeader] Clicked:', computer.home, 'machine:', computer.id);
    switchToWorkspace(computer.home, computer.name+' (remote)', computer.id);
  };
  header.oncontextmenu=(e)=>{
    e.preventDefault();
    e.stopPropagation();
    const menu=document.createElement('div');
    menu.className='machine-context-menu';
    menu.style.cssText='position:fixed;background:#0a0a0a;border:1px solid rgba(255,255,255,0.1);border-radius:8px;box-shadow:0 4px 24px rgba(0,0,0,.6);z-index:1000;min-width:160px;overflow:hidden;';
    menu.style.left=e.clientX+'px';
    menu.style.top=e.clientY+'px';

    const addOpt=document.createElement('div');
    addOpt.style.cssText='padding:8px 14px;font-size:12px;color:var(--text);cursor:pointer;transition:background .12s;text-transform:lowercase;background:transparent;';
    addOpt.textContent='add';
    addOpt.onmouseover=()=>addOpt.style.background='rgba(255,255,255,.05)';
    addOpt.onmouseout=()=>addOpt.style.background='transparent';
    addOpt.onclick=()=>{
      _showRemotePathModal(computer.id);
      document.body.removeChild(menu);
    };

    menu.appendChild(addOpt);
    document.body.appendChild(menu);

    const closeMenu=()=>{if(menu.parentNode) document.body.removeChild(menu);};
    const handleClickOutside=(ev)=>{if(!menu.contains(ev.target)) closeMenu(); document.removeEventListener('click',handleClickOutside);};
    setTimeout(()=>document.addEventListener('click',handleClickOutside),10);
  };
  
  const nameSpan=document.createElement('span');
  nameSpan.style.cssText='font-size:13px;font-weight:600;color:var(--text);';
  nameSpan.textContent=computer.name;
  
  const ipSpan=document.createElement('span');
  ipSpan.style.cssText='font-size:11px;color:var(--muted);';
  ipSpan.textContent=computer.ip;
  
  header.appendChild(nameSpan);
  header.appendChild(ipSpan);
  
  card.appendChild(header);
  
  if(computerPaths.length>0){
    const body=document.createElement('div');
    body.style.cssText='padding:0 14px 12px 14px;';
    
    for(const p of computerPaths){
      const pathCard=document.createElement('div');
      pathCard.style.cssText='padding:8px 10px;margin-top:6px;border-radius:10px;background:rgba(255,255,255,.05);border:1px solid var(--border);cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:8px;';
      pathCard.onclick=async (e)=>{
        if(e.button===2) return;
        e.stopPropagation();
        console.log('[PathCard] Clicked:', p, 'machine:', computer.id);
        // Ensure path is in backend workspace list before switching (skip local validation for remote paths)
        try{
          await api('/api/workspaces/add',{method:'POST',body:JSON.stringify({path:p,skip_validation:true})});
        }catch(e){
          // If already in list, that's fine - proceed with switch
          if(!e.message.includes('already in list')){
            console.warn('[PathCard] Failed to add path to backend:', e);
          }
        }
        await switchToWorkspace(p, computer.name, computer.id);
      };
      pathCard.oncontextmenu=(e)=>_showRemotePathContextMenu(e,computer.id,p);

      const pathText=document.createElement('span');
      pathText.style.cssText='font-size:12px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;';
      pathText.textContent=p;

      // Inline delete button for discoverability
      const delBtn=document.createElement('button');
      delBtn.type='button';
      delBtn.innerHTML='&times;';
      delBtn.style.cssText='width:20px;height:20px;border-radius:4px;border:none;background:transparent;color:var(--muted);font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .1s,color .1s,background .1s;';
      delBtn.title='remove path';
      delBtn.onclick=(e)=>{
        e.stopPropagation();
        _removeRemotePath(computer.id,p);
        loadWorkspacesPanel();
      };
      delBtn.onmouseover=()=>{delBtn.style.color='#f87171';delBtn.style.background='rgba(248,113,113,.1)';};
      delBtn.onmouseout=()=>{delBtn.style.color='var(--muted)';delBtn.style.background='transparent';};
      pathCard.onmouseenter=()=>delBtn.style.opacity='1';
      pathCard.onmouseleave=()=>delBtn.style.opacity='0';

      pathCard.appendChild(pathText);
      pathCard.appendChild(delBtn);
      body.appendChild(pathCard);
    }
    
    card.appendChild(body);
  }
  
  // Add path button at bottom for discoverability
  const addBtn=document.createElement('button');
  addBtn.type='button';
  addBtn.textContent='+ add path';
  addBtn.style.cssText='margin:8px 14px 12px 14px;padding:6px 10px;font-size:11px;color:var(--muted);background:transparent;border:1px dashed var(--border);border-radius:6px;cursor:pointer;transition:all .12s;text-transform:lowercase;width:calc(100% - 28px);';
  addBtn.onmouseover=()=>{addBtn.style.color='var(--text)';addBtn.style.borderColor='rgba(255,255,255,0.2)';};
  addBtn.onmouseout=()=>{addBtn.style.color='var(--muted)';addBtn.style.borderColor='var(--border)';};
  addBtn.onclick=()=>_showRemotePathModal(computer.id);
  card.appendChild(addBtn);
  
  return card;
}

function renderWorkspacesPanel(workspaces){
  const panel=$('workspacesPanel');
  panel.innerHTML='';
  const currentWs = S.session ? S.session.workspace : '';

  // Merge local workspaces into remote paths so everything shows in machine cards
  if(workspaces && workspaces.length){
    const remotePaths=_getRemotePaths();
    let changed=false;
    for(const w of workspaces){
      // Add local workspace paths to the 'popos' card (local machine)
      // Deduplicate against existing remote paths
      if(!remotePaths['popos']) remotePaths['popos']=[];
      const norm=_normalizePath(w.path);
      if(norm && !remotePaths['popos'].map(_normalizePath).includes(norm)){
        remotePaths['popos'].push(norm);
        changed=true;
      }
    }
    if(changed){
      _saveRemotePaths(remotePaths,false);
    }
  }

  // Render remote computer cards
  for(const computer of REMOTE_COMPUTERS){
    panel.appendChild(_renderComputerCard(computer));
  }

  // Add path input row (adds to local machine card)
  const addRow=document.createElement('div');addRow.className='ws-add-row';
  addRow.style.marginTop='8px';
  addRow.innerHTML=`
    <input id="wsAddInput" placeholder="${esc(t('workspace_add_path_placeholder'))}" style="flex:1;background:rgba(255,255,255,.06);border:1px solid var(--border2);border-radius:7px;color:var(--text);padding:7px 10px;font-size:12px;outline:none;">
    <button class="ws-action-btn" onclick="addRemoteWorkspacePath()">${li('plus',12)} ${esc(t('add'))}</button>`;
  panel.appendChild(addRow);
  const hint=document.createElement('div');
  hint.style.cssText='font-size:11px;color:var(--muted);padding:4px 0 8px';
  hint.textContent=t('workspace_paths_validated_hint');
  panel.appendChild(hint);
}

function addRemoteWorkspacePath(){
  const input=$('wsAddInput');
  const path=(input?input.value:'').trim();
  if(!path) return;
  _addRemotePath('popos',path);
  loadWorkspacesPanel();
  if(input) input.value='';
}

async function addWorkspace(){
  const input=$('wsAddInput');
  const path=(input?input.value:'').trim();
  if(!path)return;
  try{
    const data=await api('/api/workspaces/add',{method:'POST',body:JSON.stringify({path})});
    _workspaceList=data.workspaces;
    renderWorkspacesPanel(data.workspaces);
    if(input)input.value='';
  }catch(e){setStatus(t('add_failed')+e.message);}
}

async function removeWorkspace(path){
  // Remove without showing fullscreen modal - use direct removal
  try{
    const data=await api('/api/workspaces/remove',{method:'POST',body:JSON.stringify({path})});
    _workspaceList=data.workspaces;
    renderWorkspacesPanel(data.workspaces);
  }catch(e){setStatus(t('remove_failed')+e.message);}
}

async function promptWorkspacePath(){
  if(!S.session)return;
  const value=await showPromptDialog({
    title:t('workspace_switch_prompt_title'),
    message:t('workspace_switch_prompt_message'),
    confirmLabel:t('workspace_switch_prompt_confirm'),
    placeholder:t('workspace_switch_prompt_placeholder'),
    value:S.session.workspace||''
  });
  const path=(value||'').trim();
  if(!path)return;
  try{
    const data=await api('/api/workspaces/add',{method:'POST',body:JSON.stringify({path})});
    _workspaceList=data.workspaces||[];
    const target=_workspaceList[_workspaceList.length-1];
    if(!target) throw new Error(t('workspace_not_added'));
    await switchToWorkspace(target.path,target.name);
  }catch(e){
    if(String(e.message||'').includes('Workspace already in list')){
      return;
    }
    setStatus(t('workspace_switch_failed')+e.message);
  }
}

window.switchToWorkspace = async function switchToWorkspace(path,name,machineId){
  console.log('[WS] === START ===', path, name, machineId);
  console.log('[WS] S.session before:', S.session);

  if (S.busy) {
    if (typeof showToast === 'function') showToast(t('workspace_busy_switch'));
    return;
  }

  const sessionInProgress = S.session && Array.isArray(S.messages) && S.messages.length > 0;
  const machines = typeof getMachines === 'function' ? getMachines() : [];
  const machine = machineId ? machines.find(function(m){ return m.id === machineId; }) : null;
  const machineHostname = machine ? machine.hostname : null;
  const machinePayload = machine ? {machine_id: machineId, machine_hostname: machineHostname} : {};

  if(!S.session || sessionInProgress){
    if (sessionInProgress) {
      console.log('[WS] Existing session has messages; creating a fresh session for workspace switch');
    } else {
      console.log('[WS] No session - creating new one for:', path);
    }

    try{
      const model = ($('modelSelect') && $('modelSelect').value) || 'openai/gpt-4o';
      console.log('[WS] Creating session with model:', model, 'workspace:', path, 'machineId:', machineId);
      console.log('[WS] getMachines available?:', typeof getMachines === 'function');
      console.log('[WS] Machines:', machines);
      const requestBody = {
        model: model,
        workspace: path,
        ...machinePayload
      };
      console.log('[WS] Request body:', JSON.stringify(requestBody));
      const data = await api('/api/session/new',{method:'POST',body:JSON.stringify(requestBody)});
      console.log('[WS] Session API response:', JSON.stringify(data));

      // Handle both {session: {...}} and direct {...} formats
      S.session = data.session || data;
      console.log('[WS] S.session set to:', S.session);
      console.log('[WS] S.session.machine_id:', S.session.machine_id);
      console.log('[WS] S.session.machine_hostname:', S.session.machine_hostname);

      // Save to localStorage
      if(S.session && S.session.session_id){
        localStorage.setItem('hermes-webui-session', S.session.session_id);
        console.log('[WS] Saved session_id to localStorage');
      }

      syncTopbar();
      syncWorkspaceDisplays();

      // Open workspace panel using the proper function
      if(typeof openWorkspacePanel==='function'){
        openWorkspacePanel('browse');
      } else {
        // Fallback: manual panel open
        var layout=document.querySelector('.layout');
        if(layout) layout.classList.remove('workspace-panel-collapsed');
        var rp=document.querySelector('.rightpanel');
        if(rp) rp.style.display='';
        if(typeof syncWorkspacePanelState==='function') syncWorkspacePanelState();
      }

      await loadDir('.');
      if(typeof closeWsDropdown==='function') closeWsDropdown();
      return;
    }catch(e){
      console.error('[WS] Session creation FAILED:', e);
      if(typeof showToast === 'function') showToast(t('workspace_switch_failed') + e.message, 4000);
      return;
    }
  }
  
  try{
    console.log('[WS] Existing session - updating workspace to:', path);
    if(typeof closeWsDropdown==='function') closeWsDropdown();
    
    console.log('[WS] Calling API to update session...');
    var requestBody = {
      session_id: S.session.session_id,
      workspace: path,
      model: S.session.model,
      ...machinePayload
    };
    console.log('[WS] Request body:', JSON.stringify(requestBody));
    var r=await api('/api/session/update',{method:'POST',body:JSON.stringify(requestBody)});
    console.log('[WS] API response:', r);

    console.log('[WS] Updating S.session.workspace to:', path);
    S.session.workspace = path;
    if (machine) {
      S.session.machine_id = machineId;
      S.session.machine_hostname = machineHostname;
    }
    
    syncTopbar();
    syncWorkspaceDisplays();
    
    // Open workspace panel
    console.log('[WS] Opening workspace panel...');
    if(typeof openWorkspacePanel==='function'){
      openWorkspacePanel('browse');
    } else {
      // Fallback: manual panel open
      var layout=document.querySelector('.layout');
      if(layout) layout.classList.remove('workspace-panel-collapsed');
      var rp=document.querySelector('.rightpanel');
      if(rp) rp.style.display='';
      if(typeof syncWorkspacePanelState==='function') syncWorkspacePanelState();
    }
    
    // Clear directory cache to force fresh load from potentially different machine
    S._dirCache = {};
    localStorage.removeItem('hermes-dircache:' + S.session.session_id + ':.');
    
    await loadDir('.');
    console.log('[WS] === SUCCESS ===');
  }catch(e){
    console.error('[WS] Workspace update FAILED:', e);
    if(typeof showToast === 'function') showToast(t('workspace_switch_failed') + e.message, 4000);
  }
}

// ── Profile panel + dropdown ──
let _profilesCache = null;

async function loadProfilesPanel() {
  const panel = $('profilesPanel');
  if (!panel) return;
  // Show cached profiles instantly while fetching fresh data
  if (!_profilesCache) {
    let cached = null;
    try { cached = localStorage.getItem('hermes-profiles-cache'); } catch (e) {}
    if (cached) {
      try {
        _profilesCache = JSON.parse(cached);
        _renderProfiles(_profilesCache);
      } catch (e) { /* ignore parse errors */ }
    }
  }
  try {
    const data = await api('/api/profiles');
    console.log('[profiles] API response:', data);
    _profilesCache = data;
    // Cache for instant load next time
    try { localStorage.setItem('hermes-profiles-cache', JSON.stringify(data)); } catch (e) {}
    _renderProfiles(data);
  } catch (e) {
    console.error('[profiles] API error:', e);
    if (!panel.innerHTML || panel.innerHTML.includes('loading')) panel.innerHTML = `<div style="color:var(--accent);font-size:12px;padding:12px">Error: ${esc(e.message)}</div>`;
  }
}

function _renderProfiles(data) {
  const panel = $('profilesPanel');
  if (!panel) return;
  panel.innerHTML = '';
  console.log('[profiles] Rendering profiles:', data);
  if (!data || !data.profiles || !data.profiles.length) {
    panel.innerHTML = `<div style="padding:16px;color:var(--muted);font-size:12px">${esc(t('profiles_no_profiles'))}</div>`;
    return;
  }
  for (const p of data.profiles) {
    try {
      const card = document.createElement('div');
      card.className = 'profile-card';
      const meta = [];
      if (p.model) meta.push(p.model.split('/').pop());
      if (p.provider) meta.push(p.provider);
      if (p.skill_count) meta.push(t('profile_skill_count', p.skill_count));
      if (p.has_env) meta.push(t('profile_api_keys_configured'));
      const gwDot = p.gateway_running
        ? `<span class="profile-opt-badge running" title="${esc(t('profile_gateway_running'))}"></span>`
        : `<span class="profile-opt-badge stopped" title="${esc(t('profile_gateway_stopped'))}"></span>`;
      const isActive = p.name === data.active;
      const activeBadge = isActive ? `<span style="color:var(--link);font-size:10px;font-weight:600;margin-left:6px">${esc(t('profile_active'))}</span>` : '';
      const deleteBtn = !p.is_default
        ? `<button class="ws-action-btn danger" onclick="deleteProfile('${esc(p.name)}')" title="${esc(t('profile_delete_title'))}">${li('x',12)}</button>`
        : '';
      card.innerHTML = `
        <div class="profile-card-header">
          <div style="min-width:0;flex:1">
            <div class="profile-card-name${isActive ? ' is-active' : ''}">${gwDot}${esc(p.name)}${p.is_default ? ' <span style="opacity:.5">(default)</span>' : ''}${activeBadge}</div>
            ${meta.length ? `<div class="profile-card-meta">${esc(meta.join(' \u00b7 '))}</div>` : ''}
          </div>
          <div class="profile-card-actions">
            ${!isActive ? `<button class="ws-action-btn" onclick="switchToProfile('${esc(p.name)}')" title="${esc(t('profile_switch_title'))}">${esc(t('profile_use'))}</button>` : ''}
            ${deleteBtn}
          </div>
        </div>`;
      panel.appendChild(card);
    } catch (cardErr) {
      console.error('[profiles] Failed to render profile card:', p, cardErr);
    }
  }
}

function _positionProfileDropdown(){
  const dd=$('profileDropdown');
  const chip=$('profileChip');
  if(!dd||!chip) return;
  const chipRect=chip.getBoundingClientRect();
  const ddHeight=dd.offsetHeight || 240;
  const bottom = window.innerHeight - chipRect.top + 8;
  const left = Math.max(8, Math.min(chipRect.left, window.innerWidth - dd.offsetWidth - 8));
  dd.style.left = `${left}px`;
  dd.style.top = `${chipRect.bottom + 6}px`;
}

function renderProfileDropdown(data) {
  const dd = $('profileDropdown');
  if (!dd) return;
  dd.innerHTML = '';
  const active = data.active || '';
  if (!data.profiles || !data.profiles.length) {
    dd.innerHTML = `<div style="padding:16px;color:var(--muted);font-size:12px">${esc(t('profiles_no_profiles'))}</div>`;
    return;
  }
  for (const p of data.profiles) {
    const opt = document.createElement('div');
    opt.className = 'profile-opt' + (p.name === active ? ' active' : '');
    const meta = [];
    if (p.model) meta.push(p.model.split('/').pop());
    if (p.skill_count) meta.push(t('profile_skill_count', p.skill_count));
    const gwDot = `<span class="profile-opt-badge ${p.gateway_running ? 'running' : 'stopped'}"></span>`;
    const checkmark = p.name === active ? ' <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--link)" stroke-width="3" style="vertical-align:-1px"><polyline points="20 6 9 17 4 12"/></svg>' : '';
    opt.innerHTML = `<div class="profile-opt-name">${gwDot}${esc(p.name)}${p.is_default ? ' <span style="opacity:.5;font-weight:400">(default)</span>' : ''}${checkmark}</div>` +
      (meta.length ? `<div class="profile-opt-meta">${esc(meta.join(' · '))}</div>` : '');
    opt.onclick = async () => {
      closeProfileDropdown();
      if (p.name === active) return;
      await switchToProfile(p.name);
    };
    dd.appendChild(opt);
  }
  const div = document.createElement('div'); div.className = 'ws-divider'; dd.appendChild(div);
  const mgmt = document.createElement('div'); mgmt.className = 'profile-opt ws-manage';
  mgmt.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg> ${esc(t('manage_profiles'))}`;
  mgmt.onclick = () => { closeProfileDropdown(); mobileSwitchPanel('profiles'); };
  dd.appendChild(mgmt);
}

function toggleProfileDropdown() {
  const dd = $('profileDropdown');
  if (!dd) return;
  if (dd.classList.contains('open')) { closeProfileDropdown(); return; }
  closeWsDropdown(); // close workspace dropdown if open
  if(typeof closeModelDropdown==='function') closeModelDropdown();
  api('/api/profiles').then(data => {
    renderProfileDropdown(data);
    dd.classList.add('open');
    _positionProfileDropdown();
    const chip=$('profileChip');
    if(chip) chip.classList.add('active');
  }).catch(e => { showToast(t('profiles_load_failed')); });
}

function closeProfileDropdown() {
  const dd = $('profileDropdown');
  if (dd) dd.classList.remove('open');
  const chip=$('profileChip');
  if(chip) chip.classList.remove('active');
}

document.addEventListener('click', e => {
  if (!e.target.closest('#profileChipWrap') && !e.target.closest('#profileDropdown')) closeProfileDropdown();
});
window.addEventListener('resize',()=>{
  const dd=$('profileDropdown');
  if(dd&&dd.classList.contains('open')) _positionProfileDropdown();
});

async function switchToProfile(name) {
  if (S.busy) { showToast(t('profiles_busy_switch')); return; }

  // Determine whether the current session has any messages.
  // A session with messages is "in progress" and belongs to the current profile —
  // we'll start a fresh session for the new profile instead.
  const sessionInProgress = S.session && S.messages && S.messages.length > 0;

  try {
    const data = await api('/api/profile/switch', { method: 'POST', body: JSON.stringify({ name }) });
    S.activeProfile = data.active || name;

    // ── Model ──────────────────────────────────────────────────────────────
    localStorage.removeItem('hermes-webui-model');
    _skillsData = null;
    await populateModelDropdown();
    if (data.default_model) {
      const sel = $('modelSelect');
      const resolved = _applyModelToDropdown(data.default_model, sel);
      const modelToUse = resolved || data.default_model;
      S._pendingProfileModel = modelToUse;
      // Only patch the in-memory session model if we're NOT about to replace the session
      if (S.session && !sessionInProgress) {
        S.session.model = modelToUse;
      }
    }

    // ── Workspace ──────────────────────────────────────────────────────────
    _workspaceList = null;
    await loadWorkspaceList();
    if (data.default_workspace) {
      // Always store the profile default for new sessions
      S._profileDefaultWorkspace = data.default_workspace;

      if (S.session && !sessionInProgress) {
        // Empty session (no messages yet) — safe to update it in place
        try {
          await api('/api/session/update', { method: 'POST', body: JSON.stringify({
            session_id: S.session.session_id,
            workspace: data.default_workspace,
            model: S.session.model,
          })});
          S.session.workspace = data.default_workspace;
        } catch (_) {}
      }
    }

    // ── Session ────────────────────────────────────────────────────────────
    _showAllProfiles = false;

    if (sessionInProgress) {
      // The current session has messages and belongs to the previous profile.
      // Start a new session for the new profile so nothing gets cross-tagged.
      await newSession(false);
      // Apply profile default workspace to the newly created session (fixes #424)
      if (S._profileDefaultWorkspace && S.session) {
        try {
          await api('/api/session/update', { method: 'POST', body: JSON.stringify({
            session_id: S.session.session_id,
            workspace: S._profileDefaultWorkspace,
            model: S.session.model,
          })});
          S.session.workspace = S._profileDefaultWorkspace;
        } catch (_) {}
      }
      updateWorkspaceChip();
      await renderSessionList();
      showToast(t('profile_switched_new_conversation', name));
    } else {
      // No messages yet — just refresh the list and topbar in place
      await renderSessionList();
      syncTopbar();
      showToast(t('profile_switched', name));
    }

    // ── Sidebar panels ─────────────────────────────────────────────────────
    if (_currentPanel === 'skills') await loadSkills();
    if (_currentPanel === 'memory') await loadMemory();
    if (_currentPanel === 'tasks') await loadCrons();
    if (_currentPanel === 'workspaces') await loadWorkspacesPanel();

  } catch (e) { showToast(t('switch_failed') + e.message); }
}

function toggleProfileForm() {
  const form = $('profileCreateForm');
  if (!form) return;
  const open = form.style.display !== 'none';
  if (open) { form.style.display = 'none'; _editingSkillName = null; return; }
  $('profileFormName').value = '';
  $('profileFormClone').checked = false;
  if ($('profileFormBaseUrl')) $('profileFormBaseUrl').value = '';
  if ($('profileFormApiKey')) $('profileFormApiKey').value = '';
  const errEl = $('profileFormError');
  if (errEl) errEl.style.display = 'none';
  $('profileFormName').focus();
}

async function submitProfileCreate() {
  const name = ($('profileFormName').value || '').trim().toLowerCase();
  const cloneConfig = $('profileFormClone').checked;
  const errEl = $('profileFormError');
  if (!name) { errEl.textContent = t('name_required'); errEl.style.display = ''; return; }
  if (!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(name)) { errEl.textContent = t('profile_name_rule'); errEl.style.display = ''; return; }
  try {
    const baseUrl = (($('profileFormBaseUrl') && $('profileFormBaseUrl').value) || '').trim();
    const apiKey = (($('profileFormApiKey') && $('profileFormApiKey').value) || '').trim();
    if (baseUrl && !/^https?:\/\//.test(baseUrl)) {
      errEl.textContent = t('profile_base_url_rule'); errEl.style.display = ''; return;
    }
    const payload = { name, clone_config: cloneConfig };
    if (baseUrl) payload.base_url = baseUrl;
    if (apiKey) payload.api_key = apiKey;
    await api('/api/profile/create', { method: 'POST', body: JSON.stringify(payload) });
    toggleProfileForm();
    await loadProfilesPanel();
    showToast(t('profile_created', name));
  } catch (e) {
    errEl.textContent = e.message || t('create_failed');
    errEl.style.display = '';
  }
}

async function deleteProfile(name) {
  const _delProf=await showConfirmDialog({title:t('profile_delete_confirm_title',name),message:t('profile_delete_confirm_message'),confirmLabel:t('delete_title'),danger:true,focusCancel:true});
  if(!_delProf) return;
  try {
    await api('/api/profile/delete', { method: 'POST', body: JSON.stringify({ name }) });
    await loadProfilesPanel();
    showToast(t('profile_deleted', name));
  } catch (e) { showToast(t('delete_failed') + e.message, 4000); }
}

// ── Wiki Memory Browser ──
const WikiMemoryBrowser = (function() {
  let state = {
    view: 'wiki', // 'wiki' | 'memories'
    items: [],
    filtered: [],
    search: '',
    filter: 'all',
    loading: false,
    currentPage: null
  };

  const categories = {
    wiki: { all: 'all', infrastructure: 'infrastructure', project: 'project', guide: 'guide', notes: 'notes' },
    memories: { all: 'all', observation: 'observation', fact: 'fact', experience: 'experience', task: 'task' }
  };

  function init() {
    bindEvents();
    refresh();
  }

  function bindEvents() {
    // Tab switching
    document.querySelectorAll('.wmb-tab').forEach(tab => {
      tab.addEventListener('click', () => switchView(tab.dataset.tab));
    });

    // Search
    const search = $('wmbSearch');
    if (search) {
      search.addEventListener('input', (e) => {
        state.search = e.target.value.toLowerCase();
        filterItems();
      });
    }

    // Filter
    const filter = $('wmbFilter');
    if (filter) {
      filter.addEventListener('change', (e) => {
        state.filter = e.target.value;
        filterItems();
      });
    }

    // Refresh
    const refresh = $('wmbRefresh');
    if (refresh) {
      refresh.addEventListener('click', () => {
        refresh.classList.add('spinning');
        loadData().then(() => refresh.classList.remove('spinning'));
      });
    }

    // Content click
    const content = $('wmbContent');
    if (content) {
      content.addEventListener('click', handleCardClick);
      content.addEventListener('contextmenu', handleCardRightClick);
    }

    // Close context menu on click elsewhere
    document.addEventListener('click', () => hideContextMenu());
  }

  function switchView(view) {
    state.view = view;
    document.querySelectorAll('.wmb-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === view));
    $('wmbSearch').placeholder = `search ${view}...`;
    updateFilterOptions();
    refresh();
  }

  function updateFilterOptions() {
    const select = $('wmbFilter');
    const cats = categories[state.view];
    select.innerHTML = Object.entries(cats).map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
  }

  async function refresh() {
    await loadData();
  }

  async function loadData() {
    state.loading = true;
    $('wmbLoading').style.display = 'flex';
    $('wmbContent').style.display = 'none';
    $('wmbEmpty').style.display = 'none';

    // Show cached data instantly while fetching fresh data
    const cacheKey = state.view === 'wiki' ? 'hermes-wiki-cache' : 'hermes-memories-cache';
    let cached = null;
    try { cached = localStorage.getItem(cacheKey); } catch (e) {}
    if (cached && state.items.length === 0) {
      try {
        const parsed = JSON.parse(cached);
        if (state.view === 'wiki') {
          state.items = (parsed.pages || parsed || []).map(p => ({...p, type: 'wiki'}));
        } else {
          state.items = (parsed.memories || parsed || []).map(m => ({...m, type: 'memory', title: m.content?.slice(0, 50) || 'Memory ' + m.id}));
        }
        filterItems();
        $('wmbLoading').style.display = 'none';
        $('wmbContent').style.display = state.filtered.length ? '' : 'none';
        $('wmbEmpty').style.display = state.filtered.length ? 'none' : '';
      } catch (e) { /* ignore parse errors */ }
    }

    try {
      if (state.view === 'wiki') {
        const res = await api('/api/wiki/pages');
        state.items = (res.pages || []).map(p => ({...p, type: 'wiki'}));
        // Cache for instant load next time
        try { localStorage.setItem('hermes-wiki-cache', JSON.stringify(res.pages || [])); } catch (e) {}
      } else {
        const res = await api('/api/memory/list');
        state.items = (res.memories || []).map(m => ({...m, type: 'memory', title: m.content?.slice(0, 50) || 'Memory ' + m.id}));
        // Cache for instant load next time
        try { localStorage.setItem('hermes-memories-cache', JSON.stringify(res.memories || [])); } catch (e) {}
      }
      filterItems();
    } catch (e) {
      console.error('Failed to load wiki/memory:', e);
      // Keep cached data if fetch fails
      if (state.items.length === 0) {
        state.items = [];
        filterItems();
      }
    }

    state.loading = false;
    $('wmbLoading').style.display = 'none';
    $('wmbContent').style.display = state.filtered.length ? '' : 'none';
    $('wmbEmpty').style.display = state.filtered.length ? 'none' : '';
  }

  function filterItems() {
    state.filtered = state.items.filter(item => {
      const matchesSearch = !state.search || 
        (item.title || '').toLowerCase().includes(state.search) ||
        (item.content || '').toLowerCase().includes(state.search) ||
        (item.snippet || '').toLowerCase().includes(state.search);
      const matchesFilter = state.filter === 'all' || item.category === state.filter;
      return matchesSearch && matchesFilter;
    });
    render();
  }

  function render() {
    const content = $('wmbContent');
    if (!content) return;

    if (state.filtered.length === 0) {
      content.innerHTML = '';
      return;
    }

    content.innerHTML = state.filtered.map(item => {
      if (item.type === 'wiki') {
        return renderWikiCard(item);
      } else {
        return renderMemoryCard(item);
      }
    }).join('');
  }

  function renderWikiCard(page) {
    const linksOut = parseInt(page.links_out) || 0;
    const linksIn = parseInt(page.links_in) || 0;
    return `
      <div class="wmb-card wmb-card-wiki" data-type="wiki" data-slug="${esc(page.slug)}" data-id="${esc(page.slug)}">
        <div class="wmb-card-category">${esc(page.category || 'notes')}</div>
        <div class="wmb-card-title">${esc(page.title || page.slug)}</div>
        <div class="wmb-card-snippet">${esc(page.snippet || '')}</div>
        <div class="wmb-card-meta">
          <span>${(page.word_count || 0)} words</span>
          <span class="wmb-card-links">
            ${linksIn > 0 ? `<span>${linksIn} in</span>` : ''}
            ${linksOut > 0 ? `<span>${linksOut} out</span>` : ''}
          </span>
        </div>
      </div>
    `;
  }

  function renderMemoryCard(memory) {
    return `
      <div class="wmb-card wmb-card-memory" data-type="memory" data-id="${esc(memory.id)}">
        <div class="wmb-card-category">${esc(memory.category || 'observation')}</div>
        <div class="wmb-card-title">${esc(memory.title)}</div>
        <div class="wmb-card-snippet">${esc(memory.content || '')}</div>
        <div class="wmb-card-meta">
          <span>importance: ${memory.importance || 50}</span>
          ${memory.tags ? `<span>${esc(memory.tags)}</span>` : ''}
        </div>
      </div>
    `;
  }

  function handleCardClick(e) {
    const card = e.target.closest('.wmb-card');
    if (!card) return;

    const type = card.dataset.type;
    const id = card.dataset.id;

    if (type === 'wiki') {
      openWikiPage(id);
    } else if (type === 'memory') {
      showMemoryDetail(id);
    }
  }

  function handleCardRightClick(e) {
    e.preventDefault();
    const card = e.target.closest('.wmb-card');
    if (!card) return;

    const type = card.dataset.type;
    const id = card.dataset.id;
    showContextMenu(e.clientX, e.clientY, type, id);
  }

  function showContextMenu(x, y, type, id) {
    hideContextMenu();
    const menu = document.createElement('div');
    menu.className = 'wmb-context-menu show';
    menu.id = 'wmbContextMenu';
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';

    const isWiki = type === 'wiki';
    menu.innerHTML = `
      <div class="wmb-context-item" onclick="WikiMemoryBrowser.editItem('${type}', '${id}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        edit
      </div>
      ${isWiki ? `<div class="wmb-context-item" onclick="WikiMemoryBrowser.renameItem('${type}', '${id}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        rename
      </div>` : ''}
      <div class="wmb-context-divider"></div>
      <div class="wmb-context-item" onclick="WikiMemoryBrowser.copyLink('${type}', '${id}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
        copy link
      </div>
    `;

    document.body.appendChild(menu);
  }

  function hideContextMenu() {
    const existing = $('wmbContextMenu');
    if (existing) existing.remove();
  }

  async function openWikiPage(slug) {
    try {
      const res = await api(`/api/wiki/pages/${encodeURIComponent(slug)}`);
      const page = res.page || (res.slug ? res : null);
      if (page) {
        state.currentPage = page;
        showWikiModal(page, false);
      }
    } catch (e) {
      console.error('Failed to load wiki page:', e);
    }
  }

  async function editItem(type, id) {
    if (type === 'wiki') {
      try {
        const res = await api(`/api/wiki/pages/${encodeURIComponent(id)}`);
        const page = res.page || (res.slug ? res : null);
        if (page) {
          state.currentPage = page;
          showWikiModal(page, true);
        }
      } catch (e) {
        console.error('Failed to load wiki page for edit:', e);
      }
    }
  }

  function openItem(type, id) {
    if (type === 'wiki') {
      openWikiPage(id);
    } else {
      showMemoryDetail(id);
    }
  }

  function showMemoryDetail(id) {
    const memory = state.items.find(m => String(m.id) === id);
    if (!memory) return;
    // For now, just show in modal view mode
    const modal = $('wmbModal');
    const title = $('wmbModalTitle');
    const editor = $('wmbModalEditor');
    const meta = $('wmbModalMeta');

    title.value = memory.title || '';
    title.readOnly = true;
    editor.value = memory.content || '';
    editor.readOnly = true;
    meta.textContent = `category: ${memory.category || 'observation'} | importance: ${memory.importance || 50}`;

    modal.style.display = 'flex';

    // Show/hide save button based on editable
    const saveBtn = document.querySelector('.wmb-btn-primary');
    if (saveBtn) saveBtn.style.display = 'none';
  }

  function showWikiModal(page, editable) {
    const modal = $('wmbModal');
    const title = $('wmbModalTitle');
    const editor = $('wmbModalEditor');
    const meta = $('wmbModalMeta');

    title.value = page.title || page.slug;
    title.readOnly = !editable;
    editor.value = page.content || '';
    editor.readOnly = !editable;

    const backlinks = (page.backlinks || []).length;
    meta.textContent = `slug: ${page.slug} | category: ${page.category || 'notes'} | updated: ${page.updated_at || 'unknown'} | ${backlinks} backlinks`;

    modal.style.display = 'flex';

    // Show/hide save button based on editable
    const saveBtn = document.querySelector('.wmb-btn-primary');
    if (saveBtn) saveBtn.style.display = editable ? '' : 'none';
  }

  async function saveWikiPage() {
    if (!state.currentPage) return;

    const title = $('wmbModalTitle').value;
    const content = $('wmbModalEditor').value;

    try {
      const res = await api(`/api/wiki/pages/${encodeURIComponent(state.currentPage.slug)}`, {
        method: 'POST',
        body: JSON.stringify({ title, content })
      });

      if (res.ok) {
        closeWikiModal();
        refresh();
        showToast('Page saved');
      } else {
        // // %/ alert('Failed to save: ' + (res.error || 'Unknown error'));
      }
    } catch (e) {
      console.error('Failed to save wiki page:', e);
      // // %/ alert('Failed to save: ' + e.message);
    }
  }

  function copyLink(type, id) {
    const link = type === 'wiki' ? `[[${id}]]` : `memory:${id}`;
    navigator.clipboard.writeText(link).then(() => showToast('Link copied'));
  }

  async function renameItem(type, id) {
    if (type !== 'wiki') return;

    const page = state.items.find(p => p.slug === id);
    if (!page) return;

    const newTitle = prompt('Rename wiki page:', page.title || page.slug);
    if (!newTitle || newTitle === page.title) return;

    try {
      const res = await api('/api/wiki/update', {
        method: 'POST',
        body: JSON.stringify({
          slug: id,
          title: newTitle,
          category: page.category,
          content: page.content
        })
      });
      if (res.ok) {
        showToast('Page renamed');
        refresh();
      } else {
        showToast('Failed to rename: ' + (res.error || 'Unknown error'));
      }
    } catch (e) {
      console.error('Failed to rename wiki page:', e);
      showToast('Failed to rename page');
    }
  }

  return {
    init,
    switchView,
    refresh,
    openWikiPage,
    editItem,
    openItem,
    saveWikiPage,
    copyLink,
    renameItem
  };
})();

function closeWikiModal() {
  $('wmbModal').style.display = 'none';
  WikiMemoryBrowser.currentPage = null;
}

function saveWikiPage() {
  WikiMemoryBrowser.saveWikiPage();
}

// ── Memory panel ──
async function loadMemory(force) {
  // Initialize the wiki memory browser when switching to memory panel
  if (typeof WikiMemoryBrowser !== 'undefined') {
    WikiMemoryBrowser.init();
  }
}

// Drag and drop
const wrap=$('composerWrap');let dragCounter=0;
document.addEventListener('dragover',e=>e.preventDefault());
document.addEventListener('dragenter',e=>{e.preventDefault();if(e.dataTransfer.types.includes('Files')){dragCounter++;wrap.classList.add('drag-over');}});
document.addEventListener('dragleave',e=>{dragCounter--;if(dragCounter<=0){dragCounter=0;wrap.classList.remove('drag-over');}});
document.addEventListener('drop',e=>{e.preventDefault();dragCounter=0;wrap.classList.remove('drag-over');const files=Array.from(e.dataTransfer.files);if(files.length){addFiles(files);$('msg').focus();}});

// ── Settings panel ───────────────────────────────────────────────────────────

let _settingsDirty = false;
let _settingsThemeOnOpen = null; // track theme at open time for discard revert
let _settingsSection = 'conversation';

function switchSettingsSection(name){
  const validSections=['conversation','preferences','system','apikeys','config'];
  const section=validSections.includes(name)?name:'conversation';
  _settingsSection=section;
  const map={conversation:'Conversation',preferences:'Preferences',system:'System',apikeys:'ApiKeys',config:'Config'};
  validSections.forEach(key=>{
    const tab=$('settingsTab'+map[key]);
    const pane=$('settingsPane'+map[key]);
    const active=key===section;
    if(tab){
      tab.classList.toggle('active',active);
      tab.setAttribute('aria-selected',active?'true':'false');
    }
    if(pane) pane.classList.toggle('active',active);
  });
  // Load API keys when switching to apikeys tab
  if(section==='apikeys' && typeof loadApiKeys==='function'){
    loadApiKeys();
  }
  // Load config when switching to config tab
  if(section==='config' && typeof loadHermesConfig==='function'){
    loadHermesConfig();
  }
}

function _syncHermesPanelSessionActions(){
  const hasSession=!!S.session;
  const visibleMessages=hasSession?(S.messages||[]).filter(m=>m&&m.role&&m.role!=='tool').length:0;
  const title=hasSession?(S.session.title||t('untitled')):t('active_conversation_none');
  const meta=$('hermesSessionMeta');
  if(meta){
    meta.textContent=hasSession
      ? t('active_conversation_meta', title, visibleMessages)
      : t('active_conversation_none');
  }
  const setDisabled=(id,disabled)=>{
    const el=$(id);
    if(!el)return;
    el.disabled=!!disabled;
    el.classList.toggle('disabled',!!disabled);
  };
  setDisabled('btnDownload',!hasSession||visibleMessages===0);
  setDisabled('btnExportJSON',!hasSession);
  setDisabled('btnClearConvModal',!hasSession||visibleMessages===0);
}

function toggleSettings(){
  const overlay=$('settingsOverlay');
  if(!overlay) return;
  if(overlay.style.display==='none'){
    _settingsDirty = false;
    try { _settingsThemeOnOpen = localStorage.getItem('hermes-theme'); } catch (e) {}
    _settingsThemeOnOpen = _settingsThemeOnOpen || document.documentElement.dataset.theme || 'dark';
    _settingsSection = 'conversation';
    overlay.style.display='';
    loadSettingsPanel();
  } else {
    _closeSettingsPanel();
  }
}

function _resetSettingsPanelState(){
  _settingsSection = 'conversation';
  switchSettingsSection('conversation');
  const bar=$('settingsUnsavedBar');
  if(bar) bar.style.display='none';
}

function _hideSettingsPanel(){
  const overlay=$('settingsOverlay');
  if(!overlay) return;
  _resetSettingsPanelState();
  overlay.style.display='none';
}

// Close with unsaved-changes check. If dirty, show a confirm dialog.
function _closeSettingsPanel(){
  if(!_settingsDirty){
    // Nothing changed -- revert any live preview and close
    _revertSettingsPreview();
    _hideSettingsPanel();
    return;
  }
  // Dirty -- show inline confirm bar
  _showSettingsUnsavedBar();
}

// Revert live DOM/localStorage to what they were when the panel opened
function _revertSettingsPreview(){
  if(_settingsThemeOnOpen){
    localStorage.setItem('hermes-theme', _settingsThemeOnOpen);
    if(typeof _applyTheme==='function') _applyTheme(_settingsThemeOnOpen);
    else document.documentElement.dataset.theme = _settingsThemeOnOpen;
  }
}

// Show the "Unsaved changes" bar inside the settings panel
function _showSettingsUnsavedBar(){
  let bar = $('settingsUnsavedBar');
  if(bar){ bar.style.display=''; return; }
  // Create it
  bar = document.createElement('div');
  bar.id = 'settingsUnsavedBar';
  bar.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:8px;background:rgba(233,69,96,.12);border:1px solid rgba(233,69,96,.3);border-radius:8px;padding:10px 14px;margin:0 0 12px;font-size:13px;';
  bar.innerHTML = `<span style="color:var(--text)">${esc(t('settings_unsaved_changes'))}</span>`
    + '<span style="display:flex;gap:8px">'
    + `<button onclick="_discardSettings()" style="padding:5px 12px;border-radius:6px;border:1px solid var(--border2);background:rgba(255,255,255,.06);color:var(--muted);cursor:pointer;font-size:12px;font-weight:600">${esc(t('discard'))}</button>`
    + `<button onclick="saveSettings(true)" style="padding:5px 12px;border-radius:6px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:12px;font-weight:600">${esc(t('save'))}</button>`
    + '</span>';
  const body = document.querySelector('.settings-main') || document.querySelector('.settings-body') || document.querySelector('.settings-panel');
  if(body) body.prepend(bar);
}

function _discardSettings(){
  _revertSettingsPreview();
  _settingsDirty = false;
  _hideSettingsPanel();
}

// Mark settings as dirty whenever anything changes
function _markSettingsDirty(){
  _settingsDirty = true;
}

async function loadSettingsPanel(){
  try{
    const settings=await api('/api/settings');
    const resolvedLanguage=(typeof resolvePreferredLocale==='function')
      ? resolvePreferredLocale(settings.language, (()=>{ try{ return localStorage.getItem('hermes-lang'); }catch(e){ return null; } })())
      : (settings.language || (()=>{ try{ return localStorage.getItem('hermes-lang'); }catch(e){ return null; } })() || 'en');
    // Keep settings modal and current page strings in sync with the resolved locale.
    if(typeof setLocale==='function'){
      setLocale(resolvedLanguage);
      if(typeof applyLocaleToDOM==='function') applyLocaleToDOM();
    }
    // Populate model dropdown with hardcoded options (matching index.html)
    const modelSel=$('settingsModel');
    if(modelSel){
      modelSel.innerHTML='';
      // nvidia NIM group
      const nimGroup=document.createElement('optgroup');
      nimGroup.label='nvidia NIM';
      const deepseekOpt=document.createElement('option');
      deepseekOpt.value='@nvidia:deepseek-ai/deepseek-v4-pro'; deepseekOpt.textContent='deepseek';
      nimGroup.appendChild(deepseekOpt);
      const kimiOpt=document.createElement('option');
      kimiOpt.value='@nvidia:moonshotai/kimi-k2.6'; kimiOpt.textContent='kimi';
      nimGroup.appendChild(kimiOpt);
      const mistralOpt=document.createElement('option');
      mistralOpt.value='@nvidia:mistralai/mistral-medium-3.5-128b'; mistralOpt.textContent='mistral';
      nimGroup.appendChild(mistralOpt);
      const glmOpt=document.createElement('option');
      glmOpt.value='@zai:glm-5.1'; glmOpt.textContent='glm';
      nimGroup.appendChild(glmOpt);
      const minimaxOpt=document.createElement('option');
      minimaxOpt.value='@minimax:MiniMax-M2.7'; minimaxOpt.textContent='minimax';
      nimGroup.appendChild(minimaxOpt);
      modelSel.appendChild(nimGroup);
      // kilo/kilocode group
      const kiloGroup=document.createElement('optgroup');
      kiloGroup.label='kilo/kilocode';
      const nemotronOpt=document.createElement('option');
      nemotronOpt.value='nvidia/nemotron-3-super-120b-a12b:free'; nemotronOpt.textContent='nemotron';
    kiloGroup.appendChild(nemotronOpt);
      kiloGroup.appendChild(nemotronOpt);
      modelSel.appendChild(kiloGroup);
      modelSel.value=settings.default_model||'';
      modelSel.addEventListener('change',_markSettingsDirty,{once:false});
    }
    // Send key preference
    const sendKeySel=$('settingsSendKey');
    if(sendKeySel){sendKeySel.value=settings.send_key||'enter';sendKeySel.addEventListener('change',_markSettingsDirty,{once:false});}
    // Theme preference
    const themeSel=$('settingsTheme');
    if(themeSel){themeSel.value=settings.theme||'dark';themeSel.addEventListener('change',_markSettingsDirty,{once:false});}
    // Language preference — populate from LOCALES bundle
    const langSel=$('settingsLanguage');
    if(langSel){
      langSel.innerHTML='';
      if(typeof LOCALES!=='undefined'){
        for(const [code,bundle] of Object.entries(LOCALES)){
          const opt=document.createElement('option');
          opt.value=code;opt.textContent=bundle._label||code;
          langSel.appendChild(opt);
        }
      }
      langSel.value=resolvedLanguage;
      langSel.addEventListener('change',_markSettingsDirty,{once:false});
    }
    const showUsageCb=$('settingsShowTokenUsage');
    if(showUsageCb){showUsageCb.checked=!!settings.show_token_usage;showUsageCb.addEventListener('change',_markSettingsDirty,{once:false});}
    const showCliCb=$('settingsShowCliSessions');
    if(showCliCb){showCliCb.checked=!!settings.show_cli_sessions;showCliCb.addEventListener('change',_markSettingsDirty,{once:false});}
    const syncCb=$('settingsSyncInsights');
    if(syncCb){syncCb.checked=!!settings.sync_to_insights;syncCb.addEventListener('change',_markSettingsDirty,{once:false});}
    const updateCb=$('settingsCheckUpdates');
    if(updateCb){updateCb.checked=settings.check_for_updates!==false;updateCb.addEventListener('change',_markSettingsDirty,{once:false});}
    const soundCb=$('settingsSoundEnabled');
    if(soundCb){soundCb.checked=!!settings.sound_enabled;soundCb.addEventListener('change',_markSettingsDirty,{once:false});}
    const notifCb=$('settingsNotificationsEnabled');
    if(notifCb){notifCb.checked=!!settings.notifications_enabled;notifCb.addEventListener('change',_markSettingsDirty,{once:false});}
    const bubbleCb=$('settingsBubbleLayout');
    if(bubbleCb){bubbleCb.checked=!!settings.bubble_layout;document.body.classList.toggle('bubble-layout', !!settings.bubble_layout);bubbleCb.addEventListener('change',_markSettingsDirty,{once:false});}
    // Bot name
    const botNameField=$('settingsBotName');
    if(botNameField){botNameField.value=settings.bot_name||'Hermes';botNameField.addEventListener('input',_markSettingsDirty,{once:false});}
    // Password field: always blank (we don't send hash back)
    const pwField=$('settingsPassword');
    if(pwField){pwField.value='';pwField.addEventListener('input',_markSettingsDirty,{once:false});}
    // Show auth buttons only when auth is active
    try{
      const authStatus=await api('/api/auth/status');
      _setSettingsAuthButtonsVisible(!!authStatus.auth_enabled);
    }catch(e){}
    _syncHermesPanelSessionActions();
    switchSettingsSection(_settingsSection);
  }catch(e){
    showToast(t('settings_load_failed')+e.message);
  }
}

function _setSettingsAuthButtonsVisible(active){
  const signOutBtn=$('btnSignOut');
  if(signOutBtn) signOutBtn.style.display=active?'':'none';
  const disableBtn=$('btnDisableAuth');
  if(disableBtn) disableBtn.style.display=active?'':'none';
}

function _applySavedSettingsUi(saved, body, opts){
  const {sendKey,showTokenUsage,showCliSessions,theme,language}=opts;
  window._sendKey=sendKey||'enter';
  window._showTokenUsage=showTokenUsage;
  window._showCliSessions=showCliSessions;
  window._soundEnabled=body.sound_enabled;
  window._notificationsEnabled=body.notifications_enabled;
  window._botName=body.bot_name||'Hermes';
  document.body.classList.toggle('bubble-layout', !!body.bubble_layout);
  if(typeof applyBotName==='function') applyBotName();
  if(typeof setLocale==='function') setLocale(language);
  if(typeof applyLocaleToDOM==='function') applyLocaleToDOM();
  if(typeof startGatewaySSE==='function'){
    if(showCliSessions) startGatewaySSE();
    else if(typeof stopGatewaySSE==='function') stopGatewaySSE();
  }
  _setSettingsAuthButtonsVisible(!!saved.auth_enabled);
  _settingsDirty=false;
  _settingsThemeOnOpen=theme;
  const bar=$('settingsUnsavedBar');
  if(bar) bar.style.display='none';
  renderMessages();
  if(typeof syncTopbar==='function') syncTopbar();
  if(typeof renderSessionList==='function') renderSessionList();
}

async function saveSettings(andClose){
  const model=($('settingsModel')||{}).value;
  const sendKey=($('settingsSendKey')||{}).value;
  const showTokenUsage=!!($('settingsShowTokenUsage')||{}).checked;
  const showCliSessions=!!($('settingsShowCliSessions')||{}).checked;
  const pw=($('settingsPassword')||{}).value;
  const theme=($('settingsTheme')||{}).value||'dark';
  const language=($('settingsLanguage')||{}).value||'en';
  const body={};
  if(model) body.default_model=model;

  if(sendKey) body.send_key=sendKey;
  body.theme=theme;
  body.language=language;
  body.show_token_usage=showTokenUsage;
  body.show_cli_sessions=showCliSessions;
  body.sync_to_insights=!!($('settingsSyncInsights')||{}).checked;
  body.check_for_updates=!!($('settingsCheckUpdates')||{}).checked;
  body.sound_enabled=!!($('settingsSoundEnabled')||{}).checked;
  body.notifications_enabled=!!($('settingsNotificationsEnabled')||{}).checked;
  body.bubble_layout=!!($('settingsBubbleLayout')||{}).checked;
  document.body.classList.toggle('bubble-layout', body.bubble_layout);
  const botName=(($('settingsBotName')||{}).value||'').trim();
  body.bot_name=botName||'Hermes';
  // Password: only act if the field has content; blank = leave auth unchanged
  if(pw && pw.trim()){
    try{
      const saved=await api('/api/settings',{method:'POST',body:JSON.stringify({...body,_set_password:pw.trim()})});
      _applySavedSettingsUi(saved, body, {sendKey,showTokenUsage,showCliSessions,theme,language});
      showToast(t('settings_saved_pw')||t('settings_saved_pw_updated'));
      _hideSettingsPanel();
      return;
    }catch(e){showToast(t('settings_save_failed')+e.message);return;}
  }
  try{
    const saved=await api('/api/settings',{method:'POST',body:JSON.stringify(body)});
    _applySavedSettingsUi(saved, body, {sendKey,showTokenUsage,showCliSessions,theme,language});
    showToast(t('settings_saved'));
    _hideSettingsPanel();
  }catch(e){
    showToast(t('settings_save_failed')+e.message);
  }
}

async function signOut(){
  try{
    await api('/api/auth/logout',{method:'POST',body:'{}'});
    window.location.href='login';
  }catch(e){
    showToast(t('sign_out_failed')+e.message);
  }
}

async function disableAuth(){
  const _disAuth=await showConfirmDialog({title:t('disable_auth_confirm_title'),message:t('disable_auth_confirm_message'),confirmLabel:t('disable'),danger:true,focusCancel:true});
  if(!_disAuth) return;
  try{
    await api('/api/settings',{method:'POST',body:JSON.stringify({_clear_password:true})});
    showToast(t('auth_disabled'));
    // Hide both auth buttons since auth is now off
    const disableBtn=$('btnDisableAuth');
    if(disableBtn) disableBtn.style.display='none';
    const signOutBtn=$('btnSignOut');
    if(signOutBtn) signOutBtn.style.display='none';
  }catch(e){
    showToast(t('disable_auth_failed')+e.message);
  }
}

// ── API Keys Management ──────────────────────────────────────────────────────

let _apiKeys = [];
let _apiKeysDirty = false;
let _draggedKeyIndex = null;
let _dragStartTime = null;
let _dragStartY = null;
let _isDragging = false;
let _longPressTimer = null;

const API_KEYS_STORAGE_KEY = 'hermes_nvidia_api_keys';

// Load API keys from localStorage
function loadApiKeys(){
  try {
    let stored = null;
    try { stored = localStorage.getItem(API_KEYS_STORAGE_KEY); } catch (e) {}
    _apiKeys = stored ? JSON.parse(stored) : [];
  } catch (e) {
    _apiKeys = [];
  }
  renderApiKeysList();
}

// Save API keys to localStorage
function saveApiKeys(){
  try {
    localStorage.setItem(API_KEYS_STORAGE_KEY, JSON.stringify(_apiKeys));
    _apiKeysDirty = false;
  } catch (e) {
    showToast('Failed to save API keys: ' + e.message);
  }
}

// Add a new API key
async function addApiKey(){
  const input = $('apiKeyInput');
  const providerSelect = $('apiKeyProvider');
  if (!input || !providerSelect) return;
  
  const key = input.value.trim();
  const provider = providerSelect.value;
  
  if (!key) {
    showToast('Please enter an API key');
    return;
  }
  
  // Basic validation based on provider
  if (provider === 'nvidia' && !key.startsWith('nvapi-') && !key.startsWith('sk-')) {
    showToast('Warning: Key format doesn\'t match expected NVIDIA format (nvapi-...)');
  }
  
  try {
    // Send to server to save in config
    const response = await api('/api/apikeys', {
      method: 'POST',
      body: JSON.stringify({ key, provider })
    });
    
    if (response.ok) {
      // Also save to localStorage for nvidia keys (for rotation UI)
      if (provider === 'nvidia') {
        _apiKeys.push({
          id: Date.now().toString(),
          key: key,
          added: new Date().toISOString()
        });
        saveApiKeys();
        renderApiKeysList();
      }
      
      input.value = '';
      input.focus();
      showToast(`API key added for ${provider}`);
    } else {
      showToast('Failed to add API key: ' + (response.error || 'Unknown error'));
    }
  } catch (e) {
    showToast('Failed to add API key: ' + e.message);
  }
}

// Delete an API key
function deleteApiKey(id){
  const index = _apiKeys.findIndex(k => k.id === id);
  if (index === -1) return;
  
  _apiKeys.splice(index, 1);
  saveApiKeys();
  renderApiKeysList();
  
  showToast(`API key removed (${_apiKeys.length} remaining)`);
}

// Render the API keys list
function renderApiKeysList(){
  const container = $('apiKeysList');
  if (!container) return;
  
  if (_apiKeys.length === 0) {
    container.innerHTML = '<div class="api-keys-empty">no api keys added yet. add keys to enable rotation.</div>';
    return;
  }
  
  container.innerHTML = '';
  
  _apiKeys.forEach((keyObj, index) => {
    const item = document.createElement('div');
    item.className = 'api-key-item';
    item.dataset.id = keyObj.id;
    item.dataset.index = index;
    
    // Mask the key for display (show first 8 and last 4 chars)
    const maskedKey = maskApiKey(keyObj.key);
    
    item.innerHTML = `
      <div class="api-key-number">${index + 1}</div>
      <div class="api-key-value" title="Added: ${new Date(keyObj.added).toLocaleString()}">${maskedKey}</div>
      <button class="api-key-delete" onclick="deleteApiKey('${keyObj.id}')" title="Remove key">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    `;
    
    // Add drag event listeners (hold to drag)
    setupDragHandlers(item, index);
    
    container.appendChild(item);
  });
}

// Mask API key for display
function maskApiKey(key){
  if (key.length <= 12) return '•'.repeat(key.length);
  return key.substring(0, 8) + '•'.repeat(key.length - 12) + key.substring(key.length - 4);
}

// Setup drag handlers for an item
function setupDragHandlers(item, index){
  // Mouse/Touch down - start long press timer
  const startDrag = (e) => {
    _dragStartTime = Date.now();
    _dragStartY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
    _isDragging = false;
    
    _longPressTimer = setTimeout(() => {
      _isDragging = true;
      _draggedKeyIndex = index;
      item.classList.add('dragging');
      item.style.cursor = 'grabbing';
      
      // Prevent scrolling on touch devices during drag
      if (e.type.includes('touch')) {
        e.preventDefault();
      }
    }, 400); // 400ms hold to start drag
  };
  
  // Mouse/Touch move
  const moveDrag = (e) => {
    if (!_isDragging || _draggedKeyIndex === null) return;
    
    e.preventDefault();
    
    const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
    const container = $('apiKeysList');
    
    // Find element under cursor
    const elementsBelow = document.elementsFromPoint(
      e.type.includes('touch') ? e.touches[0].clientX : e.clientX,
      clientY
    );
    
    const targetItem = elementsBelow.find(el => 
      el.classList && el.classList.contains('api-key-item') && el !== item
    );
    
    if (targetItem) {
      const targetIndex = parseInt(targetItem.dataset.index);
      if (targetIndex !== _draggedKeyIndex) {
        // Swap in array
        const temp = _apiKeys[_draggedKeyIndex];
        _apiKeys[_draggedKeyIndex] = _apiKeys[targetIndex];
        _apiKeys[targetIndex] = temp;
        _draggedKeyIndex = targetIndex;
        
        saveApiKeys();
        renderApiKeysList();
      }
    }
  };
  
  // Mouse/Touch up - end drag
  const endDrag = (e) => {
    if (_longPressTimer) {
      clearTimeout(_longPressTimer);
      _longPressTimer = null;
    }
    
    if (_isDragging) {
      item.classList.remove('dragging');
      item.style.cursor = 'grab';
      _isDragging = false;
      _draggedKeyIndex = null;
    }
  };
  
  // Mouse events
  item.addEventListener('mousedown', startDrag);
  document.addEventListener('mousemove', moveDrag);
  document.addEventListener('mouseup', endDrag);
  
  // Touch events
  item.addEventListener('touchstart', startDrag, { passive: false });
  document.addEventListener('touchmove', moveDrag, { passive: false });
  document.addEventListener('touchend', endDrag);
  
  // Cancel drag if mouse leaves the item before long press
  item.addEventListener('mouseleave', () => {
    if (_longPressTimer && !_isDragging) {
      clearTimeout(_longPressTimer);
      _longPressTimer = null;
    }
  });
}

// Get current active API key (for rotation)
function getCurrentApiKey(){
  if (_apiKeys.length === 0) return null;
  
  // Get current index from localStorage or start at 0
  let currentIndex = 0;
  try { currentIndex = parseInt(localStorage.getItem('hermes_api_key_index') || '0'); } catch (e) {}
  if (currentIndex >= _apiKeys.length) currentIndex = 0;
  
  return _apiKeys[currentIndex];
}

// Rotate to next API key
function rotateApiKey(){
  if (_apiKeys.length <= 1) return null;
  
  let currentIndex = 0;
  try { currentIndex = parseInt(localStorage.getItem('hermes_api_key_index') || '0'); } catch (e) {}
  currentIndex = (currentIndex + 1) % _apiKeys.length;
  try { localStorage.setItem('hermes_api_key_index', currentIndex.toString()); } catch (e) {}
  
  return _apiKeys[currentIndex];
}

// Initialize API keys on load
document.addEventListener('DOMContentLoaded', () => {
  loadApiKeys();
});

// ── Config Editor ────────────────────────────────────────────────────────────

let _currentConfig = '';

// Load Hermes config from .250
async function loadHermesConfig(){
  const editor = $('configEditor');
  const status = $('configEditorStatus');
  
  if (!editor || !status) return;
  
  status.textContent = 'loading config...';
  status.className = 'config-editor-status';
  
  try {
    // Try to load from backend API
    const response = await api('/api/config');
    
    if (response.ok && response.config) {
      // Convert config object to YAML-like string for editing
      const configYaml = configToYaml(response.config);
      editor.value = configYaml;
      _currentConfig = configYaml;
      status.textContent = 'config loaded from 192.168.4.250';
      status.className = 'config-editor-status success';
    } else {
      throw new Error(response.error || 'Failed to load config');
    }
  } catch (e) {
    // Check if it's an SSH authentication error with helpful instructions
    const errorMsg = e.message || '';
    const isSshError = errorMsg.includes('SSH authentication failed') || 
                       errorMsg.includes('SSH connection failed') ||
                       errorMsg.includes('Authentication failed');
    
    if (isSshError) {
      // Show the detailed SSH error message in the editor for clarity
      editor.value = `# SSH Connection Error
#
# ${errorMsg.replace(/\n/g, '\n# ')}
#
# Quick fix:
# 1. Ensure you can SSH to 192.168.4.250: ssh house@192.168.4.250
# 2. If prompted for password, set up key auth: ssh-copy-id -i ~/.ssh/id_ed25519 house@192.168.4.250
# 3. Or generate a new key: ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
#
# Manual fallback:
# You can manually edit config.yaml on 192.168.4.250 at:
# /home/house/.hermes/config.yaml
#
# Example config structure:
# nvidia:
#   api_keys:
#     - nvapi-xxxxxxxx
#     - nvapi-yyyyyyyy
#   current_key_index: 0
# model: nvidia/llama-3.1-405b-instruct
# workspace: /home/house/projects
`;
    } else {
      // Fallback: show placeholder with instructions
      editor.value = `# Failed to load config from 192.168.4.250
# Error: ${e.message}
#
# You can manually edit config.yaml on the .250 machine at:
# /home/house/.hermes/config.yaml
#
# Example config structure:
# nvidia:
#   api_keys:
#     - nvapi-xxxxxxxx
#     - nvapi-yyyyyyyy
#   current_key_index: 0
# model: nvidia/llama-3.1-405b-instruct
# workspace: /home/house/projects
`;
    }
    status.textContent = 'error loading config: ' + e.message;
    status.className = 'config-editor-status error';
  }
}

// Save Hermes config to .250
async function saveHermesConfig(){
  const editor = $('configEditor');
  const status = $('configEditorStatus');
  
  if (!editor || !status) return;
  
  const yamlContent = editor.value.trim();
  if (!yamlContent) {
    status.textContent = 'config is empty';
    status.className = 'config-editor-status error';
    return;
  }
  
  status.textContent = 'saving config...';
  status.className = 'config-editor-status';
  
  try {
    // Parse YAML to object
    const config = yamlToConfig(yamlContent);
    
    // Save via backend API
    const response = await api('/api/config', {
      method: 'POST',
      body: JSON.stringify({ config })
    });
    
    if (response.ok) {
      _currentConfig = yamlContent;
      status.textContent = 'config saved to 192.168.4.250 - restart hermes to apply';
      status.className = 'config-editor-status success';
      showToast('Config saved successfully');
    } else {
      throw new Error(response.error || 'Failed to save config');
    }
  } catch (e) {
    const errorMsg = e.message || '';
    const isSshError = errorMsg.includes('SSH authentication failed') || 
                       errorMsg.includes('SSH connection failed') ||
                       errorMsg.includes('Authentication failed');
    
    if (isSshError) {
      status.textContent = 'SSH error - see editor for fix instructions';
    } else {
      status.textContent = 'error saving config: ' + e.message;
    }
    status.className = 'config-editor-status error';
    showToast('Failed to save config: ' + e.message);
  }
}

// Simple config to YAML converter
function configToYaml(config, indent = 0){
  let yaml = '';
  const spaces = '  '.repeat(indent);
  
  for (const [key, value] of Object.entries(config)) {
    if (value === null || value === undefined) {
      yaml += `${spaces}${key}:\n`;
    } else if (typeof value === 'object' && !Array.isArray(value)) {
      yaml += `${spaces}${key}:\n`;
      yaml += configToYaml(value, indent + 1);
    } else if (Array.isArray(value)) {
      yaml += `${spaces}${key}:\n`;
      for (const item of value) {
        if (typeof item === 'object') {
          yaml += `${spaces}-\n`;
          yaml += configToYaml(item, indent + 1).replace(new RegExp(`^${spaces}  `, 'gm'), `${spaces}  `);
        } else {
          yaml += `${spaces}- ${item}\n`;
        }
      }
    } else {
      yaml += `${spaces}${key}: ${value}\n`;
    }
  }
  
  return yaml;
}

// Simple YAML to config parser (basic implementation)
function yamlToConfig(yaml){
  const lines = yaml.split('\n');
  const config = {};
  const stack = [{ obj: config, indent: -1 }];
  let currentArray = null;
  let currentArrayKey = null;
  
  for (let line of lines) {
    // Skip comments and empty lines
    const commentIndex = line.indexOf('#');
    if (commentIndex !== -1) {
      line = line.substring(0, commentIndex);
    }
    
    line = line.trimEnd();
    if (!line.trim()) continue;
    
    const indent = line.search(/\S/);
    const trimmed = line.trim();
    
    // Array item
    if (trimmed.startsWith('- ')) {
      const value = trimmed.substring(2).trim();
      if (currentArray) {
        // Try to parse as object if it contains colon
        if (value.includes(':')) {
          const [k, v] = value.split(':').map(s => s.trim());
          const lastItem = currentArray[currentArray.length - 1];
          if (typeof lastItem === 'object' && lastItem !== null && !(k in lastItem)) {
            lastItem[k] = v;
          } else {
            currentArray.push({ [k]: v });
          }
        } else {
          currentArray.push(value);
        }
      }
      continue;
    }
    
    // Key-value pair
    const colonIndex = trimmed.indexOf(':');
    if (colonIndex === -1) continue;
    
    const key = trimmed.substring(0, colonIndex).trim();
    let value = trimmed.substring(colonIndex + 1).trim();
    
    // Pop stack to correct level
    while (stack.length > 1 && stack[stack.length - 1].indent >= indent) {
      stack.pop();
      currentArray = null;
    }
    
    const parent = stack[stack.length - 1].obj;
    
    // Determine if value is inline or block
    if (!value) {
      // Check if next line is array or object
      parent[key] = {};
      stack.push({ obj: parent[key], indent, key });
      currentArray = null;
    } else if (value.startsWith('[') && value.endsWith(']')) {
      // Inline array
      try {
        parent[key] = JSON.parse(value.replace(/'/g, '"'));
      } catch {
        parent[key] = value;
      }
      currentArray = null;
    } else if (value === '|' || value === '>') {
      // Multiline string - skip for now
      parent[key] = '';
      currentArray = null;
    } else {
      // Scalar value
      if (value.startsWith('"') && value.endsWith('"')) {
        value = value.slice(1, -1);
      } else if (value.startsWith("'") && value.endsWith("'")) {
        value = value.slice(1, -1);
      } else if (value === 'true') {
        value = true;
      } else if (value === 'false') {
        value = false;
      } else if (!isNaN(value) && value !== '') {
        value = Number(value);
      }
      parent[key] = value;
      currentArray = null;
    }
    
  }
  
  // Second pass: find arrays
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    const indent = line.search(/\S/);
    
    if (trimmed.startsWith('- ')) {
      // Find parent key by looking backward
      const parentLine = lines[i - 1];
      const parentIndent = parentLine.search(/\S/);
      const parentKey = parentLine.trim().substring(indent + 1);
      
      if (parentKey.includes(':')) {
        const [k, v] = parentKey.split(':').map(s => s.trim());
        const lastItem = currentArray[currentArray.length - 1];
        if (typeof lastItem === 'object' && lastItem !== null && !(k in lastItem)) {
          lastItem[k] = v;
        } else {
          currentArray.push({ [k]: v });
        }
      } else {
        currentArray.push(parentKey);
      }
    }
  }
  
  return config;
}

// ── Cron completion alerts ────────────────────────────────────────────────────

let _cronPollSince=Date.now()/1000;  // track from page load
let _cronPollTimer=null;
let _cronUnreadCount=0;

function startCronPolling(){
  if(_cronPollTimer) return;
  _cronPollTimer=setInterval(async()=>{
    if(document.hidden) return;  // don't poll when tab is in background
    try{
      const data=await api(`/api/crons/recent?since=${_cronPollSince}`);
      if(data.completions&&data.completions.length>0){
        for(const c of data.completions){
          showToast(t('cron_completion_status', c.name, c.status==='error' ? t('status_failed') : t('status_completed')),4000);
          _cronPollSince=Math.max(_cronPollSince,c.completed_at);
        }
        _cronUnreadCount+=data.completions.length;
        updateCronBadge();
      }
    }catch(e){}
  },30000);
}

function updateCronBadge(){
  const tab=document.querySelector('.nav-tab[data-panel="tasks"]');
  if(!tab) return;
  let badge=tab.querySelector('.cron-badge');
  if(_cronUnreadCount>0){
    if(!badge){
      badge=document.createElement('span');
      badge.className='cron-badge';
      tab.style.position='relative';
      tab.appendChild(badge);
    }
    badge.textContent=_cronUnreadCount>9?'9+':_cronUnreadCount;
    badge.style.display='';
  }else if(badge){
    badge.style.display='none';
  }
}

// Clear cron badge when Tasks tab is opened
const _origSwitchPanel=switchPanel;
switchPanel=async function(name){
  if(name==='tasks'){_cronUnreadCount=0;updateCronBadge();}
  return _origSwitchPanel(name);
};

// Start polling on page load
startCronPolling();

// ── Background agent error tracking ──────────────────────────────────────────

const _backgroundErrors=[];  // {session_id, title, message, ts}

function trackBackgroundError(sessionId, title, message){
  // Only track if user is NOT currently viewing this session
  if(S.session&&S.session.session_id===sessionId) return;
  _backgroundErrors.push({session_id:sessionId, title:title||t('untitled'), message, ts:Date.now()});
  showErrorBanner();
}

function showErrorBanner(){
  let banner=$('bgErrorBanner');
  if(!banner){
    banner=document.createElement('div');
    banner.id='bgErrorBanner';
    banner.className='bg-error-banner';
    const msgs=document.querySelector('.messages');
    if(msgs) msgs.parentNode.insertBefore(banner,msgs);
    else document.body.appendChild(banner);
  }
  const latest=_backgroundErrors[0];  // FIFO: show oldest (first) error
  if(!latest){banner.style.display='none';return;}
  const count=_backgroundErrors.length;
  const msg=count>1?t('bg_error_multi',count):t('bg_error_single',latest.title);
  banner.innerHTML=`<span>\u26a0 ${esc(msg)}</span><div style="display:flex;gap:6px;flex-shrink:0"><button class="reconnect-btn" onclick="navigateToErrorSession()">${esc(t('view'))}</button><button class="reconnect-btn" onclick="dismissErrorBanner()">${esc(t('dismiss'))}</button></div>`;
  banner.style.display='';
}

function navigateToErrorSession(){
  const latest=_backgroundErrors.shift();  // FIFO: show oldest error first
  if(latest){
    loadSession(latest.session_id);renderSessionList();
  }
  if(_backgroundErrors.length===0) dismissErrorBanner();
  else showErrorBanner();
}

function dismissErrorBanner(){
  _backgroundErrors.length=0;
  const banner=$('bgErrorBanner');
  if(banner) banner.style.display='none';
}

// Event wiring
// Verify toggleComposerWsDropdown is exposed
if(typeof window.toggleComposerWsDropdown !== 'function'){
  console.error('[panels.js] toggleComposerWsDropdown not exposed!');
} else {
  // // console.log('[panels.js] toggleComposerWsDropdown ready');
}

// Verify switchToWorkspace is exposed
if(typeof window.switchToWorkspace !== 'function'){
  console.error('[panels.js] switchToWorkspace not exposed!');
} else {
  // // console.log('[panels.js] switchToWorkspace ready');
}

// Settings close button event listener (for Tauri desktop app compatibility)
document.addEventListener('DOMContentLoaded', function(){
  const btnCloseSettings = document.getElementById('btnCloseSettings');
  if(btnCloseSettings){
    btnCloseSettings.addEventListener('click', function(e){
      e.preventDefault();
      e.stopPropagation();
      console.log('Close button clicked');
      _closeSettingsPanel();
    });
  }
  
  // Escape key to close settings
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape'){
      const overlay = document.getElementById('settingsOverlay');
      if(overlay && overlay.style.display !== 'none'){
        _closeSettingsPanel();
      }
    }
  });
});

// ── Mobile Navigation ─────────────────────────────────────────────────────

let _mobilePanelVisible = false;
let _currentMobilePanel = 'chat';

function closeMobilePanels() {
  if (!_mobilePanelVisible && !document.documentElement.classList.contains('apk-force-mobile')) {
    return;
  }
  _mobilePanelVisible = false;
  _currentMobilePanel = 'chat';

  document.querySelectorAll('.mobile-nav-item').forEach(item => {
    item.classList.remove('active');
  });
  const chatNav = document.querySelector('.mobile-nav-item[data-panel="chat"]');
  if(chatNav){
    chatNav.classList.add('active');
  }
  const wt = document.getElementById('btnWorkspacePanelToggle');
  const tt = document.getElementById('btnTerminalPanelToggle');
  if(wt) wt.classList.remove('active');
  if(tt) tt.classList.remove('active');
  document.querySelectorAll('.panel-view').forEach(panel => {
    panel.classList.remove('active');
    panel.style.display = '';
    panel.style.opacity = '';
    panel.style.visibility = '';
    panel.style.pointerEvents = '';
  });
  const chatPanel = document.getElementById('panelChat');
  if (chatPanel) {
    chatPanel.style.display = '';
    chatPanel.style.opacity = '';
    chatPanel.style.visibility = '';
    chatPanel.style.pointerEvents = '';
  }
  document.querySelector('.main')?.classList.remove('mobile-panel-active');
  const bottomPanel = document.getElementById('bottomPanel');
  if (bottomPanel) {
    bottomPanel.classList.remove('active');
    bottomPanel.style.display = '';
  }
  const panelTerminal = document.getElementById('panelTerminal');
  if (panelTerminal) panelTerminal.classList.remove('active');
}

function switchMobilePanel(name) {
  // Terminal lives in bottom panel - show/hide it
  if (name === 'terminal') {
    const bottomPanel = document.getElementById('bottomPanel');
    const panelTerminal = document.getElementById('panelTerminal');
    const isActive = !!bottomPanel?.classList.contains('active');
    if (isActive) {
      closeMobilePanels();
      return;
    }
    _mobilePanelVisible = true;
    _currentMobilePanel = 'terminal';
    document.querySelectorAll('.mobile-nav-item').forEach(item => {
      item.classList.remove('active');
    });
    const termNav = document.querySelector('.mobile-nav-item[data-panel="terminal"]');
    if(termNav) termNav.classList.add('active');
    if (bottomPanel) {
      bottomPanel.classList.add('active');
      bottomPanel.style.display = 'flex';
    }
    if (panelTerminal) {
      panelTerminal.classList.add('active');
      panelTerminal.style.display = 'flex';
      panelTerminal.style.opacity = '1';
      panelTerminal.style.visibility = 'visible';
      panelTerminal.style.pointerEvents = 'auto';
    }
    document.querySelector('.main')?.classList.add('mobile-panel-active');
    if (typeof initTerminalPanel === 'function') initTerminalPanel();
    if (typeof onTerminalPanelShow === 'function') onTerminalPanelShow();
    return;
  }

  // Update topbar toggle buttons active state in APK mode
  if(document.documentElement.classList.contains('apk-force-mobile')){
    const wt = document.getElementById('btnWorkspacePanelToggle');
    const tt = document.getElementById('btnTerminalPanelToggle');
    if(wt) {
      wt.classList.toggle('active', name === 'workspaces');
      // Force rounded corners via inline !important (most reliable in WebView)
      wt.style.setProperty('border-radius', '999px', 'important');
      wt.style.setProperty('-webkit-appearance', 'none', 'important');
      wt.style.setProperty('appearance', 'none', 'important');
    }
    if(tt) {
      tt.classList.toggle('active', name === 'terminal');
      tt.style.setProperty('border-radius', '999px', 'important');
      tt.style.setProperty('-webkit-appearance', 'none', 'important');
      tt.style.setProperty('appearance', 'none', 'important');
    }
  }
  const currentPanelEl = name === 'chat'
    ? document.getElementById('panelChat')
    : document.getElementById('panel' + name.charAt(0).toUpperCase() + name.slice(1));
  const isCurrentPanelOpen = !!currentPanelEl?.classList.contains('active');
  if (name === _currentMobilePanel && isCurrentPanelOpen) {
    closeMobilePanels();
    return;
  }
  if (name === 'chat' && _mobilePanelVisible && _currentMobilePanel !== 'chat') {
    closeMobilePanels();
    return;
  }

  _currentMobilePanel = name;
  _mobilePanelVisible = name !== 'chat';

  // Update mobile nav items
  document.querySelectorAll('.mobile-nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.panel === name);
  });

  // Hide all panel views first
  document.querySelectorAll('.panel-view').forEach(p => p.classList.remove('active'));

  // Hide bottom panel (terminal) when switching to other mobile panels
  const bottomPanel = document.getElementById('bottomPanel');
  if (bottomPanel) {
    bottomPanel.classList.remove('active');
    bottomPanel.style.display = '';
  }
  const panelTerminal = document.getElementById('panelTerminal');
  if (panelTerminal) panelTerminal.classList.remove('active');

  // Hide main chat area when showing a panel (except chat panel)
  if (name !== 'chat') {
    document.querySelector('.main')?.classList.add('mobile-panel-active');
  } else {
    document.querySelector('.main')?.classList.remove('mobile-panel-active');
  }

  // Handle chat panel specially - show the session list panel
  if (name === 'chat') {
    const chatPanel = document.getElementById('panelChat');
    if (chatPanel) {
      chatPanel.classList.add('active');
      chatPanel.style.display = 'flex';
      chatPanel.style.opacity = '1';
      chatPanel.style.visibility = 'visible';
      chatPanel.style.pointerEvents = 'auto';
      // Add mobile header if not present
      if (!chatPanel.querySelector('.mobile-panel-header')) {
        const header = document.createElement('div');
        header.className = 'mobile-panel-header';
        header.innerHTML = `
          <span class="mobile-panel-title">chats</span>
          <button class="mobile-panel-close" onclick="closeMobilePanels()" aria-label="close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        `;
        chatPanel.insertBefore(header, chatPanel.firstChild);
      }
      // Load sessions if not already loaded
      if (typeof renderSessionList === 'function') {
        renderSessionList();
      }
    }
    return;
  }

  // For other panels, show the panel view
  const panelEl = document.getElementById('panel' + name.charAt(0).toUpperCase() + name.slice(1));
  if (panelEl) {
    panelEl.classList.add('active');
    panelEl.style.display = 'flex';
    panelEl.style.opacity = '1';
    panelEl.style.visibility = 'visible';
    panelEl.style.pointerEvents = 'auto';
    // Add mobile header if not present
    if (!panelEl.querySelector('.mobile-panel-header')) {
      const header = document.createElement('div');
      header.className = 'mobile-panel-header';
      header.innerHTML = `
        <span class="mobile-panel-title">${name}</span>
        <button class="mobile-panel-close" onclick="closeMobilePanels()" aria-label="close">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      `;
      panelEl.insertBefore(header, panelEl.firstChild);
    }
  } else {
    return;
  }

  if (name === 'tasks' && typeof loadCrons === 'function') {
    loadCrons();
  }
  if (name === 'skills' && typeof loadSkills === 'function') {
    loadSkills();
  }
  if (name === 'memory' && typeof loadMemory === 'function') {
    loadMemory();
  }
  if (name === 'workspaces' && typeof loadWorkspacesPanel === 'function') {
    loadWorkspacesPanel();
  }
  if (name === 'todos' && typeof loadTodos === 'function') {
    loadTodos();
  }
  if (name === 'terminal') {
    if (typeof initTerminalPanel === 'function') {
      initTerminalPanel();
    }
    if (typeof onTerminalPanelShow === 'function') {
      onTerminalPanelShow();
    }
  }
}

function toggleMobileSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (sidebar && overlay) {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
  }
}

function closeMobileSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (sidebar) sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('show');
}

// Handle back button on mobile
window.addEventListener('popstate', function(e) {
  if (_mobilePanelVisible && _currentMobilePanel !== 'chat') {
    e.preventDefault();
    switchMobilePanel('chat');
    history.pushState(null, '', location.href);
  }
});

// Detect standalone PWA/APK mode and adjust UI
if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true) {
  document.body.classList.add('standalone-mode');
}

// Listen for display mode changes
window.matchMedia('(display-mode: standalone)').addEventListener('change', (e) => {
  if (e.matches) {
    document.body.classList.add('standalone-mode');
  } else {
    document.body.classList.remove('standalone-mode');
  }
});