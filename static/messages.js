async function send(){
  console.log('[send] Starting send...');
  const text=expandEmojiShortcodes($('msg').value).trim();
  if(!text&&!S.pendingFiles.length){console.log('[send] Nothing to send');return;}
  // Slash command intercept -- local commands handled without agent round-trip
  if(text.startsWith('/')&&!S.pendingFiles.length&&executeCommand(text)){
    $('msg').value='';autoResize();hideCmdDropdown();return;
  }
  // Don't send while an inline message edit is active
  if(document.querySelector('.msg-edit-area'))return;
  // If busy, queue the message instead of dropping it
  if(S.busy){
    if(text){
      if(!S.session){await newSession();await renderSessionList();}
      queueSessionMessage(S.session.session_id,{text,files:[...S.pendingFiles]});
      $('msg').value='';autoResize();
      S.pendingFiles=[];renderTray();
      updateQueueBadge(S.session.session_id);
    }
    return;
  }
  if(!S.session){await newSession();await renderSessionList();}

  const activeSid=S.session.session_id;

  // Pre-warm the multiplexed SSE connection so it's ready before the agent starts.
  // Without this, events emitted in the first few ms after chat/start are lost.
  let directStreamFallback = false;
  try{
    await SharedSSE.ensureConnection();
  }catch(e){
    console.warn('[SharedSSE] multiplex connection failed, falling back to direct stream', e);
    directStreamFallback = true;
  }

  setComposerStatus(S.pendingFiles&&S.pendingFiles.length?'Uploading…':'');
  let uploaded=[];
  try{uploaded=await uploadPendingFiles();}
  catch(e){if(!text){setComposerStatus(`Upload error: ${e.message}`);return;}}

  let msgText=text;
  if(uploaded.length&&!msgText)msgText=`I've uploaded ${uploaded.length} file(s): ${uploaded.join(', ')}`;
  else if(uploaded.length)msgText=`${text}\n\n[Attached files: ${uploaded.join(', ')}]`;
  if(!msgText){setComposerStatus('Nothing to send');return;}

  $('msg').value='';autoResize();
  const displayText=text||(uploaded.length?`Uploaded: ${uploaded.join(', ')}`:'(file upload)');
  const userMsg={role:'user',content:displayText,attachments:uploaded.length?uploaded:undefined,_ts:Date.now()/1000};
  S.toolCalls=[];  // clear tool calls from previous turn
  clearLiveToolCards();  // clear any leftover live cards from last turn
  S.messages.push(userMsg);renderMessages();appendThinking();setBusy(true);if(typeof _startComposerElapsedTimer==='function')_startComposerElapsedTimer();
  INFLIGHT[activeSid]={messages:[...S.messages],uploaded,toolCalls:[]};
  if(typeof saveInflightState==='function'){
    saveInflightState(activeSid,{streamId:null,messages:INFLIGHT[activeSid].messages,uploaded,toolCalls:[]});
  }
  startApprovalPolling(activeSid);
  startClarifyPolling(activeSid);
  startSudoPasswordPolling(activeSid);
  S.activeStreamId = null;  // will be set after stream starts

  // Set provisional title from user message immediately so session appears
  // in the sidebar right away with a meaningful name (server may refine later)
  if(S.session&&(S.session.title==='Untitled'||!S.session.title)){
    const provisionalTitle=displayText.slice(0,64);
    S.session.title=provisionalTitle;
    syncTopbar();
    // Persist it and refresh the sidebar now -- don't wait for done
    api('/api/session/rename',{method:'POST',body:JSON.stringify({
      session_id:activeSid, title:provisionalTitle
    })}).catch(()=>{});  // fire-and-forget, server refines on done
    renderSessionList();  // session appears in sidebar immediately
  } else {
    renderSessionList();  // ensure it's visible even if already titled
  }

  // Start the agent via POST, get a stream_id back
  let streamId;
  try{
    console.log('[send] Calling /api/chat/start...');
    const startData=await api('/api/chat/start',{method:'POST',body:JSON.stringify({
      session_id:activeSid,message:msgText,
      model:S.session.model||$('modelSelect').value,workspace:S.session.workspace,
      attachments:uploaded.length?uploaded:undefined
    })});
    streamId=startData.stream_id;
    console.log('[send] Got stream_id:', streamId);
    S.activeStreamId = streamId;
    markInflight(activeSid, streamId);
    if(typeof saveInflightState==='function'){
      saveInflightState(activeSid,{streamId,messages:INFLIGHT[activeSid].messages,uploaded,toolCalls:INFLIGHT[activeSid].toolCalls||[]});
    }
    // Show Cancel button
    const cancelBtn=$('btnCancel');
    if(cancelBtn) cancelBtn.style.display='inline-flex';
  }catch(e){
    const errMsg=String((e&&e.message)||'');
    const conflictActiveStream=/session already has an active stream/i.test(errMsg);
    if(conflictActiveStream){
      delete INFLIGHT[activeSid];
      if(typeof clearInflightState==='function') clearInflightState(activeSid);
      stopApprovalPolling();
      stopClarifyPolling();
      stopSudoPasswordPolling();
      // Keep the user's attempted turn by queueing it for after the current run.
      queueSessionMessage(activeSid,{text:msgText,files:[]});
      updateQueueBadge(activeSid);
      // Message queued - will be sent when current session finishes
      try{
        await loadSession(activeSid);
        setComposerStatus('');
        return;
      }catch(_){
        // Fall through to standard error handling if session reload fails.
      }
    }

    delete INFLIGHT[activeSid];
    stopApprovalPolling();
    stopClarifyPolling();
    stopSudoPasswordPolling();
    // Only hide approval card if it belongs to the session that just finished
    if(!_approvalSessionId || _approvalSessionId===activeSid) hideApprovalCard(true);removeThinking();removeLiveThinkingCard();
    if(!_clarifySessionId || _clarifySessionId===activeSid) hideClarifyCard(true);
    S.messages.push({role:'assistant',content:`**Error:** ${errMsg}`});
    renderMessages();setBusy(false);setComposerStatus(`Error: ${errMsg}`);updateSendBtn();
    return;
  }

  // Open SSE stream and render tokens live
  console.log('[send] Attaching live stream, direct fallback:', directStreamFallback);
  attachLiveStream(activeSid, streamId, uploaded, {direct: directStreamFallback});
  console.log('[send] Live stream attached');

}

// ── Shared Multiplexed SSE ─────────────────────────────────────────────────
// One EventSource carries events for ALL active streams, bypassing the
// browser's 6-connections-per-domain limit so you can run 20+ agents at once.
const SharedSSE = (function(){
  let source = null;
  const streams = new Map(); // streamId -> {sessionId, handlers}

  function getClientId(){
    let cid = null;
    try { cid = localStorage.getItem('hermes-multiplex-client-id'); } catch (e) {}
    if(!cid){
      cid = Math.random().toString(36).slice(2) + Date.now().toString(36);
      try { localStorage.setItem('hermes-multiplex-client-id', cid); } catch (e) {}
    }
    return cid;
  }

  let openPromise = null;
  let openPromiseResolve = null;
  let openPromiseReject = null;

  function connect(){
    if(source){
      try{ source.close(); }catch(_){}
    }
    const url = new URL('api/chat/stream/all', window.HERMES_API_BASE || location.href);
    url.searchParams.set('client_id', getClientId());
    source = new EventSource(url.href, {withCredentials: true});

    openPromise = new Promise((resolve, reject)=>{
      openPromiseResolve = resolve;
      openPromiseReject = reject;
    });

    source.onopen = () => {
      console.log('[SharedSSE] connected');
      if(openPromiseResolve){
        openPromiseResolve();
      }
      openPromise = null;
      openPromiseResolve = null;
      openPromiseReject = null;
      // After reconnect, any registered stream that finished while we were
      // disconnected may have lost its terminal events. Let each stream check.
      for(const [, stream] of streams){
        if(typeof stream.onReconnect === 'function'){
          try{ stream.onReconnect(); }catch(_){}
        }
      }
    };

    const eventTypes = ['token','reasoning','tool','tool_complete','approval','clarify','sudo_password','title','title_status','done','stream_end','compressed','apperror','warning'];
    for(const et of eventTypes){
      source.addEventListener(et, e => {
        try{
          const d = JSON.parse(e.data);
          const sid = d.stream_id;
          console.log('[SharedSSE] event:', et, 'stream_id:', sid, 'registered:', streams.has(sid));
          if(!sid) return;
          const stream = streams.get(sid);
          if(stream && stream.handlers[et]){
            stream.handlers[et](e);
          } else if(!stream) {
            console.warn('[SharedSSE] no stream registered for', sid);
          }
        }catch(err){
          console.error('[SharedSSE] dispatch error:', err);
        }
      });
    }

 // ── swarm broadcast events (no stream_id required) ────────────────────
 const swarmEvents=['swarm.started','swarm.worker_started','swarm.worker_completed','swarm.worker_error','swarm.completed','swarm.cancelled'];
 const swarmHandlerMap={
  'swarm.started':'onSwarmStarted',
  'swarm.worker_started':'onSwarmWorkerStarted',
  'swarm.worker_completed':'onSwarmWorkerCompleted',
  'swarm.worker_error':'onSwarmWorkerError',
  'swarm.completed':'onSwarmCompleted',
  'swarm.cancelled':'onSwarmCancelled',
 };
 for(const se of swarmEvents){
  source.addEventListener(se, e => {
   try{
    const d = JSON.parse(e.data);
    const handler = swarmHandlerMap[se];
    if(typeof SwarmUI!=='undefined' && SwarmUI[handler]){
     SwarmUI[handler](d);
    }
   }catch(err){
    console.error('[SharedSSE] swarm event error:', err);
   }
  });
 }

    source.addEventListener('error', e => {
      if(openPromiseReject){
        openPromiseReject(new Error('SSE connection failed'));
      }
      openPromise = null;
      openPromiseResolve = null;
      openPromiseReject = null;
      // Always schedule a manual reconnect. Relying solely on browser auto-reconnect
      // is unreliable in Firefox when the connection is interrupted during page load
      // or when the readyState stays CONNECTING and never resolves.
      const wasClosed = source && source.readyState === EventSource.CLOSED;
      console.log('[SharedSSE] connection error' + (wasClosed ? ' (closed)' : '') + ', reconnecting in 1s...');
      setTimeout(connect, 1000);
    });
  }

  function ensureConnection(){
    if(source && source.readyState === EventSource.OPEN){
      return Promise.resolve();
    }
    if(openPromise){
      return Promise.race([
        openPromise,
        new Promise((_, reject) => setTimeout(() => reject(new Error('SSE connection timeout')), 10000))
      ]);
    }
    connect();
    return Promise.race([
      openPromise || Promise.resolve(),
      new Promise((_, reject) => setTimeout(() => reject(new Error('SSE connection timeout')), 3000))
    ]);
  }

  return {
    register(streamId, sessionId, handlers, onReconnect){
      ensureConnection();
      streams.set(streamId, {sessionId, handlers, onReconnect});
    },
    unregister(streamId){
      streams.delete(streamId);
      // Keep source open so the next stream's events arrive without a reconnect race.
      // The connection closes naturally on page unload.
    },
    hasStream(streamId){
      return streams.has(streamId);
    },
    ensureConnection(){
      return ensureConnection();
    },
  };
})();

