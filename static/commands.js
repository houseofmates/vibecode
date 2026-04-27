// ── Slash commands ──────────────────────────────────────────────────────────
// Built-in commands intercepted before send(). Each command runs locally
// (no round-trip to the agent) and shows feedback via toast or local message.

const COMMANDS=[
  {name:'help',      desc:t('cmd_help'),             fn:cmdHelp},
  {name:'clear',     desc:t('cmd_clear'),         fn:cmdClear},
  {name:'compact',   desc:t('cmd_compact'),       fn:cmdCompact},
  {name:'model',     desc:t('cmd_model'),  fn:cmdModel,     arg:'model_name'},
  {name:'workspace', desc:t('cmd_workspace'),            fn:cmdWorkspace, arg:'name'},
  {name:'new',       desc:t('cmd_new'),            fn:cmdNew},
  {name:'usage',     desc:t('cmd_usage'),   fn:cmdUsage},
  {name:'theme',     desc:t('cmd_theme'), fn:cmdTheme, arg:'name'},
  {name:'personality', desc:t('cmd_personality'), fn:cmdPersonality, arg:'name'},
  {name:'skills', desc:t('cmd_skills'), fn:cmdSkills, arg:'query'},
];

function parseCommand(text){
  if(!text.startsWith('/'))return null;
  const parts=text.slice(1).split(/\s+/);
  const name=parts[0].toLowerCase();
  const args=parts.slice(1).join(' ').trim();
  return {name,args};
}

function executeCommand(text){
  const parsed=parseCommand(text);
  if(!parsed)return false;
  const cmd=COMMANDS.find(c=>c.name===parsed.name);
  if(!cmd)return false;
  cmd.fn(parsed.args);
  return true;
}

function getMatchingCommands(prefix){
  const q=prefix.toLowerCase();
  return COMMANDS.filter(c=>c.name.startsWith(q));
}

// ── Command handlers ────────────────────────────────────────────────────────

function cmdHelp(){
  const lines=COMMANDS.map(c=>{
    const usage=c.arg?` <${c.arg}>`:'';
    return `  /${c.name}${usage} — ${c.desc}`;
  });
  const msg={role:'assistant',content:t('available_commands')+'\n'+lines.join('\n')};
  S.messages.push(msg);
  renderMessages();
  showToast(t('type_slash'));
}

function cmdClear(){
  if(!S.session)return;
  S.messages=[];S.toolCalls=[];
  clearLiveToolCards();
  renderMessages();
  $('emptyState').style.display='';
  showToast(t('conversation_cleared'));
}

async function cmdModel(args){
  if(!args){showToast(t('model_usage'));return;}
  const sel=$('modelSelect');
  if(!sel)return;
  const q=args.toLowerCase();
  // Fuzzy match: find first option whose label or value contains the query
  let match=null;
  for(const opt of sel.options){
    if(opt.value.toLowerCase().includes(q)||opt.textContent.toLowerCase().includes(q)){
      match=opt.value;break;
    }
  }
  if(!match){showToast(t('no_model_match')+`"${args}"`);return;}
  sel.value=match;
  await sel.onchange();
  showToast(t('switched_to')+match);
}

async function cmdWorkspace(args){
  if(!args){showToast(t('workspace_usage'));return;}
  try{
    const data=await api('/api/workspaces');
    const q=args.toLowerCase();
    const ws=(data.workspaces||[]).find(w=>
      (w.name||'').toLowerCase().includes(q)||w.path.toLowerCase().includes(q)
    );
    if(!ws){showToast(t('no_workspace_match')+`"${args}"`);return;}
    if(typeof switchToWorkspace==='function') await switchToWorkspace(ws.path, ws.name||ws.path);
    else showToast(t('switched_workspace')+(ws.name||ws.path));
  }catch(e){showToast(t('workspace_switch_failed')+e.message);}
}

async function cmdNew(){
  await newSession();
  await renderSessionList();
  $('msg').focus();
  showToast(t('new_session'));
}

function cmdCompact(){
  // Send as a regular message to the agent -- the agent's run_conversation
  // preflight will detect the high token count and trigger _compress_context.
  // We send a user message so it appears in the conversation.
  $('msg').value='Please compress and summarize the conversation context to free up space.';
  send();
  showToast(t('compressing'));
}

async function cmdUsage(){
  const next=!window._showTokenUsage;
  window._showTokenUsage=next;
  try{
    await api('/api/settings',{method:'POST',body:JSON.stringify({show_token_usage:next})});
  }catch(e){}
  // Update the settings checkbox if the panel is open
  const cb=$('settingsShowTokenUsage');
  if(cb) cb.checked=next;
  renderMessages();
  showToast(next?t('token_usage_on'):t('token_usage_off'));
}

