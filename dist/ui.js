const S={session:null,messages:[],entries:[],busy:false,pendingFiles:[],toolCalls:[],activeStreamId:null,currentDir:'.',activeProfile:'default'};
const INFLIGHT={};  // keyed by session_id while request in-flight
const SESSION_QUEUES={};  // keyed by session_id for queued follow-up turns
let _queueBadgeHideTimer=null;
const $=id=>document.getElementById(id);
function _getSessionQueue(sid, create=false){
  if(!sid) return [];
  if(!SESSION_QUEUES[sid]&&create) SESSION_QUEUES[sid]=[];
  return SESSION_QUEUES[sid]||[];
}
function queueSessionMessage(sid, payload){
  if(!sid||!payload) return 0;
  const q=_getSessionQueue(sid,true);
  q.push(payload);
  return q.length;
}
function clearQueuedSessionMessages(sessionId){
  const sid=sessionId||(S.session&&S.session.session_id);
  if(!sid) return 0;
  const q=_getSessionQueue(sid,false);
  if(!q.length) return 0;
  const count=q.length;
  delete SESSION_QUEUES[sid];
  return count;
}
function shiftQueuedSessionMessage(sid){
  const q=_getSessionQueue(sid,false);
  if(!q.length) return null;
  const next=q.shift();
  if(!q.length) delete SESSION_QUEUES[sid];
  return next;
}
function getQueuedSessionCount(sid){
  return _getSessionQueue(sid,false).length;
}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// ── XML tool-tag helpers ───────────────────────────────────────────────────
// Models that emit pseudo-tool-calls as raw XML tags (e.g. <terminal>...</terminal>,
// <read_file>...</read_file>) instead of structured tool_calls need their tags
// extracted into collapsible tool cards and stripped from the chat bubble.
const _NON_TOOL_HTML_TAGS=new Set([
  'think','thinking','reasoning','REASONING_SCRATCHPAD',
  'br','p','div','span','strong','b','em','i','code','pre',
  'h1','h2','h3','h4','h5','h6','ul','ol','li','table','thead','tbody','tr','th','td',
  'hr','blockquote','a','img','sub','sup','del','s','u','mark','small','big','font',
  'center','strike','tt','var','kbd','samp','abbr','acronym','address','article','aside',
  'audio','bdi','bdo','canvas','cite','datalist','details','dfn','dialog','figcaption',
  'figure','footer','header','ins','main','map','nav','object','output','picture',
  'progress','q','rp','rt','ruby','section','summary','template','time','track','video','wbr',
  'math','mrow','mi','mo','mn','msqrt','mfrac','msub','msup','msubsup','munder','mover',
  'munderover','mtable','mtr','mtd','svg','path','rect','circle','ellipse','line','polyline',
  'polygon','text','g','defs','use','symbol','clipPath','mask','pattern','linearGradient',
  'radialGradient','stop','filter'
]);

function _isXmlToolTag(tagName){
  const tn=tagName.toLowerCase();
  if(_NON_TOOL_HTML_TAGS.has(tn)) return false;
  if(tn.includes('_')||tn.includes('-')) return true;
  const _known=new Set(['terminal','python','bash','shell','sh','cmd','powershell','js',
    'javascript','ruby','perl','rust','go','java','kotlin','swift','cpp','c','csharp','cs',
    'dart','lua','r','julia','matlab','groovy','clojure','lisp','scheme','haskell','ocaml',
    'nim','zig','v','mojo','php','typescript','ts']);
  return _known.has(tn);
}

function extractXmlToolCalls(text){
  const toolCalls=[];
  if(!text) return {displayText:text||'',toolCalls};
  let displayText=text;

  // ── NVIDIA NIM <tool_call> extraction ─────────────────────────────────────
  // NIM endpoints sometimes emit tool calls as raw XML inside message content
  // in addition to structured tool_calls. Handle the <tool_call>name<arg_key>k
  // </arg_key><arg_value>v</arg_value>...</tool_call> format explicitly.
  const nvidiaRe=/<tool_call>([\s\S]*?)<\/tool_call>/gi;
  let nm;
  while((nm=nvidiaRe.exec(text))!==null){
    const inner=nm[1].trim();
    // The tool name is the first token before any tag
    const nameMatch=inner.match(/^([a-zA-Z_][a-zA-Z0-9_\-]*)/);
    const name=nameMatch?nameMatch[1]:'tool_call';
    const args={};
    const kvRe=/<arg_key>([\s\S]*?)<\/arg_key>\s*<arg_value>([\s\S]*?)<\/arg_value>/gi;
    let kv;
    while((kv=kvRe.exec(inner))!==null){
      const k=kv[1].trim();
      const v=kv[2].trim();
      if(k) args[k]=v;
    }
    if(!Object.keys(args).length && inner) args.content=inner;
    toolCalls.push({
      name,
      preview:inner.slice(0,80),
      args,
      snippet:inner,
      done:true,
      tid:`xml-${name}-${Math.abs(inner.split('').reduce((h,c)=>((h<<5)-h)+c.charCodeAt(0),0)).toString(36)}`
    });
  }
  displayText=displayText.replace(nvidiaRe,'');
  // Strip orphaned arg_key/arg_value pairs that can remain when the outer
  // wrapper was fragmented across chunks or already removed by other code.
  displayText=displayText.replace(/<arg_key>[\s\S]*?<\/arg_key>\s*<arg_value>[\s\S]*?<\/arg_value>/gi,'');
  displayText=displayText.replace(/<arg_key>[\s\S]*?<\/arg_key>/gi,'');
  displayText=displayText.replace(/<arg_value>[\s\S]*?<\/arg_value>/gi,'');

  // ── NVIDIA NIM custom markers ──────────────────────────────────────────────
  // Strip markers like <tool_call_end>, <tool_calls_section_end>, <tool_call_begin|>
  displayText=displayText.replace(/<tool_call_end>/gi,'');
  displayText=displayText.replace(/<tool_calls_section_end>/gi,'');
  displayText=displayText.replace(/<tool_calls_section_begin>/gi,'');
  displayText=displayText.replace(/<\|tool_call_section_begin\|>/gi,'');
  displayText=displayText.replace(/<\|tool_call_section_end\|>/gi,'');
  displayText=displayText.replace(/<tool_call_begin\|>/gi,'');

  // ── JSON tool calls with "parameters" field (NVIDIA NIM style) ──────────
  // Pattern: {"name": "...", "parameters": {...}, "id": "..."}
  const jsonParamRe=/\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"parameters"\s*:\s*(\{[^\}]*\})[^\}]*\}/gi;
  let jsonMatch;
  while((jsonMatch=jsonParamRe.exec(text))!==null){
    const name=jsonMatch[1];
    let args={};
    try{ args=JSON.parse(jsonMatch[2]); }catch(e){ args={raw:jsonMatch[2]}; }
    const full=jsonMatch[0];
    toolCalls.push({
      name,
      preview:JSON.stringify(args).slice(0,80),
      args,
      snippet:full,
      done:true,
      tid:`json-${name}-${Math.abs(full.split('').reduce((h,c)=>((h<<5)-h)+c.charCodeAt(0),0)).toString(36)}`
    });
  }
  displayText=displayText.replace(jsonParamRe,'');

  // ── Partial JSON fragments (remnants of tool calls) ──────────────────────
  // Pattern: ,"id":"skills_list:1"} or similar fragments
  displayText=displayText.replace(/,\s*"id"\s*:\s*"[^"]+"\s*\}/g,'');

  // ── Generic XML pseudo-tool extraction ────────────────────────────────────
  const regex=/<([a-zA-Z_][a-zA-Z0-9_\-]*)[^>]*>([\s\S]*?)<\/\1>/g;
  let match;
  while((match=regex.exec(displayText))!==null){
    const tagName=match[1];
    const inner=match[2].trim();
    if(!_isXmlToolTag(tagName)) continue;
    // Skip already-handled NIM inner tags
    if(tagName==='arg_key'||tagName==='arg_value') continue;
    // Parse nested key-value tags like <limit>100</limit>
    const args={};
    const innerRe=/<([a-zA-Z_][a-zA-Z0-9_\-]*)>([\s\S]*?)<\/\1>/g;
    let im;
    while((im=innerRe.exec(inner))!==null) args[im[1]]=im[2].trim();
    if(!Object.keys(args).length && inner) args.content=inner;
    toolCalls.push({
      name:tagName,
      preview:inner.slice(0,80),
      args,
      snippet:inner,
      done:true,
      tid:`xml-${tagName}-${Math.abs(inner.split('').reduce((h,c)=>((h<<5)-h)+c.charCodeAt(0),0)).toString(36)}`
    });
  }
  displayText=displayText.replace(regex,(full,tagName)=>_isXmlToolTag(tagName)&&tagName!=='arg_key'&&tagName!=='arg_value'?'':full).trim();
  return {displayText,toolCalls};
}

// Dynamic model labels -- populated by populateModelDropdown(), fallback to static map
let _dynamicModelLabels={};

// ── Smart model resolver ────────────────────────────────────────────────────
// Finds the best matching option value in a <select> for a given model ID.
// Handles mismatches like 'claude-sonnet-4-6' vs 'anthropic/claude-sonnet-4.6'.
// Returns the matched option's value (already in the list), or null if no match.
function _findModelInDropdown(modelId, sel){
  if(!modelId||!sel) return null;
  const opts=Array.from(sel.options).map(o=>o.value);
  // 1. Exact match
  if(opts.includes(modelId)) return modelId;
  // 2. Normalize: lowercase, strip namespace prefix, replace hyphens→dots
  const norm=s=>s.toLowerCase().replace(/^[^/]+\//,'').replace(/-/g,'.');
  const target=norm(modelId);
  const exact=opts.find(o=>norm(o)===target);
  if(exact) return exact;
  // 3. Prefix/substring: target starts with or contains a significant chunk
  const base=target.replace(/\.\d+$/,'');  // strip trailing version number
  const partial=opts.find(o=>norm(o).startsWith(base)||norm(o).includes(base));
  return partial||null;
}

// Set the model picker to the best match for modelId.
// Returns the resolved value that was actually set, or null if nothing matched.
function _applyModelToDropdown(modelId, sel){
  if(!modelId||!sel) return null;
  const resolved=_findModelInDropdown(modelId,sel);
  if(resolved){
    sel.value=resolved;
    if(sel.id==='modelSelect' && typeof syncModelChip==='function') syncModelChip();
    return resolved;
  }
  return null;
}

async function populateModelDropdown(){
  const sel=$('modelSelect');
  if(!sel) return;
  // Skip dynamic population - use hardcoded HTML options only
  // This ensures only the models defined in index.html are available
  
  // Select first model by default if nothing selected
  if(!sel.value && sel.options.length > 0){
    sel.selectedIndex = 0;
  }
  if(typeof syncModelChip==='function') syncModelChip();
}

// Cache so we don't re-fetch on every page load
const _liveModelCache={};

async function _fetchLiveModels(provider, sel){
  if(!provider||!sel) return;
  // Don't fetch for providers where we know it's unsupported or unnecessary
  // All providers now supported via agent's provider_model_ids() — no exclusions needed
  if(_liveModelCache[provider]) return; // already fetched this session
  try{
    const url=new URL('api/models/live', window.HERMES_API_BASE || location.href);
    url.searchParams.set('provider',provider);
    const data=await fetch(url.href,{credentials:'include'}).then(r=>r.json());
    if(!data.models||!data.models.length) return;
    _liveModelCache[provider]=data.models;
    // Remember current selection before rebuilding options
    const currentVal=sel.value;
    // Rebuild the optgroup for this provider with live models
    // Keep other providers' optgroups intact
    let providerGroup=null;
    for(const og of sel.querySelectorAll('optgroup')){
      if(og.label&&og.label.toLowerCase().includes(provider.toLowerCase())){
        providerGroup=og; break;
      }
    }
    if(!providerGroup){
      // No existing group — add a new one
      providerGroup=document.createElement('optgroup');
      providerGroup.label=provider.charAt(0).toUpperCase()+provider.slice(1)+' (live)';
      sel.appendChild(providerGroup);
    }
    // Rebuild options from live data
    const existingIds=new Set([...sel.options].map(o=>o.value));
    let added=0;
    for(const m of data.models){
      if(existingIds.has(m.id)) continue; // already shown from static list
      const opt=document.createElement('option');
      opt.value=m.id;
      opt.textContent=m.label||m.id;
      opt.title='Live model — fetched from provider';
      providerGroup.appendChild(opt);
      _dynamicModelLabels[m.id]=m.label||m.id;
      added++;
    }
    if(added>0){
      // Restore selection
      if(currentVal) _applyModelToDropdown(currentVal, sel);
      if(typeof syncModelChip==='function') syncModelChip();
      console.log('[hermes] Live models loaded for',provider+':',added,'new models added');
    }
  }catch(e){
    console.debug('[hermes] Live model fetch failed for',provider,e.message);
  }
}

/**
 * Check if the given model ID belongs to a different provider than the one
 * currently configured in Hermes. Returns a warning string if mismatched,
 * or null if the selection looks compatible.
 *
 * Provider detection is intentionally loose — we compare the model's slash
 * prefix (e.g. "openai/" from "openai/gpt-4o") against the active provider
 * name. Custom/local endpoints report active_provider='custom' or the
 * base_url hostname and we skip the check to avoid false positives.
 */
function _checkProviderMismatch(modelId){
  const ap=(window._activeProvider||'').toLowerCase();
  if(!ap||ap==='custom'||ap==='openrouter') return null; // can't reliably check
  const slash=modelId.indexOf('/');
  if(slash<0) return null; // bare model name, no provider prefix
  const modelProvider=modelId.substring(0,slash).toLowerCase();
  // Normalise common aliases
  const aliases={'claude':'anthropic','gpt':'openai','gemini':'google'};
  const norm=p=>aliases[p]||p;
  if(norm(modelProvider)!==norm(ap)){
    return (window.t?window.t('provider_mismatch_warning',modelId,ap):
      `"${modelId}" may not work with your configured provider (${ap}). Send anyway or run \`hermes model\` to switch.`);
  }
  return null;
}

function _selectedModelOption(){
  const sel=$('modelSelect');
  if(!sel) return null;
  return sel.options[sel.selectedIndex]||null;
}

function syncModelChip(){
  console.log('[syncModelChip] called');
  const sel=$('modelSelect');
  const chip=$('composerModelChip');
  const label=$('composerModelLabel');
  const dd=$('composerModelDropdown');
  if(!sel||!chip||!label) { console.log('[syncModelChip] missing elements'); return; }
  console.log('[syncModelChip] sel:', sel ? sel.value : 'null');
  const opt=_selectedModelOption();
  label.textContent=opt?opt.textContent:getModelLabel(sel.value||'');
  chip.title=sel.value||'Conversation model';
  chip.classList.toggle('active',!!(dd&&dd.classList.contains('open')));
}

function _positionModelDropdown(){
  const dd=$('composerModelDropdown');
  const chip=$('composerModelChip');
  const footer=document.querySelector('.composer-footer');
  if(!dd||!chip||!footer) return;
  const chipRect=chip.getBoundingClientRect();
  const footerRect=footer.getBoundingClientRect();
  let left=chipRect.left-footerRect.left;
  const maxLeft=Math.max(0, footer.clientWidth-dd.offsetWidth);
  left=Math.max(0, Math.min(left, maxLeft));
  dd.style.left=`${left}px`;
}

function renderModelDropdown(){
  const dd=$('composerModelDropdown');
  const sel=$('modelSelect');
  if(!dd||!sel) return;
  dd.innerHTML='';
  for(const child of Array.from(sel.children)){
    if(child.tagName==='OPTGROUP'){
      const heading=document.createElement('div');
      heading.className='model-group';
      heading.textContent=child.label||'Models';
      if(child.dataset.group) heading.dataset.group=child.dataset.group;
      dd.appendChild(heading);
      for(const opt of Array.from(child.children)){
        const row=document.createElement('div');
        row.className='model-opt'+(opt.value===sel.value?' active':'');
        row.innerHTML=`<span class="model-opt-name">${esc(opt.textContent||getModelLabel(opt.value))}</span><span class="model-opt-id">${esc(_stripProviderPrefix(opt.value))}</span>`;
        row.onclick=()=>selectModelFromDropdown(opt.value);
        dd.appendChild(row);
      }
      continue;
    }
    if(child.tagName==='OPTION'){
      const row=document.createElement('div');
      row.className='model-opt'+(child.value===sel.value?' active':'');
      row.innerHTML=`<span class="model-opt-name">${esc(child.textContent||getModelLabel(child.value))}</span><span class="model-opt-id">${esc(_stripProviderPrefix(child.value))}</span>`;
      row.onclick=()=>selectModelFromDropdown(child.value);
      dd.appendChild(row);
    }
  }
  // Custom model ID input — lets users type any model not in the curated list
  const _custSep=document.createElement('div');
  _custSep.className='model-group model-custom-sep';
  _custSep.textContent=t('model_custom_label')||'custom model id';
  dd.appendChild(_custSep);
  const _custRow=document.createElement('div');
  _custRow.className='model-custom-row';
  _custRow.innerHTML=`<input class="model-custom-input" type="text" placeholder="${esc(t('model_custom_placeholder')||'e.g. openai/gpt-5.4')}" spellcheck="false" autocomplete="off"><button class="model-custom-btn" title="Use this model">${li('plus',12)}</button>`;
  const _ci=_custRow.querySelector('.model-custom-input');
  const _cb=_custRow.querySelector('.model-custom-btn');
  const _applyCustom=()=>{const v=_ci.value.trim();if(!v)return;selectModelFromDropdown(v);_ci.value='';};
  _cb.onclick=_applyCustom;
  _ci.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();_applyCustom();}if(e.key==='Escape'){closeModelDropdown();}});
  _ci.addEventListener('click',e=>e.stopPropagation());
  dd.appendChild(_custRow);
}