const LIVE_STREAMS={}; // sessionId -> streamId

// ── Initialize swarm UI ──────────────────────────────────────────────────
if(typeof SwarmUI!=='undefined'&&typeof SwarmUI.init==='function'){SwarmUI.init();}

function closeLiveStream(sessionId, streamId){
  const sid=LIVE_STREAMS[sessionId];
  if(!sid) return;
  if(streamId&&sid!==streamId) return;
  SharedSSE.unregister(sid);
  delete LIVE_STREAMS[sessionId];
}

function attachLiveStream(activeSid, streamId, uploaded=[], options={}){
  if(!activeSid||!streamId) return;
  const reconnecting=!!options.reconnecting;
  closeLiveStream(activeSid);
  if(!INFLIGHT[activeSid]) INFLIGHT[activeSid]={messages:[...S.messages],uploaded:[...uploaded],toolCalls:[]};
  else {
    if(uploaded.length) INFLIGHT[activeSid].uploaded=[...uploaded];
    if(!Array.isArray(INFLIGHT[activeSid].toolCalls)) INFLIGHT[activeSid].toolCalls=[];
  }

  let assistantText='';
  let reasoningText='';
  let _xmlToolCalls=[];
  let directSource = null;
  // ── Restore accumulated text on reconnect ─────────────────────────────────
  // When reloading mid-stream, the INFLIGHT state has the partial assistant
  // message. Restore it so we don't lose already-streamed content.
  if(reconnecting && INFLIGHT[activeSid] && Array.isArray(INFLIGHT[activeSid].messages)){
    for(let i=INFLIGHT[activeSid].messages.length-1;i>=0;i--){
      const msg=INFLIGHT[activeSid].messages[i];
      if(msg && msg.role==='assistant'){
        if(msg.content) assistantText=msg.content;
        if(msg.reasoning) reasoningText=msg.reasoning;
        break;
      }
    }
    // Also restore from INFLIGHT uploaded if we couldn't find it in messages
    if(!assistantText && INFLIGHT[activeSid].assistantText){
      assistantText = INFLIGHT[activeSid].assistantText;
    }
    if(!reasoningText && INFLIGHT[activeSid].reasoningText){
      reasoningText = INFLIGHT[activeSid].reasoningText;
    }
  }
  // ───────────────────────────────────────────────────────────────────────────
  let assistantRow=null;
  let assistantBody=null;
  let _liveThinkingCard=null;
  // Thinking tag patterns for streaming display
  const _thinkPairs=[
    {open:'<think>',close:'</think>'},
    {open:'<thinking>',close:'</thinking>'},
    {open:'<reasoning>',close:'</reasoning>'},
    {open:'<|channel>thought\n',close:'<channel|>'},
    // Kimi K2 tool call format — hide raw tool call XML from visible stream
    {open:'<|tool_call_section_begin|>',close:'<|tool_call_section_end|>'},
    {open:'<|tool_calls_section_begin|>',close:'<|tool_calls_section_end|>'},
    {open:'<|tool_call_begin|>',close:'<|tool_call_end|>'},
    {open:'<tool>',close:'</tool>'},
    // DeepSeek V3 / V3.1
    {open:'<｜tool▁calls▁begin｜>',close:'<｜tool▁calls▁end｜>'},
    {open:'<｜tool▁call▁begin｜>',close:'<｜tool▁call▁end｜>'},
    // Hermes / Qwen / GLM
    {open:'<tool_call>',close:'</tool_call>'},
    {open:'<|python_tag|>',close:'<|python_tag|>'},
    // Mistral
    {open:'[TOOL_CALLS]',close:'[TOOL_CALLS]'},
    // NVIDIA NIM / OpenAI-style function calls in content
    {open:'<function_calls>',close:'</function_calls>'},
    {open:'<function>',close:'</function>'},
    {open:'<functions>',close:'</functions>'},
    {open:'<invoke>',close:'</invoke>'},
    {open:'<tool_calls>',close:'</tool_calls>'},
    // JSON array/object markers for tool calls (common in NIM models)
    {open:'[{"name":',close:']',jsonBlock:true},
    {open:'{"name":',close:'}',jsonBlock:true,matchBrace:true},
    // NVIDIA NIM custom markers
    {open:'<tool_call_end>',close:''},
    {open:'<tool_calls_section_end>',close:''},
    {open:'<tool_calls_section_begin>',close:''},
    {open:'<tool_call_begin|>',close:''},
    // NVIDIA NIM format with "parameters" field
    {open:'{"name":',close:'"parameters":',jsonBlock:true},
  ];

  function _isActiveSession(){
    return !!(S.session&&S.session.session_id===activeSid);
  }
  function persistInflightState(){
    const inflight=INFLIGHT[activeSid];
    if(!inflight||typeof saveInflightState!=='function') return;
    saveInflightState(activeSid,{
      streamId,
      messages:inflight.messages||[],
      uploaded:inflight.uploaded||[...uploaded],
      toolCalls:inflight.toolCalls||[],
    });
  }
  function _closeSource(){
    if(directSource){
      try{ directSource.close(); }catch(_){ }
      directSource = null;
    }
    closeLiveStream(activeSid, streamId);
  }
  function syncInflightAssistantMessage(){
    const inflight=INFLIGHT[activeSid];
    if(!inflight) return;
    if(!Array.isArray(inflight.messages)) inflight.messages=[];
    let assistantIdx=-1;
    for(let i=inflight.messages.length-1;i>=0;i--){
      const msg=inflight.messages[i];
      if(msg&&msg.role==='assistant'&&msg._live){assistantIdx=i;break;}
    }
    const ts=Date.now()/1000;
    if(assistantIdx>=0){
      inflight.messages[assistantIdx].content=assistantText;
      inflight.messages[assistantIdx].reasoning=reasoningText||undefined;
      inflight.messages[assistantIdx]._ts=inflight.messages[assistantIdx]._ts||ts;
    }else{
      inflight.messages.push({role:'assistant',content:assistantText,reasoning:reasoningText||undefined,_live:true,_ts:ts});
    }
    // Also save raw text for additional recovery safety
    inflight.assistantText = assistantText;
    inflight.reasoningText = reasoningText;
    persistInflightState();
  }
  function ensureAssistantRow(){
    if(!_isActiveSession()) return;
    if(assistantRow&&!assistantRow.isConnected){assistantRow=null;assistantBody=null;}
    if(!assistantRow){
      const existing=$('msgInner').querySelector('.msg-row[data-live-assistant="1"]');
      if(existing){
        assistantRow=existing;
        assistantBody=existing.querySelector('.msg-body');
      }
    }
    if(assistantRow){
      if(typeof placeLiveToolCardsHost==='function') placeLiveToolCardsHost();
      return;
    }

    // Don't remove thinking indicator yet - it should stay visible until actual content arrives
    // removeThinking();
    const tr=$('toolRunningRow');if(tr)tr.remove();
    $('emptyState').style.display='none';
    assistantRow=document.createElement('div');assistantRow.className='msg-row';
    assistantBody=document.createElement('div');assistantBody.className='msg-body';
    const role=document.createElement('div');role.className='msg-role assistant';
    const _bn=window._botName||'Hermes';
    const icon=document.createElement('div');icon.className='role-icon assistant';
    // Use hermes.png as avatar with circle cutout
    icon.innerHTML='<img src="/static/hermes.png" style="width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;" alt="'+_bn+'">';
    const lbl=document.createElement('span');lbl.style.fontSize='12px';lbl.textContent=_bn;
    role.appendChild(icon);role.appendChild(lbl);
    assistantRow.appendChild(role);assistantRow.appendChild(assistantBody);
    // Insert before thinking row to ensure loading dots appear below the message
    const thinkingRow=$('thinkingRow');
    if(thinkingRow){
      $('msgInner').insertBefore(assistantRow, thinkingRow);
    }else{
      $('msgInner').appendChild(assistantRow);
    }
  }

  // ── Shared SSE handler wiring (used for initial connection and reconnect) ──
  let _reconnectAttempted=false;
  let _terminalStateReached=false;

  // rAF-throttled rendering: buffer tokens, render at most once per frame
  let _renderPending=false;
  // Extract display text from assistantText, stripping completed thinking blocks
  // and hiding content still inside an open thinking block.
  function _streamDisplay(){
    let text=assistantText;
    // Heuristic: if structured reasoning events delivered the same text that
    // the provider also sent inside regular tokens (without tags), hide the
    // duplicate from the visible stream. Check exact match first, then prefix.
    // Case-insensitive to handle models that vary casing (e.g. uppercase SQL
    // keywords in reasoning, lowercase in content).
    if(reasoningText&&text){
      const tTrim=text.trim();
      const rTrim=reasoningText.trim();
      // Exact match — hide everything
      if(tTrim.toLowerCase()===rTrim.toLowerCase()){
        return '';
      }
      // Prefix match — strip the matching prefix
      const tStart=text.trimStart().toLowerCase();
      const rStart=reasoningText.trim().toLowerCase();
      let matchLen=0;
      for(let i=Math.min(tStart.length,rStart.length);i>20;i--){
        if(tStart.slice(0,i)===rStart.slice(0,i)){
          matchLen=i;
          break;
        }
      }
      if(matchLen>20){
        const leading=text.length-text.trimStart().length;
        text=text.slice(0,leading)+text.slice(leading+matchLen).replace(/^\s+/,'');
      }
    }
    // Always strip inline thinking tags from the visible stream, even when
    // reasoning is arriving via structured SSE events. Some providers emit
    // reasoning both through a dedicated API field AND as inline <think>
    // tags inside regular tokens (or the tags get split across chunks and
    // missed by the server-side extractor). Without this, raw <think> tags
    // leak into the chat bubble.
    for(const {open,close} of _thinkPairs){
      // Strip all complete thinking blocks anywhere in the text.
      let idx;
      while((idx=text.indexOf(open))!==-1){
        const closeIdx=text.indexOf(close,idx+open.length);
        if(closeIdx!==-1){
          text=text.slice(0,idx)+text.slice(closeIdx+close.length);
        }else{
          // Unclosed block — truncate from the open tag onward.
          text=text.slice(0,idx);
          break;
        }
      }
      // Hide partial open-tag suffixes at the end of the text so users don't
      // see `<thi`, `<think`, etc. while the tag is still being streamed.
      for(let i=open.length-1;i>0;i--){
        if(text.endsWith(open.slice(0,i))){
          text=text.slice(0,-i);
          break;
        }
      }
    }
    // Strip any orphan tool-call tags that remain after pair stripping.
    // This handles fragmented output (e.g. a turn that resumes mid-tool-call
    // or close tags without their matching open tags).
    const _toolOrphans=[
      '</tool>','</tool_call>','<|tool_call_section_end|>',
      '</tool>','<|tool_call_argument_end|>',
      '<｜tool▁call▁end｜>','<｜tool▁calls▁end｜>','<｜tool▁sep｜>',
      '</tool_call>','<|python_tag|>','[TOOL_CALLS]',
      '</function_calls>','</function>','</functions>','</invoke>','</tool_calls>',
      '<tool_call_end>','<tool_calls_section_end>','<tool_calls_section_begin>',
      '<tool_call_begin|>','<|tool_call_section_begin|>',
    ];
    for(const tag of _toolOrphans){
      let idx;
      while((idx=text.indexOf(tag))!==-1){
        text=text.slice(0,idx)+text.slice(idx+tag.length);
      }
    }
    // Strip JSON tool call fragments that might remain
    // Match patterns like {"name": "...", "arguments": {...}} or [{"name": ...}]
    text=text.replace(/\{[^{}]*"name"\s*:\s*"[^"]+"[^{}]*\}/g,'');
    text=text.replace(/\[\s*\{[^{}]*"name"\s*:\s*"[^"]+"[^\]]*\}\s*\]/g,'');
    // Match NVIDIA NIM format with "parameters" field: {"name": "...", "parameters": {...}}
    text=text.replace(/\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^\}]*\}[^\}]*\}/g,'');
    // Match partial JSON fragments like ,"id":"skills_list:1"}
    text=text.replace(/,\s*"id"\s*:\s*"[^"]+"\s*\}/g,'');
    // Strip NVIDIA NIM <tool_call> blocks explicitly (some NIM endpoints emit
    // tool calls as raw XML in content in addition to structured tool_calls).
    text=text.replace(/<tool_call>[\s\S]*?<\/tool_call>/gi,'');
    // Also strip orphaned inner arg_key/arg_value pairs that sometimes remain
    // when the outer <tool_call> wrapper was fragmented across chunks.
    text=text.replace(/<arg_key>[\s\S]*?<\/arg_key>\s*<arg_value>[\s\S]*?<\/arg_value>/gi,'');
    text=text.replace(/<arg_key>[\s\S]*?<\/arg_key>/gi,'');
    text=text.replace(/<arg_value>[\s\S]*?<\/arg_value>/gi,'');
    // Strip DeepSeek/NVIDIA hallucinated custom markup (e.g. < | dsml | tool_calls>)
    text=text.replace(/<\s*\|\s*dsml\s*\|\s*tool_calls\s*>[\s\S]*?<\s*\/\s*\|\s*dsml\s*\|\s*tool_calls\s*>/gi,'');
    text=text.replace(/<\s*\|\s*DSML\s*\|\s*tool_calls\s*>[\s\S]*?<\s*\/\s*\|\s*DSML\s*\|\s*tool_calls\s*>/gi,'');
    text=text.replace(/<\s*\|\s*dsml\s*\|\s*tool_calls\s*>/gi,'');
    text=text.replace(/<\s*\|\s*DSML\s*\|\s*tool_calls\s*>/gi,'');
    text=text.replace(/<\s*\/\s*\|\s*dsml\s*\|\s*tool_calls\s*>/gi,'');
    text=text.replace(/<\s*\/\s*\|\s*DSML\s*\|\s*tool_calls\s*>/gi,'');
    // Strip pipe-delimited tool metadata fragments (ToolPill, tool-result, etc.)
    text=text.replace(/\w*\|ToolPill\|[^\s|]*/gi,'');
    text=text.replace(/\w*\|toolpill\|[^\s|]*/gi,'');
    text=text.replace(/tool-result\|ToolResult\|tool_result[^\n]*/gi,'');
    // Strip GLM inline tool call text (Tool name key=val...)
    text=text.replace(/Tool '\w+'.*$/gm,'');
    // Strip does not exist / Available tools error text from GLM models
    text=text.replace(/does not exist.*Available tools:.*$/gm,'');
    // Strip XML pseudo-tool tags (e.g. <terminal>...</terminal>, <read_file>...</read_file>)
    // that models emit as raw text instead of structured tool_calls.
    const xmlRegex=/<([a-zA-Z_][a-zA-Z0-9_\-]*)[^>]*>([\s\S]*?)<\/\1>/g;
    text=text.replace(xmlRegex,(full,tagName)=>_isXmlToolTag(tagName)?'':full);
    // Hide partial unclosed XML tool open tags at the end of the stream
    const xmlOpen=/<([a-zA-Z_][a-zA-Z0-9_\-]*)[^>]*>/g;
    let lastOpen=null,lastOpenMatch=null;
    let om;
    while((om=xmlOpen.exec(text))!==null){
      if(_isXmlToolTag(om[1])){lastOpen=om.index;lastOpenMatch=om;}
    }
    if(lastOpenMatch){
      const afterOpen=text.slice(lastOpenMatch.index+lastOpenMatch[0].length);
      if(!afterOpen.includes(`</${lastOpenMatch[1]}>`)){
        text=text.slice(0,lastOpenMatch.index);
      }
    }
    return text.trim();
  }
  function _parseStreamState(){
    const raw=assistantText;
    if(reasoningText){
      return {thinkingText:reasoningText, displayText:_streamDisplay(), inThinking:false};
    }
    // Find the last thinking block to determine if we're currently inside one.
    for(const {open,close} of _thinkPairs){
      const idx=raw.lastIndexOf(open);
      if(idx!==-1){
        const afterOpen=raw.slice(idx+open.length);
        const closeIdx=afterOpen.indexOf(close);
        if(closeIdx!==-1){
          // Complete block — _streamDisplay handles stripping all blocks.
          return {
            thinkingText:afterOpen.slice(0,closeIdx).trim(),
            displayText:_streamDisplay(),
            inThinking:false,
          };
        }
        // Unclosed block
        return {
          thinkingText:afterOpen.trim(),
          displayText:_streamDisplay(),
          inThinking:true,
        };
      }
      // Entire text is a prefix of the open tag (e.g. "<thi")
      if(raw && open.startsWith(raw)){
        return {thinkingText:'', displayText:'', inThinking:true};
      }
    }
    return {thinkingText:'', displayText:_streamDisplay(), inThinking:false};
  }
  function _renderLiveThinking(parsed){
    const text=(parsed&&parsed.thinkingText)||'';
    if(text||(parsed&&parsed.inThinking)){
      if(typeof updateThinking==='function') updateThinking(text||'Thinking…');
      else appendThinking();
    }
    // Note: Don't remove thinking indicator here - let terminal handlers
    // (done, apperror, cancel, _handleStreamError) remove it when stream ends.
    // This keeps the indicator visible throughout the entire streaming process.
  }
  function _renderXmlToolCards(){
    // Parse complete XML tool tags from the raw stream and render them as
    // collapsible cards in #liveToolCards, mirroring structured tool events.
    const {toolCalls}=extractXmlToolCalls(assistantText);
    // Only keep cards that aren't already rendered (dedupe by tid)
    const container=$('liveToolCards');
    if(!container) return;
    const existingTids=new Set(Array.from(container.querySelectorAll('[data-tid]')).map(el=>el.dataset.tid));
    for(const tc of toolCalls){
      if(!existingTids.has(tc.tid)){
        appendLiveToolCard(tc);
        _xmlToolCalls.push(tc);
      }
    }
  }
  function ensureLiveThinkingCard(text){
    if(!assistantRow||!assistantRow.parentNode) return;
    if(!_liveThinkingCard||!_liveThinkingCard.isConnected){
      _liveThinkingCard=document.createElement('div');
      _liveThinkingCard.className='msg-row thinking-card-row';
      _liveThinkingCard.dataset.liveThinking='1';
      assistantRow.parentNode.insertBefore(_liveThinkingCard,assistantRow);
    }
    const _icon=(typeof li==='function')?li('lightbulb',14):'💡';
    const _chevron=(typeof li==='function')?li('chevron-right',12):'▶';
    const _label=(typeof t==='function')?t('thinking'):'Thinking';
    _liveThinkingCard.innerHTML='<div class="thinking-card"><div class="thinking-card-header" onclick="this.parentElement.classList.toggle(\'open\')"><span class="thinking-card-icon">'+_icon+'</span><span class="thinking-card-label">'+_label+'</span><span class="thinking-card-toggle">'+_chevron+'</span></div><div class="thinking-card-body"><pre>'+esc(text)+'</pre></div></div>';
  }
  function removeLiveThinkingCard(){
    if(_liveThinkingCard){if(_liveThinkingCard.isConnected)_liveThinkingCard.remove();_liveThinkingCard=null;}
  }

  function _scheduleRender(){
    if(_renderPending) return;
    _renderPending=true;
    requestAnimationFrame(()=>{
      _renderPending=false;
      const parsed=_parseStreamState();
      _renderLiveThinking(parsed);
      _renderXmlToolCards();
      if(assistantBody){
        if(parsed.displayText){
          assistantBody.innerHTML=renderMd(parsed.displayText);
        }else if(assistantText.trim()){
          // Tokens are arriving but being stripped (tool calls, thinking tags, etc.).
          // Show a subtle working indicator so the stream doesn't appear frozen.
          const _hasToolPatterns=/<\|?tool|tool_call|function_call|<functions>|<invoke|\{"name"|\{"name"[^}]*"parameters"|\|ToolPill\||\|toolpill\||tool-result\|ToolResult|<\s*\|\s*[dD][sS][mM][lL]\s*\|\s*tool_calls|tool_call_end|tool_calls_section_end/i.test(assistantText);
          assistantBody.innerHTML=_hasToolPatterns
            ?'<span style="opacity:.6;font-style:italic;">working on tools…</span>'
            :'';
        }else{
          assistantBody.innerHTML='';
        }
      }
      // Render reasoning in a live clickable thinking card instead of inline
      if(parsed.thinkingText){
        ensureLiveThinkingCard(parsed.thinkingText);
      }else{
        removeLiveThinkingCard();
      }
      scrollIfPinned();
    });
  }

  function _wireSSE(source){
    const handlers={};
    handlers['token']=e=>{
      if(_terminalStateReached) return;
      if(!S.session||S.session.session_id!==activeSid) return;
      const d=JSON.parse(e.data);
      if(d.text) console.log('[SSE] token:', d.text.slice(0,80));
      assistantText+=d.text;
      syncInflightAssistantMessage();
      if(!S.session||S.session.session_id!==activeSid) return;

      ensureAssistantRow();
      _scheduleRender();
    };

    // Track inline tool call previews separately from thinking
    let _inlineToolPreviews=[];

    handlers['reasoning']=e=>{
      if(_terminalStateReached) return;
      const d=JSON.parse(e.data);
      const text=d.text||'';
      if(text) console.log('[SSE] reasoning:', text.slice(0,80));
      // Check if this is a tool call preview (from inline tool extraction)
      if(text.startsWith('[Tool Call Preview]')){
        // Extract the tool call content
        const previewContent=text.replace('[Tool Call Preview]','').trim();
        _inlineToolPreviews.push({
          name:'tool_call_preview',
          preview:previewContent.substring(0,200),
          fullContent:previewContent,
          timestamp:Date.now()
        });
        // Don't add to reasoningText - we'll display as tool card
        syncInflightAssistantMessage();
        if(!S.session||S.session.session_id!==activeSid) return;
        // Render inline tool previews as tool cards
        _renderInlineToolPreviews();
        return;
      }
      reasoningText += text;
      syncInflightAssistantMessage();
      if(!S.session||S.session.session_id!==activeSid) return;
      ensureAssistantRow();
      _scheduleRender();
    };

    function _renderInlineToolPreviews(){
      if(!assistantRow||!_isActiveSession()) return;
      // Create or get the inline tool previews container
      let container=$('inlineToolPreviews');
      if(!container){
        container=document.createElement('div');
        container.id='inlineToolPreviews';
        container.className='inline-tool-previews';
        assistantRow.insertBefore(container,assistantBody.nextSibling);
      }
      // Build tool cards for each preview
      container.innerHTML=_inlineToolPreviews.map((tc,i)=>`
        <div class="tool-card inline-tool-preview collapsed" data-idx="${i}">
          <div class="tool-card-header" onclick="this.parentElement.classList.toggle('collapsed');this.parentElement.classList.toggle('expanded')">
            <span class="tool-card-icon">🔧</span>
            <span class="tool-card-name">Tool Call Preview</span>
            <span class="tool-card-preview">${esc(tc.preview)}</span>
            <span class="tool-card-toggle">▸</span>
          </div>
          <div class="tool-card-detail">
            <pre class="tool-call-preview-content">${esc(tc.fullContent)}</pre>
          </div>
        </div>
      `).join('');
    }

    handlers['tool']=e=>{
      console.log('[SSE] tool event', e.data?.slice(0,200));
      const d=JSON.parse(e.data);
      if(d.name==='clarify') return;
      const tc={name:d.name, preview:d.preview||'', args:d.args||{}, snippet:'', done:false, tid:d.tid||`live-${Date.now()}-${Math.random().toString(36).slice(2,8)}`};
      const inflight = INFLIGHT[activeSid] || (INFLIGHT[activeSid] = {
        messages:[...S.messages],
        uploaded:[],
        toolCalls:[]
      });
      if(!Array.isArray(inflight.toolCalls)) inflight.toolCalls=[];
      INFLIGHT[activeSid].toolCalls.push(tc);
      S.toolCalls=INFLIGHT[activeSid].toolCalls;
      persistInflightState();

      if(!S.session||S.session.session_id!==activeSid) return;
      removeThinking();removeLiveThinkingCard();
      const oldRow=$('toolRunningRow');if(oldRow)oldRow.remove();
      appendLiveToolCard(tc);
      scrollIfPinned();
    };

    handlers['tool_complete']=e=>{
      const d=JSON.parse(e.data);
      if(d.name==='clarify') return;
      const inflight=INFLIGHT[activeSid];
      if(!inflight) return;
      if(!Array.isArray(inflight.toolCalls)) inflight.toolCalls=[];
      let tc=null;
      for(let i=inflight.toolCalls.length-1;i>=0;i--){
        const cur=inflight.toolCalls[i];
        if(cur&&cur.done===false&&(!d.name||cur.name===d.name)){
          tc=cur;
          break;
        }
      }
      if(!tc){
        tc={name:d.name||'tool', preview:d.preview||'', args:d.args||{}, snippet:'', done:true};
        inflight.toolCalls.push(tc);
      }
      tc.preview=d.preview||tc.preview||'';
      tc.args=d.args||tc.args||{};
      tc.done=true;
      tc.is_error=!!d.is_error;
      if(d.duration!==undefined) tc.duration=d.duration;
      S.toolCalls=inflight.toolCalls;
      persistInflightState();
      if(!S.session||S.session.session_id!==activeSid) return;
      appendLiveToolCard(tc);
      scrollIfPinned();

      // Check for steering message to send after this tool completes
      const steeringMsg = typeof window._popSteeringMessage === 'function' ? window._popSteeringMessage() : null;
      if(steeringMsg){
        // Send the steering message as a user follow-up
        setTimeout(()=>{
          if(S.session && S.session.session_id === activeSid && S.busy){
            $('msg').value = steeringMsg;
            send();
          }
        }, 100);
      }
    };

    handlers['approval']=e=>{
      const d=JSON.parse(e.data);
      d._session_id=activeSid;
      // Auto-approve with "always" choice to skip the popup
      api("/api/approval/respond", {
        method: "POST",
        body: JSON.stringify({ session_id: activeSid, choice: "always", approval_id: d.approval_id || "" })
      }).catch(err => {
        // Fallback to showing popup if auto-approve fails
        showApprovalCard(d, 1);
        playNotificationSound();
        sendDesktopNotification('Approval required',d.description||'Tool approval needed');
      });
    };

    handlers['clarify']=e=>{
      const d=JSON.parse(e.data);
      d._session_id=activeSid;
      showClarifyCard(d);
      playNotificationSound();
      sendDesktopNotification('Clarification needed',d.question||'Tool clarification needed');
    };

    handlers['sudo_password']=e=>{
      const d=JSON.parse(e.data);
      d._session_id=activeSid;
      // Check if we have a cached password to auto-submit
      const cachedPassword = _getCachedSudoPassword();
      if (cachedPassword) {
        _sudoPasswordSessionId = activeSid;
        respondSudoPassword('submit', cachedPassword);
      } else {
        showSudoPasswordCard(d);
        playNotificationSound();
        sendDesktopNotification('Sudo password required','A command needs sudo privileges');
      }
    };

    handlers['title']=e=>{
      let d={};
      try{ d=JSON.parse(e.data||'{}'); }catch(_){}
      if((d.session_id||activeSid)!==activeSid) return;
      const newTitle=String(d.title||'').trim();
      if(!newTitle) return;
      if(S.session&&S.session.session_id===activeSid){
        S.session.title=newTitle;
        syncTopbar();
      }
      if(typeof _allSessions!=='undefined'&&Array.isArray(_allSessions)){
        const row=_allSessions.find(s=>s&&s.session_id===activeSid);
        if(row) row.title=newTitle;
      }
      if(typeof renderSessionListFromCache==='function') renderSessionListFromCache();
      else if(typeof renderSessionList==='function') renderSessionList();
    };

    handlers['title_status']=e=>{
      let d={};
      try{ d=JSON.parse(e.data||'{}'); }catch(_){}
      if((d.session_id||activeSid)!==activeSid) return;
      try{
        console.info('[title]', {
          status:String(d.status||''),
          reason:String(d.reason||''),
          title:String(d.title||''),
          raw_preview:String(d.raw_preview||''),
          session_id:String(d.session_id||activeSid)
        });
      }catch(_){}
    };

    handlers['done']=e=>{
      console.log('[SSE] received DONE event', e.data?.slice(0,200));
      _terminalStateReached=true;
      const d=JSON.parse(e.data);
      let finalAssistantText='';
      delete INFLIGHT[activeSid];
      clearInflight();clearInflightState(activeSid);
      stopApprovalPolling();
      stopClarifyPolling();
      stopSudoPasswordPolling();
      if(!_approvalSessionId || _approvalSessionId===activeSid) hideApprovalCard(true);
      if(!_clarifySessionId || _clarifySessionId===activeSid) hideClarifyCard(true);
      if(!_sudoPasswordVisible) hideSudoPasswordCard(true);
      if(S.session&&S.session.session_id===activeSid){
        S.activeStreamId=null;
        const _cb=$('btnCancel');if(_cb)_cb.style.display='none';
      }
      if(S.session&&S.session.session_id===activeSid){
        S.session=d.session;S.messages=d.session.messages||[];
        // Find the last assistant message once for both reasoning persistence and timestamp
        const lastAsst=[...S.messages].reverse().find(m=>m.role==='assistant');
        // Persist reasoning trace so thinking card survives page reload
        if(reasoningText&&lastAsst&&!lastAsst.reasoning) lastAsst.reasoning=reasoningText;
        // Stamp _ts on the last assistant message if it has no timestamp
        if(lastAsst&&!lastAsst._ts&&!lastAsst.timestamp) lastAsst._ts=Date.now()/1000;
        if(d.usage){S.lastUsage=d.usage;_syncCtxIndicator(d.usage);}
        if(d.session.tool_calls&&d.session.tool_calls.length){
          S.toolCalls=d.session.tool_calls.map(tc=>({...tc,done:true}));
        } else {
          S.toolCalls=S.toolCalls.map(tc=>({...tc,done:true}));
        }
        if(uploaded.length){
          const lastUser=[...S.messages].reverse().find(m=>m.role==='user');
          if(lastUser)lastUser.attachments=uploaded;
        }
        clearLiveToolCards();
        S.busy=false;
        // Save final text before clearing, for notification and no-reply check
        finalAssistantText=assistantText;
        // Clear reasoningText and assistantText BEFORE rendering to prevent pending rAF callback from re-adding thinking indicator
        reasoningText='';
        assistantText='';
        _inlineToolPreviews=[]; // Clear inline tool previews
        const _inlineContainer=$('inlineToolPreviews');if(_inlineContainer)_inlineContainer.remove();
        // No-reply guard (#373): if agent returned nothing, show inline error
        const _asstMsgs=S.messages.filter(m=>m.role==='assistant');
        console.log('[done] assistant messages:', _asstMsgs.length, 'finalAssistantText:', JSON.stringify(finalAssistantText), 'content samples:', _asstMsgs.slice(-2).map(m=>JSON.stringify(m.content).slice(0,100)));
        if(!S.messages.some(m=>m.role==='assistant'&&String(m.content||'').trim())&&!finalAssistantText.trim()){removeThinking();removeLiveThinkingCard();S.messages.push({role:'assistant',content:'**No response received.** Check your API key and model selection.'});}
        else{removeThinking();removeLiveThinkingCard();} // Remove live thinking before rendering message with its thinking card
        syncTopbar();renderMessages();loadDir('.');
      }
      renderSessionList();setBusy(false);setStatus('');
      setComposerStatus('');
      updateSendBtn();
      // Skip notifications for cron job sessions
      const cronPatterns = ['cron_', 'session_cron', 'sessions_cron'];
      const isCronSession = cronPatterns.some(p => (activeSid || '').toLowerCase().startsWith(p));
      if (!isCronSession) {
        playNotificationSound();
        sendDesktopNotification('Response complete',finalAssistantText?finalAssistantText.slice(0,100):'Task finished');
      }
    };

    handlers['stream_end']=e=>{
      console.log('[SSE] stream_end event');
      _terminalStateReached=true;
      try{
        const d=JSON.parse(e.data||'{}');
        if((d.session_id||activeSid)!==activeSid) return;
      }catch(_){}
      _closeSource();
    };

    handlers['compressed']=e=>{
      // Context was auto-compressed during this turn -- show a system message
      if(!S.session||S.session.session_id!==activeSid) return;
      try{
        const d=JSON.parse(e.data);
        const sysMsg={role:'assistant',content:'*[Context was auto-compressed to continue the conversation]*'};
        S.messages.push(sysMsg);
        // Context was auto-compressed to continue the conversation
      }catch(err){}
    };

    handlers['apperror']=e=>{
      console.log('[SSE] apperror event', e.data?.slice(0,200));
      _terminalStateReached=true;
      // Application-level error sent explicitly by the server (rate limit, crash, etc.)
      // This is distinct from the SSE network 'error' event below.
      _closeSource();
      delete INFLIGHT[activeSid];clearInflight();clearInflightState(activeSid);stopApprovalPolling();stopClarifyPolling();stopSudoPasswordPolling();
      if(!_approvalSessionId||_approvalSessionId===activeSid) hideApprovalCard(true);
      if(!_clarifySessionId||_clarifySessionId===activeSid) hideClarifyCard(true);
      if(!_sudoPasswordVisible) hideSudoPasswordCard(true);
      if(S.session&&S.session.session_id===activeSid){
        S.activeStreamId=null;const _cbe=$('btnCancel');if(_cbe)_cbe.style.display='none';
        clearLiveToolCards();reasoningText='';assistantText='';_inlineToolPreviews=[];removeThinking();removeLiveThinkingCard();
        const _inlineContainer=$('inlineToolPreviews');if(_inlineContainer)_inlineContainer.remove();
        try{
          const d=JSON.parse(e.data);
          const isRateLimit=d.type==='rate_limit';
          const isAuthMismatch=d.type==='auth_mismatch';
          const isNoResponse=d.type==='no_response';
          const label=isRateLimit?'Rate limit reached':isAuthMismatch?(typeof t==='function'?t('provider_mismatch_label'):'Provider mismatch'):isNoResponse?'No response received':'Error';
          const hint=d.hint?`\n\n${d.hint}*`:'';
          S.messages.push({role:'assistant',content:`**${label}:** ${d.message}${hint}`});
        }catch(_){
          S.messages.push({role:'assistant',content:'**Error:** An error occurred. Check server logs.'});
        }
        renderMessages();
        setBusy(false);setComposerStatus('');updateSendBtn();
      }else if(typeof trackBackgroundError==='function'){
        const _errTitle=(typeof _allSessions!=='undefined'&&_allSessions.find(s=>s.session_id===activeSid)||{}).title||null;
        try{const d=JSON.parse(e.data);trackBackgroundError(activeSid,_errTitle,d.message||'Error');}
        catch(_){trackBackgroundError(activeSid,_errTitle,'Error');}
      }
    };

    handlers['warning']=e=>{
      // Non-fatal warning from server (e.g. fallback activated, retrying)
      if(!S.session||S.session.session_id!==activeSid) return;
      try{
        const d=JSON.parse(e.data);
        // Show as a small inline notice, not a full error
        setComposerStatus(`${d.message||'Warning'}`);
        // If it's a fallback notice, show it briefly then clear
        if(d.type==='fallback') setTimeout(()=>setComposerStatus(''),4000);
      }catch(_){}
    };

    handlers['cancel']=e=>{
      _terminalStateReached=true;
      _closeSource();
      delete INFLIGHT[activeSid];clearInflight();clearInflightState(activeSid);stopApprovalPolling();stopClarifyPolling();stopSudoPasswordPolling();
      if(!_approvalSessionId||_approvalSessionId===activeSid) hideApprovalCard(true);
      if(!_clarifySessionId||_clarifySessionId===activeSid) hideClarifyCard(true);
      if(!_sudoPasswordVisible) hideSudoPasswordCard(true);
      if(S.session&&S.session.session_id===activeSid){
        S.activeStreamId=null;const _cbc=$('btnCancel');if(_cbc)_cbc.style.display='none';
        clearLiveToolCards();reasoningText='';assistantText='';removeThinking();removeLiveThinkingCard();
        S.messages.push({role:'assistant',content:'*Task cancelled.*'});renderMessages();
        setBusy(false);setComposerStatus('');updateSendBtn();
      }
      renderSessionList();
    };

    if(source){
      directSource = source;
      for(const eventName of Object.keys(handlers)){
        source.addEventListener(eventName, handlers[eventName]);
      }
      source.addEventListener('error', async e => {
        try{ source.close(); }catch(_){ }
        if(_terminalStateReached){
          _closeSource();
          return;
        }
        // Attempt one reconnect if the stream is still active server-side
        if(!_reconnectAttempted && streamId){
          _reconnectAttempted=true;
          setComposerStatus('Reconnecting…');
          setTimeout(async()=>{
            try{
              const st=await api(`/api/chat/stream/status?stream_id=${encodeURIComponent(streamId)}`);
              if(st.active){
                setComposerStatus('Reconnected');
                _wireSSE(new EventSource(new URL(`api/chat/stream?stream_id=${encodeURIComponent(streamId)}`,location.href).href,{withCredentials:true}));
                return;
              }
            }catch(_){ }
            if(await _restoreSettledSession()) return;
            _handleStreamError();
          },1500);
          return;
        }
        if(await _restoreSettledSession()) return;
        _handleStreamError();
      });
    }

    return handlers;
  }

  async function _restoreSettledSession(){
    try{
      const data=await api(`/api/session?session_id=${encodeURIComponent(activeSid)}`);
      const session=data&&data.session;
      if(!session) return false;
      if(session.active_stream_id||session.pending_user_message) return false;
      delete INFLIGHT[activeSid];clearInflight();clearInflightState(activeSid);stopApprovalPolling();stopClarifyPolling();
      _closeSource();
      if(!_approvalSessionId||_approvalSessionId===activeSid) hideApprovalCard(true);
      if(!_clarifySessionId||_clarifySessionId===activeSid) hideClarifyCard(true);
      if(S.session&&S.session.session_id===activeSid){
        S.activeStreamId=null;const _cbe=$('btnCancel');if(_cbe)_cbe.style.display='none';
        clearLiveToolCards();reasoningText='';assistantText='';removeThinking();removeLiveThinkingCard();
        S.session=session;S.messages=session.messages||[];
        syncTopbar();renderMessages();
        setBusy(false);setComposerStatus('');updateSendBtn();
      }
      renderSessionList();
      return true;
    }catch(_){
      return false;
    }
  }

  function _handleStreamError(){
    delete INFLIGHT[activeSid];clearInflight();clearInflightState(activeSid);stopApprovalPolling();stopClarifyPolling();stopSudoPasswordPolling();
    _closeSource();
    if(!_approvalSessionId||_approvalSessionId===activeSid) hideApprovalCard(true);
    if(!_clarifySessionId||_clarifySessionId===activeSid) hideClarifyCard(true);
    if(!_sudoPasswordVisible) hideSudoPasswordCard(true);
    if(S.session&&S.session.session_id===activeSid){
      S.activeStreamId=null;const _cbe=$('btnCancel');if(_cbe)_cbe.style.display='none';
      clearLiveToolCards();reasoningText='';assistantText='';removeThinking();removeLiveThinkingCard();
      S.messages.push({role:'assistant',content:'**Error:** Connection lost'});renderMessages();
      setBusy(false);setComposerStatus('');updateSendBtn();
    }else{
      if(typeof trackBackgroundError==='function'){
        const _errTitle=(typeof _allSessions!=='undefined'&&_allSessions.find(s=>s.session_id===activeSid)||{}).title||null;
        trackBackgroundError(activeSid,_errTitle,'Connection lost');
      }
    }
  }

  (async()=>{
    // Reattach path can carry stale stream ids after server restart; preflight
    // status avoids opening a dead SSE URL that will 404 in the console.
    if(reconnecting){
      try{
        const st=await api(`/api/chat/stream/status?stream_id=${encodeURIComponent(streamId)}`);
        if(!st.active){
          delete INFLIGHT[activeSid];
          clearInflight();
          clearInflightState(activeSid);
          stopApprovalPolling();
          stopClarifyPolling();
          stopSudoPasswordPolling();
          if(!_approvalSessionId||_approvalSessionId===activeSid) hideApprovalCard(true);
          if(!_clarifySessionId||_clarifySessionId===activeSid) hideClarifyCard(true);
          if(!_sudoPasswordVisible) hideSudoPasswordCard(true);
          if(S.session&&S.session.session_id===activeSid){
            S.activeStreamId=null;
            const _cbe=$('btnCancel');if(_cbe)_cbe.style.display='none';
            clearLiveToolCards();
            reasoningText='';assistantText='';removeThinking();removeLiveThinkingCard();
            S.busy=false;
            setComposerStatus('');
            updateSendBtn();
            renderMessages();
            renderSessionList();
          }
          return;
        }
      }catch(_){}
    }
    // Register with shared multiplexed SSE (one connection for all streams)
    const handlers=_wireSSE();
    if(options.direct){
      _wireSSE(new EventSource(new URL(`api/chat/stream?stream_id=${encodeURIComponent(streamId)}`,location.href).href,{withCredentials:true}));
    } else {
      SharedSSE.register(streamId, activeSid, handlers, async () => {
        try{
          const st = await api(`/api/chat/stream/status?stream_id=${encodeURIComponent(streamId)}`);
          if(!st.active){
            if(await _restoreSettledSession()) return;
            _closeSource();
          }
        }catch(_){ }
      });
    }
    LIVE_STREAMS[activeSid]=streamId;
  })();

}

