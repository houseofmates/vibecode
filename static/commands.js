// ── Slash commands ──────────────────────────────────────────────────────────
// Local commands (intercepted before send, no agent round-trip) + catalog
// commands from hermes-agent COMMAND_REGISTRY (sent to the agent).
// The catalog is fetched from /api/commands on boot and merged at autocomplete time.

// ── Local command handlers ─────────────────────────────────────────────────
const LOCAL_COMMANDS=[
 {name:'help', desc:t('cmd_help'), fn:cmdHelp},
 {name:'clear', desc:t('cmd_clear'), fn:cmdClear},
 {name:'compress', desc:t('cmd_compress'), fn:cmdCompress},
 {name:'model', desc:t('cmd_model'), fn:cmdModel, arg:'model_name'},
 {name:'workspace', desc:t('cmd_workspace'), fn:cmdWorkspace, arg:'name'},
 {name:'new', desc:t('cmd_new'), fn:cmdNew},
 {name:'usage', desc:t('cmd_usage'), fn:cmdUsage},
 {name:'theme', desc:t('cmd_theme'), fn:cmdTheme, arg:'name'},
 {name:'personality', desc:t('cmd_personality'), fn:cmdPersonality, arg:'name'},
 {name:'skills', desc:t('cmd_skills'), fn:cmdSkills, arg:'query'},
 {name:'clear-sudo-cache', desc:'Clear cached sudo password', fn:cmdClearSudoCache},
 {name:'steer', desc:'Queue a message to send after next tool completes', fn:cmdSteer, arg:'message'},
];

// ── Catalog from hermes-agent COMMAND_REGISTRY ────────────────────────────
let _catalog=null;       // raw /api/commands response: {commands:[...], sub:{...}}
let _catalogByName=null; // map: name -> cmd entry (including aliases)
let _skillsCatalog=null; // raw /api/skills response: {skills:[...]}
let _skillsByName=null;  // map: name -> skill entry

async function fetchCommandsCatalog(){
 try{
 const data=await api('/api/commands');
 if(data&&data.commands){
 _catalog=data;
 _buildCatalogLookup();
 }
 }catch(e){
 console.warn('failed to fetch commands catalog:',e);
 }
}

function _buildCatalogLookup(){
 if(!_catalog)return;
 _catalogByName={};
 for(const cmd of _catalog.commands){
 // skip cli_only commands (they need a terminal, not available in webui)
 if(cmd.cli_only)continue;
 _catalogByName[cmd.name.toLowerCase()]=cmd;
 for(const alias of (cmd.aliases||[])){
 _catalogByName[alias.toLowerCase()]=cmd;
 }
 }
}

async function fetchSkillsCatalog(){
 try{
 const data=await api('/api/skills');
 if(data&&Array.isArray(data.skills)){
 _skillsCatalog=data.skills;
 _buildSkillsLookup();
 }
 }catch(e){
 console.warn('failed to fetch skills catalog:',e);
 }
}

function _buildSkillsLookup(){
 if(!_skillsCatalog)return;
 _skillsByName={};
 for(const skill of _skillsCatalog){
 if(!skill || !skill.name) continue;
 _skillsByName[skill.name.toLowerCase()] = skill;
 }
}

// Fetch catalog on load, then refresh every 5 minutes
fetchCommandsCatalog();
fetchSkillsCatalog();
setInterval(fetchCommandsCatalog,300000);
setInterval(fetchSkillsCatalog,300000);

// ── Backwards compat: COMMANDS alias ───────────────────────────────────────
const COMMANDS=LOCAL_COMMANDS;

// ── Parse & execute ────────────────────────────────────────────────────────

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
 const normalizedName=parsed.name.toLowerCase();
 // local commands take priority
 const local=LOCAL_COMMANDS.find(c=>c.name===normalizedName);
 if(local){local.fn(parsed.args);return true;}
 // catalog commands: send to the agent as a chat message
 if(_catalogByName&&_catalogByName[normalizedName]){
 _sendCatalogCommand(parsed.name,parsed.args);
 return true;
 }
 // skills: allow /<skill-name> with optional extra instructions
 if(_skillsByName&&_skillsByName[normalizedName]){
 _sendSkillCommand(parsed.name,parsed.args);
 return true;
 }
 return false;
}