async function selectModelFromDropdown(value){
  const sel=$('modelSelect');
  if(!sel||sel.value===value) { closeModelDropdown(); return; }
  // If the value isn't in the option list (custom model ID), add a temporary option
  // so sel.value assignment succeeds and the model chip shows the custom ID.
  if(!Array.from(sel.options).some(o=>o.value===value)){
    const opt=document.createElement('option');
    opt.value=value;
    opt.textContent=value.split('/').pop()||value;
    opt.dataset.custom='1';
    // Remove any previous custom option before adding new one
    sel.querySelectorAll('option[data-custom]').forEach(o=>o.remove());
    sel.appendChild(opt);
  }
  sel.value=value;
  syncModelChip();
  closeModelDropdown();
  if(typeof sel.onchange==='function') await sel.onchange();
}

function toggleModelDropdown(){
  const dd=$('composerModelDropdown');
  const chip=$('composerModelChip');
  const sel=$('modelSelect');
  if(!dd||!chip||!sel) return;
  const open=dd.classList.contains('open');
  if(open){closeModelDropdown(); return;}
  if(typeof closeProfileDropdown==='function') closeProfileDropdown();
  if(typeof closeWsDropdown==='function') closeWsDropdown();
  renderModelDropdown();
  dd.classList.add('open');
  _positionModelDropdown();
  chip.classList.add('active');
}

function closeModelDropdown(){
  const dd=$('composerModelDropdown');
  const chip=$('composerModelChip');
  if(dd) dd.classList.remove('open');
  if(chip) chip.classList.remove('active');
}

document.addEventListener('click',e=>{
  if(!e.target.closest('#composerModelChip') && !e.target.closest('#composerModelDropdown')) closeModelDropdown();
});
window.addEventListener('resize',()=>{
  const dd=$('composerModelDropdown');
  if(dd&&dd.classList.contains('open')) _positionModelDropdown();
});

// ── Scroll pinning ──────────────────────────────────────────────────────────
// When streaming, auto-scroll only if the user hasn't manually scrolled up.
// Once the user scrolls back to within 80px of the bottom, re-pin.
let _scrollPinned=true;
(function(){
  const el=document.getElementById('messages');
  if(!el) return;
  el.addEventListener('scroll',()=>{
    const nearBottom=el.scrollHeight-el.scrollTop-el.clientHeight<80;
    _scrollPinned=nearBottom;
  });
})();
function _fmtTokens(n){if(!n||n<0)return'0';if(n>=1e6)return(n/1e6).toFixed(1)+'M';if(n>=1e3)return(n/1e3).toFixed(1)+'k';return String(n);}

// Context usage indicator in composer footer
function _syncCtxIndicator(usage){
  const wrap=$('ctxIndicatorWrap');
  const el=$('ctxIndicator');
  if(!el)return;
  const promptTok=usage.last_prompt_tokens||usage.input_tokens||0;
  const totalTok=(usage.input_tokens||0)+(usage.output_tokens||0);
  const ctxWindow=usage.context_length||0;
  const cost=usage.estimated_cost;
  // Show indicator whenever we have any usage data (tokens or cost)
  if(!promptTok&&!totalTok&&!cost){
    if(wrap) wrap.style.display='none';
    return;
  }
  if(wrap) wrap.style.display='';
  const hasCtxWindow=!!(promptTok&&ctxWindow);
  const pct=hasCtxWindow?Math.min(100,Math.round((promptTok/ctxWindow)*100)):0;
  const center=$('ctxPercent');
  const usageLine=$('ctxTooltipUsage');
  const tokensLine=$('ctxTooltipTokens');
  const thresholdLine=$('ctxTooltipThreshold');
  const costLine=$('ctxTooltipCost');
  const bar=$('ctxBarValue');
  if(bar){
    bar.style.width=String(pct)+'%';
  }
  if(center) center.textContent=hasCtxWindow?String(pct)+'%':'0%';
  el.classList.toggle('ctx-mid',pct>50&&pct<=75);
  el.classList.toggle('ctx-high',pct>75);
  let label=hasCtxWindow?`Context window ${pct}% used`:`${_fmtTokens(totalTok)} tokens used`;
  if(cost) label+=` \u00b7 $${cost<0.01?cost.toFixed(4):cost.toFixed(2)}`;
  el.setAttribute('aria-label',label);
  if(usageLine) usageLine.textContent=hasCtxWindow?`${pct}% used (${Math.max(0,100-pct)}% left)`:`${_fmtTokens(totalTok)} tokens used`;
  if(tokensLine) tokensLine.textContent=hasCtxWindow?`${_fmtTokens(promptTok)} / ${_fmtTokens(ctxWindow)} tokens used`:`In: ${_fmtTokens(usage.input_tokens||0)} \u00b7 Out: ${_fmtTokens(usage.output_tokens||0)}`;
  const threshold=usage.threshold_tokens||0;
  if(thresholdLine){
    if(threshold&&ctxWindow){
      thresholdLine.style.display='';
      thresholdLine.textContent=`Auto-compress at ${_fmtTokens(threshold)} (${Math.round(threshold/ctxWindow*100)}%)`;
    }else{
      thresholdLine.style.display='none';
      thresholdLine.textContent='';
    }
  }
  if(costLine){
    if(cost){
      costLine.style.display='';
      costLine.textContent=`Estimated cost: $${cost<0.01?cost.toFixed(4):cost.toFixed(2)}`;
    }else{
      costLine.style.display='none';
      costLine.textContent='';
    }
  }
}

function scrollIfPinned(){
  if(!_scrollPinned) return;
  const el=$('messages');
  if(el) el.scrollTop=el.scrollHeight;
}
function scrollToBottom(){
  _scrollPinned=true;
  const el=$('messages');
  if(el) el.scrollTop=el.scrollHeight;
}

const EMOJI_SHORTCODES = {
  '+1': '👍',
  '-1': '👎',
  '100': '💯',
  '1st_place_medal': '🥇',
  '2nd_place_medal': '🥈',
  '3rd_place_medal': '🥉',
  'clap': '👏',
  'cry': '😢',
  'sob': '😭',
  'joy': '😂',
  'laughing': '😆',
  'sweat_smile': '😅',
  'smile': '😄',
  'grin': '😁',
  'wink': '😉',
  'blush': '😊',
  'heart_eyes': '😍',
  'star_struck': '🤩',
  'sunglasses': '😎',
  'thinking': '🤔',
  'raised_hands': '🙌',
  'pray': '🙏',
  'muscle': '💪',
  'ok_hand': '👌',
  'thumbsup': '👍',
  'thumbsdown': '👎',
  'wave': '👋',
  'fire': '🔥',
  'sparkles': '✨',
  'tada': '🎉',
  'rocket': '🚀',
  'boom': '💥',
  'poop': '💩',
  'heart': '❤️',
  'star': '⭐',
  'eyes': '👀',
  'ghost': '👻',
  'skull': '💀',
  'alien': '👽',
  'key': '🔑',
  'lock': '🔒',
  'zzz': '💤',
  'trophy': '🏆',
  'money_mouth': '🤑',
  'party': '🥳',
  'see_no_evil': '🙈',
  'hear_no_evil': '🙉',
  'speak_no_evil': '🙊',
  'thumbs_up': '👍',
  'thumbs_down': '👎',
  'heartpulse': '💗',
  'sparkling_heart': '💖',
  'purple_heart': '💜',
  'blue_heart': '💙',
  'green_heart': '💚',
  'yellow_heart': '💛',
  'broken_heart': '💔'
};

function expandEmojiShortcodes(raw){
  if(!raw||raw.indexOf(':')===-1) return raw;
  return raw.replace(/:([a-z0-9_+\-]+):/gi,(_,name)=>{
    const key = name.toLowerCase().replace(/-/g,'_');
    return EMOJI_SHORTCODES[key] || `:${name}:`;
  });
}

function _stripProviderPrefix(modelId){
  // Strip @provider: prefix used for credential routing (e.g., @nvidia:model-name)
  if(!modelId) return '';
  if(modelId.startsWith('@') && modelId.includes(':')){
    return modelId.split(':').slice(1).join(':')||modelId;
  }
  return modelId;
}
function getModelLabel(modelId){
  if(!modelId) return 'Unknown';
  // Check dynamic labels first, then fall back to splitting the ID
  if(_dynamicModelLabels[modelId]) return _dynamicModelLabels[modelId];
  // Static fallback for common models
  const STATIC_LABELS={'openai/gpt-5.4-mini':'GPT-5.4 Mini','openai/gpt-4o':'GPT-4o','openai/o3':'o3','openai/o4-mini':'o4-mini','anthropic/claude-sonnet-4.6':'Sonnet 4.6','anthropic/claude-sonnet-4-5':'Sonnet 4.5','anthropic/claude-haiku-3-5':'Haiku 3.5','google/gemini-2.5-pro':'Gemini 2.5 Pro','deepseek/deepseek-chat-v3-0324':'DeepSeek V3','meta-llama/llama-4-scout':'Llama 4 Scout'};
  if(STATIC_LABELS[modelId]) return STATIC_LABELS[modelId];
  return _stripProviderPrefix(modelId).split('/').pop()||'Unknown';
}

function renderMd(raw){
  let s=raw||'';
  // ── Filter random 2-3 digit number sequences (DeepSeek v4 Pro NIM bug) ─────
  // Removes numbers like "20", "60", "16" inserted directly into words without
  // punctuation (e.g., "its20", "tokens60", "it16") while preserving legitimate
  // numbers like version numbers (v1.0), ports (:8786), years (2024), etc.
  s=s.replace(/([a-zA-Z])\d{2,3}([a-zA-Z])/g,'$1$2');
  // Also handle numbers at end of words followed by space or punctuation
  s=s.replace(/([a-zA-Z])\d{2,3}([\s.,;:!?])/g,'$1$2');
  // ── End random number filter ──────────────────────────────────────────────
  // ── MEDIA: token stash (must run first, before any other processing) ───────
  // Detect MEDIA:<path-or-url> tokens emitted by the agent (e.g. screenshots,
  // generated images) and replace them with inline <img> or download links.
  // Stashed so the path/URL is never processed as markdown.
  const _IMAGE_EXTS=/\.(png|jpg|jpeg|gif|webp|bmp|ico)$/i;
  const media_stash=[];
  s=s.replace(/MEDIA:([^\s\)\]]+)/g,(_,raw_ref)=>{
    media_stash.push(raw_ref);
    return '\x00D'+(media_stash.length-1)+'\x00';
  });
  // ── End MEDIA stash ─────────────────────────────────────────────────────────
  // Pre-pass: decode HTML entities first so markdown processing works correctly.
  // This prevents double-escaping when LLM outputs entities like &lt; &gt; &amp;
  const decode=s=>s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'");
  s=decode(s);
  // Pre-pass: convert safe inline HTML tags the model may emit into their
  // markdown equivalents so the pipeline can render them correctly.
  // Only runs OUTSIDE fenced code blocks and backtick spans (stash + restore).
  // Unsafe tags (anything not in the allowlist) are left as-is and will be
  // HTML-escaped by esc() when they reach an innerHTML assignment -- no XSS risk.
  // Fence stash: protect code blocks and backtick spans from all further processing
  // Must run BEFORE math_stash so $..$ inside code spans is not extracted as math
  const fence_stash=[];
  s=s.replace(/(```[\s\S]*?```|`[^`\n]+`)/g,m=>{fence_stash.push(m);return '\x00F'+(fence_stash.length-1)+'\x00';});
  // Math stash: protect $$..$$ and $..$ from markdown processing
  // Runs AFTER fence_stash so backtick code spans protect their dollar-sign contents
  const math_stash=[];
  // Display math: $$...$$  (must come before inline to avoid mis-parsing)
  s=s.replace(/\$\$([\s\S]+?)\$\$/g,(_,m)=>{math_stash.push({type:'display',src:m});return '\x00M'+(math_stash.length-1)+'\x00';});
  // Inline math: $...$ — require non-space at boundaries to avoid false positives
  // e.g. "costs $5 and $10" should not trigger (space after opening $)
  s=s.replace(/\$([^\s$\n][^$\n]*?[^\s$\n]|\S)\$/g,(_,m)=>{math_stash.push({type:'inline',src:m});return '\x00M'+(math_stash.length-1)+'\x00';});
  // Also stash \(...\) and \[...\] LaTeX delimiters
  s=s.replace(/\\\\\((.+?)\\\\\)/g,(_,m)=>{math_stash.push({type:'inline',src:m});return '\x00M'+(math_stash.length-1)+'\x00';});
  s=s.replace(/\\\\\[(.+?)\\\\\]/gs,(_,m)=>{math_stash.push({type:'display',src:m});return '\x00M'+(math_stash.length-1)+'\x00';});
  // Safe tag → markdown equivalent (these produce the same output as **text** etc.)
  s=s.replace(/<strong>([\s\S]*?)<\/strong>/gi,(_,t)=>'**'+t+'**');
  s=s.replace(/<b>([\s\S]*?)<\/b>/gi,(_,t)=>'**'+t+'**');
  s=s.replace(/<em>([\s\S]*?)<\/em>/gi,(_,t)=>'*'+t+'*');
  s=s.replace(/<i>([\s\S]*?)<\/i>/gi,(_,t)=>'*'+t+'*');
  s=s.replace(/<code>([^<]*?)<\/code>/gi,(_,t)=>'`'+t+'`');
  s=s.replace(/<br\s*\/?>/gi,'\n');
  s = expandEmojiShortcodes(s);
  // Restore stashed code blocks
  s=s.replace(/\x00F(\d+)\x00/g,(_,i)=>fence_stash[+i]);
  // Mermaid blocks: render as diagram containers (processed after DOM insertion)
  s=s.replace(/```mermaid\n?([\s\S]*?)```/g,(_,code)=>{
    const id='mermaid-'+Math.random().toString(36).slice(2,10);
    return `<div class="mermaid-block" data-mermaid-id="${id}">${esc(code.trim())}</div>`;
  });
  s=s.replace(/```([\w+-]*)\n?([\s\S]*?)```/g,(_,lang,code)=>{
    const normalizedLang=(lang||'').trim().toLowerCase();
    const h=normalizedLang?`<div class="pre-header">${esc(normalizedLang)}</div>`:'';
    const langAttr=normalizedLang?` class="language-${esc(normalizedLang)}"`:'';
    return `${h}<pre><code${langAttr}>${esc(code.replace(/\n$/,''))}</code></pre>`;
  });
  s=s.replace(/`([^`\n]+)`/g,(_,c)=>`<code>${esc(c)}</code>`);
  // inlineMd: process bold/italic/code/links within a single line of text.
  // Used inside list items and blockquotes where the text may already contain
  // HTML from the pre-pass → bold pipeline, so we cannot call esc() directly.
  function inlineMd(t){
    // Stash backtick code spans first so bold/italic never esc() their content
    const _code_stash=[];
    t=t.replace(/`([^`\n]+)`/g,(_,x)=>{_code_stash.push(`<code>${esc(x)}</code>`);return `\x00C${_code_stash.length-1}\x00`;});
    t=t.replace(/\*\*\*(.+?)\*\*\*/g,(_,x)=>`<strong><em>${esc(x)}</em></strong>`);
    t=t.replace(/\*\*(.+?)\*\*/g,(_,x)=>`<strong>${esc(x)}</strong>`);
    t=t.replace(/\*([^*\n]+)\*/g,(_,x)=>`<em>${esc(x)}</em>`);
    // #487: Image pass — runs while code stash is active so ![x](url) inside
    // backticks stays protected as a \x00C token and is never rendered as <img>.
    // Must run before _code_stash restore and before _link_stash so the image
    // is not consumed by the [label](url) link regex.
    t=t.replace(/!\[([^\]]*)\]\((https?:\/\/[^\)]+)\)/g,(_,alt,url)=>`<img src="${url.replace(/"/g,'%22')}" alt="${esc(alt)}" class="msg-media-img" loading="lazy" onclick="this.classList.toggle('msg-media-img--full')">`);
    // Stash rendered <img> tags so autolink never matches URLs inside src=
    const _img_stash=[];
    t=t.replace(/(<img\b[^>]*>)/g,m=>{_img_stash.push(m);return `\x00G${_img_stash.length-1}\x00`;});
    t=t.replace(/\x00C(\d+)\x00/g,(_,i)=>_code_stash[+i]);
    // Stash [label](url) links before autolink so the URL in href= is not re-linked
    const _link_stash=[];
    t=t.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,(_,lb,u)=>{_link_stash.push(`<a href="${u.replace(/"/g,'%22')}" target="_blank" rel="noopener">${esc(lb)}</a>`);return `\x00L${_link_stash.length-1}\x00`;});
    t=t.replace(/(https?:\/\/[^\s<>"')\]]+)/g,(url)=>{const trail=url.match(/[.,;:!?)]$/)?url.slice(-1):'';const clean=trail?url.slice(0,-1):url;return `<a href="${clean}" target="_blank" rel="noopener">${esc(clean)}</a>${trail}`;});
    t=t.replace(/\x00L(\d+)\x00/g,(_,i)=>_link_stash[+i]);
    t=t.replace(/\x00G(\d+)\x00/g,(_,i)=>_img_stash[+i]);
    // Escape any plain text that isn't already wrapped in a tag we produced
    // by escaping bare < > that are not part of our own tags
    const SAFE_INLINE=/^<\/?(strong|em|code|a|img)([\s>]|$)/i;
    t=t.replace(/<\/?[a-z][^>]*>/gi,tag=>SAFE_INLINE.test(tag)?tag:esc(tag));
    return t;
  }
  // Stash <code> tags from the backtick pass above so the outer bold/italic
  // regexes don't esc() their content (e.g. **`code`** → <strong><code>code</code></strong>)
  const _ob_stash=[];
  s=s.replace(/(<code>[^<]*<\/code>)/g,m=>{_ob_stash.push(m);return `\x00O${_ob_stash.length-1}\x00`;});
  s=s.replace(/\*\*\*(.+?)\*\*\*/g,(_,t)=>`<strong><em>${esc(t)}</em></strong>`);
  s=s.replace(/\*\*(.+?)\*\*/g,(_,t)=>`<strong>${esc(t)}</strong>`);
  s=s.replace(/\*([^*\n]+)\*/g,(_,t)=>`<em>${esc(t)}</em>`);
  s=s.replace(/\x00O(\d+)\x00/g,(_,i)=>_ob_stash[+i]);
  s=s.replace(/^### (.+)$/gm,(_,t)=>`<h3>${inlineMd(t)}</h3>`).replace(/^## (.+)$/gm,(_,t)=>`<h2>${inlineMd(t)}</h2>`).replace(/^# (.+)$/gm,(_,t)=>`<h1>${inlineMd(t)}</h1>`);
  s=s.replace(/^---+$/gm,'<hr>');
  s=s.replace(/^> (.+)$/gm,(_,t)=>`<blockquote>${inlineMd(t)}</blockquote>`);
  // B8: improved list handling supporting up to 2 levels of indentation
  s=s.replace(/((?:^(?:  )?[-*+] .+\n?)+)/gm,block=>{
    const lines=block.trimEnd().split('\n');
    let html='<ul>';
    for(const l of lines){
      const indent=/^ {2,}/.test(l);
      const text=l.replace(/^ {0,4}[-*+] /,'');
      if(indent) html+=`<li style="margin-left:16px">${inlineMd(text)}</li>`;
      else html+=`<li>${inlineMd(text)}</li>`;
    }
    return html+'</ul>';
  });
  s=s.replace(/((?:^(?:  )?\d+\. .+\n?)+)/gm,block=>{
    const lines=block.trimEnd().split('\n');
    let html='<ol>';
    for(const l of lines){
      const text=l.replace(/^ {0,4}\d+\. /,'');
      html+=`<li>${inlineMd(text)}</li>`;
    }
    return html+'</ol>';
  });
  // Tables: | col | col | header row followed by | --- | --- | separator then data rows
  // NOTE: table pass runs BEFORE outer link pass so [label](url) in table cells
  // is handled by inlineMd() only — prevents double-linking.
  s=s.replace(/((?:^\|.+\|\n?)+)/gm,block=>{
    const rows=block.trim().split('\n').filter(r=>r.trim());
    if(rows.length<2)return block;
    const isSep=r=>/^\|[\s|:-]+\|$/.test(r.trim());
    if(!isSep(rows[1]))return block;
    const parseRow=r=>r.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(c=>`<td>${inlineMd(c.trim())}</td>`).join('');
    const parseHeader=r=>r.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(c=>`<th>${inlineMd(c.trim())}</th>`).join('');
    const header=`<tr>${parseHeader(rows[0])}</tr>`;
    const body=rows.slice(2).map(r=>`<tr>${parseRow(r)}</tr>`).join('');
    return `<table><thead>${header}</thead><tbody>${body}</tbody></table>`;
  });
  // #487: Outer image pass — handles ![alt](url) in plain paragraphs (outside tables/lists).
  // Runs AFTER the table pass (images in table cells are handled by inlineMd() above).
  // Runs BEFORE the outer [label](url) link pass so the image is not consumed as a plain link.
  s=s.replace(/!\[([^\]]*)\]\((https?:\/\/[^\)]+)\)/g,(_,alt,url)=>`<img src="${url.replace(/"/g,'%22')}" alt="${esc(alt)}" class="msg-media-img" loading="lazy" onclick="this.classList.toggle('msg-media-img--full')">`);
  // Outer link pass for labeled links in plain paragraphs (outside table cells).
  // Runs AFTER the table pass so table cells are processed by inlineMd() only.
  // Stash existing <a> tags first to avoid re-linking already-linked URLs.
  const _a_stash=[];
  s=s.replace(/(<a\b[^>]*>[\s\S]*?<\/a>)/g,m=>{_a_stash.push(m);return `\x00A${_a_stash.length-1}\x00`;});
  s=s.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,(_,label,url)=>`<a href="${url.replace(/"/g,'%22')}" target="_blank" rel="noopener">${esc(label)}</a>`);
  s=s.replace(/\x00A(\d+)\x00/g,(_,i)=>_a_stash[+i]);
  // Escape any remaining HTML tags that are NOT from our own markdown output.
  // Our pipeline only emits: <strong>,<em>,<code>,<pre>,<h1-6>,<ul>,<ol>,<li>,
  // <table>,<thead>,<tbody>,<tr>,<th>,<td>,<hr>,<blockquote>,<p>,<br>,<a>,
  // <div class="..."> (mermaid/pre-header). Everything else is untrusted input.
  const SAFE_TAGS=/^<\/?(strong|em|code|pre|h[1-6]|ul|ol|li|table|thead|tbody|tr|th|td|hr|blockquote|p|br|a|img|div|span)([\s>]|$)/i;
  s=s.replace(/<\/?[a-z][^>]*>/gi,tag=>SAFE_TAGS.test(tag)?tag:esc(tag));
  // Hex color buttons: render #rrggbb as a clickable copy pill outside protected tags.
  const _hex_stash=[];
  s=s.replace(/(<code>[\s\S]*?<\/code>|<a\b[^>]*>[\s\S]*?<\/a>|<img\b[^>]*>)/g,m=>{_hex_stash.push(m);return `\x00H${_hex_stash.length-1}\x00`;});
  s=s.replace(/(^|[^A-Za-z0-9_-])#([0-9A-Fa-f]{6})\b/g,(_,pre,hex)=>`${pre}<button type="button" class="msg-hex-button" onclick="copyColorCode('#${hex}')" title="Copy #${hex}"><span class="msg-hex-swatch" style="background:#${hex}"></span><span class="msg-hex-label" style="color:#${hex}">#${hex}</span></button>`);
  s=s.replace(/\x00H(\d+)\x00/g,(_,i)=>_hex_stash[+i]);
  // Autolink: convert plain URLs to clickable links.
  // Stash existing <a> tags first so we never re-link a URL already inside href="...".
  const _al_stash=[];
  s=s.replace(/(<a\b[^>]*>[\s\S]*?<\/a>|<img\b[^>]*>)/g,m=>{_al_stash.push(m);return `\x00B${_al_stash.length-1}\x00`;});
  s=s.replace(/(https?:\/\/[^\s<>"'\)\]]+)/g,(url)=>{
    // Strip trailing punctuation that was likely not part of the URL
    const trail=url.match(/[.,;:!?)]$/)?url.slice(-1):'';
    const clean=trail?url.slice(0,-1):url;
    return `<a href="${clean}" target="_blank" rel="noopener">${esc(clean)}</a>${trail}`;
  });
  s=s.replace(/\x00B(\d+)\x00/g,(_,i)=>_al_stash[+i]);
  // Restore math stash → katex placeholder spans/divs
  // These will be rendered by renderKatexBlocks() after DOM insertion
  s=s.replace(/\x00M(\d+)\x00/g,(_,i)=>{
    const item=math_stash[+i];
    if(item.type==='display'){
      return `<div class="katex-block" data-katex="display">${esc(item.src)}</div>`;
    }
    return `<span class="katex-inline" data-katex="inline">${esc(item.src)}</span>`;
  });
  const parts=s.split(/\n{2,}/);
  s=parts.map(p=>{p=p.trim();if(!p)return '';if(/^<(h[1-6]|ul|ol|pre|hr|blockquote)/.test(p))return p;return `<p>${p.replace(/\n/g,'<br>')}</p>`;}).join('\n');
  // ── Restore MEDIA stash → inline images or download links ─────────────────
  s=s.replace(/\x00D(\d+)\x00/g,(_,i)=>{
    const ref=media_stash[+i];
    // HTTP(S) URL
    if(/^https?:\/\//i.test(ref)){
      if(_IMAGE_EXTS.test(ref.split('?')[0])){
        return `<img class="msg-media-img" src="${esc(ref)}" alt="image" loading="lazy" onclick="this.classList.toggle('msg-media-img--full')">`;
      }
      return `<a href="${esc(ref)}" target="_blank" rel="noopener">${esc(ref)}</a>`;
    }
    // Local file path
    const apiUrl='api/media?path='+encodeURIComponent(ref);
    if(_IMAGE_EXTS.test(ref)){
      return `<img class="msg-media-img" src="${esc(apiUrl)}" alt="${esc(ref.split('/').pop())}" loading="lazy" onclick="this.classList.toggle('msg-media-img--full')">`;
    }
    // Non-image local file — show download link with filename
    const fname=esc(ref.split('/').pop()||ref);
    return `<a class="msg-media-link" href="${esc(apiUrl+'&download=1')}" download="${fname}">📎 ${fname}</a>`;
  });
  // ── End MEDIA restore ──────────────────────────────────────────────────────
  return s;
}