function transcript(){
  const lines=[`# Hermes session ${S.session?.session_id||''}`,``,
    `Workspace: ${S.session?.workspace||''}`,`Model: ${S.session?.model||''}`,``];
  for(const m of S.messages){
    if(!m||m.role==='tool')continue;
    let c=m.content||'';
    if(Array.isArray(c))c=c.filter(p=>p&&p.type==='text').map(p=>p.text||'').join('\n');
    const ct=String(c).trim();
    if(!ct&&!m.attachments?.length)continue;
    const attach=m.attachments?.length?`\n\n_Files: ${m.attachments.join(', ')}_`:'';
    lines.push(`## ${m.role}`,'',ct+attach,'');
  }
  return lines.join('\n');
}

function autoResize(){const el=$('msg');el.style.height='auto';el.style.height=Math.min(el.scrollHeight,200)+'px';updateSendBtn();}


// ── Approval polling ──
var _approvalPollTimer = null;
var _approvalHideTimer = null;
var _approvalVisibleSince = 0;
var _approvalSignature = '';
const APPROVAL_MIN_VISIBLE_MS = 30000;

// showApprovalCard moved above respondApproval

function _clearApprovalHideTimer() {
  if (_approvalHideTimer) {
    clearTimeout(_approvalHideTimer);
    _approvalHideTimer = null;
  }
}

