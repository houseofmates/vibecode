function _normalizeApiBase(base){
  if(!base) return null;
  try{
    const href=new URL(base, location.href).href;
    return href.endsWith('/') ? href : href + '/';
  }catch{
    return null;
  }
}

function _getApiBaseCandidates(isCapacitorApp, isTauri){
  const candidates=[];
  const seen=new Set();
  const isHostedWeb = /^https?:$/.test(location.protocol) && !isCapacitorApp && !isTauri;
  const add=base=>{
    const normalized=_normalizeApiBase(base);
    if(!normalized || seen.has(normalized)) return;
    if(isHostedWeb){
      try{
        const parsed = new URL(normalized, location.href);
        if(parsed.origin !== location.origin) return;
      }catch{
        return;
      }
    }
    seen.add(normalized);
    candidates.push(normalized);
  };

  add(window.HERMES_API_BASE);
  try { add(localStorage.getItem('hermes-api-base')); } catch (e) {}
  try { add(localStorage.getItem('hermes-api-origin')); } catch (e) {}
  add(typeof window.WEBVIEW_SERVER_URL==='string' ? window.WEBVIEW_SERVER_URL : '');

  if(/^https?:$/.test(location.protocol)) add(location.origin + '/');

  if(isCapacitorApp || isTauri){
    add('http://localhost:8786/');
    add('http://127.0.0.1:8786/');
    // Fallback to the development server on 192.168.4.233 if local is unavailable
    add('http://192.168.4.233:8786/');
  }
  // Only use localhost fallbacks in packaged or local-webview contexts.
  if(!isHostedWeb){
    add('http://localhost:8786/');
    add('http://127.0.0.1:8786/');
  }
  if(isCapacitorApp){
    add('https://vc.houseofmates.space/');
  }

  if(!candidates.length) add(location.href);
  return candidates;
}

async function api(path,opts={}){
  const rel = path.startsWith('/') ? path.slice(1) : path;
  const isCapacitorApp = !!(window.Capacitor || window.__capacitor || location.protocol==='capacitor:' || document.documentElement.classList.contains('apk-force-mobile') || document.documentElement.classList.contains('capacitor'));
  const isTauri = !isCapacitorApp && (
    window.__TAURI__ ||
    location.protocol==='tauri:' ||
    location.protocol==='file:' ||
    location.hostname==='tauri.localhost' ||
    location.host==='tauri.localhost' ||
    location.hostname.includes('tauri')
  );
  const baseCandidates = _getApiBaseCandidates(isCapacitorApp, isTauri);
  const fetchOpts = {credentials:'include',...opts};
  if(opts.headers){
    fetchOpts.headers = opts.headers;
  }else if(!(opts.body instanceof FormData)){
    fetchOpts.headers = {'Content-Type':'application/json'};
  }

  let lastError = null;
  for(let i=0;i<baseCandidates.length;i++){
    const baseUrl=baseCandidates[i];
    const url=new URL(rel,baseUrl);
    console.log('[api] Calling:', path, opts.method||'GET', 'base:', baseUrl, 'isTauri:', isTauri);
    let res;
    try{
      res=await fetch(url.href,fetchOpts);
    }catch(err){
      lastError = err;
      console.warn('[api] Network error:', url.href, err.message);
      continue;
    }
    if(!res.ok){
      const text=await res.text();
      console.log('[api] Error response:', res.status, text);
      // If there are more candidates, try the next one (e.g. Tauri bundled origin returns 404)
      if(i<baseCandidates.length-1){
        lastError = new Error(text);
        continue;
      }
      // Parse JSON error body and surface the human-readable message,
      // rather than showing raw JSON like {"error":"Profile 'x' does not exist."}
      try{const j=JSON.parse(text);throw new Error(j.error||j.message||text);}
      catch(e){if(e instanceof SyntaxError)throw new Error(text);throw e;}
    }
    const ct=res.headers.get('content-type')||'';
    const result = ct.includes('application/json')?await res.json():await res.text();
    console.log('[api] Response:', result);
    return result;
  }
  throw lastError || new Error('Failed to fetch');
}