function renderTextWithHexButtons(raw){
  const escaped=esc(String(raw||'')).replace(/\n/g,'<br>');
  return escaped.replace(/(^|[^A-Za-z0-9_-])#([0-9A-Fa-f]{6})\b/g,(_,pre,hex)=>`${pre}<button type="button" class="msg-hex-button" onclick="copyColorCode('#${hex}')" title="Copy #${hex}"><span class="msg-hex-swatch" style="background:#${hex}"></span><span class="msg-hex-label" style="color:#${hex}">#${hex}</span></button>`);
}

function copyColorCode(hex){
  if(typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(hex).then(()=>showToast(`${hex} copied`),()=>showToast('Copy failed'));
    return;
  }
  const ta=document.createElement('textarea');
  ta.value=hex;
  ta.setAttribute('readonly','');
  ta.style.position='absolute';
  ta.style.left='-9999px';
  document.body.appendChild(ta);
  ta.select();
  try{document.execCommand('copy');showToast(`${hex} copied`);}catch(e){showToast('Copy failed');}
  document.body.removeChild(ta);
}

function setStatus(t){
  if(!t)return;
  showToast(t, 4000);
}

function setComposerStatus(t){
  const el=$('composerStatus');
  if(!el)return;
  if(!t){
    el.style.display='none';
    el.textContent='';
    return;
  }
  el.textContent=t;
  el.style.display='';
}

let _composerElapsedTimer=null;
let _composerElapsedStart=0;
let _composerElapsedStoppedAt=0;

function _formatElapsedLabel(seconds){
  if(seconds<60) return `${seconds} sec.`;
  const minutes=Math.floor(seconds/60);
  if(minutes<60) return `${minutes} min.`;
  const hours=Math.floor(minutes/60);
  if(hours<24) return `${hours} hr.`;
  const days=Math.floor(hours/24);
  if(days<7) return `${days} ${days===1?'day':'days'}`;
  const weeks=Math.floor(days/7);
  if(weeks<4) return `${weeks} ${weeks===1?'week':'weeks'}`;
  const months=Math.max(1,Math.floor(days/30));
  if(months<12) return `${months} ${months===1?'month':'months'}`;
  const years=Math.floor(months/12) || 1;
  return `${years} ${years===1?'year':'years'}`;
}

function _composerElapsedElement(){
  return $('composerElapsed');
}

function _renderComposerElapsed(){
  const el=_composerElapsedElement();
  if(!el) return;
  if(!_composerElapsedStart){
    el.style.display='none';
    return;
  }
  const now=_composerElapsedTimer?Date.now():(_composerElapsedStoppedAt||Date.now());
  const elapsedSecs=Math.floor(Math.max(0, now-_composerElapsedStart)/1000);
  el.textContent=_formatElapsedLabel(elapsedSecs);
  el.style.display='';
  if(!_composerElapsedTimer && elapsedSecs>0 && elapsedSecs<60){
    el.classList.add('highlight');
  } else {
    el.classList.remove('highlight');
  }
}

function _startComposerElapsedTimer(){
  if(_composerElapsedTimer) clearInterval(_composerElapsedTimer);
  _composerElapsedStart=Date.now();
  _composerElapsedStoppedAt=0;
  _renderComposerElapsed();
  _composerElapsedTimer=setInterval(_renderComposerElapsed,1000);
}

function _stopComposerElapsedTimer(){
  if(_composerElapsedTimer){
    clearInterval(_composerElapsedTimer);
    _composerElapsedTimer=null;
  }
  if(!_composerElapsedStart) return;
  _composerElapsedStoppedAt=Date.now();
  _renderComposerElapsed();
}

function _resetComposerElapsedTimer(){
  if(_composerElapsedTimer){
    clearInterval(_composerElapsedTimer);
    _composerElapsedTimer=null;
  }
  _composerElapsedStart=0;
  _composerElapsedStoppedAt=0;
  const el=_composerElapsedElement();
  if(el){
    el.textContent='';
    el.style.display='none';
    el.classList.remove('highlight');
  }
}

let _composerLockState=null;

function lockComposerForClarify(placeholderText){
  const input=$('msg');
  if(!input) return;
  if(!_composerLockState){
    _composerLockState={
      disabled: input.disabled,
      placeholder: input.placeholder,
    };
  }
  input.disabled=true;
  if(placeholderText) input.placeholder=placeholderText;
  updateSendBtn();
}

function unlockComposerForClarify(){
  const input=$('msg');
  if(!input) return;
  if(_composerLockState){
    input.disabled=!!_composerLockState.disabled;
    if(typeof _composerLockState.placeholder==='string'){
      input.placeholder=_composerLockState.placeholder;
    }
    _composerLockState=null;
  }else{
    input.disabled=false;
  }
  updateSendBtn();
}

function updateSendBtn(){
  const btn=$('btnSend');
  if(!btn) return;
  const msg=$('msg');
  const hasContent=msg&&msg.value.trim().length>0||S.pendingFiles.length>0;
  const canSend=hasContent&&!S.busy&&!(msg&&msg.disabled);
  // Hide while busy (cancel button takes its place); show otherwise
  btn.style.display=S.busy?'none':'';
  btn.disabled=!canSend;
  if(canSend&&!btn.classList.contains('visible')){
    btn.classList.remove('visible');
    requestAnimationFrame(()=>btn.classList.add('visible'));
  }
}
function setBusy(v){
  S.busy=v;
  updateSendBtn();
  // Hide composer spinner - use thinking dots instead
  const spinner=$('composerSpinner');
  if(spinner) spinner.style.display='none';
  if(!v){
    _stopComposerElapsedTimer();
    setStatus('');
    setComposerStatus('');
    // Always hide Cancel button when not busy
    const _cb=$('btnCancel');if(_cb)_cb.style.display='none';
    const sid=S.session&&S.session.session_id;
    updateQueueBadge(sid);
    // Drain one queued message for the currently viewed session after UI settles
    const next=sid?shiftQueuedSessionMessage(sid):null;
    if(next){
      updateQueueBadge(sid);
      setTimeout(()=>{
        $('msg').value=next.text||'';
        S.pendingFiles=Array.isArray(next.files)?[...next.files]:[];
        autoResize();
        renderTray();
        send();
      },120);
    }
  }
}

function updateQueueBadge(sessionId){
  const sid=sessionId||(S.session&&S.session.session_id);
  const count=sid?getQueuedSessionCount(sid):0;
  let badge=$('queueBadge');
  if(count>0){
    if(!badge){
      badge=document.createElement('div');
      badge.id='queueBadge';
      badge.style.cssText='position:fixed;bottom:80px;right:24px;display:flex;align-items:center;gap:8px;background:rgba(124,185,255,.18);border:1px solid rgba(124,185,255,.4);color:var(--blue);font-size:12px;font-weight:600;padding:6px 14px;border-radius:20px;z-index:50;pointer-events:auto;backdrop-filter:blur(8px);';
      const content=document.createElement('span');
      content.className='queueBadge-text';
      badge.appendChild(content);
      const close=document.createElement('button');
      close.type='button';
      close.className='queueBadge-close';
      close.textContent='×';
      close.title='Cancel queued chat';
      close.style.cssText='all:unset;cursor:pointer;color:var(--blue);font-size:14px;width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;border-radius:999px;';
      close.addEventListener('click', e=>{
        e.stopPropagation();
        clearQueuedSessionMessages(sid);
        updateQueueBadge(sid);
      });
      badge.appendChild(close);
      document.body.appendChild(badge);
    }
    const content=badge.querySelector('.queueBadge-text');
    if(content) content.textContent=count===1?'1 message queued':`${count} messages queued`;
    clearTimeout(_queueBadgeHideTimer);
    _queueBadgeHideTimer=setTimeout(()=>{
      const b=$('queueBadge');
      if(b) b.remove();
      _queueBadgeHideTimer=null;
    },2000);
  } else if(badge) {
    badge.remove();
    clearTimeout(_queueBadgeHideTimer);
    _queueBadgeHideTimer=null;
  }
}
function showToast(msg,ms){const el=$('toast');if(!el)return; if(/cron|session|sync|deleted|archived|restored|failed|duplicate|import|export|update|saved|moved|created|renamed|cleared|removed|deleted|copied|failed\//i.test(msg)) return; el.textContent=msg; el.classList.add('show'); clearTimeout(el._t); el._t=setTimeout(()=>el.classList.remove('show'),ms||2800);}

// ── Shared app dialogs ───────────────────────────────────────────────────────
// showConfirmDialog(opts) and showPromptDialog(opts) replace browser-native dialog calls
// throughout the UI. Both return Promises and support: title, message, confirmLabel,
// cancelLabel, danger (confirm only), placeholder/value/inputType (prompt only).

const APP_DIALOG={resolve:null,kind:null,lastFocus:null};
let _appDialogBound=false;

function _isAppDialogOpen(){
  const overlay=$('appDialogOverlay');
  return !!(overlay&&overlay.style.display!=='none');
}

function _getAppDialogFocusable(){
  return [$('appDialogInput'), $('appDialogCancel'), $('appDialogConfirm'), $('appDialogClose')]
    .filter(el=>el&&el.style.display!=='none'&&!el.disabled);
}

function _finishAppDialog(result, restoreFocus=true){
  const overlay=$('appDialogOverlay');
  const dialog=$('appDialog');
  const input=$('appDialogInput');
  const confirmBtn=$('appDialogConfirm');
  const resolve=APP_DIALOG.resolve;
  const lastFocus=APP_DIALOG.lastFocus;
  APP_DIALOG.resolve=null;
  APP_DIALOG.kind=null;
  APP_DIALOG.lastFocus=null;
  if(overlay){overlay.style.display='none';overlay.setAttribute('aria-hidden','true');}
  if(dialog) dialog.setAttribute('role','dialog');
  if(input){input.value='';input.style.display='none';input.placeholder='';}
  if(confirmBtn){confirmBtn.classList.remove('danger');confirmBtn.textContent=t('dialog_confirm_btn');}
  if(restoreFocus&&lastFocus&&typeof lastFocus.focus==='function'){setTimeout(()=>lastFocus.focus(),0);}
  if(resolve) resolve(result);
}

function _ensureAppDialogBindings(){
  if(_appDialogBound) return;
  _appDialogBound=true;
  const overlay=$('appDialogOverlay');
  const cancelBtn=$('appDialogCancel');
  const confirmBtn=$('appDialogConfirm');
  const closeBtn=$('appDialogClose');
  if(overlay){
    overlay.addEventListener('click',e=>{
      if(e.target===overlay) _finishAppDialog(APP_DIALOG.kind==='prompt'?null:false);
    });
  }
  if(cancelBtn) cancelBtn.addEventListener('click',()=>_finishAppDialog(APP_DIALOG.kind==='prompt'?null:false));
  if(closeBtn)  closeBtn.addEventListener('click',()=>_finishAppDialog(APP_DIALOG.kind==='prompt'?null:false));
  if(confirmBtn){
    confirmBtn.addEventListener('click',()=>{
      if(APP_DIALOG.kind==='prompt'){
        const input=$('appDialogInput');
        _finishAppDialog(input?input.value:null);
      }else{
        _finishAppDialog(true);
      }
    });
  }
  document.addEventListener('keydown',e=>{
    if(!_isAppDialogOpen()) return;
    if(e.key==='Escape'){
      e.preventDefault();
      _finishAppDialog(APP_DIALOG.kind==='prompt'?null:false);
      return;
    }
    if(e.key==='Enter'){
      if(e.isComposing) return;
      const target=e.target;
      const isTextarea=target&&target.tagName==='TEXTAREA';
      if(!isTextarea){
        e.preventDefault();
        if(target===cancelBtn||target===closeBtn){
          _finishAppDialog(APP_DIALOG.kind==='prompt'?null:false);
        }else if(APP_DIALOG.kind==='prompt'){
          const input=$('appDialogInput');
          _finishAppDialog(input?input.value:null);
        }else{
          _finishAppDialog(true);
        }
      }
      return;
    }
    if(e.key==='Tab'){
      const nodes=_getAppDialogFocusable();
      if(!nodes.length) return;
      const idx=nodes.indexOf(document.activeElement);
      let nextIdx=idx;
      if(e.shiftKey){nextIdx=idx<=0?nodes.length-1:idx-1;}
      else{nextIdx=idx===-1||idx===nodes.length-1?0:idx+1;}
      e.preventDefault();
      nodes[nextIdx].focus();
    }
  }, true);
}

function showConfirmDialog(opts={}){
  _ensureAppDialogBindings();
  if(APP_DIALOG.resolve) _finishAppDialog(false,false);
  const overlay=$('appDialogOverlay'),dialog=$('appDialog'),title=$('appDialogTitle'),
    desc=$('appDialogDesc'),input=$('appDialogInput'),cancelBtn=$('appDialogCancel'),confirmBtn=$('appDialogConfirm');
  APP_DIALOG.resolve=null;APP_DIALOG.kind='confirm';APP_DIALOG.lastFocus=document.activeElement;
  if(title) title.textContent=opts.title||t('dialog_confirm_title');
  if(desc) desc.textContent=opts.message||'';
  if(input){input.style.display='none';input.value='';}
  if(cancelBtn) cancelBtn.textContent=opts.cancelLabel||t('cancel');
  if(confirmBtn){
    confirmBtn.textContent=opts.confirmLabel||t('dialog_confirm_btn');
    confirmBtn.classList.toggle('danger',!!opts.danger);
  }
  if(dialog) dialog.setAttribute('role',opts.danger?'alertdialog':'dialog');
  if(overlay){overlay.style.display='flex';overlay.setAttribute('aria-hidden','false');}
  return new Promise(resolve=>{
    APP_DIALOG.resolve=resolve;
    setTimeout(()=>((opts.focusCancel?cancelBtn:confirmBtn)||confirmBtn||cancelBtn).focus(),0);
  });
}

function showPromptDialog(opts={}){
  _ensureAppDialogBindings();
  if(APP_DIALOG.resolve) _finishAppDialog(null,false);
  const overlay=$('appDialogOverlay'),dialog=$('appDialog'),title=$('appDialogTitle'),
    desc=$('appDialogDesc'),input=$('appDialogInput'),cancelBtn=$('appDialogCancel'),confirmBtn=$('appDialogConfirm');
  APP_DIALOG.resolve=null;APP_DIALOG.kind='prompt';APP_DIALOG.lastFocus=document.activeElement;
  if(title) title.textContent=opts.title||t('dialog_prompt_title');
  if(desc) desc.textContent=opts.message||'';
  if(input){
    input.type=opts.inputType||'text';input.style.display='';
    input.value=opts.value||'';input.placeholder=opts.placeholder||'';
    input.autocomplete='off';input.spellcheck=false;
  }
  if(cancelBtn) cancelBtn.textContent=opts.cancelLabel||t('cancel');
  if(confirmBtn){confirmBtn.textContent=opts.confirmLabel||t('create');confirmBtn.classList.remove('danger');}
  if(dialog) dialog.setAttribute('role','dialog');
  if(overlay){overlay.style.display='flex';overlay.setAttribute('aria-hidden','false');}
  return new Promise(resolve=>{
    APP_DIALOG.resolve=resolve;
    setTimeout(()=>{if(input&&input.style.display!=='none')input.focus();else if(confirmBtn)confirmBtn.focus();},0);
  });
}


function copyMsg(btn){
  const row=btn.closest('.msg-row');
  const text=row?row.dataset.rawText:'';
  if(!text)return;
  navigator.clipboard.writeText(text).then(()=>{
    const orig=btn.innerHTML;btn.innerHTML=li('check',13);btn.style.color='var(--blue)';
    setTimeout(()=>{btn.innerHTML=orig;btn.style.color='';},1500);
  }).catch(()=>showToast('Copy failed'));
}

// ── Reconnect banner (B4/B5: reload resilience) ──
const INFLIGHT_KEY = 'hermes-webui-inflight'; // localStorage key for in-flight session tracking
const INFLIGHT_STATE_KEY = 'hermes-webui-inflight-state'; // localStorage snapshots for mid-stream reload recovery

function _readInflightStateMap(){
  try{
    const raw=localStorage.getItem(INFLIGHT_STATE_KEY);
    const parsed=raw?JSON.parse(raw):{};
    return parsed&&typeof parsed==='object'?parsed:{};
  }catch(_){
    return {};
  }
}
function saveInflightState(sid, state){
  if(!sid||!state) return;
  try{
    const all=_readInflightStateMap();
    all[sid]={...state,updated_at:Date.now()};
    localStorage.setItem(INFLIGHT_STATE_KEY, JSON.stringify(all));
  }catch(_){ }
}
function loadInflightState(sid, streamId){
  if(!sid) return null;
  const all=_readInflightStateMap();
  const entry=all[sid];
  if(!entry) return null;
  // If server reports an active stream, require exact streamId match to prevent
  // connecting to a stale stream. If no active stream (streamId is null), reject
  // any stored state that has a streamId (it was from an old completed stream).
  if(streamId){
    // Active stream on server - only use stored state if stream IDs match
    if(entry.streamId!==streamId) return null;
  }else{
    // No active stream on server - reject stored state that has a streamId
    // (stale data from a completed stream that wasn't cleaned up)
    if(entry.streamId) return null;
  }
  if(entry.updated_at&&Date.now()-entry.updated_at>10*60*1000){
    clearInflightState(sid);
    return null;
  }
  return entry;
}
function clearInflightState(sid){
  if(!sid) return;
  try{
    const all=_readInflightStateMap();
    if(!(sid in all)) return;
    delete all[sid];
    if(Object.keys(all).length) localStorage.setItem(INFLIGHT_STATE_KEY, JSON.stringify(all));
    else localStorage.removeItem(INFLIGHT_STATE_KEY);
  }catch(_){ }
}

function markInflight(sid, streamId) {
  localStorage.setItem(INFLIGHT_KEY, JSON.stringify({sid, streamId, ts: Date.now()}));
}
function clearInflight() {
  localStorage.removeItem(INFLIGHT_KEY);
}
function showReconnectBanner(msg) {
  $('reconnectMsg').textContent = msg || 'A response may have been in progress when you last left.';
  $('reconnectBanner').classList.add('visible');
}
function dismissReconnect() {
  $('reconnectBanner').classList.remove('visible');
  clearInflight();
}
async function refreshSession() {
  dismissReconnect();
  if (!S.session) return;
  try {
    const data = await api(`/api/session?session_id=${encodeURIComponent(S.session.session_id)}`);
    S.session = data.session;
    S.messages = data.session.messages || [];
    const pendingMsg=getPendingSessionMessage(data.session);
    if(pendingMsg) S.messages.push(pendingMsg);
    S.activeStreamId=data.session.active_stream_id||null;

    syncTopbar(); renderMessages();
  } catch(e) { setStatus('Refresh failed: ' + e.message); }
}
// ── Update banner ──
function _showUpdateBanner(data){
  const parts=[];
  if(data.webui&&data.webui.behind>0) parts.push(`WebUI: ${data.webui.behind} update${data.webui.behind>1?'s':''}`);
  if(data.agent&&data.agent.behind>0) parts.push(`Agent: ${data.agent.behind} update${data.agent.behind>1?'s':''}`);
  if(!parts.length)return;
  const msg=$('updateMsg');
  if(msg) msg.textContent='\u2B06 '+parts.join(', ')+' available';
  const banner=$('updateBanner');
  if(banner) banner.classList.add('visible');
  window._updateData=data;
}
function dismissUpdate(){
  const b=$('updateBanner');if(b)b.classList.remove('visible');
  sessionStorage.setItem('hermes-update-dismissed','1');
}
async function applyUpdates(){
  const btn=$('btnApplyUpdate');
  if(btn){btn.disabled=true;btn.textContent='Updating\u2026';}
  const targets=[];
  if(window._updateData?.webui?.behind>0) targets.push('webui');
  if(window._updateData?.agent?.behind>0) targets.push('agent');
  try{
    for(const target of targets){
      const res=await api('/api/updates/apply',{method:'POST',body:JSON.stringify({target})});
      if(!res.ok){
        showToast('Update failed ('+target+'): '+(res.message||'unknown error'));
        if(btn){btn.disabled=false;btn.textContent='Update Now';}
        return;
      }
    }
    showToast('Updated! Reloading\u2026');
    sessionStorage.removeItem('hermes-update-checked');
    sessionStorage.removeItem('hermes-update-dismissed');
    setTimeout(()=>location.reload(),1500);
  }catch(e){
    showToast('Update failed: '+e.message);
    if(btn){btn.disabled=false;btn.textContent='Update Now';}
  }
}

function getPendingSessionMessage(session){
  const text=String(session?.pending_user_message||'').trim();
  if(!text) return null;
  const attachments=Array.isArray(session?.pending_attachments)?session.pending_attachments.filter(Boolean):[];
  const messages=Array.isArray(session?.messages)?session.messages:[];
  const lastUser=[...messages].reverse().find(m=>m&&m.role==='user');
  if(lastUser){
    const lastText=String(msgContent(lastUser)||'').trim();
    if(lastText===text){
      if(attachments.length&&!lastUser.attachments?.length) lastUser.attachments=attachments;
      return null;
    }
  }
  return {
    role:'user',
    content:text,
    attachments:attachments.length?attachments:undefined,
    _ts:session?.pending_started_at||Date.now()/1000,
    _pending:true,
  };
}
async function checkInflightOnBoot(sid) {
  const raw = localStorage.getItem(INFLIGHT_KEY);
  if (!raw) return;
  try {
    const {sid: inflightSid, streamId, ts} = JSON.parse(raw);
    if (inflightSid !== sid) { clearInflight(); return; }
    if (S.activeStreamId && S.activeStreamId === streamId) return;
    // Only show banner if the in-flight entry is less than 10 minutes old
    if (Date.now() - ts > 10 * 60 * 1000) { clearInflight(); return; }
    // Check if stream is still active
    const status = await api(`/api/chat/stream/status?stream_id=${encodeURIComponent(streamId || '')}`);
    if (status.active) {
      if (S.session && S.session.session_id === inflightSid && S.session.active_stream_id === streamId && S.activeStreamId !== streamId) {
        S.activeStreamId = streamId;
        S.busy = true;
        setBusy(true);
        const cancelBtn = $('btnCancel');
        if (cancelBtn) cancelBtn.style.display = 'inline-flex';
        if (typeof attachLiveStream === 'function') {
          attachLiveStream(inflightSid, streamId, S.session.pending_attachments || [], {reconnecting:true});
          return;
        }
      }
      // Stream is genuinely still running -- show the banner
      showReconnectBanner(t('reconnect_active'));
    } else {
      // Stream finished. Only show banner if reload happened within 90 seconds
      // (longer gap = normal completed session, not a mid-stream reload)
      if (Date.now() - ts < 90 * 1000) {
        showReconnectBanner(t('reconnect_finished'));
      } else {
        clearInflight();  // completed normally, no banner needed
      }
    }
  } catch(e) { clearInflight(); }
}

// ── Topbar title edit + right-click context menu ─────────────────────────────
function editTopbarTitle(event){
  if(event) event.preventDefault();
  if(!S.session) return;
  const titleEl=$('topbarTitle');
  if(!titleEl) return;
  const currentTitle=S.session.title||'untitled';
  showPromptDialog({
    title:'Rename conversation',
    message:'Enter a new title for this conversation:',
    confirmLabel:'Save',
    cancelLabel:'Cancel',
    value:currentTitle,
    placeholder:'Conversation title'
  }).then(async (newTitle)=>{
    if(!newTitle||!newTitle.trim()) return;
    newTitle=newTitle.trim();
    // Optimistic update: update UI immediately
    const oldTitle = S.session.title;
    S.session.title = newTitle;
    syncTopbar();
    const cached = (typeof _allSessions !== 'undefined') ? _allSessions.find(s => s.session_id === S.session.session_id) : null;
    if (cached) cached.title = newTitle;
    if(typeof renderSessionListFromCache==='function')renderSessionListFromCache();
    try{
      await api('/api/session/rename',{method:'POST',body:JSON.stringify({
        session_id:S.session.session_id, title:newTitle
      })});
    }catch(e){
      // Revert on failure
      S.session.title = oldTitle;
      if (cached) cached.title = oldTitle;
      syncTopbar();
      if (typeof renderSessionListFromCache === 'function') renderSessionListFromCache();
      showToast('Rename failed: '+e.message);
    }
  });
}

let _topbarContextMenu = null;

function handleTopbarRightClick(event){
  if(event){
    event.preventDefault();
    event.stopPropagation();
  }

  // Remove any existing context menu
  hideTopbarContextMenu();

  // Only show "+ add" if there's a current session with a workspace, or we have a default workspace
  const currentWorkspace = S.session?.workspace;
  const hasWorkspace = !!currentWorkspace;

  // Create context menu
  const menu = document.createElement('div');
  menu.className = 'topbar-context-menu';
  menu.style.cssText = 'position:fixed;background:#0a0a0a;border:1px solid rgba(255,255,255,0.1);border-radius:8px;box-shadow:0 4px 24px rgba(0,0,0,.6);z-index:10000;min-width:160px;overflow:hidden;';
  
  // Estimate menu height (~75px for 1-2 items)
  const menuHeight = 75;
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

  // Add new conversation button
  const addBtn = document.createElement('button');
  addBtn.style.cssText = 'display:flex;align-items:center;gap:8px;width:100%;padding:10px 14px;border:none;background:transparent;color:var(--text);font-size:13px;cursor:pointer;text-align:left;transition:background 0.15s;';
  addBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> new chat';
  addBtn.onmouseenter = () => addBtn.style.background = 'rgba(255,255,255,0.05)';
  addBtn.onmouseleave = () => addBtn.style.background = 'transparent';
  addBtn.onclick = async () => {
    hideTopbarContextMenu();
    // If there's a current workspace, newSession will inherit it
    await newSession(true);
    await renderSessionList();
    if($('msg')) $('msg').focus();
  };

  menu.appendChild(addBtn);

  // If there's a workspace, show it as disabled info
  if(hasWorkspace && currentWorkspace !== 'default'){
    const wsInfo = document.createElement('div');
    wsInfo.style.cssText = 'padding:8px 14px;border-top:1px solid rgba(255,255,255,0.05);font-size:11px;color:var(--muted);text-overflow:ellipsis;overflow:hidden;white-space:nowrap;';
    wsInfo.textContent = 'workspace: ' + currentWorkspace.split('/').pop();
    menu.appendChild(wsInfo);
  }

  document.body.appendChild(menu);
  _topbarContextMenu = menu;

  // Close on click outside or right-click elsewhere
  setTimeout(() => {
    document.addEventListener('click', hideTopbarContextMenu, { once: true });
    document.addEventListener('contextmenu', hideTopbarContextMenu, { once: true });
  }, 10);
}

function hideTopbarContextMenu(){
  if(_topbarContextMenu){
    _topbarContextMenu.remove();
    _topbarContextMenu = null;
  }
}

let _titleEditing = false;

function startInlineTitleEdit(){
  if(!S.session || _titleEditing) return;
  _titleEditing = true;
  const titleEl = $('topbarTitle');
  if(!titleEl) return;
  
  const currentTitle = S.session.title || 'untitled';
  const inp = document.createElement('input');
  inp.type = 'text';
  inp.value = currentTitle;
  inp.style.cssText = 'background:transparent;border:1px solid var(--accent);border-radius:6px;padding:3px 8px;font-size:inherit;color:inherit;outline:none;width:auto;min-width:120px;max-width:300px;';
  
  const finish = async (save) => {
    _titleEditing = false;
    const newTitle = inp.value.trim();
    inp.replaceWith(titleEl);
    
    if(save && newTitle && newTitle !== currentTitle){
      const oldTitle = S.session.title;
      S.session.title = newTitle;
      titleEl.textContent = newTitle;
      
      const cached = (typeof _allSessions !== 'undefined') ? _allSessions.find(s => s.session_id === S.session.session_id) : null;
      if(cached) cached.title = newTitle;
      
      renderSessionTabs();
      if(typeof renderSessionListFromCache === 'function') renderSessionListFromCache();
      
      try{
        await api('/api/session/rename',{method:'POST',body:JSON.stringify({
          session_id:S.session.session_id, title:newTitle
        })});
      }catch(e){
        S.session.title = oldTitle;
        titleEl.textContent = oldTitle;
        if(cached) cached.title = oldTitle;
        syncTopbar();
        renderSessionTabs();
        showToast('Rename failed: '+e.message);
      }
    } else {
      titleEl.textContent = currentTitle;
    }
  };
  
  inp.onkeydown = (e) => {
    if(e.key === 'Enter'){ e.preventDefault(); finish(true); }
    if(e.key === 'Escape'){ e.preventDefault(); finish(false); }
  };
  inp.onblur = () => finish(false);
  
  titleEl.replaceWith(inp);
  inp.focus();
  inp.select();
}

// Session tabs: show open sessions as rounded cards
let _openSessions = []; // Recently opened sessions
const OPEN_SESSIONS_STORAGE_KEY = 'hermes-webui-open-sessions';

function saveOpenSessions(){
  try { localStorage.setItem(OPEN_SESSIONS_STORAGE_KEY, JSON.stringify(_openSessions)); } catch (e) {}
}

function restoreOpenSessions(){
  let raw = null;
  try { raw = localStorage.getItem(OPEN_SESSIONS_STORAGE_KEY); } catch (e) {}
  if(!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if(Array.isArray(parsed)){
      _openSessions = parsed.filter(s => s && s.session_id).slice(0, 10);
      renderSessionTabs();
      return _openSessions;
    }
  } catch (e) {}
  return [];
}

function addToOpenSessions(session){
  if(!session) return;
  // Check if already exists - if so, don't rearrange (preserve user's tab order)
  const existingIndex = _openSessions.findIndex(s => s.session_id === session.session_id);
  if(existingIndex !== -1){
    // Update title if changed, but keep position
    _openSessions[existingIndex].title = session.title || 'untitled';
    _openSessions[existingIndex].workspace = session.workspace;
  } else {
    // Add to front only for new sessions
    _openSessions.unshift({
      session_id: session.session_id,
      title: session.title || 'untitled',
      workspace: session.workspace
    });
  }
  // Keep only last 10
  if(_openSessions.length > 10) _openSessions.pop();
  renderSessionTabs();
  saveOpenSessions();
}

function removeFromOpenSessions(sessionId){
  _openSessions = _openSessions.filter(s => s.session_id !== sessionId);
  renderSessionTabs();
  saveOpenSessions();
}

function renderSessionTabs(){
  const container = $('sessionTabs');
  if(!container) return;
  container.innerHTML = '';
  
  if(_openSessions.length === 0) return;
  
  _openSessions.forEach(s => {
    const isActive = S.session && S.session.session_id === s.session_id;
    const card = document.createElement('div');
    card.className = 'session-tab-card';
    card.dataset.sessionId = s.session_id;
    card.style.cssText = `
      display:flex;align-items:center;gap:6px;padding:4px 10px;
      background:${isActive ? 'var(--accent, #f0c000)' : 'rgba(255,255,255,0.06)'};
      color:${isActive ? 'var(--bg, #0a0a0a)' : 'var(--text, #eee)'};
      border-radius:20px;font-size:12px;cursor:pointer;white-space:nowrap;
      transition:all 0.15s;border:1px solid ${isActive ? 'var(--accent)' : 'transparent'};
    `;
    
    // Title text
    const title = document.createElement('span');
    title.textContent = (s.title || 'untitled').substring(0, 25) + ((s.title||'').length > 25 ? '...' : '');
    title.style.cssText = 'overflow:hidden;text-overflow:ellipsis;max-width:120px;';
    
    // Close button (small X)
    const closeBtn = document.createElement('span');
    closeBtn.innerHTML = '&times;';
    closeBtn.style.cssText = `
      display:${isActive ? 'none' : 'flex'};align-items:center;justify-content:center;
      width:14px;height:14px;border-radius:50%;font-size:11px;font-weight:bold;
      background:rgba(255,255,255,0.15);color:var(--text);cursor:pointer;
    `;
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      removeFromOpenSessions(s.session_id);
      // If closing active session, switch to next available or create new
      if(isActive && _openSessions.length > 0){
        loadSession(_openSessions[0].session_id);
      } else if(isActive){
        newSession(true);
      }
    };
    
    card.appendChild(title);
    if(!isActive) card.appendChild(closeBtn);
    
    // Click to switch
    card.onclick = async () => {
      await loadSession(s.session_id);
      if (typeof renderSessionListFromCache === 'function') renderSessionListFromCache();
    };
    
    // Right-click for context menu (rename or close)
    card.oncontextmenu = (e) => {
      e.preventDefault();
      e.stopPropagation();
      showSessionTabContextMenu(e, s, card);
    };
    
    // Drag and drop support
    card.draggable = true;
    card.ondragstart = (e) => {
      e.dataTransfer.setData('text/plain', s.session_id);
      e.dataTransfer.effectAllowed = 'move';
      card.style.opacity = '0.5';
      card.dataset.dragging = 'true';
    };
    card.ondragend = (e) => {
      card.style.opacity = '1';
      card.dataset.dragging = 'false';
      // Remove all drag-over styles
      document.querySelectorAll('.session-tab-card').forEach(c => {
        c.style.borderLeft = '';
        c.style.borderRight = '';
      });
    };
    card.ondragover = (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      const draggingCard = document.querySelector('.session-tab-card[data-dragging="true"]');
      if(draggingCard && draggingCard !== card){
        const rect = card.getBoundingClientRect();
        const midX = rect.left + rect.width / 2;
        if(e.clientX < midX){
          card.style.borderLeft = '2px solid var(--accent)';
          card.style.borderRight = '';
        } else {
          card.style.borderRight = '2px solid var(--accent)';
          card.style.borderLeft = '';
        }
      }
    };
    card.ondragleave = () => {
      card.style.borderLeft = '';
      card.style.borderRight = '';
    };
    card.ondrop = (e) => {
      e.preventDefault();
      const draggedSessionId = e.dataTransfer.getData('text/plain');
      const targetSessionId = s.session_id;
      
      if(draggedSessionId && targetSessionId && draggedSessionId !== targetSessionId){
        const draggedIndex = _openSessions.findIndex(s => s.session_id === draggedSessionId);
        const targetIndex = _openSessions.findIndex(s => s.session_id === targetSessionId);
        
        if(draggedIndex !== -1 && targetIndex !== -1){
          const [draggedSession] = _openSessions.splice(draggedIndex, 1);
          const rect = card.getBoundingClientRect();
          const midX = rect.left + rect.width / 2;
          const insertIndex = e.clientX < midX ? targetIndex : targetIndex + 1;
          _openSessions.splice(insertIndex > draggedIndex ? insertIndex - 1 : insertIndex, 0, draggedSession);
          renderSessionTabs();
          saveOpenSessions();
        }
      }
      
      card.style.borderLeft = '';
      card.style.borderRight = '';
    };
    
    // Hover effects
    card.onmouseenter = () => {
      if(!isActive) card.style.background = 'rgba(255,255,255,0.12)';
    };
    card.onmouseleave = () => {
      if(!isActive) card.style.background = 'rgba(255,255,255,0.06)';
    };
    
    container.appendChild(card);
  });
}

let _sessionTabMenu = null;

function showSessionTabContextMenu(event, session, cardEl){
  hideSessionTabMenu();
  
  const menu = document.createElement('div');
  menu.className = 'session-tab-context-menu';
  menu.style.cssText = `
    position:fixed;background:#0a0a0a;border:1px solid rgba(255,255,255,0.1);
    border-radius:8px;box-shadow:0 4px 24px rgba(0,0,0,.6);z-index:10001;
    min-width:140px;overflow:hidden;
  `;
  
  // Adjust position to stay within viewport
  let x = event.clientX;
  let y = event.clientY;
  if(y + 80 > window.innerHeight) y = Math.max(10, y - 80);
  if(x + 140 > window.innerWidth) x = Math.max(10, x - 140);
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';
  
  // Rename option
  const renameBtn = document.createElement('button');
  renameBtn.style.cssText = 'width:100%;padding:10px 14px;border:none;background:transparent;color:var(--text);font-size:13px;cursor:pointer;text-align:left;';
  renameBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg> rename';
  renameBtn.onmouseenter = () => renameBtn.style.background = 'rgba(255,255,255,0.05)';
  renameBtn.onmouseleave = () => renameBtn.style.background = 'transparent';
  renameBtn.onclick = () => {
    hideSessionTabMenu();
    startSessionTabRename(session, cardEl);
  };
  
  // Close (exit) option - just removes from open tabs, doesn't delete
  const closeBtn = document.createElement('button');
  closeBtn.style.cssText = 'width:100%;padding:10px 14px;border:none;background:transparent;color:var(--text);font-size:13px;cursor:pointer;text-align:left;border-top:1px solid rgba(255,255,255,0.05);';
  closeBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> close tab';
  closeBtn.onmouseenter = () => closeBtn.style.background = 'rgba(255,255,255,0.05)';
  closeBtn.onmouseleave = () => closeBtn.style.background = 'transparent';
  closeBtn.onclick = () => {
    hideSessionTabMenu();
    removeFromOpenSessions(session.session_id);
    const isActive = S.session && S.session.session_id === session.session_id;
    if(isActive && _openSessions.length > 0){
      loadSession(_openSessions[0].session_id);
    } else if(isActive){
      newSession(true);
    }
  };
  
  menu.appendChild(renameBtn);
  menu.appendChild(closeBtn);
  document.body.appendChild(menu);
  _sessionTabMenu = menu;
  
  setTimeout(() => {
    document.addEventListener('click', hideSessionTabMenu, { once: true });
    document.addEventListener('contextmenu', hideSessionTabMenu, { once: true });
  }, 10);
}

function hideSessionTabMenu(){
  if(_sessionTabMenu){
    _sessionTabMenu.remove();
    _sessionTabMenu = null;
  }
}

function startSessionTabRename(session, cardEl){
  const titleEl = cardEl.querySelector('span');
  if(!titleEl) return;
  
  const currentTitle = session.title || 'untitled';
  const inp = document.createElement('input');
  inp.type = 'text';
  inp.value = currentTitle;
  inp.style.cssText = 'background:#0a0a0a;border:1px solid var(--accent);border-radius:4px;padding:2px 6px;font-size:12px;color:var(--text);outline:none;width:100px;';
  
  const finish = async (save) => {
    const newTitle = inp.value.trim() || 'untitled';
    inp.replaceWith(titleEl);
    
    if(save && newTitle !== currentTitle){
      session.title = newTitle;
      titleEl.textContent = newTitle.substring(0, 25) + (newTitle.length > 25 ? '...' : '');
      
      // Update in open sessions
      const openSess = _openSessions.find(s => s.session_id === session.session_id);
      if(openSess) openSess.title = newTitle;
      
      // Update current session if active
      if(S.session && S.session.session_id === session.session_id){
        S.session.title = newTitle;
        $('topbarTitle').textContent = newTitle;
      }
      
      const cached = (typeof _allSessions !== 'undefined') ? _allSessions.find(s => s.session_id === session.session_id) : null;
      if(cached) cached.title = newTitle;
      if(typeof renderSessionListFromCache === 'function') renderSessionListFromCache();
      saveOpenSessions();
      
      try{
        await api('/api/session/rename',{method:'POST',body:JSON.stringify({
          session_id:session.session_id, title:newTitle
        })});
      }catch(e){
        showToast('Rename failed: '+e.message);
      }
    }
  };
  
  inp.onkeydown = (e) => {
    if(e.key === 'Enter'){ e.preventDefault(); finish(true); }
    if(e.key === 'Escape'){ e.preventDefault(); finish(false); }
  };
  inp.onblur = () => finish(true);
  
  titleEl.replaceWith(inp);
  inp.focus();
  inp.select();
}

function syncTopbar(){
  if(!S.session){
    document.title=window._botName||'Hermes';
    if(typeof syncWorkspaceDisplays==='function') syncWorkspaceDisplays();
    if(typeof syncModelChip==='function') syncModelChip();
    if(typeof _syncHermesPanelSessionActions==='function') _syncHermesPanelSessionActions();
    else {
      const sidebarName=$('sidebarWsName');
      if(sidebarName && sidebarName.textContent==='Workspace'){
        sidebarName.textContent=t('no_workspace');
      }
    }
    return;
  }
  const sessionTitle=S.session.title||t('untitled');
  if(!_titleEditing) $('topbarTitle').textContent=sessionTitle;
  document.title=sessionTitle+' \u2014 '+(window._botName||'Hermes');
  
  // Add current session to open tabs
  addToOpenSessions(S.session);
  renderSessionTabs();
  // If a profile switch just happened, apply its model rather than the session's stale value.
  // S._pendingProfileModel is set by switchToProfile() and cleared here after one application.
  const modelOverride=S._pendingProfileModel;
  let currentModel=S.session.model||'';
  if(modelOverride){
    S._pendingProfileModel=null;
    _applyModelToDropdown(modelOverride,$('modelSelect'));
    currentModel=modelOverride;
  } else {
    const applied=_applyModelToDropdown(currentModel,$('modelSelect'));
    // If the model isn't in the current provider list, add it as a visually marked
    // "(unavailable)" entry so the session value is preserved without misleading the user.
    // Selecting it will still attempt to send (same as before), but the label makes
    // clear it's a stale model from a previous session.
    if(!applied && currentModel){
      const opt=document.createElement('option');
      opt.value=currentModel;
      opt.textContent=getModelLabel(currentModel)+t('model_unavailable');
      opt.style.color='var(--muted, #888)';
      opt.title=t('model_unavailable_title');
      $('modelSelect').appendChild(opt);
      $('modelSelect').value=currentModel;
    }
  }
  if(typeof syncModelChip==='function') syncModelChip();
  // Show Clear button only when session has messages
  const clearBtn=$('btnClearConv');
  if(clearBtn) clearBtn.style.display=(S.messages&&S.messages.filter(msg=>msg.role!=='tool').length>0)?'':'none';
  if(typeof _syncHermesPanelSessionActions==='function') _syncHermesPanelSessionActions();
  if(typeof syncWorkspaceDisplays==='function') syncWorkspaceDisplays();
  // modelSelect already set above
  // Update right panel title with current workspace name
  const rightPanelTitle=$('rightPanelTitle');
  if(rightPanelTitle){
    const wsName=S.session&&S.session.workspace?getWorkspaceFriendlyName(S.session.workspace):'workspace';
    rightPanelTitle.textContent=wsName.toLowerCase();
  }
}

// Load an existing session by ID
async function loadSession(sessionId){
 if(!sessionId) return;
 const data=await api(`/api/session?session_id=${encodeURIComponent(sessionId)}`);
 S.session=data.session;
 S.messages=data.session?.messages||[];
 if(typeof syncTopbar==='function') syncTopbar();
 if(typeof syncWorkspaceDisplays==='function') syncWorkspaceDisplays();
 if(typeof renderMessages==='function') renderMessages();
 if(typeof renderSessionListFromCache==='function') renderSessionListFromCache();
 if(typeof renderSessionTabs==='function') renderSessionTabs();
 return data.session;
}

// Create a new session
async function newSession(focus=true){
  const model=$('modelSelect')?.value||'openai/gpt-4o';
  // Use current session's workspace if available, otherwise default to ubuntu /home/house
  const currentWs=S.session?.workspace;
  const defaultWs=currentWs||'/home/house';
  const body={model,workspace:defaultWs};
  const data=await api('/api/session/new',{method:'POST',body:JSON.stringify(body)});
  S.session=data.session||data;
  S.messages=[];
  if(typeof syncTopbar==='function') syncTopbar();
  if(typeof syncWorkspaceDisplays==='function') syncWorkspaceDisplays();
  if(focus && $('msg')) $('msg').focus();
  return S.session;
}

function msgContent(m){
  // Extract plain text content from a message for filtering
  let c=m.content||'';
  if(Array.isArray(c))c=c.filter(p=>p&&p.type==='text').map(p=>p.text||'').join('').trim();
  return String(c).trim();
}

function renderMessages(){
  const inner=$('msgInner');
  const vis=S.messages.filter(m=>{
    if(!m||!m.role||m.role==='tool')return false;
    // Keep assistant messages with tool_use content even if they have no text,
    // so tool cards can be anchored to their DOM rows on page reload (#140).
    if(m.role==='assistant'&&Array.isArray(m.content)&&m.content.some(p=>p&&p.type==='tool_use'))return true;
    return msgContent(m)||m.attachments?.length||(m.role==='assistant'&&String(m.reasoning||'').trim());
  });
  $('emptyState').style.display=vis.length?'none':'';
  const _prevThinkingRow=$('thinkingRow');
  inner.innerHTML='';
  // Preserve live thinking indicator during active streams so it survives
  // full re-renders triggered by session refreshes or panel switches.
  if(_prevThinkingRow&&S.busy) inner.appendChild(_prevThinkingRow);
  // Track original indices (in S.messages) so truncate knows the cut point.
  // Also include assistant messages that have tool_calls (OpenAI format) or
  // tool_use content (Anthropic format) even when their text is empty — these
  // rows serve as DOM anchors for tool card insertion on page reload.
  const visWithIdx=[];
  let rawIdx=0;
  for(const m of S.messages){
    if(!m||!m.role||m.role==='tool'){rawIdx++;continue;}
    const hasTc=Array.isArray(m.tool_calls)&&m.tool_calls.length>0;
    const hasTu=Array.isArray(m.content)&&m.content.some(p=>p&&p.type==='tool_use');
    if(msgContent(m)||m.attachments?.length||(m.role==='assistant'&&(hasTc||hasTu||String(m.reasoning||'').trim()))) visWithIdx.push({m,rawIdx});
    rawIdx++;
  }
  // Track which message indices have had thinking cards rendered to prevent duplicates
  const _thinkingCardsRendered = new Set();
  for(let vi=0;vi<visWithIdx.length;vi++){
    const {m,rawIdx}=visWithIdx[vi];
    let content=m.content||'';
    // Extract thinking/reasoning blocks from structured content (Claude extended thinking, o3)
    let thinkingText='';
    if(Array.isArray(content)){
      thinkingText=content.filter(p=>p&&(p.type==='thinking'||p.type==='reasoning')).map(p=>p.thinking||p.reasoning||p.text||'').join('\n');
      content=content.filter(p=>p&&p.type==='text').map(p=>p.text||p.content||'').join('\n');
    }
    // Also check top-level reasoning field (Hermes format)
    if(!thinkingText && m.reasoning){
      thinkingText=m.reasoning;
    }
    // Parse inline thinking tags from plain text: <think>...</think> (DeepSeek, QwQ, MiniMax, etc.)
    // and Gemma 4 channel tokens: <|channel>thought\n...<channel|>
    // Note: no ^ anchor — some models emit leading whitespace/newlines before <think>.
    if(!thinkingText && typeof content==='string'){
      const thinkMatch=content.match(/<think>([\s\S]*?)<\/think>/);
      if(thinkMatch){
        thinkingText=thinkMatch[1].trim();
        content=content.replace(/<think>[\s\S]*?<\/think>\s*/,'').trimStart();
      }
      if(!thinkingText){
        const gemmaMatch=content.match(/<\|channel>thought\n([\s\S]*?)<channel\|>/);
        if(gemmaMatch){
          thinkingText=gemmaMatch[1].trim();
          content=content.replace(/<\|channel>thought\n[\s\S]*?<channel\|>\s*/,'').trimStart();
        }
      }
    }
    // Deduplicate: if assistant content starts with the same text as the
    // reasoning/thinking trace (case-insensitive), strip it so the bubble
    // doesn't echo the thinking card. Handles models that emit reasoning
    // both via structured API fields and inside regular content deltas.
    if(thinkingText && typeof content==='string' && content.trim()){
      const cTrim=content.trim();
      const tTrim=thinkingText.trim();
      if(cTrim.toLowerCase()===tTrim.toLowerCase()){
        content='';
      }else if(cTrim.toLowerCase().startsWith(tTrim.toLowerCase())){
        const leading=content.length-content.trimStart().length;
        content=content.slice(0,leading)+content.trimStart().slice(tTrim.length).replace(/^\s+/,'');
      }
    }
    const isUser=m.role==='user';
    // Extract XML pseudo-tool tags from assistant content (e.g. <terminal>, <read_file>)
    // that models emit as raw text instead of structured tool_calls.
    if(!isUser && typeof content==='string'){
      const xmlResult=extractXmlToolCalls(content);
      content=xmlResult.displayText;
    }
    const isSwarmWorker=m.role==='swarm-worker';
    const isLastAssistant=!isUser&&!isSwarmWorker&&vi===visWithIdx.length-1;
    const row=document.createElement('div');row.className='msg-row';
    row.dataset.msgIdx=rawIdx;row.dataset.role=m.role||'assistant';
    if(m._live) row.setAttribute('data-live-assistant','1');
    // Swarm-worker: use worker metadata for name/color
    const workerColor=m._workerColor||'#a78bfa';
    const workerName=esc(m._workerName||m.worker_name||m.worker_id?.slice(0,8)||'worker');
    let filesHtml='';
    if(m.attachments&&m.attachments.length)
      filesHtml=`<div class="msg-files">${m.attachments.map(f=>`<div class="msg-file-badge">${li('paperclip',12)} ${esc(f)}</div>`).join('')}</div>`;
    const bodyHtml = isUser ? renderTextWithHexButtons(String(content)) : renderMd(String(content));
    // Action buttons for this bubble
    const editBtn  = (isUser && !isSwarmWorker) ? `<button class="msg-action-btn" title="${t('edit_message')}" onclick="editMessage(this)">${li('pencil',13)}</button>` : '';
    const retryBtn = isLastAssistant ? `<button class="msg-action-btn" title="${t('regenerate')}" onclick="regenerateResponse(this)">${li('rotate-ccw',13)}</button>` : '';
    const tsVal=m._ts||m.timestamp;
    const tsTitle=tsVal?new Date(tsVal*1000).toLocaleString():'';
    // Format timestamp like "5:51am - 4/28/26"
    const formatTimestamp = (ts) => {
      if (!ts) return '';
      const d = new Date(ts * 1000);
      const hours = d.getHours();
      const minutes = d.getMinutes();
      const ampm = hours >= 12 ? 'pm' : 'am';
      const h = hours % 12 || 12;
      const m = minutes < 10 ? '0' + minutes : minutes;
      const month = d.getMonth() + 1;
      const day = d.getDate();
      const year = d.getFullYear().toString().slice(-2);
      return `${h}:${m}${ampm} - ${month}/${day}/${year}`;
    };
    const tsBottom = tsVal ? formatTimestamp(tsVal) : '';
    const _bn=isSwarmWorker?workerName:window._botName||'Hermes';
    // Use hermes.png for assistant avatar, circle letter for user
    const roleIconContent=isUser?'Y':isSwarmWorker?`<span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:${workerColor}22;border:2px solid ${workerColor};font-size:11px;font-weight:700;color:${workerColor}">W</span>`:`<img src="/static/hermes.png" style="width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;" alt="'+esc(_bn)+'">`;
    // Tool indicator badge for assistant messages with tool calls
    const msgToolCalls = m.tool_calls?.length || (Array.isArray(m.content) && m.content.some(p=>p?.type==='tool_use'));
    const sessionToolCalls = S.toolCalls?.filter(tc => tc.assistant_msg_idx === rawIdx).length > 0;
    const hasToolCalls = msgToolCalls || sessionToolCalls;
    const toolCount = m.tool_calls?.length || S.toolCalls?.filter(tc => tc.assistant_msg_idx === rawIdx).length || 0;
    const toolBtn = (!isUser && hasToolCalls) ? `<button class="msg-tool-badge" data-msg-idx="${rawIdx}" onclick="toggleToolCardsForMessage(${rawIdx})" title="show tool calls">${li('paperclip',10)} tool (${toolCount||'1+'})</button>` : '';
    const toolCardContainer = (!isUser && hasToolCalls) ? `<div class="tool-card-container" data-msg-idx="${rawIdx}"></div>` : '';
    row.innerHTML=`<div class="msg-role ${m.role}" ${tsTitle?`title="${esc(tsTitle)}"`:''}><div class="role-icon ${m.role}">${roleIconContent}</div><span style="font-size:12px">${isUser?t('you'):esc(_bn)}</span><span class="msg-actions">${editBtn}<button class="msg-copy-btn msg-action-btn" title="${t('copy')}" onclick="copyMsg(this)">${li('copy',13)}</button>${retryBtn}</span></div>${toolBtn}${toolCardContainer}${filesHtml}<div class="msg-body">${bodyHtml}</div>${tsBottom?`<div class="msg-timestamp">${tsBottom}</div>`:''}`;
    row.dataset.rawText = String(content).trim();
    inner.appendChild(row);
    // Render thinking card after the assistant message (collapsed by default)
    // Only render if we haven't already rendered a thinking card for this message index.
    // Live streaming thoughts should still appear as a collapsed card while the
    // model continues to think, rather than disappearing on reload.
    if(thinkingText&&!isUser&&!_thinkingCardsRendered.has(rawIdx)){
      _thinkingCardsRendered.add(rawIdx);
      const thinkRow=document.createElement('div');thinkRow.className='msg-row thinking-card-row';
      thinkRow.innerHTML=`<div class="thinking-card"><div class="thinking-card-header" onclick="this.parentElement.classList.toggle('open')"><span class="thinking-card-icon">${li('lightbulb',14)}</span><span class="thinking-card-label">${t('thinking')}</span><span class="thinking-card-toggle">${li('chevron-right',12)}</span></div><div class="thinking-card-body"><pre>${esc(thinkingText)}</pre></div></div>`;
      inner.appendChild(thinkRow);
    }
  }
  // Insert settled tool call cards (history view only).
  // During live streaming, tool cards are rendered in #liveToolCards by the
  // tool SSE handler and never mixed into the message list until done fires.
  //
  // Fallback: if S.toolCalls is empty (sessions that predate session-level tool
  // tracking, or runs that didn't go through the normal streaming path), build
  // a display list from per-message tool_calls (OpenAI format) stored in each
  // assistant message. This covers the reload case described in issue #140.
  // Collect XML-derived tool calls from all assistant messages
  const allXmlTools=[];
  if(!S.busy){
    S.messages.forEach((m,rawIdx)=>{
      if(m.role!=='assistant'||!m.content) return;
      const c=typeof m.content==='string'?m.content:'';
      if(!c) return;
      const xmlResult=extractXmlToolCalls(c);
      for(const tc of xmlResult.toolCalls){
        allXmlTools.push({...tc,assistant_msg_idx:rawIdx});
      }
    });
  }
  if(!S.busy && (!S.toolCalls||!S.toolCalls.length)){
    const derived=[];
    S.messages.forEach((m,rawIdx)=>{
      if(m.role!=='assistant') return;
      (m.tool_calls||[]).forEach(tc=>{
        if(!tc||typeof tc!=='object') return;
        const fn=tc.function||{};
        const name=fn.name||tc.name||'tool';
        let args={};
        try{ args=JSON.parse(fn.arguments||'{}'); }catch(e){}
        let argsSnap={};
        Object.keys(args).slice(0,4).forEach(k=>{ const v=String(args[k]); argsSnap[k]=v.slice(0,120)+(v.length>120?'...':''); });
        derived.push({name,snippet:'',tid:tc.id||tc.call_id||'',assistant_msg_idx:rawIdx,args:argsSnap,done:true});
      });
      // Also add XML-derived tools for this message
      const c=typeof m.content==='string'?m.content:'';
      if(c){
        const xmlResult=extractXmlToolCalls(c);
        for(const tc of xmlResult.toolCalls){
          derived.push({...tc,assistant_msg_idx:rawIdx});
        }
      }
    });
    if(derived.length) S.toolCalls=derived;
  }
  // Deduplicate by tid so XML-derived tools don't duplicate structured ones
  const _allToolCallsMap=new Map();
  for(const tc of [...(S.toolCalls||[]),...allXmlTools]){
    if(tc.tid) _allToolCallsMap.set(tc.tid,tc);
    else _allToolCallsMap.set(Math.random().toString(36),tc);
  }
  const _allToolCalls=Array.from(_allToolCallsMap.values());
  if(!S.busy && _allToolCalls.length){
    inner.querySelectorAll('.tool-card-row').forEach(el=>el.remove());
    // Also clear tool-card containers so they get fresh cards
    inner.querySelectorAll('.tool-card-container').forEach(el=>{while(el.firstChild)el.removeChild(el.firstChild);});
    const byAssistant = {};
    for(const tc of _allToolCalls){
      const key = tc.assistant_msg_idx !== undefined ? tc.assistant_msg_idx : -1;
      if(!byAssistant[key]) byAssistant[key] = [];
      byAssistant[key].push(tc);
    }
    const allRows = Array.from(inner.querySelectorAll('.msg-row[data-msg-idx]'));
    // Track the last inserted node per anchor so back-to-back groups for the
    // same (filtered) anchor row are inserted in chronological order.
    const anchorInsertAfter = new Map();
    for(const [key, cards] of Object.entries(byAssistant)){
      const aIdx = parseInt(key);
      // Find the right insertion point: cards go AFTER the assistant message
      // that triggered them. We look for the row at aIdx, or the nearest
      // visible ASSISTANT row at or before aIdx (the assistant message may be
      // filtered out if it contained only tool_use blocks with no text response).
      let anchorRow = null;
      if(aIdx >= 0){
        // First: exact match for the assistant row
        for(const r of allRows){
          const ri=parseInt(r.dataset.msgIdx||'-1');
          if(ri===aIdx){anchorRow=r;break;}
        }
        // Fallback: nearest visible ASSISTANT row at or before aIdx
        if(!anchorRow){
          for(let i=allRows.length-1;i>=0;i--){
            const ri=parseInt(allRows[i].dataset.msgIdx||'-1');
            if(ri<=aIdx&&S.messages[ri]&&S.messages[ri].role==='assistant'){anchorRow=allRows[i];break;}
          }
        }
      }
      // aIdx === -1 or no assistant anchor found: attach after the last assistant row
      if(!anchorRow){
        for(let i=allRows.length-1;i>=0;i--){
          const ri=parseInt(allRows[i].dataset.msgIdx||'-1',10);
          if(ri>=0&&S.messages[ri]&&S.messages[ri].role==='assistant'){anchorRow=allRows[i];break;}
        }
      }
      const frag=document.createDocumentFragment();
      for(const tc of cards){
        const card=buildToolCard(tc);
        card.dataset.msgIdx=aIdx;
        frag.appendChild(card);
      }
      // Add expand/collapse toggle for groups with 2+ collapsible cards
      const collapsibleCards = cards.filter(tc => tc.snippet || (tc.args && Object.keys(tc.args).length > 0));
      if(collapsibleCards.length>=2){
        const toggle=document.createElement('div');
        toggle.className='tool-cards-toggle';
        // Collect card elements before they get moved to DOM
        const cardEls=Array.from(frag.querySelectorAll('.tool-card'));
        const expandBtn=document.createElement('button');
        expandBtn.textContent=t('expand_all');
        expandBtn.onclick=()=>cardEls.forEach(c=>c.classList.add('open'));
        const collapseBtn=document.createElement('button');
        collapseBtn.textContent=t('collapse_all');
        collapseBtn.onclick=()=>cardEls.forEach(c=>c.classList.remove('open'));
        toggle.appendChild(expandBtn);
        toggle.appendChild(collapseBtn);
        frag.insertBefore(toggle,frag.firstChild);
      }
      // Insert the tool cards into the container inside the anchor row,
      // directly under the tool pill button. Fall back to after the row
      // if no container exists (e.g. for older sessions without container).
      let container = anchorRow ? anchorRow.querySelector(`.tool-card-container[data-msg-idx="${aIdx}"]`) : null;
      // If no container, create one inside the row
      if(!container && anchorRow){
        container = document.createElement('div');
        container.className = 'tool-card-container';
        container.dataset.msgIdx = aIdx;
        const toolBtn = anchorRow.querySelector(`.msg-tool-badge[data-msg-idx="${aIdx}"]`);
        if(toolBtn){
          toolBtn.insertAdjacentElement('afterend', container);
        } else {
          anchorRow.appendChild(container);
        }
      }
      // Now place the fragment into the container
      if(container){
        // Clear any existing cards in this container first
        while(container.firstChild) container.removeChild(container.firstChild);
        container.appendChild(frag);
      } else {
        // Fallback: insert after the row as before
        const insertAfterNode = anchorInsertAfter.get(anchorRow) || anchorRow;
        const refNode = insertAfterNode ? insertAfterNode.nextSibling : null;
        if(refNode) inner.insertBefore(frag,refNode);
        else inner.appendChild(frag);
        anchorInsertAfter.set(anchorRow, inner.lastChild);
      }
    }
  }
  // Render usage badge on the last assistant message row (if enabled and usage data exists)
  if(window._showTokenUsage&&S.session&&(S.session.input_tokens||S.session.output_tokens)){
    const rows=inner.querySelectorAll('.msg-row');
    let lastAssist=null;
    for(let i=rows.length-1;i>=0;i--){if(rows[i].dataset.role==='assistant'){lastAssist=rows[i];break;}}
    if(lastAssist&&!lastAssist.querySelector('.msg-usage')){
      const usage=document.createElement('div');
      usage.className='msg-usage';
      const inTok=S.session.input_tokens||0;
      const outTok=S.session.output_tokens||0;
      const cost=S.session.estimated_cost;
      let text=`${_fmtTokens(inTok)} in · ${_fmtTokens(outTok)} out`;
      if(cost) text+=` · ~$${cost<0.01?cost.toFixed(4):cost.toFixed(2)}`;
      usage.textContent=text;
      lastAssist.appendChild(usage);
    }
  }
  scrollToBottom();
  // Apply syntax highlighting after DOM is built
  requestAnimationFrame(()=>{highlightCode();addCopyButtons();renderMermaidBlocks();renderKatexBlocks();});
  // inject canvas inline cards and file links
  inner.querySelectorAll('.msg-row').forEach(row=>{
   if(typeof injectCanvasCards==='function')injectCanvasCards(row);
   if(typeof injectCanvasFileLinks==='function')injectCanvasFileLinks(row);
  });
  // Refresh todo panel if it's currently open
  if(typeof loadTodos==='function' && document.getElementById('panelTodos') && document.getElementById('panelTodos').classList.contains('active')){
    loadTodos();
  }
}

function toolIcon(name){
  const icons={
    terminal:        li('terminal'),
    read_file:       li('file-text'),
    write_file:      li('file-pen'),
    search_files:    li('search'),
    web_search:      li('globe'),
    web_extract:     li('globe'),
    execute_code:    li('play'),
    patch:           li('wrench'),
    memory:          li('brain'),
    skill_manage:    li('book-open'),
    todo:            li('list-todo'),
    cronjob:         li('clock'),
    delegate_task:   li('bot'),
    send_message:    li('message-square'),
    browser_navigate:li('globe'),
    vision_analyze:  li('eye'),
    subagent_progress:li('shuffle'),
 swarm_start:li('zap'),
  };
  return icons[name]||li('wrench');
}

function toggleToolCardsForMessage(msgIdx){
  const inner=$('msgInner');
  if(!inner)return;
  // Find the tool card container inside the message row for this msgIdx
  const container=inner.querySelector(`.tool-card-container[data-msg-idx="${msgIdx}"]`);
  // Also find any legacy tool-card-row siblings outside the container
  const legacyRows=inner.querySelectorAll(`.tool-card-row[data-msg-idx="${msgIdx}"]`);
  // Get the cards inside the container
  const containerCards=container?container.querySelectorAll('.tool-card-row'):[];
  // Check if any are currently visible
  const anyContainerOpen=Array.from(containerCards).some(r=>r.style.display!=='none');
  const anyLegacyOpen=Array.from(legacyRows).some(r=>r.style.display!=='none');
  const anyOpen=anyContainerOpen||anyLegacyOpen;
  const shouldShow=!anyOpen;
  // Toggle container cards
  if(container) containerCards.forEach(r=>{r.style.display=shouldShow?'':'none';});
  // Toggle legacy cards too
  legacyRows.forEach(r=>{r.style.display=shouldShow?'':'none';});
  // Update button text/icon
  const btn=inner.querySelector(`.msg-tool-badge[data-msg-idx="${msgIdx}"]`);
  if(btn){
    const count=containerCards.length||legacyRows.length;
    btn.innerHTML=shouldShow?`${li('paperclip',10)} hide`:`${li('paperclip',10)} tool (${count})`;
  }
}

function buildToolCard(tc){
  const row=document.createElement('div');
  row.className='msg-row tool-card-row';
  row.style.display='none';  // Hidden by default, shown when tool button clicked
  const icon=toolIcon(tc.name);
  const hasDetail=tc.snippet||(tc.args&&Object.keys(tc.args).length>0);
  let displaySnippet='';
  if(tc.snippet){
    const s=tc.snippet;
    if(s.length<=220){displaySnippet=s;}
    else{
      const cutoff=s.slice(0,220);
      const lastBreak=Math.max(cutoff.lastIndexOf('. '),cutoff.lastIndexOf('\n'),cutoff.lastIndexOf('; '));
      displaySnippet=lastBreak>80?s.slice(0,lastBreak+1):cutoff;
    }
  }
  const hasMore=tc.snippet&&tc.snippet.length>displaySnippet.length;
  const runIndicator=tc.done===false?'<span class="tool-card-running-dot"></span>':'';
  const isSubagent=tc.name==='subagent_progress';
  const isDelegation=tc.name==='delegate_task';
 const isSwarm=tc.name==='swarm_start';
  const cardClass='tool-card'+(tc.done===false?' tool-card-running':'')+(isSubagent?' tool-card-subagent':'')+(isSwarm?' tool-card-swarm':'');
  // Clean up legacy subagent prefixes since the Lucide icon already shows it
  let displayName=tc.name;
  if(isSubagent) displayName='Subagent';
  if(isDelegation) displayName='Delegate task';
 if(isSwarm) displayName='Swarm';
  let previewText=tc.preview||displaySnippet||'';
  if(isSubagent) previewText=previewText.replace(/^(?:\u{1F500}|↳)\s*/u,'');
  row.innerHTML=`
    <div class="${cardClass}">
      <div class="tool-card-header" onclick="this.closest('.tool-card').classList.toggle('open')">
        ${runIndicator}
        <span class="tool-card-icon">${icon}</span>
        <span class="tool-card-name">${esc(displayName)}</span>
        <span class="tool-card-preview">${esc(previewText)}</span>
        ${hasDetail?'<span class="tool-card-toggle">▸</span>':''}
      </div>
      ${hasDetail?`<div class="tool-card-detail">
        ${tc.args&&Object.keys(tc.args).length?`<div class="tool-card-args">${
          Object.entries(tc.args).map(([k,v])=>`<div><span class="tool-arg-key">${esc(k)}</span> <span class="tool-arg-val">${esc(String(v))}</span></div>`).join('')
        }</div>`:''}
        ${displaySnippet?`<div class="tool-card-result">
          <pre>${esc(displaySnippet)}</pre>
          ${hasMore?`<button class="tool-card-more" data-full="${esc(tc.snippet||'').replace(/"/g,'&quot;')}" data-short="${esc(displaySnippet||'').replace(/"/g,'&quot;')}" onclick="event.stopPropagation();const p=this.previousElementSibling;const full=this.dataset.full;const short=this.dataset.short;p.textContent=p.textContent===short?full:short;this.textContent=p.textContent===short?'Show more':'Show less'">Show more</button>`:''}
        </div>`:''}
      </div>`:''}
    </div>`;
  return row;
}

// ── Live tool card helpers (called during SSE streaming) ──
function appendLiveToolCard(tc){
  const container=$('liveToolCards');
  if(!container)return;
  container.style.display='';
  // Update existing card if same tool call id (e.g. snippet arrives after done)
  const existing=container.querySelector(`[data-tid="${CSS.escape(tc.tid||'')}"]`);
  if(existing){existing.replaceWith(buildToolCard(tc));return;}
  const card=buildToolCard(tc);
  if(tc.tid)card.dataset.tid=tc.tid;
  container.appendChild(card);
}

function clearLiveToolCards(){
  const container=$('liveToolCards');
  if(!container)return;
  container.innerHTML='';
  container.style.display='none';
}

// ── Edit + Regenerate ──

function editMessage(btn) {
  if(S.busy) return;
  const row = btn.closest('.msg-row');
  if(!row) return;
  const msgIdx = parseInt(row.dataset.msgIdx, 10);
  const originalText = row.dataset.rawText || '';
  const body = row.querySelector('.msg-body');
  if(!body || row.dataset.editing) return;
  row.dataset.editing = '1';

  // Replace msg-body with an editable textarea
  const ta = document.createElement('textarea');
  ta.className = 'msg-edit-area';
  ta.value = originalText;
  body.replaceWith(ta);
  // Resize after DOM insertion so scrollHeight is correct
  requestAnimationFrame(() => { autoResizeTextarea(ta); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); });
  ta.addEventListener('input', () => autoResizeTextarea(ta));

  // Action bar below the textarea
  const bar = document.createElement('div');
  bar.className = 'msg-edit-bar';
  bar.innerHTML = `<button class="msg-edit-send">Send edit</button><button class="msg-edit-cancel">Cancel</button>`;
  ta.after(bar);

  bar.querySelector('.msg-edit-send').onclick = async () => {
    const newText = ta.value.trim();
    if(!newText) return;
    await submitEdit(msgIdx, newText);
  };
  bar.querySelector('.msg-edit-cancel').onclick = () => cancelEdit(row, originalText, body);

  ta.addEventListener('keydown', e => {
    if(e.key==='Enter' && !e.shiftKey) { if(e.isComposing) return; e.preventDefault(); bar.querySelector('.msg-edit-send').click(); }
    if(e.key==='Escape') { e.preventDefault(); cancelEdit(row, originalText, body); }
  });
}

function cancelEdit(row, originalText, originalBody) {
  delete row.dataset.editing;
  const ta = row.querySelector('.msg-edit-area');
  const bar = row.querySelector('.msg-edit-bar');
  if(ta) ta.replaceWith(originalBody);
  if(bar) bar.remove();
}

function autoResizeTextarea(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 300) + 'px';
}