function _resetApprovalCardState() {
  _clearApprovalHideTimer();
  _approvalVisibleSince = 0;
  _approvalSignature = '';
}

// Track session_id of the active approval so respond goes to the right session
let _approvalSessionId = null;
let _approvalCurrentId = null;  // approval_id of the card currently shown

function hideApprovalCard(force=false) {
  const card = $("approvalCard");
  if (!card) return;
  if (!force && _approvalVisibleSince) {
    const remaining = APPROVAL_MIN_VISIBLE_MS - (Date.now() - _approvalVisibleSince);
    if (remaining > 0) {
      const scheduledSignature = _approvalSignature;
      _clearApprovalHideTimer();
      _approvalHideTimer = setTimeout(() => {
        _approvalHideTimer = null;
        if (_approvalSignature !== scheduledSignature) return;
        hideApprovalCard(true);
      }, remaining);
      return;
    }
  }
  _approvalSessionId = null;
  _resetApprovalCardState();
  card.classList.remove("visible");
  $("approvalCmd").textContent = "";
  $("approvalDesc").textContent = "";
}

function showApprovalCard(pending, pendingCount) {
  const keys = pending.pattern_keys || (pending.pattern_key ? [pending.pattern_key] : []);
  const desc = (pending.description || "") + (keys.length ? " [" + keys.join(", ") + "]" : "");
  const cmd = pending.command || "";
  const sig = JSON.stringify({desc, cmd, sid: pending._session_id || (S.session && S.session.session_id) || null});
  const card = $("approvalCard");
  const sameApproval = card.classList.contains("visible") && _approvalSignature === sig;
  $("approvalDesc").textContent = desc;
  $("approvalCmd").textContent = cmd;
  _approvalSessionId = pending._session_id || (S.session && S.session.session_id) || null;
  _approvalCurrentId = pending.approval_id || null;
  _approvalSignature = sig;
  // Show "1 of N" counter when multiple approvals are queued
  const counter = $("approvalCounter");
  if (counter) {
    if (pendingCount && pendingCount > 1) {
      counter.textContent = "1 of " + pendingCount + " pending";
      counter.style.display = "";
    } else {
      counter.style.display = "none";
    }
  }
  if (!sameApproval) {
    _approvalVisibleSince = Date.now();
    _clearApprovalHideTimer();
  }
  // Re-enable buttons in case a previous approval disabled them
  ["approvalBtnOnce","approvalBtnSession","approvalBtnAlways","approvalBtnDeny"].forEach(id => {
    const b = $(id); if (b) { b.disabled = false; b.classList.remove("loading"); }
  });
  card.classList.add("visible");
  if (!sameApproval) card.scrollIntoView({block:"nearest", behavior:"smooth"});
  // Apply current locale to data-i18n elements inside the card
  if (typeof applyLocaleToDOM === "function") applyLocaleToDOM();
  // Focus Allow once button so Enter works immediately
  const onceBtn = $("approvalBtnOnce");
  if (onceBtn) setTimeout(() => onceBtn.focus(), 50);
}