// File extension helper
function fileExt(p){ const i=p.lastIndexOf('.'); return i>=0?p.slice(i).toLowerCase():''; }

// Expose api globally for cross-script access
window.api = api;

// Image extensions for preview
const image_exts=new Set(['.png','.jpg','.jpeg','.gif','.svg','.webp','.ico','.bmp']);

// Persist/restore expanded directory state per workspace in localStorage
function _wsExpandKey(){
  const ws=S.session&&S.session.workspace;
  return ws?'hermes-webui-expanded:'+ws:null;
}
function _saveExpandedDirs(){
  const key=_wsExpandKey();if(!key)return;
  try{localStorage.setItem(key,JSON.stringify([...(S._expandedDirs||new Set())]));}catch(e){}
}
function _restoreExpandedDirs(){
  const key=_wsExpandKey();
  if(!key){S._expandedDirs=new Set();return;}
  try{
    const raw=localStorage.getItem(key);
    S._expandedDirs=raw?new Set(JSON.parse(raw)):new Set();
  }catch(e){S._expandedDirs=new Set();}
}

async function loadDir(path){
  if(!S.session)return;
  console.log('[loadDir] Starting for path:', path, 'session:', S.session.session_id, 'machine:', S.session.machine_hostname);
  try{
    if(!path||path==='.'){
      S._dirCache={};
      _restoreExpandedDirs();  // restore per-workspace expanded state on root load
    }
    S.currentDir=path||'.';

    // Show cached entries instantly while fetching fresh data
    const cacheKey = 'hermes-dircache:' + S.session.session_id + ':' + (path || '.');
    let cached = null;
    try { cached = localStorage.getItem(cacheKey); } catch (e) {}
    if (cached && !S._dirCache[path || '.']) {
      try {
        const parsed = JSON.parse(cached);
        S.entries = parsed.entries || [];
        S._dirCache[path || '.'] = S.entries;
        renderBreadcrumb();
        renderFileTree();
      } catch (e) { /* ignore parse errors */ }
    }

    const apiUrl = `/api/list?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(path)}`;
    console.log('[loadDir] Calling API:', apiUrl);
    const data=await api(apiUrl);
    console.log('[loadDir] API response:', data);
    S.entries=data.entries||[];renderBreadcrumb();renderFileTree();

    // Cache the directory contents
    try {
      localStorage.setItem(cacheKey, JSON.stringify({entries: S.entries, ts: Date.now()}));
    } catch (e) { /* ignore quota errors */ }

    // Pre-fetch contents of restored expanded dirs so they render without a second click
    if(!path||path==='.'){
      for(const dirPath of (S._expandedDirs||[])){
        if(!S._dirCache[dirPath]){
          try{
            const dc=await api(`/api/list?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(dirPath)}`);
            S._dirCache[dirPath]=dc.entries||[];
            // Cache subdirectory
            try {
              localStorage.setItem('hermes-dircache:' + S.session.session_id + ':' + dirPath, JSON.stringify({entries: dc.entries || [], ts: Date.now()}));
            } catch (e) {}
          }catch(e2){S._dirCache[dirPath]=[];}
        }
      }
      if(S._expandedDirs&&S._expandedDirs.size>0)renderFileTree();
    }
    if(typeof clearPreview==='function'){
      if(typeof _previewDirty!=='undefined'&&_previewDirty){
        await autoSavePreview();
      }
      clearPreview();
    }
    // Fetch git info for workspace root (non-blocking)
    if(!path||path==='.') _refreshGitBadge();
  }catch(e){console.warn('loadDir',e);}
}