async function cmdTheme(args){
  const themes=['oled'];
  if(!args||!themes.includes(args.toLowerCase())){
    showToast(t('theme_usage')+themes.join('|'));
    return;
  }
  const themeName=args.toLowerCase();
  localStorage.setItem('hermes-theme',themeName);
  _applyTheme(themeName);
  try{await api('/api/settings',{method:'POST',body:JSON.stringify({theme:themeName})});}catch(e){}
  // Update settings dropdown if panel is open
  const sel=$('settingsTheme');
  if(sel)sel.value=themeName;
  showToast(t('theme_set')+themeName);
}

async function cmdSkills(args){
  try{
    const data = await api('/api/skills');
    let skills = data.skills || [];
    if(args){
      const q = args.toLowerCase();
      skills = skills.filter(s =>
        (s.name||'').toLowerCase().includes(q) ||
        (s.description||'').toLowerCase().includes(q) ||
        (s.category||'').toLowerCase().includes(q)
      );
    }
    if(!skills.length){
      const msg = {role:'assistant', content: args ? `No skills matching "${args}".` : 'No skills found.'};
      S.messages.push(msg); renderMessages(); return;
    }
    // Group by category
    const byCategory = {};
    skills.forEach(s => {
      const cat = s.category || 'General';
      if(!byCategory[cat]) byCategory[cat] = [];
      byCategory[cat].push(s);
    });
    const lines = [];
    for(const [cat, items] of Object.entries(byCategory).sort()){
      lines.push(`**${cat}**`);
      items.forEach(s => {
        const desc = s.description ? ` — ${s.description.slice(0,80)}${s.description.length>80?'...':''}` : '';
        lines.push(`  \`${s.name}\`${desc}`);
      });
      lines.push('');
    }
    const header = args
      ? `Skills matching "${args}" (${skills.length}):\n\n`
      : `Available skills (${skills.length}):\n\n`;
    S.messages.push({role:'assistant', content: header + lines.join('\n')});
    renderMessages();
    showToast(t('type_slash'));
  }catch(e){
    showToast('Failed to load skills: '+e.message);
  }
}

async function cmdPersonality(args){
  if(!S.session){showToast(t('no_active_session'));return;}
  if(!args){
    // List available personalities
    try{
      const data=await api('/api/personalities');
      if(!data.personalities||!data.personalities.length){
        showToast(t('no_personalities'));
        return;
      }
      const list=data.personalities.map(p=>`  **${p.name}**${p.description?' — '+p.description:''}`).join('\n');
      S.messages.push({role:'assistant',content:t('available_personalities')+'\n\n'+list+t('personality_switch_hint')});
      renderMessages();
    }catch(e){showToast(t('personalities_load_failed'));}
    return;
  }
  const name=args.trim();
  if(name.toLowerCase()==='none'||name.toLowerCase()==='default'||name.toLowerCase()==='clear'){
    try{
      await api('/api/personality/set',{method:'POST',body:JSON.stringify({session_id:S.session.session_id,name:''})});
      showToast(t('personality_cleared'));
    }catch(e){showToast(t('failed_colon')+e.message);}
    return;
  }
  try{
    const res=await api('/api/personality/set',{method:'POST',body:JSON.stringify({session_id:S.session.session_id,name})});
    showToast(t('personality_set')+name);
  }catch(e){showToast(t('failed_colon')+e.message);}
}

// ── Autocomplete dropdown ───────────────────────────────────────────────────

let _cmdSelectedIdx=-1;

function showCmdDropdown(matches){
  const dd=$('cmdDropdown');
  if(!dd)return;
  dd.innerHTML='';
  _cmdSelectedIdx=-1;
  for(let i=0;i<matches.length;i++){
    const c=matches[i];
    const el=document.createElement('div');
    el.className='cmd-item';
    el.dataset.idx=i;
    const usage=c.arg?` <span class="cmd-item-arg">${esc(c.arg)}</span>`:'';
    el.innerHTML=`<div class="cmd-item-name">/${esc(c.name)}${usage}</div><div class="cmd-item-desc">${esc(c.desc)}</div>`;
    el.onmousedown=(e)=>{
      e.preventDefault();
      $('msg').value='/'+c.name+(c.arg?' ':'');
      hideCmdDropdown();
      $('msg').focus();
    };
    dd.appendChild(el);
  }
  dd.classList.add('open');
}

function hideCmdDropdown(){
  const dd=$('cmdDropdown');
  if(dd)dd.classList.remove('open');
  _cmdSelectedIdx=-1;
  _dirSelectedIdx=-1;
  _dirCurrentPrefix='';
  if(_dirDebounceTimer){clearTimeout(_dirDebounceTimer);_dirDebounceTimer=null;}
}