async function respondApproval(choice) {
  const sid = _approvalSessionId || (S.session && S.session.session_id);
  if (!sid) return;
  const approvalId = _approvalCurrentId;
  // Disable all buttons immediately to prevent double-submit
  ["approvalBtnOnce","approvalBtnSession","approvalBtnAlways","approvalBtnDeny"].forEach(id => {
    const b = $(id);
    if (b) { b.disabled = true; if (b.id === "approvalBtn" + choice.charAt(0).toUpperCase() + choice.slice(1)) b.classList.add("loading"); }
  });
  _approvalSessionId = null;
  _approvalCurrentId = null;
  hideApprovalCard(true);
  try {
    await api("/api/approval/respond", {
      method: "POST",
      body: JSON.stringify({ session_id: sid, choice, approval_id: approvalId })
    });
  } catch(e) { setStatus(t("approval_responding") + " " + e.message); }
}

function startApprovalPolling(sid) {
  stopApprovalPolling();
  _approvalPollTimer = setInterval(async () => {
    if (!S.busy || !S.session || S.session.session_id !== sid) {
      stopApprovalPolling(); hideApprovalCard(true); return;
    }
    try {
      const data = await api("/api/approval/pending?session_id=" + encodeURIComponent(sid));
      if (data.pending) {
        // Auto-approve with "always" choice to skip the popup
        await api("/api/approval/respond", {
          method: "POST",
          body: JSON.stringify({ session_id: sid, choice: "always", approval_id: data.pending.approval_id || "" })
        });
      }
      else { hideApprovalCard(); }
    } catch(e) { /* ignore poll errors */ }
  }, 1500);
}