async function _refreshGitBadge(){
  const badge=$('gitBadge');
  if(!badge||!S.session)return;
  try{
    const data=await api(`/api/git-info?session_id=${encodeURIComponent(S.session.session_id)}`);
    if(data.git&&data.git.is_git){
      const g=data.git;
      let text=g.branch||'git';
      if(g.dirty>0) text+=` \u00b7 ${g.dirty}\u2206`; // middot + delta
      if(g.behind>0) text+=` \u2193${g.behind}`;
      if(g.ahead>0) text+=` \u2191${g.ahead}`;
      badge.textContent=text;
      badge.className='git-badge'+(g.dirty>0?' dirty':'');
      badge.style.display='';
    } else {
      badge.style.display='none';
      badge.textContent='';
    }
  }catch(e){badge.style.display='none';}
}

function navigateUp(){
  if(!S.session||S.currentDir==='.')return;
  const parts=S.currentDir.split('/');
  parts.pop();
  loadDir(parts.length?parts.join('/'):'.');
}

// File extension sets for preview routing (must match server-side sets)
const md_exts     = new Set(['.md','.markdown','.mdown']);
// Binary formats that should download rather than preview
const download_exts = new Set([
  '.docx','.doc','.xlsx','.xls','.pptx','.ppt','.odt','.ods','.odp',
  '.pdf','.zip','.tar','.gz','.bz2','.7z','.rar',
  '.mp3','.mp4','.wav','.m4a','.ogg','.flac','.mov','.avi','.mkv','.webm',
  '.exe','.dmg','.pkg','.deb','.rpm',
  '.woff','.woff2','.ttf','.otf','.eot',
  '.bin','.dat','.db','.sqlite','.pyc','.class','.so','.dylib','.dll',
]);

let _previewCurrentPath = '';  // relative path of currently previewed file
let _previewCurrentMode = '';  // 'code' | 'md' | 'image'
let _previewDirty = false;     // true when edits are unsaved

function showPreview(mode){
  // mode: 'code' | 'image' | 'md'
  $('previewCode').style.display     = mode==='code'  ? '' : 'none';
  $('previewImgWrap').style.display  = mode==='image' ? '' : 'none';
  $('previewMd').style.display       = mode==='md'    ? '' : 'none';
  $('previewEditArea').style.display = 'none';  // start in read-only
  const badge=$('previewBadge');
  badge.className='preview-badge '+mode;
  badge.textContent = mode==='image'?'image':mode==='md'?'md':fileExt($('previewPathText').textContent)||'text';
  _previewCurrentMode = mode;
  _previewDirty = false;
  updateEditBtn();
}

function updateEditBtn(){
  const btn=$('btnEditFile');
  if(!btn)return;
  const editable = _previewCurrentMode==='code'||_previewCurrentMode==='md';
  btn.style.display = editable?'':'none';
  const editing = $('previewEditArea').style.display!=='none';
  btn.innerHTML = editing ? `&#128190; ${t('save')}` : `&#9998; ${t('edit')}`;
  btn.title = editing ? t('save_title') : t('edit_title');
  btn.style.color = editing ? 'var(--blue)' : '';
  if(_previewDirty) btn.innerHTML = '&#128190; Save*';
}

async function toggleEditMode(){
  const editing = $('previewEditArea').style.display!=='none';
  if(editing){
    // Save
    if(!S.session||!_previewCurrentPath)return;
    const content=$('previewEditArea').value;
    try{
      await api('/api/file/save',{method:'POST',body:JSON.stringify({
        session_id:S.session.session_id, path:_previewCurrentPath, content
      })});
      _previewDirty=false;
      // Update read-only views
      if(_previewCurrentMode==='code') $('previewCode').textContent=content;
      else { $('previewMd').innerHTML=renderMd(content); requestAnimationFrame(()=>{if(typeof renderKatexBlocks==='function')renderKatexBlocks();}); }
      $('previewEditArea').style.display='none';
      if(_previewCurrentMode==='code') $('previewCode').style.display='';
      else $('previewMd').style.display='';
      showToast(t('saved'));
    }catch(e){setStatus(t('save_failed')+e.message);}
  }else{
    // Enter edit mode: populate textarea with current content
    const currentText = _previewCurrentMode==='code'
      ? $('previewCode').textContent
      : _previewRawContent||'';
    $('previewEditArea').value=currentText;
    $('previewEditArea').style.display='';
    if(_previewCurrentMode==='code') $('previewCode').style.display='none';
    else $('previewMd').style.display='none';
    // Escape cancels the edit without saving
    $('previewEditArea').onkeydown=e=>{
      if(e.key==='Escape'){e.preventDefault();cancelEditMode();}
    };
  }
  updateEditBtn();
}