async function submitEdit(msgIdx, newText) {
  if(!S.session || S.busy) return;
  // Truncate session at msgIdx (keep messages before the edited one)
  // then re-send the edited text
  try {
    await api('/api/session/truncate', {method:'POST', body:JSON.stringify({
      session_id: S.session.session_id,
      keep_count: msgIdx  // keep messages[0..msgIdx-1], discard from msgIdx onward
    })});
    S.messages = S.messages.slice(0, msgIdx);
    renderMessages();
    // Now send the edited message as a new chat
    $('msg').value = newText;
    await send();
  } catch(e) { setStatus(t('edit_failed') + e.message); }
}

async function regenerateResponse(btn) {
  if(!S.session || S.busy) return;
  // Find the last user message and re-run it
  // Remove the last assistant message first (truncate to before it)
  const row = btn.closest('.msg-row');
  if(!row) return;
  const assistantIdx = parseInt(row.dataset.msgIdx, 10);
  // Find the last user message text (one before this assistant message)
  let lastUserText = '';
  for(let i = assistantIdx - 1; i >= 0; i--) {
    const m = S.messages[i];
    if(m && m.role === 'user') { lastUserText = msgContent(m); break; }
  }
  if(!lastUserText) return;
  try {
    await api('/api/session/truncate', {method:'POST', body:JSON.stringify({
      session_id: S.session.session_id,
      keep_count: assistantIdx  // remove the assistant message
    })});
    S.messages = S.messages.slice(0, assistantIdx);
    renderMessages();
    $('msg').value = lastUserText;
    await send();
  } catch(e) { setStatus(t('regen_failed') + e.message); }
}