function stopApprovalPolling() {
  if (_approvalPollTimer) { clearInterval(_approvalPollTimer); _approvalPollTimer = null; }
}

// ── Clarify polling ──
var _clarifyPollTimer = null;
var _clarifyHideTimer = null;
let _clarifyVisibleSince = 0;
let _clarifySignature = '';
let _clarifySessionId = null;
let _clarifyMissingEndpointWarned = false;
const CLARIFY_MIN_VISIBLE_MS = 30000;

function _ensureClarifyCardDom() {
  let card = $("clarifyCard");
  if (card) return card;
  const host = $("msgInner") || $("messages");
  if (!host) return null;
  card = document.createElement("div");
  card.className = "clarify-card";
  card.id = "clarifyCard";
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-labelledby", "clarifyHeading");
  card.setAttribute("aria-describedby", "clarifyQuestion clarifyHint");
  card.innerHTML = `
    <div class="clarify-inner">
      <div class="clarify-header">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 17h.01"/><path d="M9.09 9a3 3 0 1 1 5.82 1c0 2-3 2-3 4"/><circle cx="12" cy="12" r="10"/></svg>
        <span id="clarifyHeading" data-i18n="clarify_heading">Clarification needed</span>
      </div>
      <div class="clarify-question" id="clarifyQuestion"></div>
      <div class="clarify-choices" id="clarifyChoices"></div>
      <div class="clarify-response">
        <input class="clarify-input" id="clarifyInput" type="text" data-i18n-placeholder="clarify_input_placeholder" placeholder="type your response…">
        <button class="clarify-submit" id="clarifySubmit" data-i18n="clarify_send">Send</button>
      </div>
      <div class="clarify-hint" id="clarifyHint" data-i18n="clarify_hint">Please choose one option, or type your own response below.</div>
    </div>
  `;
  host.appendChild(card);
  const submit = $("clarifySubmit");
  if (submit) submit.onclick = () => respondClarify();
  if (typeof applyLocaleToDOM === "function") applyLocaleToDOM();
  return card;
}