let _previewRawContent = '';  // raw text for md files (to populate editor)

function cancelEditMode(){
  // Discard changes and return to read-only view
  $('previewEditArea').style.display='none';
  $('previewEditArea').onkeydown=null;
  if(_previewCurrentMode==='code') $('previewCode').style.display='';
  else $('previewMd').style.display='';
  _previewDirty=false;
  updateEditBtn();
}

async function autoSavePreview(){
  // Auto-save unsaved changes when navigating away
  if(!S.session||!_previewCurrentPath||!_previewDirty)return;
  const content=$('previewEditArea').value;
  try{
    await api('/api/file/save',{method:'POST',body:JSON.stringify({
      session_id:S.session.session_id, path:_previewCurrentPath, content
    })});
    _previewDirty=false;
    showToast(t('saved'));
  }catch(e){/* silent fail - will be discarded */}
}

async function openFile(path){
  if(!S.session)return;
  const ext=fileExt(path);

  // Binary/download-only formats: trigger browser download, don't preview
  if(download_exts.has(ext)){
    downloadFile(path);
    return;
  }

  $('previewPathText').textContent=path;
  $('previewArea').classList.add('visible');
  $('fileTree').style.display='none';

  // Add right-click context menu to preview path
  const previewPathEl=$('previewPath');
  previewPathEl.oncontextmenu=(e)=>{
    e.preventDefault();
    e.stopPropagation();
    _showPreviewPathContextMenu(e,path);
  };

  _previewCurrentPath = path;
  renderFileBreadcrumb(path);
  if(image_exts.has(ext)){
    // Image: load via raw endpoint, show as <img>
    showPreview('image');
    const url=`api/file/raw?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(path)}`;
    $('previewImg').alt=path;
    $('previewImg').src=url;
    $('previewImg').onerror=()=>setStatus(t('image_load_failed'));
  } else if(md_exts.has(ext)){
    // Markdown: fetch text, render with renderMd, display as formatted HTML
    try{
      const data=await api(`/api/file?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(path)}`);
      showPreview('md');
      _previewRawContent = data.content;
      $('previewMd').innerHTML=renderMd(data.content);
      requestAnimationFrame(()=>{if(typeof renderKatexBlocks==='function')renderKatexBlocks();});
    }catch(e){setStatus(t('file_open_failed'));}
  } else {
    // Plain code / text -- but fall back to download if server signals binary
    try{
      const data=await api(`/api/file?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(path)}`);
      if(data.binary){
        // Server flagged this as binary content
        downloadFile(path);
        return;
      }
      showPreview('code');
      $('previewCode').textContent=data.content;
    }catch(e){
      // If it's a 400/too-large error, offer download instead
      downloadFile(path);
    }
  }
}

function downloadFile(path){
  if(!S.session)return;
  // Trigger browser download via the raw file endpoint with content-disposition attachment
  const url=`api/file/raw?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(path)}&download=1`;
  const filename=path.split('/').pop();
  const a=document.createElement('a');
  a.href=url;a.download=filename;
  document.body.appendChild(a);a.click();
  setTimeout(()=>document.body.removeChild(a),100);
  showToast(t('downloading',filename),2000);
}