function highlightCode(container) {
  // Apply Prism.js syntax highlighting to all code blocks in container (or whole messages area)
  if(typeof Prism === 'undefined' || !Prism.highlightAllUnder) return;
  const el = container || $('msgInner');
  if(!el) return;
  Prism.highlightAllUnder(el);
}

function addCopyButtons(container){
  const el=container||$('msgInner');
  if(!el) return;
  el.querySelectorAll('pre > code').forEach(codeEl=>{
    const pre=codeEl.parentElement;
    if(pre.querySelector('.code-copy-btn')) return;
    const btn=document.createElement('button');
    btn.className='code-copy-btn';
    btn.textContent=t('copy');
    btn.onclick=(e)=>{
      e.stopPropagation();
      navigator.clipboard.writeText(codeEl.textContent).then(()=>{
        btn.textContent=t('copied');
        setTimeout(()=>{btn.textContent=t('copy');},1500);
      });
    };
    const header=pre.previousElementSibling;
    if(header&&header.classList.contains('pre-header')){
      header.style.display='flex';
      header.style.justifyContent='space-between';
      header.style.alignItems='center';
      header.appendChild(btn);
    }else{
      pre.style.position='relative';
      btn.style.cssText='position:absolute;top:6px;right:6px;';
      pre.appendChild(btn);
    }
  });
}

