async function api(path,opts={}){
  // Strip leading slash so URL resolves relative to location.href (supports subpath mounts)
  const rel = path.startsWith('/') ? path.slice(1) : path;
  const url=new URL(rel,location.href);
  console.log('[api] Calling:', path, opts.method||'GET');
  const res=await fetch(url.href,{credentials:'include',headers:{'Content-Type':'application/json'},...opts});
  if(!res.ok){
    const text=await res.text();
    console.log('[api] Error response:', res.status, text);
    // Parse JSON error body and surface the human-readable message,
    // rather than showing raw JSON like {"error":"Profile 'x' does not exist."}
    try{const j=JSON.parse(text);throw new Error(j.error||j.message||text);}
    catch(e){if(e instanceof SyntaxError)throw new Error(text);throw e;}
  }
  const ct=res.headers.get('content-type')||'';
  const result = ct.includes('application/json')?res.json():res.text();
  console.log('[api] Response:', result);
  return result;
}

// File extension helper
function fileExt(p){ const i=p.lastIndexOf('.'); return i>=0?p.slice(i).toLowerCase():''; }

// Expose api globally for cross-script access
window.api = api;

// Image extensions for preview
const IMAGE_EXTS=new Set(['.png','.jpg','.jpeg','.gif','.svg','.webp','.ico','.bmp']);

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
  try{
    if(!path||path==='.'){
      S._dirCache={};
      _restoreExpandedDirs();  // restore per-workspace expanded state on root load
    }
    S.currentDir=path||'.';
    const data=await api(`/api/list?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(path)}`);
    S.entries=data.entries||[];renderBreadcrumb();renderFileTree();
    // Pre-fetch contents of restored expanded dirs so they render without a second click
    if(!path||path==='.'){
      for(const dirPath of (S._expandedDirs||[])){
        if(!S._dirCache[dirPath]){
          try{
            const dc=await api(`/api/list?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(dirPath)}`);
            S._dirCache[dirPath]=dc.entries||[];
          }catch(e2){S._dirCache[dirPath]=[];}
        }
      }
      if(S._expandedDirs&&S._expandedDirs.size>0)renderFileTree();
    }
    if(typeof clearPreview==='function'){
      if(typeof _previewDirty!=='undefined'&&_previewDirty){
        showConfirmDialog({title:t('unsaved_confirm'),message:'',confirmLabel:'Discard',danger:true,focusCancel:true}).then(ok=>{if(ok)clearPreview();});
      }else{
        clearPreview();
      }
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
const MD_EXTS     = new Set(['.md','.markdown','.mdown']);
// Binary formats that should download rather than preview
const DOWNLOAD_EXTS = new Set([
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

async function openFile(path){
  if(!S.session)return;
  const ext=fileExt(path);

  // Binary/download-only formats: trigger browser download, don't preview
  if(DOWNLOAD_EXTS.has(ext)){
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
  if(IMAGE_EXTS.has(ext)){
    // Image: load via raw endpoint, show as <img>
    showPreview('image');
    const url=`api/file/raw?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(path)}`;
    $('previewImg').alt=path;
    $('previewImg').src=url;
    $('previewImg').onerror=()=>setStatus(t('image_load_failed'));
  } else if(MD_EXTS.has(ext)){
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
  menu.style.left=event.clientX+'px';
  menu.style.top=event.clientY+'px';

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