function _showPreviewPathContextMenu(event,path){
  const menu=document.createElement('div');
  menu.className='preview-context-menu';
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

  const filename=path.split('/').pop();

  // Rename option
  const renameOpt=document.createElement('div');
  renameOpt.style.cssText='padding:8px 14px;font-size:12px;color:var(--text);cursor:pointer;transition:background .12s;text-transform:lowercase;';
  renameOpt.textContent='rename';
  renameOpt.onmouseover=()=>renameOpt.style.background='rgba(255,255,255,.05)';
  renameOpt.onmouseout=()=>renameOpt.style.background='';
  renameOpt.onclick=()=>{
    document.body.removeChild(menu);
    _startRenameFromPreview(path,filename);
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
    deleteWorkspaceFile(path,filename);
  };
  menu.appendChild(deleteOpt);

  document.body.appendChild(menu);

  const closeMenu=()=>{if(menu.parentNode) document.body.removeChild(menu);};
  const handleClickOutside=(e)=>{if(!menu.contains(e.target)) closeMenu(); document.removeEventListener('click',handleClickOutside);};
  setTimeout(()=>document.addEventListener('click',handleClickOutside),10);
}

async function _startRenameFromPreview(path,oldName){
  const newName=await showPromptDialog({
    title:'rename file',
    message:'enter new name:',
    confirmLabel:'rename',
    cancelLabel:'cancel',
    placeholder:oldName,
    value:oldName
  });

  if(!newName||!newName.trim()||newName.trim()===oldName)return;

  try{
    await api('/api/file/rename',{method:'POST',body:JSON.stringify({
      session_id:S.session.session_id,path:path,new_name:newName.trim()
    })});
    showToast('renamed to '+newName.trim());
    clearPreview();
    await loadDir(S.currentDir);
  }catch(err){showToast('rename failed: '+err.message);}
}


// ── Render breadcrumb for file preview mode ──────────────────────────────────
function renderFileBreadcrumb(filePath) {
  const bar = $('breadcrumbBar');
  if (!bar) return;
  bar.style.display = 'flex';
  const upBtn = $('btnUpDir');
  if (upBtn) upBtn.style.display = '';

  bar.innerHTML = '';
  // Root
  const root = document.createElement('span');
  root.className = 'breadcrumb-seg breadcrumb-link';
  root.textContent = '~';
  root.onclick = () => { clearPreview(); loadDir('.'); };
  bar.appendChild(root);

  const parts = filePath.split('/');
  let accumulated = '';
  for (let i = 0; i < parts.length; i++) {
    const sep = document.createElement('span');
    sep.className = 'breadcrumb-sep';
    sep.textContent = '/';
    bar.appendChild(sep);

    accumulated += (accumulated ? '/' : '') + parts[i];
    const seg = document.createElement('span');
    seg.textContent = parts[i];
    if (i < parts.length - 1) {
      seg.className = 'breadcrumb-seg breadcrumb-link';
      const target = accumulated;
      seg.onclick = () => { clearPreview(); loadDir(target); };
    } else {
      seg.className = 'breadcrumb-seg breadcrumb-current';
    }
    bar.appendChild(seg);
  }
}

// ── Real-time directory type-ahead ───────────────────────────────────────────
let _dirInputDebounceTimer = null;
let _lastValidPath = '';

function initDirPathInput() {
  const input = $('dirPathInput');
  const pathBar = $('pathInputBar');
  if (!input || !pathBar) return;

  input.addEventListener('input', (e) => {
    const value = e.target.value.trim();

    if (_dirInputDebounceTimer) {
      clearTimeout(_dirInputDebounceTimer);
    }

    if (!value) {
      // Empty input - restore breadcrumb view
      pathBar.style.display = 'none';
      if (S.session) loadDir('.');
      return;
    }

    pathBar.style.display = 'block';

    _dirInputDebounceTimer = setTimeout(() => {
      loadAbsoluteDir(value);
    }, 200);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      if (_dirInputDebounceTimer) clearTimeout(_dirInputDebounceTimer);
      const value = input.value.trim();
      if (value) loadAbsoluteDir(value);
    }
    if (e.key === 'Escape') {
      input.value = '';
      pathBar.style.display = 'none';
      if (S.session) loadDir('.');
    }
  });

  // Focus input on Ctrl/Cmd+L
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
      e.preventDefault();
      input.focus();
      input.select();
    }
  });
}