function _clearClarifyHideTimer() {
  if (_clarifyHideTimer) {
    clearTimeout(_clarifyHideTimer);
    _clarifyHideTimer = null;
  }
}

function _resetClarifyCardState() {
  _clearClarifyHideTimer();
  _clarifyVisibleSince = 0;
  _clarifySignature = '';
}

function hideClarifyCard(force=false) {
  const card = $("clarifyCard");
  if (!card) {
    _clarifySessionId = null;
    _resetClarifyCardState();
    if (typeof unlockComposerForClarify === "function") unlockComposerForClarify();
    return;
  }
  if (!force && _clarifyVisibleSince) {
    const remaining = CLARIFY_MIN_VISIBLE_MS - (Date.now() - _clarifyVisibleSince);
    if (remaining > 0) {
      const scheduledSignature = _clarifySignature;
      _clearClarifyHideTimer();
      _clarifyHideTimer = setTimeout(() => {
        _clarifyHideTimer = null;
        if (_clarifySignature !== scheduledSignature) return;
        hideClarifyCard(true);
      }, remaining);
      return;
    }
  }
  _clarifySessionId = null;
  _resetClarifyCardState();
  card.classList.remove("visible");
  if (typeof unlockComposerForClarify === "function") unlockComposerForClarify();
  $("clarifyQuestion").textContent = "";
  $("clarifyChoices").innerHTML = "";
  $("clarifyInput").value = "";
  $("clarifyInput").disabled = false;
  $("clarifyInput").onkeydown = null;
  const submit = $("clarifySubmit");
  if (submit) { submit.disabled = false; submit.classList.remove("loading"); }
}

function _clarifySetControlsDisabled(disabled, loading=false) {
  const input = $("clarifyInput");
  const submit = $("clarifySubmit");
  if (input) input.disabled = disabled;
  if (submit) {
    submit.disabled = disabled;
    submit.classList.toggle("loading", !!loading);
  }
  const choices = $("clarifyChoices");
  if (choices) {
    choices.querySelectorAll("button").forEach(btn => {
      btn.disabled = disabled;
      if (loading && btn.dataset && btn.dataset.choice === "other") {
        btn.classList.toggle("loading", false);
      }
    });
  }
}

function showClarifyCard(pending) {
  const question = pending.question || pending.description || '';
  const choices = Array.isArray(pending.choices_offered)
    ? pending.choices_offered
    : (Array.isArray(pending.choices) ? pending.choices : []);
  const sig = JSON.stringify({
    question,
    choices,
    sid: pending._session_id || (S.session && S.session.session_id) || null,
  });
  const card = _ensureClarifyCardDom();
  if (!card) return;
  const questionEl = $("clarifyQuestion");
  const choicesEl = $("clarifyChoices");
  const input = $("clarifyInput");
  const sameClarify = card.classList.contains("visible") && _clarifySignature === sig;
  _clarifySessionId = pending._session_id || (S.session && S.session.session_id) || null;
  _clarifySignature = sig;
  if (!sameClarify) {
    _clarifyVisibleSince = Date.now();
    _clearClarifyHideTimer();
  }
  if (questionEl) questionEl.textContent = question;
  if (choicesEl) {
    choicesEl.innerHTML = '';
    choicesEl.style.display = choices.length ? '' : 'none';
    if (choices.length) {
      choices.forEach((choice, idx) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'clarify-choice';
        btn.dataset.choice = choice;
        btn.onclick = () => respondClarify(choice);
        const badge = document.createElement('span');
        badge.className = 'clarify-choice-badge';
        badge.textContent = String(idx + 1);
        const text = document.createElement('span');
        text.className = 'clarify-choice-text';
        text.textContent = choice;
        btn.appendChild(badge);
        btn.appendChild(text);
        choicesEl.appendChild(btn);
      });
      const other = document.createElement('button');
      other.type = 'button';
      other.className = 'clarify-choice other';
      other.dataset.choice = 'other';
      other.setAttribute('data-i18n', 'clarify_other');
      const otherBadge = document.createElement('span');
      otherBadge.className = 'clarify-choice-badge other';
      otherBadge.textContent = '•';
      const otherText = document.createElement('span');
      otherText.className = 'clarify-choice-text';
      otherText.textContent = t('clarify_other') || 'Other';
      other.appendChild(otherBadge);
      other.appendChild(otherText);
      other.onclick = () => {
        const el = $("clarifyInput");
        if (el) {
          el.focus();
          if (typeof el.select === 'function') el.select();
        }
      };
      choicesEl.appendChild(other);
    }
  }
  if (input) {
    if (!sameClarify) input.value = '';
    input.disabled = false;
    input.onkeydown = (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        respondClarify();
      }
    };
  }
  if (typeof lockComposerForClarify === "function") {
    lockComposerForClarify(question ? `clarification needed: ${question}` : "clarification needed");
  }
  _clarifySetControlsDisabled(false, false);
  const msgInner = $("msgInner");
  if (msgInner && card.parentElement !== msgInner) {
    msgInner.appendChild(card);
  }
  card.classList.add("visible");
  if (!sameClarify) card.scrollIntoView({block:"nearest", behavior:"smooth"});
  if (typeof applyLocaleToDOM === "function") applyLocaleToDOM();
  if (input && !sameClarify) setTimeout(() => input.focus(), 50);
}