async function _sendSkillCommand(name,args){
 const displayText=args?`/${name} ${args}`:`/${name}`;
 const userMsg={role:'user',content:displayText,_ts:Date.now()/1000};
 S.messages.push(userMsg);
 renderMessages();
 if(!S.session){await newSession();await renderSessionList();}
 const activeSid=S.session.session_id;
 S.toolCalls=[];
 clearLiveToolCards();
 appendThinking();
 setBusy(true);
 INFLIGHT[activeSid]={messages:[...S.messages],uploaded:[],toolCalls:[]};
 if(typeof saveInflightState==='function'){
 saveInflightState(activeSid,{streamId:null,messages:INFLIGHT[activeSid].messages,uploaded:[],toolCalls:[]});
 }
 let skillContent='';
 try{
 const data=await api(`/api/skills/content?name=${encodeURIComponent(name)}`);
 if(data&&typeof data.content==='string'){
 skillContent=data.content.trim();
 }
 }catch(_){
 // ignore failures and fall back to a simple skill request
 }
 let msgText='';
 if(skillContent){
 msgText=`Use the skill "${name}" and follow its instructions exactly.\n\nSkill definition:\n${skillContent}`;
 if(args){
 msgText += `\n\nAdditional instructions: ${args}`;
 }
 } else {
 msgText=`Use the skill "${name}".`;
 if(args){
 msgText += ` Additional instructions: ${args}`;
 }
 }
 if(!msgText){
 msgText=displayText;
 }
 if(!S.session){await newSession();await renderSessionList();}
 const activeSessionId=S.session.session_id;
 try{
 const startData=await api('/api/chat/start',{method:'POST',body:JSON.stringify({
 session_id:activeSessionId,
 message:msgText,
 model:S.session.model||$('modelSelect').value,
 workspace:S.session.workspace,
 })});
 const streamId=startData.stream_id;
 S.activeStreamId=streamId;
 markInflight(activeSessionId,streamId);
 if(typeof saveInflightState==='function'){
 saveInflightState(activeSessionId,{streamId,messages:INFLIGHT[activeSessionId].messages,uploaded:[],toolCalls:[]});
 }
 if(typeof startStreamPolling==='function')startStreamPolling(activeSessionId,streamId);
 }catch(e){
 setBusy(false);
 showToast('command failed: '+e.message);
 }
}

async function _sendCatalogCommand(name,args){
 // Show the command as a user message, then send to the agent
 const displayText=args?`/${name} ${args}`:`/${name}`;
 const userMsg={role:'user',content:displayText,_ts:Date.now()/1000};
 S.messages.push(userMsg);
 renderMessages();
 // Send via the normal chat flow — the gateway dispatches slash commands
 if(!S.session){await newSession();await renderSessionList();}
 const activeSid=S.session.session_id;
 S.toolCalls=[];
 clearLiveToolCards();
 appendThinking();
 setBusy(true);
 INFLIGHT[activeSid]={messages:[...S.messages],uploaded:[],toolCalls:[]};
 if(typeof saveInflightState==='function'){
 saveInflightState(activeSid,{streamId:null,messages:INFLIGHT[activeSid].messages,uploaded:[],toolCalls:[]});
 }
 startApprovalPolling(activeSid);
 startClarifyPolling(activeSid);
 startSudoPasswordPolling(activeSid);
 S.activeStreamId=null;
 let streamId;
 try{
 const startData=await api('/api/chat/start',{method:'POST',body:JSON.stringify({
 session_id:activeSid,message:displayText,
 model:S.session.model||$('modelSelect').value,workspace:S.session.workspace
 })});
 streamId=startData.stream_id;
 S.activeStreamId=streamId;
 markInflight(activeSid,streamId);
 if(typeof saveInflightState==='function'){
 saveInflightState(activeSid,{streamId,messages:INFLIGHT[activeSid].messages,uploaded:[],toolCalls:[]});
 }
 if(typeof startStreamPolling==='function')startStreamPolling(activeSid,streamId);
 }catch(e){
 setBusy(false);
 showToast('command failed: '+e.message);
 }
}

// ── Autocomplete matching ─────────────────────────────────────────────────