async function loadAbsoluteDir(absPath) {
  if (!S.session) return;
  const input = $('dirPathInput');
  const pathBar = $('pathInputBar');

  try {
    const data = await api(`/api/list-absolute?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(absPath)}`);
    S.entries = data.entries || [];
    S.currentDir = data.path || absPath;
    _lastValidPath = absPath;

    // Update breadcrumb to show current path
    renderBreadcrumbFromAbsolute(data.path || absPath);
    renderFileTree();

    // Visual feedback on success
    if (input) input.style.borderColor = 'var(--border2)';
  } catch (err) {
    // Path doesn't exist or is invalid - show empty state but keep trying
    S.entries = [];
    renderFileTree();
    if (input) input.style.borderColor = '#e74c3c'; // Red border for invalid path
  }
}

function renderBreadcrumbFromAbsolute(relPath) {
  const bar = $('breadcrumbBar');
  if (!bar) return;
  bar.style.display = 'flex';
  const upBtn = $('btnUpDir');
  if (upBtn) upBtn.style.display = 'none'; // Hide up button for absolute paths

  bar.innerHTML = '';

  // Show full path segments
  const parts = relPath.split('/').filter(p => p && p !== '.');
  let accumulated = '';

  for (let i = 0; i < parts.length; i++) {
    if (i > 0) {
      const sep = document.createElement('span');
      sep.className = 'breadcrumb-sep';
      sep.textContent = '/';
      bar.appendChild(sep);
    }

    accumulated += (accumulated ? '/' : '') + parts[i];
    const seg = document.createElement('span');
    seg.textContent = parts[i];
    if (i < parts.length - 1) {
      seg.className = 'breadcrumb-seg breadcrumb-link';
      const target = accumulated;
      seg.onclick = () => loadAbsoluteDirFromWorkspace(target);
    } else {
      seg.className = 'breadcrumb-seg breadcrumb-current';
    }
    bar.appendChild(seg);
  }
}

async function loadAbsoluteDirFromWorkspace(relPath) {
  if (!S.session) return;
  const workspace = S.session.workspace;
  const absPath = workspace + '/' + relPath;
  $('dirPathInput').value = absPath;
  await loadAbsoluteDir(absPath);
}

// Initialize on load
document.addEventListener('DOMContentLoaded', initDirPathInput);

// Try to render file tree from cache when session becomes available
function _tryRenderFileTreeFromCache(attempt = 1) {
  const MAX_ATTEMPTS = 50; // 5 seconds max

  if (!S.session || !S.session.session_id) {
    if (attempt < MAX_ATTEMPTS) {
      setTimeout(() => _tryRenderFileTreeFromCache(attempt + 1), 100);
    }
    return;
  }

  // Try to load root directory from cache
  const cacheKey = 'hermes-dircache:' + S.session.session_id + ':.';
  let cached = null;
  try { cached = localStorage.getItem(cacheKey); } catch (e) {}
  if (cached && (!S.entries || S.entries.length === 0)) {
    try {
      const parsed = JSON.parse(cached);
      if (parsed.entries && parsed.entries.length) {
        S.currentDir = '.';
        S.entries = parsed.entries;
        S._dirCache = S._dirCache || {};
        S._dirCache['.'] = parsed.entries;
        _restoreExpandedDirs();
        if (typeof renderBreadcrumb === 'function') renderBreadcrumb();
        if (typeof renderFileTree === 'function') {
          renderFileTree();
          console.log('[workspace] File tree rendered from cache:', parsed.entries.length);
        }
      }
    } catch (e) { /* ignore parse errors */ }
  }
}