let _mermaidLoading=false;
let _mermaidReady=false;

function renderMermaidBlocks(){
  const blocks=document.querySelectorAll('.mermaid-block:not([data-rendered])');
  if(!blocks.length) return;
  if(!_mermaidReady){
    if(!_mermaidLoading){
      _mermaidLoading=true;
      const script=document.createElement('script');
      script.src='https://cdn.jsdelivr.net/npm/mermaid@10.9.3/dist/mermaid.min.js';
      script.integrity='sha384-R63zfMfSwJF4xCR11wXii+QUsbiBIdiDzDbtxia72oGWfkT7WHJfmD/I/eeHPJyT';
      script.crossOrigin='anonymous';
      script.onload=()=>{
        if(typeof mermaid!=='undefined'){
          mermaid.initialize({startOnLoad:false,theme:'dark',themeVariables:{
            primaryColor:'#4a6fa5',primaryTextColor:'#e2e8f0',lineColor:'#718096',
            secondaryColor:'#2d3748',tertiaryColor:'#1a202c',primaryBorderColor:'#4a5568',
          }});
          _mermaidReady=true;
          renderMermaidBlocks();
        }
      };
      document.head.appendChild(script);
    }
    return;
  }
  blocks.forEach(async(block)=>{
    block.dataset.rendered='true';
    const code=block.textContent;
    const id=block.dataset.mermaidId||('m-'+Math.random().toString(36).slice(2));
    try{
      const {svg}=await mermaid.render(id,code);
      block.innerHTML=svg;
      block.classList.add('mermaid-rendered');
    }catch(e){
      // Fall back to showing as a code block
      block.innerHTML=`<div class="pre-header">mermaid</div><pre><code>${esc(code)}</code></pre>`;
    }
  });
}