function getMatchingCommands(prefix){
 const q=prefix.toLowerCase();
 const seen=new Set();
 const results=[];
 // local commands first
 for(const c of LOCAL_COMMANDS){
 if(c.name.startsWith(q)&&!seen.has(c.name)){
 seen.add(c.name);
 results.push({
 name:c.name,
 desc:c.desc,
 arg:c.arg||'',
 category:'local',
 aliases:[],
 subcommands:[],
 });
 }
 }
 // catalog commands (skip cli_only, skip duplicates with local)
 if(_catalogByName){
 // we need to iterate the raw catalog to get all entries, not just by-lookup
 for(const cmd of (_catalog?_catalog.commands:[])){
 if(cmd.cli_only)continue;
 const nameMatch=cmd.name.toLowerCase().startsWith(q);
 const aliasMatch=(cmd.aliases||[]).some(a=>a.toLowerCase().startsWith(q));
 if((nameMatch||aliasMatch)&&!seen.has(cmd.name)){
 seen.add(cmd.name);
 results.push({
 name:cmd.name,
 desc:cmd.description,
 arg:cmd.args_hint||'',
 category:cmd.category,
 aliases:cmd.aliases||[],
 subcommands:cmd.subcommands||[],
 });
 }
 // also show matching aliases as separate entries
 for(const alias of (cmd.aliases||[])){
 if(alias.toLowerCase().startsWith(q)&&!seen.has(alias)){
 seen.add(alias);
 results.push({
 name:alias,
 desc:cmd.description+' (alias for /'+cmd.name+')',
 arg:cmd.args_hint||'',
 category:cmd.category,
 aliases:[],
 subcommands:cmd.subcommands||[],
 isAlias:true,
 aliasOf:cmd.name,
 });
 }
 }
 }
 }
 // Skill names available via /api/skills
 if(_skillsCatalog){
 for(const skill of _skillsCatalog){
 if(!skill||!skill.name) continue;
 const lowerName=skill.name.toLowerCase();
 const title=(skill.title||skill.category||'').toString();
 if(lowerName.startsWith(q) && !seen.has(skill.name)){
 seen.add(skill.name);
 results.push({
 name:skill.name,
 desc:title||'Skill',
 arg:'instructions',
 category:skill.category||'skills',
 aliases:[],
 subcommands:[],
 isSkill:true,
 });
 }
 }
 }
 return results;
}

// ── Command handlers (local) ──────────────────────────────────────────────