async function respondClarify(response) {
  const sid = _clarifySessionId || (S.session && S.session.session_id);
  if (!sid) return;
  const input = $("clarifyInput");
  let value = typeof response === 'string' ? response : (input ? input.value : '');
  value = String(value || '').trim();
  if (!value) {
    if (input) input.focus();
    return;
  }
  _clarifySessionId = null;
  _clarifySetControlsDisabled(true, true);
  hideClarifyCard(true);
  try {
    await api("/api/clarify/respond", {
      method: "POST",
      body: JSON.stringify({ session_id: sid, response: value })
    });
  } catch(e) { setStatus(t("clarify_responding") + " " + e.message); }
}

function startClarifyPolling(sid) {
  stopClarifyPolling();
  _clarifyMissingEndpointWarned = false;
  _clarifyPollTimer = setInterval(async () => {
    if (!S.session || S.session.session_id !== sid) {
      stopClarifyPolling(); hideClarifyCard(true); return;
    }
    try {
      const data = await api("/api/clarify/pending?session_id=" + encodeURIComponent(sid));
      if (data.pending) { data.pending._session_id=sid; showClarifyCard(data.pending); }
      else { hideClarifyCard(); }
    } catch(e) {
      const msg = String((e && e.message) || "");
      if (!_clarifyMissingEndpointWarned && /(^|\b)(404|not found)(\b|$)/i.test(msg)) {
        _clarifyMissingEndpointWarned = true;
        setComposerStatus("clarify endpoint unavailable. please restart server.");
        if (typeof showToast === "function") {
          showToast("clarify endpoint unavailable. please restart server.", 5000);
        }
        stopClarifyPolling();
      }
      // Ignore transient poll errors; SSE clarify event still provides a fast path.
    }
  }, 1500);
}

function stopClarifyPolling() {
  if (_clarifyPollTimer) { clearInterval(_clarifyPollTimer); _clarifyPollTimer = null; }
}

// ── Sudo password handling ────────────────────────────────────────────────────
var _sudoPasswordPollTimer = null;
var _sudoPasswordSessionId = null;
let _sudoPasswordVisible = false;

const SUDO_PASSWORD_CACHE_KEY = 'hermes_sudo_password_cache';

function _getCachedSudoPassword() {
  try {
    const cached = localStorage.getItem(SUDO_PASSWORD_CACHE_KEY);
    if (!cached) return null;
    const data = JSON.parse(cached);
    // Cache expires after session ends (we use a timestamp but don't auto-expire)
    return data.password || null;
  } catch (_) {
    return null;
  }
}

function _setCachedSudoPassword(password) {
  try {
    if (!password) {
      localStorage.removeItem(SUDO_PASSWORD_CACHE_KEY);
      return;
    }
    const data = { password, cached_at: Date.now() };
    localStorage.setItem(SUDO_PASSWORD_CACHE_KEY, JSON.stringify(data));
  } catch (_) {
    // localStorage might be full or unavailable
  }
}

function _clearCachedSudoPassword() {
  try {
    localStorage.removeItem(SUDO_PASSWORD_CACHE_KEY);
  } catch (_) {}
}

function showSudoPasswordCard(pending) {
  const card = $("sudoPasswordCard");
  if (!card) return;

  // Check if we have a cached password - use it automatically
  const cachedPassword = _getCachedSudoPassword();
  if (cachedPassword && pending) {
    // Auto-submit the cached password
    const sid = pending.session_id || (S.session && S.session.session_id);
    if (sid) {
      _sudoPasswordSessionId = sid;
      respondSudoPassword('submit', cachedPassword);
      return;
    }
  }

  _sudoPasswordSessionId = pending.session_id || (S.session && S.session.session_id) || null;
  _sudoPasswordVisible = true;

  const input = $("sudoPasswordInput");
  if (input) {
    input.value = '';
    input.disabled = false;
    input.onkeydown = (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        respondSudoPassword('submit');
      }
    };
  }

  // Enable buttons
  const cancelBtn = $("sudoPasswordBtnCancel");
  const submitBtn = $("sudoPasswordBtnSubmit");
  if (cancelBtn) { cancelBtn.disabled = false; cancelBtn.classList.remove('loading'); }
  if (submitBtn) { submitBtn.disabled = false; submitBtn.classList.remove('loading'); }

  card.classList.add("visible");
  card.scrollIntoView({block:"nearest", behavior:"smooth"});
  if (typeof applyLocaleToDOM === "function") applyLocaleToDOM();
  if (input) setTimeout(() => input.focus(), 50);
}

function hideSudoPasswordCard(force=false) {
  const card = $("sudoPasswordCard");
  if (!card) {
    _sudoPasswordSessionId = null;
    _sudoPasswordVisible = false;
    return;
  }
  _sudoPasswordSessionId = null;
  _sudoPasswordVisible = false;
  card.classList.remove("visible");
  const input = $("sudoPasswordInput");
  if (input) {
    input.value = '';
    input.disabled = false;
    input.onkeydown = null;
  }
  const cancelBtn = $("sudoPasswordBtnCancel");
  const submitBtn = $("sudoPasswordBtnSubmit");
  if (cancelBtn) { cancelBtn.disabled = false; cancelBtn.classList.remove('loading'); }
  if (submitBtn) { submitBtn.disabled = false; submitBtn.classList.remove('loading'); }
}

async function respondSudoPassword(action, cachedPassword=null) {
  const sid = _sudoPasswordSessionId || (S.session && S.session.session_id);
  if (!sid) return;

  let password = cachedPassword;
  if (action === 'cancel') {
    password = '';
  } else if (!password) {
    const input = $("sudoPasswordInput");
    password = input ? String(input.value || '').trim() : '';
    if (!password) {
      if (input) input.focus();
      return;
    }
  }

  // Cache the password for future sudo commands in this session
  if (password && action !== 'cancel') {
    _setCachedSudoPassword(password);
  }

  _sudoPasswordSessionId = null;
  _sudoPasswordVisible = false;

  // Disable controls and show loading
  const input = $("sudoPasswordInput");
  const cancelBtn = $("sudoPasswordBtnCancel");
  const submitBtn = $("sudoPasswordBtnSubmit");
  if (input) input.disabled = true;
  if (cancelBtn) cancelBtn.disabled = true;
  if (submitBtn) { submitBtn.disabled = true; submitBtn.classList.add('loading'); }

  hideSudoPasswordCard(true);

  try {
    await api("/api/sudo_password/respond", {
      method: "POST",
      body: JSON.stringify({ session_id: sid, password: password })
    });
  } catch(e) {
    setStatus("sudo password error: " + e.message);
    // Clear cache on error
    _clearCachedSudoPassword();
  }
}

function startSudoPasswordPolling(sid) {
  stopSudoPasswordPolling();
  _sudoPasswordPollTimer = setInterval(async () => {
    if (!S.session || S.session.session_id !== sid) {
      stopSudoPasswordPolling(); hideSudoPasswordCard(true); return;
    }
    try {
      const data = await api("/api/sudo_password/pending?session_id=" + encodeURIComponent(sid));
      if (data.pending) {
        data.pending._session_id = sid;
        // Check if we have a cached password to auto-submit
        const cachedPassword = _getCachedSudoPassword();
        if (cachedPassword) {
          _sudoPasswordSessionId = sid;
          respondSudoPassword('submit', cachedPassword);
        } else {
          showSudoPasswordCard(data.pending);
        }
      } else {
        hideSudoPasswordCard();
      }
    } catch(e) {
      // Ignore transient poll errors; SSE sudo_password event still provides a fast path.
    }
  }, 1500);
}

function stopSudoPasswordPolling() {
  if (_sudoPasswordPollTimer) { clearInterval(_sudoPasswordPollTimer); _sudoPasswordPollTimer = null; }
}

// ── Notifications and Sound ──────────────────────────────────────────────────

function playNotificationSound(){
  if(!window._soundEnabled) return;
  try{
    const ctx=new (window.AudioContext||window.webkitAudioContext)();
    const osc=ctx.createOscillator();
    const gain=ctx.createGain();
    osc.connect(gain);gain.connect(ctx.destination);
    osc.type='sine';osc.frequency.setValueAtTime(660,ctx.currentTime);
    osc.frequency.setValueAtTime(880,ctx.currentTime+0.1);
    gain.gain.setValueAtTime(0.3,ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+0.3);
    osc.start(ctx.currentTime);osc.stop(ctx.currentTime+0.3);
    osc.onended=()=>ctx.close();
  }catch(e){console.warn('Notification sound failed:',e);}
}

function sendBrowserNotification(title,body){
  if(!window._notificationsEnabled||!document.hidden) return;
  if(!('Notification' in window)) return;
  const botName=window._botName||'Hermes';
  if(Notification.permission==='granted'){
    new Notification(title||botName,{body:body});
  }else if(Notification.permission!=='denied'){
    Notification.requestPermission().then(p=>{
      if(p==='granted') new Notification(title||botName,{body:body});
    });
  }
}

async function sendTauriNotification(title,body){
  // Tauri uses the browser's Notification API in webview
  // No special handling needed - browser notifications work in Tauri
  return false;
}

async function sendDesktopNotification(title,body){
  // In Tauri desktop app, browser Notification API works natively
  sendBrowserNotification(title,body);
}

// ── Panel navigation (Chat / Tasks / Skills / Memory) ──