let _katexLoading=false;
let _katexReady=false;

function renderKatexBlocks(){
  const blocks=document.querySelectorAll('.katex-block:not([data-rendered]),.katex-inline:not([data-rendered])');
  if(!blocks.length) return;
  if(!_katexReady){
    if(!_katexLoading){
      _katexLoading=true;
      const script=document.createElement('script');
      script.src='https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.js';
      script.integrity='sha384-cMkvdD8LoxVzGF/RPUKAcvmm49FQ0oxwDF3BGKtDXcEc+T1b2N+teh/OJfpU0jr6';
      script.crossOrigin='anonymous';
      script.onload=()=>{
        if(typeof katex!=='undefined'){
          _katexReady=true;
          renderKatexBlocks();
        }
      };
      document.head.appendChild(script);
    }
    return;
  }
  blocks.forEach(el=>{
    el.dataset.rendered='true';
    const src=el.textContent||'';
    const displayMode=el.dataset.katex==='display';
    try{
      katex.render(src,el,{
        displayMode,
        throwOnError:false,
        trust:false,
        strict:'ignore',
      });
    }catch(e){
      // Leave as raw text in a code span on failure
      el.outerHTML=`<code>${esc(src)}</code>`;
    }
  });
}

function _thinkingMarkup(text=''){
  const _bn=window._botName||'Hermes';
  const icon=esc(_bn.charAt(0).toUpperCase());
  const label=esc(_bn);
  const textStr=String(text||'').trim();
  // Show a short preview of what the model is thinking so the stream doesn't feel frozen
  const preview=textStr
    ? `<span class="thinking-preview">${esc(textStr.slice(0,120))}${textStr.length>120?'…':''}</span>`
    : '';
  const body=`<div class="thinking"><div class="thinking-label">${t('thinking')}</div><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>${preview}`;
  return `<div class="msg-role assistant"><div class="role-icon assistant">${icon}</div>${label}</div>${body}`;
}
// Track the last thinking text to avoid unnecessary DOM updates that reset CSS animation
let _lastThinkingText = null;

function appendThinking(text=''){
  $('emptyState').style.display='none';
  let row=$('thinkingRow');
  const textStr = String(text || '');

  if(!row){
    row=document.createElement('div');
    row.className='msg-row';
    row.id='thinkingRow';
    $('msgInner').appendChild(row);
    // Always set innerHTML when creating new row
    row.innerHTML=_thinkingMarkup(text);
    _lastThinkingText = textStr;
  } else {
    // Move existing thinking row to end to ensure it's always after the latest message
    $('msgInner').appendChild(row);
    row.className='msg-row';
    // Only update innerHTML if text content changed to prevent animation glitch
    if (textStr !== _lastThinkingText) {
      row.innerHTML=_thinkingMarkup(text);
      _lastThinkingText = textStr;
    }
  }
  scrollToBottom();
}
function updateThinking(text=''){appendThinking(text);}
function removeThinking(){const el=$('thinkingRow');if(el){el.remove();_lastThinkingText=null;}}

function gearIcon(size){
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:-0.15em;flex-shrink:0"><path fill-rule="evenodd" d="M16 12a4 4 0 11-8 0 4 4 0 018 0zm-1.5 0a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"/><path fill-rule="evenodd" d="M12 1c-.268 0-.534.01-.797.028-.763.055-1.345.617-1.512 1.304l-.352 1.45c-.02.078-.09.172-.225.22a8.45 8.45 0 00-.728.303c-.13.06-.246.044-.315.002l-1.274-.776c-.604-.368-1.412-.354-1.99.147-.403.348-.78.726-1.129 1.128-.5.579-.515 1.387-.147 1.99l.776 1.275c.042.069.059.185-.002.315-.112.237-.213.48-.302.728-.05.135-.143.206-.221.225l-1.45.352c-.687.167-1.249.749-1.304 1.512a11.149 11.149 0 000 1.594c.055.763.617 1.345 1.304 1.512l1.45.352c.078.02.172.09.22.225.09.248.191.491.303.729.06.129.044.245.002.314l-.776 1.274c-.368.604-.354 1.412.147 1.99.348.403.726.78 1.128 1.129.579.5 1.387.515 1.99.147l1.275-.776c.069-.042.185-.059.315.002.237.112.48.213.728.302.135.05.206.143.225.221l.352 1.45c.167.687.749 1.249 1.512 1.303a11.125 11.125 0 001.594 0c.763-.054 1.345-.616 1.512-1.303l.352-1.45c.02-.078.09-.172.225-.22.248-.09.491-.191.729-.303.129-.06.245-.044.314-.002l1.274.776c.604.368 1.412.354 1.99-.147.403-.348.78-.726 1.129-1.128.5-.579.515-1.387.147-1.99l-.776-1.275c-.042-.069-.059-.185.002-.315.112-.237.213-.48.302-.728.05-.135.143-.206.221-.225l1.45-.352c.687-.167 1.249-.749 1.303-1.512a11.125 11.125 0 000-1.594c-.054-.763-.616-1.345-1.303-1.512l-1.45-.352c-.078-.02-.172-.09-.22-.225a8.469 8.469 0 00-.303-.728c-.06-.13-.044-.246-.002-.315l.776-1.274c.368-.604.354-1.412-.147-1.99-.348-.403-.726-.78-1.128-1.129-.579-.5-1.387-.515-1.99-.147l-1.275.776c-.069.042-.185.059-.315-.002a8.465 8.465 0 00-.728-.302c-.135-.05-.206-.143-.225-.221l-.352-1.45c-.167-.687-.749-1.249-1.512-1.304A11.149 11.149 0 0012 1zm-.69 1.525a9.648 9.648 0 011.38 0c.055.004.135.05.162.16l.351 1.45c.153.628.626 1.08 1.173 1.278.205.074.405.157.6.249a1.832 1.832 0 001.733-.074l1.275-.776c.097-.06.186-.036.228 0 .348.302.674.628.976.976.036.042.06.13 0 .228l-.776 1.274a1.832 1.832 0 00-.074 1.734c.092.195.175.395.248.6.198.547.652 1.02 1.278 1.172l1.45.353c.111.026.157.106.161.161a9.653 9.653 0 010 1.38c-.004.055-.05.135-.16.162l-1.45.351a1.833 1.833 0 00-1.278 1.173 6.926 6.926 0 01-.25.6 1.832 1.832 0 00.075 1.733l.776 1.275c.06.097.036.186 0 .228a9.555 9.555 0 01-.976.976c-.042.036-.13.06-.228 0l-1.275-.776a1.832 1.832 0 00-1.733-.074 6.926 6.926 0 01-.6.248 1.833 1.833 0 00-1.172 1.278l-.353 1.45c-.026.111-.106.157-.161.161a9.653 9.653 0 01-1.38 0c-.055-.004-.135-.05-.162-.16l-.351-1.45a1.833 1.833 0 00-1.173-1.278 6.928 6.928 0 01-.6-.25 1.832 1.832 0 00-1.734.075l-1.274.776c-.097.06-.186.036-.228 0a9.56 9.56 0 01-.976-.976c-.036-.042-.06-.13 0-.228l.776-1.275a1.832 1.832 0 00.074-1.733 6.948 6.948 0 01-.249-.6 1.833 1.833 0 00-1.277-1.172l-1.45-.353c-.111-.026-.157-.106-.161-.161a9.648 9.648 0 010-1.38c.004-.055.05-.135.16-.162l1.45-.351a1.833 1.833 0 001.278-1.173 6.95 6.95 0 01.249-.6 1.832 1.832 0 00-.074-1.734l-.776-1.274c-.06-.097-.036-.186 0-.228.302-.348.628-.674.976-.976.042-.036.13-.06.228 0l1.274.776a1.832 1.832 0 001.734.074 6.95 6.95 0 01.6-.249 1.833 1.833 0 001.172-1.277l.353-1.45c.026-.111.106-.157.161-.161z"/></svg>`;
}