function cmdHelp(){
 const lines=LOCAL_COMMANDS.map(c=>{
 const usage=c.arg?` <${c.arg}>`:'';
 return ` /${c.name}${usage} — ${c.desc}`;
 });
 let catalogLines='';
 if(_catalog){
 const byCat={};
 for(const cmd of _catalog.commands){
 if(cmd.cli_only)continue;
 // skip ones that are already in LOCAL_COMMANDS
 if(LOCAL_COMMANDS.find(lc=>lc.name===cmd.name))continue;
 const cat=cmd.category||'other';
 if(!byCat[cat])byCat[cat]=[];
 byCat[cat].push(cmd);
 }
 for(const[cat,cmds] of Object.entries(byCat).sort()){
 catalogLines+=`\n\n**${cat}** (sent to agent)\n`;
 for(const cmd of cmds){
 const usage=cmd.args_hint?` ${cmd.args_hint}`:'';
 const aliases=cmd.aliases.length?` (aliases: ${cmd.aliases.map(a=>'/'+a).join(', ')})`:'';
 catalogLines+=` /${cmd.name}${usage} — ${cmd.description}${aliases}\n`;
 }
 }
 }
 const msg={role:'assistant',content:t('available_commands')+'\n'+lines.join('\n')+catalogLines};
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

async function cmdCompress(){
 if(!S.session){
 showToast(t('no_active_session'));
 return;
 }
 
 try{
 showToast('Compressing conversation...');
 const data=await api('/api/session/compress',{
 method:'POST',
 body:JSON.stringify({session_id:S.session.session_id})
 });
 
 if(data.error){
 showToast('Compression failed: '+data.error);
 return;
 }
 
 // Update session with compressed messages
 if(data.session){
 S.session=data.session;
 S.messages=data.session.messages||[];
 renderMessages();
 }
 
 // Show summary
 if(data.summary){
 const summary=data.summary;
 const msg={role:'assistant',content:`🗜️ ${summary.headline}\n${summary.token_line}${summary.note?'\n'+summary.note:''}`};
 S.messages.push(msg);
 renderMessages();
 }
 
 // Show warnings if any
 if(data.warnings&&data.warnings.length){
 showToast('⚠️ '+data.warnings.join(' '));
 }else{
 showToast('Conversation compressed successfully');
 }
 }catch(e){
 showToast('Compression failed: '+e.message);
 }
}

// Global function for onclick handlers
function triggerCompress(){
 if(S.busy){
 showToast('Wait for current task to finish, then use /compress');
 return;
 }
 // Execute the /compress command directly
 executeCommand('/compress');
}

// Expose for HTML onclick
window.triggerCompress = triggerCompress;

// Backwards compatibility alias
function triggerCompact(){
 triggerCompress();
}
window.triggerCompact = triggerCompact;

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
 lines.push(` \`${s.name}\`${desc}`);
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

function cmdClearSudoCache(){
 if(typeof _clearCachedSudoPassword === 'function'){
 _clearCachedSudoPassword();
 showToast('Sudo password cache cleared');
 } else {
 // Fallback: clear directly from localStorage
 try{
 localStorage.removeItem('hermes_sudo_password_cache');
 showToast('Sudo password cache cleared');
 }catch(e){
 showToast('Failed to clear sudo password cache');
 }
 }
}

let _steeringMessage = null;

function cmdSteer(args){
 if(!args || !args.trim()){
 // Show current steering message if any
 if(_steeringMessage){
 S.messages.push({role:'assistant',content:`**Steering message queued:**\n> ${_steeringMessage}`});
 renderMessages();
 } else {
 showToast('Usage: /steer <message> — queue message for next tool\n/steer cancel — clear queued message');
 }
 return;
 }
 // Handle cancel
 if(args.trim().toLowerCase() === 'cancel'){
 if(_steeringMessage){
 _steeringMessage = null;
 showToast('Steering message cancelled');
 } else {
 showToast('No steering message to cancel');
 }
 return;
 }
 if(!S.busy || !S.session){
 showToast('No active task to steer. Send normally instead.');
 return;
 }
 _steeringMessage = args.trim();
 showToast('Steering message queued for next tool completion');
}

function _popSteeringMessage(){
 const msg = _steeringMessage;
 _steeringMessage = null;
 return msg;
}

// Expose for messages.js
window._popSteeringMessage = _popSteeringMessage;

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
 const list=data.personalities.map(p=>` **${p.name}**${p.description?' — '+p.description:''}`).join('\n');
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

 // Group matches by category
 const byCategory={};
 for(const m of matches){
 const cat=m.category||'other';
 if(!byCategory[cat])byCategory[cat]=[];
 byCategory[cat].push(m);
 }

 // Render categories with headers
 for(const[cat,items] of Object.entries(byCategory)){
 // category header
 const hdr=document.createElement('div');
 hdr.className='cmd-category-header';
 hdr.textContent=cat;
 dd.appendChild(hdr);

 for(let i=0;i<items.length;i++){
 const c=items[i];
 const el=document.createElement('div');
 el.className='cmd-item';
 el.dataset.idx=String(dd.querySelectorAll('.cmd-item').length);

 // Build display: /name [args_hint] — desc
 let usage='';
 if(c.arg){
 usage=` <span class="cmd-item-arg">${esc(c.arg)}</span>`;
 }
 let aliasTag='';
 if(c.isAlias){
 aliasTag=` <span class="cmd-item-alias">→ /${esc(c.aliasOf)}</span>`;
 }
 let aliasesTag='';
 if(c.aliases&&c.aliases.length&&!c.isAlias){
 aliasesTag=` <span class="cmd-item-aliases">${c.aliases.map(a=>'/' +a).join(', ')}</span>`;
 }
 el.innerHTML=`<div class="cmd-item-name">/${esc(c.name)}${usage}${aliasTag}${aliasesTag}</div><div class="cmd-item-desc">${esc(c.desc)}</div>`;
 el.onmousedown=(e)=>{
 e.preventDefault();
 const targetName=c.isAlias?c.aliasOf:c.name;
 $('msg').value='/'+targetName+(c.arg?' ':'');
 hideCmdDropdown();
 $('msg').focus();
 };
 dd.appendChild(el);
 }
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
 // scroll into view
 items[_cmdSelectedIdx].scrollIntoView({block:'nearest'});
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