function navigateCmdDropdown(dir){
  const dd=$('cmdDropdown');
  if(!dd)return;
  const items=dd.querySelectorAll('.cmd-item');
  if(!items.length)return;
  items.forEach(el=>el.classList.remove('selected'));
  _cmdSelectedIdx+=dir;
  if(_cmdSelectedIdx<0)_cmdSelectedIdx=items.length-1;
  if(_cmdSelectedIdx>=items.length)_cmdSelectedIdx=0;
  items[_cmdSelectedIdx].classList.add('selected');
}

function selectCmdDropdownItem(){
  const dd=$('cmdDropdown');
  if(!dd)return;
  const items=dd.querySelectorAll('.cmd-item');
  if(_cmdSelectedIdx>=0&&_cmdSelectedIdx<items.length){
    items[_cmdSelectedIdx].onmousedown({preventDefault:()=>{}});
  } else if(items.length===1){
    items[0].onmousedown({preventDefault:()=>{}});
  }
  hideCmdDropdown();
}

// ── Directory path autocomplete ───────────────────────────────────────────

let _dirSelectedIdx=-1;
let _dirDebounceTimer=null;
let _dirCurrentPrefix='';

const _dirPathRe=/^(\.{1,2}\/|~\/|\/[^\s/]+\/|[^\s/]+\/)[^\s/]*$/;

function detectDirPrefix(text){
  if(!text) return null;
  const m=text.match(_dirPathRe);
  return m?m[0]:null;
}

function showDirDropdown(matches){
  const dd=$('cmdDropdown');
  if(!dd)return;
  dd.innerHTML='';
  _dirSelectedIdx=-1;
  for(let i=0;i<matches.length;i++){
    const m=matches[i];
    const el=document.createElement('div');
    el.className='cmd-item';
    el.dataset.idx=i;
    el.innerHTML=`<div class="cmd-item-name dir-path-suggest"><span class="dir-path-icon">&#128193;</span> ${esc(m.path)}</div>`;
    el.onmousedown=(e)=>{
      e.preventDefault();
      _insertDirPath(m.path);
      hideCmdDropdown();
    };
    dd.appendChild(el);
  }
  dd.classList.add('open');
}

function hideDirDropdown(){
  const dd=$('cmdDropdown');
  if(dd)dd.classList.remove('open');
  _dirSelectedIdx=-1;
  _dirCurrentPrefix='';
  if(_dirDebounceTimer){clearTimeout(_dirDebounceTimer);_dirDebounceTimer=null;}
}

function navigateDirDropdown(dir){
  const dd=$('cmdDropdown');
  if(!dd)return;
  const items=dd.querySelectorAll('.cmd-item');
  if(!items.length)return;
  items.forEach(el=>el.classList.remove('selected'));
  _dirSelectedIdx+=dir;
  if(_dirSelectedIdx<0)_dirSelectedIdx=items.length-1;
  if(_dirSelectedIdx>=items.length)_dirSelectedIdx=0;
  items[_dirSelectedIdx].classList.add('selected');
}

function selectDirDropdownItem(){
  const dd=$('cmdDropdown');
  if(!dd)return;
  const items=dd.querySelectorAll('.cmd-item');
  if(_dirSelectedIdx>=0&&_dirSelectedIdx<items.length){
    items[_dirSelectedIdx].onmousedown({preventDefault:()=>{}});
  } else if(items.length===1){
    items[0].onmousedown({preventDefault:()=>{}});
  }
  hideDirDropdown();
}

function _insertDirPath(fullPath){
  const input=$('msg');
  if(!input)return;
  const text=input.value;
  const prefix=_dirCurrentPrefix;
  if(!prefix)return;
  const startIdx=text.lastIndexOf(prefix);
  if(startIdx===-1)return;
  const before=text.slice(0,startIdx);
  const after=input.selectionStart<text.length?text.slice(input.selectionStart):'';
  const insertChar=after&&!after.startsWith('/')&&!after.startsWith(' ')?'/':'';
  input.value=before+fullPath+insertChar+after;
  input.selectionStart=input.selectionEnd=before.length+fullPath.length+(insertChar?1:0);
  autoResize();
  updateSendBtn();
}

async function searchDirPaths(prefix){
  if(!S.session)return[];
  try{
    const data=await api(`/api/workspaces/path-suggest?session_id=${encodeURIComponent(S.session.session_id)}&prefix=${encodeURIComponent(prefix)}`);
    return data.matches||[];
  }catch(e){return[];}
}

function handleDirInput(text){
  const prefix=detectDirPrefix(text);
  if(!prefix){
    hideDirDropdown();
    return;
  }
  if(prefix===_dirCurrentPrefix)return;
  hideDirDropdown();
  _dirCurrentPrefix=prefix;
  if(_dirDebounceTimer)clearTimeout(_dirDebounceTimer);
  _dirDebounceTimer=setTimeout(async()=>{
    const matches=await searchDirPaths(prefix);
    if(_dirCurrentPrefix===prefix&&matches.length){
      showDirDropdown(matches);
    }
  },150);
}