function fileIcon(name, type){
  if(type==='dir') return li('folder',14);
  const e=fileExt(name);
  if(IMAGE_EXTS.has(e)) return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path d="M14.2639 15.9375L12.5958 14.2834C11.7909 13.4851 11.3884 13.086 10.9266 12.9401C10.5204 12.8118 10.0838 12.8165 9.68048 12.9536C9.22188 13.1095 8.82814 13.5172 8.04068 14.3326L4.04409 18.2801M14.2639 15.9375L14.6053 15.599C15.4112 14.7998 15.8141 14.4002 16.2765 14.2543C16.6831 14.126 17.12 14.1311 17.5236 14.2687C17.9824 14.4251 18.3761 14.8339 19.1634 15.6514L20 16.4934M14.2639 15.9375L18.275 19.9565M18.275 19.9565C17.9176 20 17.4543 20 16.8 20H7.2C6.07989 20 5.51984 20 5.09202 19.782C4.71569 19.5903 4.40973 19.2843 4.21799 18.908C4.12796 18.7313 4.07512 18.5321 4.04409 18.2801M18.275 19.9565C18.5293 19.9256 18.7301 19.8727 18.908 19.782C19.2843 19.5903 19.5903 19.2843 19.782 18.908C20 18.4802 20 17.9201 20 16.8V16.4934M4.04409 18.2801C4 17.9221 4 17.4575 4 16.8V7.2C4 6.0799 4 5.51984 4.21799 5.09202C4.40973 4.71569 4.71569 4.40973 5.09202 4.21799C5.51984 4 6.07989 4 7.2 4H16.8C17.9201 4 18.4802 4 18.908 4.21799C19.2843 4.40973 19.5903 4.71569 19.782 5.09202C20 5.51984 20 6.0799 20 7.2V16.4934M17 8.99989C17 10.1045 16.1046 10.9999 15 10.9999C13.8954 10.9999 13 10.1045 13 8.99989C13 7.89532 13.8954 6.99989 15 6.99989C16.1046 6.99989 17 7.89532 17 8.99989Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:-0.15em;flex-shrink:0"></path> </g></svg>';
  if(MD_EXTS.has(e))    return gearIcon(14);
  if(e==='.zip') return '<svg width="14" height="14" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true" style="display:inline-block;vertical-align:-0.15em;flex-shrink:0"><path d="M422.741,42.667h-60.07V32.491C362.671,14.543,348.128,0,330.18,0H181.828c-17.947,0-32.491,14.543-32.491,32.491v10.176 H89.259c-25.734,0-46.592,20.858-46.592,46.592v376.149c0,25.734,20.858,46.592,46.592,46.592h333.483 c25.734,0,46.592-20.858,46.592-46.592V89.259C469.333,63.525,448.475,42.667,422.741,42.667z M192.004,42.667H320v42.667 H192.004V42.667z M426.667,465.408c0,2.17-1.755,3.925-3.925,3.925H89.259c-2.17,0-3.925-1.755-3.925-3.925V89.259 c0-2.17,1.755-3.925,3.925-3.925h60.075v10.176c0,17.947,14.543,32.491,32.491,32.491h0.004h148.348h0.004 c17.947,0,32.491-14.543,32.491-32.491V85.333h60.07c2.17,0,3.925,1.755,3.925,3.925V465.408z M298.667,234.667c11.782,0,21.333-9.551,21.333-21.333c0-11.782-9.551-21.333-21.333-21.333h-21.333v-21.333 c0-11.782-9.551-21.333-21.333-21.333c-11.782,0-21.333,9.551-21.333,21.333V192h-21.333C201.551,192,192,201.551,192,213.333 c0,11.782,9.551,21.333,21.333,21.333h21.333V256h-21.333C201.551,256,192,265.551,192,277.333 c0,11.782,9.551,21.333,21.333,21.333h21.333V320h-21.333C201.551,320,192,329.551,192,341.333v85.333 c0,11.782,9.551,21.333,21.333,21.333h85.333c11.782,0,21.333-9.551,21.333-21.333v-85.333c0-11.782-9.551-21.333-21.333-21.333 h-21.333v-21.333h21.333c11.782,0,21.333-9.551,21.333-21.333c0-11.782-9.551-21.333-21.333-21.333h-21.333v-21.333H298.667z M277.333,405.333h-42.667v-42.667h42.667V405.333z"/></svg>';
  if(typeof DOWNLOAD_EXTS!=='undefined'&&DOWNLOAD_EXTS.has(e)) return li('download',14);
  if(e==='.py')   return li('file-code',14);
  if(e==='.js'||e==='.ts'||e==='.jsx'||e==='.tsx') return li('zap',14);
  if(e==='.json'||e==='.yaml'||e==='.yml'||e==='.toml') return gearIcon(14);
  if(e==='.sh'||e==='.bash') return li('terminal',14);
  if(e==='.pdf') return li('download',14);
  return gearIcon(14);
}

function renderBreadcrumb(){
  const bar=$('breadcrumbBar');
  const upBtn=$('btnUpDir');
  if(!bar)return;
  if(S.currentDir==='.'){
    bar.style.display='none';
    if(upBtn)upBtn.style.display='none';
    return;
  }
  bar.style.display='flex';
  if(upBtn)upBtn.style.display='';
  bar.innerHTML='';
  // Root segment
  const root=document.createElement('span');
  root.className='breadcrumb-seg breadcrumb-link';
  root.textContent='~';
  root.onclick=()=>loadDir('.');
  bar.appendChild(root);
  // Path segments
  const parts=S.currentDir.split('/');
  let accumulated='';
  for(let i=0;i<parts.length;i++){
    const sep=document.createElement('span');
    sep.className='breadcrumb-sep';sep.textContent='/';
    bar.appendChild(sep);
    accumulated+=(accumulated?'/':'')+parts[i];
    const seg=document.createElement('span');
    seg.textContent=parts[i];
    if(i<parts.length-1){
      seg.className='breadcrumb-seg breadcrumb-link';
      const target=accumulated;
      seg.onclick=()=>loadDir(target);
    } else {
      seg.className='breadcrumb-seg breadcrumb-current';
    }
    bar.appendChild(seg);
  }
  // Edit icon to trigger path input
  const editIcon=document.createElement('span');
  editIcon.className='breadcrumb-seg';
  editIcon.style.cssText='margin-left:auto;cursor:pointer;opacity:.5;font-size:11px;';
  editIcon.innerHTML='✎';
  editIcon.title='Type path (Ctrl+L)';
  editIcon.onclick=()=>{
    const pathBar=$('pathInputBar');
    const input=$('dirPathInput');
    if(pathBar&&input){
      const isVisible=pathBar.style.display!=='none';
      if(isVisible){
        pathBar.style.display='none';
      } else {
        pathBar.style.display='block';
        input.focus();
        if(S.session) input.value=S.session.workspace+'/';
        input.setSelectionRange(input.value.length,input.value.length);
      }
    }
  };
  bar.appendChild(editIcon);
}

// Track expanded directories for tree view
if(!S._expandedDirs) S._expandedDirs=new Set();
// Cache of fetched directory contents: path -> entries[]
if(!S._dirCache) S._dirCache={};

function renderFileTree(){
  const box=$('fileTree');box.innerHTML='';
  // Cache current dir entries
  S._dirCache[S.currentDir||'.']=S.entries;
  _renderTreeItems(box, S.entries, 0);
}

function _renderTreeItems(container, entries, depth){
  for(const item of entries){
    const el=document.createElement('div');el.className='file-item';
    el.style.paddingLeft=(8+depth*16)+'px';

    if(item.type==='dir'){
      // Toggle arrow for directories
      const arrow=document.createElement('span');
      arrow.className='file-tree-toggle';
      const isExpanded=S._expandedDirs.has(item.path);
      arrow.textContent=isExpanded?'\u25BE':'\u25B8';
      el.appendChild(arrow);
    }

    // Icon
    const iconEl=document.createElement('span');
    iconEl.className='file-icon';iconEl.innerHTML=fileIcon(item.name,item.type);
    el.appendChild(iconEl);

    // Name
    const nameEl=document.createElement('span');
    nameEl.className='file-name';nameEl.textContent=item.name;nameEl.title=t('double_click_rename');
    nameEl.ondblclick=(e)=>{
      e.stopPropagation();
      // For directories, double-click navigates (breadcrumb view)
      if(item.type==='dir'){loadDir(item.path);return;}
      const inp=document.createElement('input');
      inp.className='file-rename-input';inp.value=item.name;
      inp.onclick=(e2)=>e2.stopPropagation();
      const finish=async(save)=>{
        inp.onblur=null;
        if(save){
          const newName=inp.value.trim();
          if(newName&&newName!==item.name){
            try{
              await api('/api/file/rename',{method:'POST',body:JSON.stringify({
                session_id:S.session.session_id,path:item.path,new_name:newName
              })});
              // Invalidate cache and re-render
              delete S._dirCache[S.currentDir];
              await loadDir(S.currentDir);
            }catch(err){showToast(t('rename_failed')+err.message);}
          }
        }
        inp.replaceWith(nameEl);
      };
      inp.onkeydown=(e2)=>{
        if(e2.key==='Enter'){
          if(e2.isComposing){return;}
          e2.preventDefault();
          finish(true);
        }
        if(e2.key==='Escape'){e2.preventDefault();finish(false);}
      };
      inp.onblur=()=>finish(false);
      nameEl.replaceWith(inp);
      setTimeout(()=>{inp.focus();inp.select();},10);
    };
    el.appendChild(nameEl);

    // Size -- only for files
    if(item.type==='file'&&item.size){
      const sizeEl=document.createElement('span');
      sizeEl.className='file-size';
      sizeEl.textContent=`${(item.size/1024).toFixed(1)}k`;
      el.appendChild(sizeEl);
    }

    // Right-click context menu for all items
    el.oncontextmenu=(e)=>{
      e.preventDefault();
      e.stopPropagation();
      _showFileContextMenu(e,item);
    };

    if(item.type==='dir'){
      // Single-click toggles expand/collapse
      el.onclick=async(e)=>{
        e.stopPropagation();
        if(S._expandedDirs.has(item.path)){
          S._expandedDirs.delete(item.path);
          if(typeof _saveExpandedDirs==='function')_saveExpandedDirs();
          renderFileTree();
        }else{
          S._expandedDirs.add(item.path);
          if(typeof _saveExpandedDirs==='function')_saveExpandedDirs();
          // Fetch children if not cached
          if(!S._dirCache[item.path]){
            try{
              const data=await api(`/api/list?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(item.path)}`);
              S._dirCache[item.path]=data.entries||[];
            }catch(e2){S._dirCache[item.path]=[];}
          }
          renderFileTree();
        }
      };
    }else{
      el.onclick=async()=>openFile(item.path);
    }

    container.appendChild(el);

    // Render children if directory is expanded
    if(item.type==='dir'&&S._expandedDirs.has(item.path)){
      const children=S._dirCache[item.path]||[];
      if(children.length){
        _renderTreeItems(container, children, depth+1);
      }else{
        const empty=document.createElement('div');
        empty.className='file-item file-empty';
        empty.style.paddingLeft=(8+(depth+1)*16)+'px';
        empty.textContent=t('empty_dir');
        container.appendChild(empty);
      }
    }
  }
}

async function deleteWorkspaceFile(relPath, name){
  if(!S.session)return;
  const _delFile=await showConfirmDialog({title:t('delete_confirm',name),message:'',confirmLabel:'Delete',danger:true,focusCancel:true});
  if(!_delFile) return;
  try{
    await api('/api/file/delete',{method:'POST',body:JSON.stringify({session_id:S.session.session_id,path:relPath})});
    // Close preview if we just deleted the viewed file
    if($('previewPathText').textContent===relPath)$('btnClearPreview').onclick();
    await loadDir(S.currentDir);
  }catch(e){setStatus(t('delete_failed')+e.message);}
}

function _showFileContextMenu(event,item){
  const menu=document.createElement('div');
  menu.className='file-context-menu';
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
    document.body.removeChild(menu);
    _startRenameFile(item);
  };
  menu.appendChild(renameOpt);

  // Delete option
  const deleteOpt=document.createElement('div');
  deleteOpt.style.cssText='padding:8px 14px;font-size:12px;color:#f87171;cursor:pointer;transition:background .12s;text-transform:lowercase;border-top:1px solid rgba(255,255,255,0.05);';
  deleteOpt.textContent='delete';
  deleteOpt.onmouseover=()=>deleteOpt.style.background='rgba(248,113,113,.08)';
  deleteOpt.onmouseout=()=>deleteOpt.style.background='';
  deleteOpt.onclick=()=>{
    document.body.removeChild(menu);
    deleteWorkspaceFile(item.path,item.name);
  };
  menu.appendChild(deleteOpt);

  document.body.appendChild(menu);

  const closeMenu=()=>{if(menu.parentNode) document.body.removeChild(menu);};
  const handleClickOutside=(e)=>{if(!menu.contains(e.target)) closeMenu(); document.removeEventListener('click',handleClickOutside);};
  setTimeout(()=>document.addEventListener('click',handleClickOutside),10);
}

async function _startRenameFile(item){
  // Find the file item element
  const fileItems=document.querySelectorAll('.file-item');
  let el=null;
  for(const fi of fileItems){
    const nameEl=fi.querySelector('.file-name');
    if(nameEl&&nameEl.textContent===item.name){
      el=fi;
      break;
    }
  }
  if(!el)return;

  const nameEl=el.querySelector('.file-name');
  if(!nameEl)return;

  const inp=document.createElement('input');
  inp.className='file-rename-input';
  inp.value=item.name;
  inp.onclick=(e2)=>e2.stopPropagation();

  const finish=async(save)=>{
    inp.onblur=null;
    if(save){
      const newName=inp.value.trim();
      if(newName&&newName!==item.name){
        try{
          await api('/api/file/rename',{method:'POST',body:JSON.stringify({
            session_id:S.session.session_id,path:item.path,new_name:newName
          })});
          delete S._dirCache[S.currentDir];
          await loadDir(S.currentDir);
        }catch(err){showToast(t('rename_failed')+err.message);}
      }
    }
    inp.replaceWith(nameEl);
  };

  inp.onkeydown=(e2)=>{
    if(e2.key==='Enter'){
      if(e2.isComposing)return;
      e2.preventDefault();
      finish(true);
    }
    if(e2.key==='Escape'){e2.preventDefault();finish(false);}
  };
  inp.onblur=()=>finish(false);

  nameEl.replaceWith(inp);
  setTimeout(()=>{inp.focus();inp.select();},10);
}

async function promptNewFile(){
  if(!S.session)return;
  const name=await showPromptDialog({title:t('new_file_prompt'),placeholder:'filename.txt',confirmLabel:t('create')});
  if(!name||!name.trim())return;
  const relPath=S.currentDir==='.'?name.trim():(S.currentDir+'/'+name.trim());
  try{
    await api('/api/file/create',{method:'POST',body:JSON.stringify({session_id:S.session.session_id,path:relPath,content:''})});
    await loadDir(S.currentDir);
    openFile(relPath);
  }catch(e){setStatus(t('create_failed')+e.message);}
}

async function promptNewFolder(){
  if(!S.session)return;
  const name=await showPromptDialog({title:t('new_folder_prompt'),placeholder:'folder-name',confirmLabel:t('create')});
  if(!name||!name.trim())return;
  const relPath=S.currentDir==='.'?name.trim():(S.currentDir+'/'+name.trim());
  try{
    await api('/api/file/create-dir',{method:'POST',body:JSON.stringify({session_id:S.session.session_id,path:relPath})});
    await loadDir(S.currentDir);
  }catch(e){setStatus(t('folder_create_failed')+e.message);}
}

function renderTray(){
  const tray=$('attachTray');tray.innerHTML='';
  if(!S.pendingFiles.length){tray.classList.remove('has-files');updateSendBtn();return;}
  tray.classList.add('has-files');
  updateSendBtn();
  S.pendingFiles.forEach((f,i)=>{
    const chip=document.createElement('div');chip.className='attach-chip';
    chip.innerHTML=`${li('paperclip',12)} ${esc(f.name)} <button title="${t('remove_title')}">${li('x',12)}</button>`;
    chip.querySelector('button').onclick=()=>{S.pendingFiles.splice(i,1);renderTray();};
    tray.appendChild(chip);
  });
}
function addFiles(files){for(const f of files){if(!S.pendingFiles.find(p=>p.name===f.name))S.pendingFiles.push(f);}renderTray();}

async function uploadPendingFiles(){
  if(!S.pendingFiles.length||!S.session)return[];
  const names=[];let failures=0;
  const bar=$('uploadBar');const barWrap=$('uploadBarWrap');
  barWrap.classList.add('active');bar.style.width='0%';
  const total=S.pendingFiles.length;
  for(let i=0;i<total;i++){
    const f=S.pendingFiles[i];const fd=new FormData();
    fd.append('session_id',S.session.session_id);fd.append('file',f,f.name);
    try{
      const res=await fetch(new URL('api/upload', window.HERMES_API_BASE || location.href).href,{method:'POST',credentials:'include',body:fd});
      if(!res.ok){const err=await res.text();throw new Error(err);}
      const data=await res.json();
      if(data.error)throw new Error(data.error);
      names.push(data.filename);
    }catch(e){failures++;setStatus(`\u274c ${t('upload_failed')}${f.name} \u2014 ${e.message}`);}
    bar.style.width=`${Math.round((i+1)/total*100)}%`;
  }
  barWrap.classList.remove('active');bar.style.width='0%';
  S.pendingFiles=[];renderTray();
  if(failures===total&&total>0)throw new Error(t('all_uploads_failed',total));
  return names;
}
