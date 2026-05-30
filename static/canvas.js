/* ── canvas.js — inline file/artifact viewer for vibecode ──────────────── */
/* sits between main chat and workspace rightpanel */

// ── state ────────────────────────────────────────────────────────────────
const Canvas = {
  _open: false,
  _currentType: '',       // 'html'|'svg'|'pdf'|'md'|'code'|'json'|'csv'|'image'|'mermaid'
  _currentTitle: '',
  _currentContent: '',     // raw content being displayed
  _currentPath: '',        // file path if viewing from workspace
  _versions: [],           // array of {type, title, content, ts}
  _activeVersion: 0,
  _mode: 'preview',        // 'preview' | 'code' (for html: rendered vs source)
  _resizeState: null,
};

// shorthand
const $c = id => document.getElementById(id);

// ── extension → type mapping ─────────────────────────────────────────────
const CANVAS_HTML_EXTS = new Set(['.html','.htm','.xhtml']);
const CANVAS_SVG_EXTS = new Set(['.svg','.svgz']);
const CANVAS_PDF_EXTS = new Set(['.pdf']);
const CANVAS_MD_EXTS = new Set(['.md','.markdown','.mdown','.mdx']);
const CANVAS_JSON_EXTS = new Set(['.json','.jsonl','.json5']);
const CANVAS_YAML_EXTS = new Set(['.yaml','.yml','.toml']);
const CANVAS_CSV_EXTS = new Set(['.csv','.tsv']);
const CANVAS_CODE_EXTS = new Set([
  '.js','.jsx','.ts','.tsx','.mjs','.cjs',
  '.py','.pyw','.pyi',
  '.rb','.rs','.go','.zig','.swift','.kt','.kts','.scala','.clj',
  '.c','.h','.cpp','.hpp','.cc','.cxx','.m','.mm',
  '.java','.cs','.fs','.fsx','.fsi',
  '.sh','.bash','.zsh','.fish','.ps1','.psm1','.bat','.cmd',
  '.sql','.r','.R','.lua','.pl','.pm','.php',
  '.css','.scss','.sass','.less','.styl',
  '.vue','.svelte','.astro',
  '.dockerfile','.dockerignore','.gitignore','.env','.ini','.cfg','.conf',
  '.xml','.graphql','.gql','.prisma','.proto','.tf','.hcl',
]);
const CANVAS_IMAGE_EXTS = new Set(['.png','.jpg','.jpeg','.gif','.webp','.ico','.bmp','.avif']);
const CANVAS_MERMAID_EXTS = new Set(['.mmd','.mermaid']);

// languages for fenced code block detection → canvas type
const CANVAS_FENCED_LANGS = {
  html: 'html', htm: 'html', svg: 'svg',
  mermaid: 'mermaid',
};

function canvasTypeForExt(ext) {
  if (CANVAS_HTML_EXTS.has(ext)) return 'html';
  if (CANVAS_SVG_EXTS.has(ext)) return 'svg';
  if (CANVAS_PDF_EXTS.has(ext)) return 'pdf';
  if (CANVAS_MD_EXTS.has(ext)) return 'md';
  if (CANVAS_JSON_EXTS.has(ext)) return 'json';
  if (CANVAS_YAML_EXTS.has(ext)) return 'json'; // reuse json renderer
  if (CANVAS_CSV_EXTS.has(ext)) return 'csv';
  if (CANVAS_IMAGE_EXTS.has(ext)) return 'image';
  if (CANVAS_MERMAID_EXTS.has(ext)) return 'mermaid';
  if (CANVAS_CODE_EXTS.has(ext)) return 'code';
  return 'code'; // fallback
}

function canvasTypeForLang(lang) {
  const l = (lang || '').toLowerCase().trim();
  if (CANVAS_FENCED_LANGS[l]) return CANVAS_FENCED_LANGS[l];
  if (l === 'markdown' || l === 'md') return 'md';
  if (l === 'json' || l === 'jsonl' || l === 'yaml' || l === 'yml' || l === 'toml') return 'json';
  if (l === 'csv' || l === 'tsv') return 'csv';
  if (l === 'python' || l === 'py' || l === 'javascript' || l === 'js' || l === 'typescript' || l === 'ts') return 'code';
  return 'code';
}

function canvasBadgeClass(type) {
  const map = { html:'html', svg:'svg', pdf:'pdf', md:'md', code:'code', json:'json', csv:'csv', image:'image', mermaid:'mermaid' };
  return map[type] || 'code';
}

function canvasBadgeLabel(type) {
  const map = { html:'html', svg:'svg', pdf:'pdf', md:'markdown', code:'code', json:'json', csv:'csv', image:'image', mermaid:'mermaid' };
  return map[type] || type;
}

// ── panel open/close ─────────────────────────────────────────────────────

function openCanvas(type, title, content, { path, versions } = {}) {
  const panel = $c('canvasPanel');
  if (!panel) return;

  Canvas._open = true;
  Canvas._currentType = type;
  Canvas._currentTitle = title || 'untitled';
  Canvas._currentContent = content || '';
  Canvas._currentPath = path || '';
  Canvas._mode = (type === 'html') ? 'preview' : 'preview';

  // version tracking
  if (versions && versions.length) {
    Canvas._versions = versions;
    Canvas._activeVersion = versions.length - 1;
  } else {
    Canvas._versions = [{ type, title: Canvas._currentTitle, content: Canvas._currentContent, ts: Date.now() }];
    Canvas._activeVersion = 0;
  }

  // update header
  const headerIcon = panel.querySelector('.canvas-header-icon');
  const headerTitle = panel.querySelector('.canvas-header-title');
  const headerBadge = panel.querySelector('.canvas-header-badge');

  if (headerIcon) headerIcon.innerHTML = canvasIcon(type);
  if (headerTitle) headerTitle.textContent = Canvas._currentTitle;
  if (headerBadge) {
    headerBadge.className = 'canvas-header-badge ' + canvasBadgeClass(type);
    headerBadge.textContent = canvasBadgeLabel(type);
  }

  // show/hide mode tabs (only for html: preview vs source)
  const modes = panel.querySelector('.canvas-modes');
  if (modes) {
    modes.style.display = (type === 'html') ? 'flex' : 'none';
    updateCanvasModeTabs();
  }

  // render version pills
  renderCanvasVersions();

  // render content
  renderCanvasContent();

  // open panel
  panel.classList.add('open');

  // save state for potential resume
  try {
    sessionStorage.setItem('canvas_state', JSON.stringify({
      type: Canvas._currentType,
      title: Canvas._currentTitle,
      content: Canvas._currentContent.substring(0, 50000), // cap at 50k for storage
      path: Canvas._currentPath,
    }));
  } catch(e) {}
}

function closeCanvas() {
  const panel = $c('canvasPanel');
  if (!panel) return;
  Canvas._open = false;
  panel.classList.remove('open', 'fullscreen');
  try { sessionStorage.removeItem('canvas_state'); } catch(e) {}
}

function toggleCanvas() {
  if (Canvas._open) {
    closeCanvas();
  } else {
    // Don't auto-restore from sessionStorage on toggle
    // Only open if user explicitly opens something
    // restoreCanvas();
  }
}

function restoreCanvas() {
  try {
    const raw = sessionStorage.getItem('canvas_state');
    if (raw) {
      const s = JSON.parse(raw);
      openCanvas(s.type, s.title, s.content, { path: s.path });
    }
  } catch(e) {}
}

function toggleCanvasFullscreen() {
  const panel = $c('canvasPanel');
  if (!panel) return;
  panel.classList.toggle('fullscreen');
}

// ── version management ───────────────────────────────────────────────────

function addCanvasVersion(type, title, content) {
  // if same title exists, add as new version; otherwise reset
  const existing = Canvas._versions.findIndex(v => v.title === title);
  if (existing >= 0) {
    Canvas._versions.push({ type, title, content, ts: Date.now() });
  } else {
    Canvas._versions = [{ type, title, content, ts: Date.now() }];
  }
  Canvas._activeVersion = Canvas._versions.length - 1;
  renderCanvasVersions();
  renderCanvasContent();
}

function switchCanvasVersion(idx) {
  if (idx < 0 || idx >= Canvas._versions.length) return;
  Canvas._activeVersion = idx;
  const v = Canvas._versions[idx];
  Canvas._currentType = v.type;
  Canvas._currentContent = v.content;
  Canvas._currentTitle = v.title;
  renderCanvasVersions();
  renderCanvasContent();

  // update header
  const panel = $c('canvasPanel');
  if (!panel) return;
  const headerTitle = panel.querySelector('.canvas-header-title');
  const headerBadge = panel.querySelector('.canvas-header-badge');
  if (headerTitle) headerTitle.textContent = v.title;
  if (headerBadge) {
    headerBadge.className = 'canvas-header-badge ' + canvasBadgeClass(v.type);
    headerBadge.textContent = canvasBadgeLabel(v.type);
  }
}

function renderCanvasVersions() {
  const container = $c('canvasVersions');
  if (!container) return;

  if (Canvas._versions.length <= 1) {
    container.style.display = 'none';
    return;
  }

  container.style.display = 'flex';
  container.innerHTML = '';
  Canvas._versions.forEach((v, i) => {
    const pill = document.createElement('button');
    pill.className = 'canvas-version-pill' + (i === Canvas._activeVersion ? ' active' : '');
    pill.textContent = 'v' + (i + 1);
    pill.title = new Date(v.ts).toLocaleTimeString();
    pill.onclick = () => switchCanvasVersion(i);
    container.appendChild(pill);
  });
}

// ── mode tabs (preview/source for html) ──────────────────────────────────

function setCanvasMode(mode) {
  Canvas._mode = mode;
  updateCanvasModeTabs();
  renderCanvasContent();
}

function updateCanvasModeTabs() {
  const panel = $c('canvasPanel');
  if (!panel) return;
  panel.querySelectorAll('.canvas-mode-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.mode === Canvas._mode);
  });
}

// ── content rendering ────────────────────────────────────────────────────

function renderCanvasContent() {
  const body = $c('canvasBody');
  if (!body) return;

  const ver = Canvas._versions[Canvas._activeVersion];
  if (!ver) return;

  const type = ver.type;
  const content = ver.content;

  // for html in code mode, override type
  const renderType = (type === 'html' && Canvas._mode === 'code') ? 'code' : type;

  body.className = 'canvas-body' + (renderType === 'code' ? ' scroll-code' : '');
  body.innerHTML = '';

  switch (renderType) {
    case 'html':  renderCanvasHTML(body, content); break;
    case 'svg':   renderCanvasSVG(body, content); break;
    case 'pdf':   renderCanvasPDF(body, content); break;
    case 'md':    renderCanvasMD(body, content); break;
    case 'code':  renderCanvasCode(body, content, type); break;
    case 'json':  renderCanvasJSON(body, content); break;
    case 'csv':   renderCanvasCSV(body, content); break;
    case 'image': renderCanvasImage(body, content); break;
    case 'mermaid': renderCanvasMermaid(body, content); break;
    default:      renderCanvasCode(body, content, 'text'); break;
  }

  // make body focusable for keyboard shortcut (Ctrl+C)
  if (renderType !== 'code' && renderType !== 'json' && renderType !== 'csv') {
    body.setAttribute('tabindex', '0');
    body.setAttribute('aria-label', 'canvas content — press Ctrl+C to copy source');
  } else {
    body.removeAttribute('tabindex');
  }

  // add a subtle copy hint for visual content (html, svg, mermaid)
  if (renderType === 'html' || renderType === 'svg' || renderType === 'mermaid') {
    const hint = document.createElement('div');
    hint.className = 'canvas-copy-hint';
    hint.textContent = '\u2318C to copy source';
    body.appendChild(hint);
  }
}

// ── html renderer ─────────────────────────────────────────────────────────

function renderCanvasHTML(container, html) {
  const wrap = document.createElement('div');
  wrap.className = 'canvas-html-wrap';

  // inject Ctrl+C handler into the iframe content so users can copy
  // when focused inside the rendered preview
  const copyHandler = `
<script>
(function(){
  var hint = document.createElement('div');
  hint.id = '__copy_hint';
  hint.textContent = '\u2318C to copy source';
  Object.assign(hint.style, {
    position:'fixed', bottom:'8px', right:'8px',
    padding:'4px 10px', borderRadius:'6px',
    background:'rgba(0,0,0,.65)', color:'#ccc',
    fontSize:'11px', fontFamily:'sans-serif',
    pointerEvents:'none', zIndex:999999,
    opacity:'0', transition:'opacity .2s',
  });
  document.body.appendChild(hint);
  var timer;
  document.addEventListener('keydown', function(e){
    if((e.ctrlKey||e.metaKey)&&e.key==='c'){
      if(window.parent&&typeof window.parent.copyCanvasContent==='function'){
        e.preventDefault();
        window.parent.copyCanvasContent();
      }
    }
  });
  document.addEventListener('mouseenter', function(){ hint.style.opacity='1'; clearTimeout(timer); });
  document.addEventListener('mouseleave', function(){ timer=setTimeout(function(){ hint.style.opacity='0'; },1200); });
})();
<\/script>`;

  let modifiedHtml = html;
  if (modifiedHtml.includes('</html>')) {
    modifiedHtml = modifiedHtml.replace('</html>', copyHandler + '</html>');
  } else if (modifiedHtml.includes('</body>')) {
    modifiedHtml = modifiedHtml.replace('</body>', copyHandler + '</body>');
  } else {
    modifiedHtml = modifiedHtml + copyHandler;
  }

  const iframe = document.createElement('iframe');
  iframe.className = 'canvas-html-frame';
  iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');
  iframe.setAttribute('loading', 'lazy');

  iframe.srcdoc = modifiedHtml;
  wrap.appendChild(iframe);
  container.appendChild(wrap);
}

// ── svg renderer ──────────────────────────────────────────────────────────

function renderCanvasSVG(container, svgContent) {
  const wrap = document.createElement('div');
  wrap.className = 'canvas-svg-wrap';

  // sanitize: only allow <svg> and children
  const clean = svgContent.trim().startsWith('<svg') ? svgContent : '<svg>' + svgContent + '</svg>';
  wrap.innerHTML = clean;

  // ensure svg fills container nicely
  const svg = wrap.querySelector('svg');
  if (svg) {
    svg.style.maxWidth = '100%';
    svg.style.maxHeight = '100%';
    svg.style.height = 'auto';
    if (!svg.getAttribute('width')) svg.setAttribute('width', '100%');
  }

  container.appendChild(wrap);
}

// ── pdf renderer ──────────────────────────────────────────────────────────

function renderCanvasPDF(container, content) {
  const wrap = document.createElement('div');
  wrap.className = 'canvas-pdf-wrap';

  // if content is a URL (from workspace), embed in iframe
  if (Canvas._currentPath && S.session) {
    const url = `api/file/raw?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(Canvas._currentPath)}`;
    const iframe = document.createElement('iframe');
    iframe.src = url;
    iframe.style.cssText = 'width:100%;height:100%;border:none;';
    wrap.appendChild(iframe);
  } else {
    // if raw PDF bytes as blob
    wrap.innerHTML = '<div class="canvas-empty"><div class="canvas-empty-icon">' + canvasIcon('pdf') + '</div><div class="canvas-empty-text">pdf preview requires a file path<br>open from the workspace file tree</div></div>';
  }

  container.appendChild(wrap);
}

// ── markdown renderer ─────────────────────────────────────────────────────

function renderCanvasMD(container, mdContent) {
  const div = document.createElement('div');
  div.className = 'canvas-md';
  div.innerHTML = renderMd(mdContent);
  container.appendChild(div);

  // post-render hooks
  requestAnimationFrame(() => {
    if (typeof renderKatexBlocks === 'function') renderKatexBlocks();
    if (typeof renderMermaidBlocks === 'function') renderMermaidBlocks();
  });
}

// ── code renderer ─────────────────────────────────────────────────────────

function renderCanvasCode(container, code, lang) {
  // header bar
  const header = document.createElement('div');
  header.className = 'canvas-code-header';

  const langLabel = document.createElement('span');
  langLabel.className = 'canvas-code-lang';
  langLabel.textContent = lang || 'text';

  const copyBtn = document.createElement('button');
  copyBtn.className = 'canvas-copy-btn';
  copyBtn.textContent = 'copy';
  copyBtn.onclick = () => {
    navigator.clipboard.writeText(code).then(() => {
      copyBtn.textContent = 'copied';
      setTimeout(() => { copyBtn.textContent = 'copy'; }, 1500);
    });
  };

  header.appendChild(langLabel);
  header.appendChild(copyBtn);
  container.appendChild(header);

  // code body with line numbers
  const codeEl = document.createElement('div');
  codeEl.className = 'canvas-code';

  const lines = code.split('\n');
  lines.forEach((line, i) => {
    const lineEl = document.createElement('div');
    lineEl.className = 'canvas-code-line';

    const numEl = document.createElement('span');
    numEl.className = 'canvas-line-num';
    numEl.textContent = i + 1;

    const contentEl = document.createElement('span');
    contentEl.className = 'canvas-line-content';
    // use textContent for safety, then apply prism highlighting if available
    contentEl.textContent = line;

    lineEl.appendChild(numEl);
    lineEl.appendChild(contentEl);
    codeEl.appendChild(lineEl);
  });

  container.appendChild(codeEl);

  // apply prism highlighting after DOM insert
  requestAnimationFrame(() => {
    if (typeof Prism !== 'undefined') {
      codeEl.querySelectorAll('.canvas-line-content').forEach(el => {
        const langClass = lang ? `language-${lang}` : '';
        if (langClass) {
          el.innerHTML = '<code class="' + langClass + '">' + esc(el.textContent) + '</code>';
          try { Prism.highlightElement(el.querySelector('code')); } catch(e) {}
        }
      });
    }
  });
}

// ── json renderer (tree view) ─────────────────────────────────────────────

function renderCanvasJSON(container, jsonStr) {
  const div = document.createElement('div');
  div.className = 'canvas-json';

  let parsed;
  try {
    parsed = JSON.parse(jsonStr);
  } catch(e) {
    // not valid json — show as code
    renderCanvasCode(container, jsonStr, 'json');
    return;
  }

  div.appendChild(buildJsonTree(parsed, ''));
  container.appendChild(div);
}

function buildJsonTree(obj, path) {
  const frag = document.createDocumentFragment();

  if (obj === null) {
    const span = document.createElement('span');
    span.className = 'canvas-json-null';
    span.textContent = 'null';
    frag.appendChild(span);
    return frag;
  }

  if (typeof obj !== 'object') {
    const span = document.createElement('span');
    if (typeof obj === 'string') { span.className = 'canvas-json-string'; span.textContent = '"' + esc(obj) + '"'; }
    else if (typeof obj === 'number') { span.className = 'canvas-json-number'; span.textContent = obj; }
    else if (typeof obj === 'boolean') { span.className = 'canvas-json-bool'; span.textContent = obj; }
    frag.appendChild(span);
    return frag;
  }

  const isArray = Array.isArray(obj);
  const entries = isArray ? obj.map((v, i) => [i, v]) : Object.entries(obj);
  const collapsed = entries.length > 10; // auto-collapse big arrays/objects

  const toggle = document.createElement('span');
  toggle.className = 'canvas-json-toggle';
  toggle.textContent = collapsed ? '▶' : '▽';

  const open = document.createElement('span');
  open.textContent = isArray ? '[' : '{';

  const close = document.createElement('span');
  close.textContent = isArray ? ']' : '}';

  const body = document.createElement('div');
  body.style.marginLeft = '12px';
  if (collapsed) body.classList.add('canvas-json-collapsed');

  toggle.onclick = () => {
    body.classList.toggle('canvas-json-collapsed');
    toggle.textContent = body.classList.contains('canvas-json-collapsed') ? '▶' : '▽';
  };

  entries.forEach(([key, val], i) => {
    const line = document.createElement('div');
    if (!isArray) {
      const keySpan = document.createElement('span');
      keySpan.className = 'canvas-json-key';
      keySpan.textContent = '"' + esc(String(key)) + '": ';
      line.appendChild(keySpan);
    }
    line.appendChild(buildJsonTree(val, path + '.' + key));
    if (i < entries.length - 1) line.appendChild(document.createTextNode(','));
    body.appendChild(line);
  });

  frag.appendChild(toggle);
  frag.appendChild(open);
  frag.appendChild(body);
  frag.appendChild(close);
  return frag;
}

// ── csv renderer ──────────────────────────────────────────────────────────

function renderCanvasCSV(container, csvStr) {
  const wrap = document.createElement('div');
  wrap.className = 'canvas-csv';

  const table = document.createElement('table');

  const lines = csvStr.split('\n').filter(l => l.trim());
  if (lines.length === 0) {
    wrap.innerHTML = '<div class="canvas-empty"><div class="canvas-empty-icon">' + canvasIcon('csv') + '</div><div class="canvas-empty-text">empty csv</div></div>';
    container.appendChild(wrap);
    return;
  }

  // detect delimiter
  const firstLine = lines[0];
  const delim = firstLine.split('\t').length > firstLine.split(',').length ? '\t' : ',';

  const thead = document.createElement('thead');
  const tbody = document.createElement('tbody');

  lines.forEach((line, i) => {
    const row = document.createElement('tr');
    parseCSVLine(line, delim).forEach(cell => {
      const el = document.createElement(i === 0 ? 'th' : 'td');
      el.textContent = cell.trim();
      row.appendChild(el);
    });
    (i === 0 ? thead : tbody).appendChild(row);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  wrap.appendChild(table);
  container.appendChild(wrap);
}

// simple csv line parser (handles quoted fields)
function parseCSVLine(line, delim) {
  const cells = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') { current += '"'; i++; }
        else inQuotes = false;
      } else current += ch;
    } else {
      if (ch === '"') inQuotes = true;
      else if (ch === delim) { cells.push(current); current = ''; }
      else current += ch;
    }
  }
  cells.push(current);
  return cells;
}

// ── image renderer ────────────────────────────────────────────────────────

function renderCanvasImage(container, content) {
  const wrap = document.createElement('div');
  wrap.className = 'canvas-image-wrap';

  const img = document.createElement('img');
  if (Canvas._currentPath && S.session) {
    img.src = `api/file/raw?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(Canvas._currentPath)}`;
  } else if (content.startsWith('data:') || content.startsWith('http')) {
    img.src = content;
  }
  img.alt = Canvas._currentTitle;
  img.style.cssText = 'max-width:100%;max-height:100%;object-fit:contain;border-radius:6px;';
  img.onerror = () => { img.alt = 'failed to load image'; };

  wrap.appendChild(img);
  container.appendChild(wrap);
}

// ── mermaid renderer ──────────────────────────────────────────────────────

function renderCanvasMermaid(container, mermaidCode) {
  const wrap = document.createElement('div');
  wrap.className = 'canvas-mermaid-wrap';

  const pre = document.createElement('pre');
  pre.className = 'mermaid';
  pre.textContent = mermaidCode;
  wrap.appendChild(pre);
  container.appendChild(wrap);

  // trigger mermaid rendering
  requestAnimationFrame(() => {
    if (typeof mermaid !== 'undefined' && mermaid.run) {
      try { mermaid.run({ nodes: [pre] }); } catch(e) {}
    }
  });
}

// ── icons ─────────────────────────────────────────────────────────────────

function canvasIcon(type) {
  const icons = {
    html: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    svg: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
    pdf: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    md: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    code: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    json: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h10"/></svg>',
    csv: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>',
    image: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>',
    mermaid: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
  };
  return icons[type] || icons.code;
}

// ── resize handle ─────────────────────────────────────────────────────────

function initCanvasResize() {
  const handle = $c('canvasResize');
  const panel = $c('canvasPanel');
  if (!handle || !panel) return;

  let startX, startW;

  handle.onmousedown = (e) => {
    e.preventDefault();
    startX = e.clientX;
    startW = panel.offsetWidth;
    Canvas._resizeState = { startX, startW };
    handle.classList.add('active');
    document.addEventListener('mousemove', onCanvasResize);
    document.addEventListener('mouseup', onCanvasResizeEnd);
  };

  function onCanvasResize(e) {
    if (!Canvas._resizeState) return;
    const { startX, startW } = Canvas._resizeState;
    const delta = startX - e.clientX; // dragging left = growing
    const newW = Math.max(320, Math.min(800, startW + delta));
    panel.style.width = newW + 'px';
    panel.style.minWidth = newW + 'px';
  }

  function onCanvasResizeEnd() {
    Canvas._resizeState = null;
    handle.classList.remove('active');
    document.removeEventListener('mousemove', onCanvasResize);
    document.removeEventListener('mouseup', onCanvasResizeEnd);
  }
}

// ── open file from workspace ──────────────────────────────────────────────

async function openFileInCanvas(path) {
  if (!S.session) return;
  const ext = fileExt(path);
  const type = canvasTypeForExt(ext);

  // for images and pdfs, we use the raw endpoint
  if (type === 'image' || type === 'pdf') {
    openCanvas(type, path.split('/').pop(), '', { path });
    return;
  }

  // fetch text content
  try {
    const data = await api(`/api/file?session_id=${encodeURIComponent(S.session.session_id)}&path=${encodeURIComponent(path)}`);
    if (data.binary) {
      // fallback: download
      downloadFile(path);
      return;
    }
    openCanvas(type, path.split('/').pop(), data.content, { path });
  } catch(e) {
    console.warn('[canvas] failed to open file:', path, e);
  }
}

// ── open content from chat message ────────────────────────────────────────

function openCodeBlockInCanvas(lang, code, messageIdx) {
  const type = canvasTypeForLang(lang);
  const title = lang ? `${lang} snippet` : 'code snippet';
  openCanvas(type, title, code);
}

// ── inline card for chat messages ─────────────────────────────────────────
// renders as a compact clickable card inside the message, which opens canvas on click

function createCanvasInlineCard(type, title, content) {
  const card = document.createElement('div');
  card.className = 'canvas-inline-card';
  card.onclick = () => openCanvas(type, title, content);

  // preview area
  const preview = document.createElement('div');
  preview.className = 'canvas-inline-preview';

  if (type === 'html') {
    // larger iframe preview — scaled down to show more context
    const iframe = document.createElement('iframe');
    iframe.srcdoc = content;
    iframe.style.cssText = 'width:480px;height:320px;transform:scale(0.5);transform-origin:top left;pointer-events:none;border:none;';
    iframe.setAttribute('sandbox', 'allow-scripts');
    preview.style.cssText = 'height:160px;';
    preview.appendChild(iframe);
  } else if (type === 'svg') {
    preview.innerHTML = content.startsWith('<svg') ? content : '';
    const svg = preview.querySelector('svg');
    if (svg) { svg.style.cssText = 'max-width:100%;max-height:140px;'; }
  } else {
    // code preview
    const code = document.createElement('code');
    const previewLines = content.split('\n').slice(0, 8).join('\n');
    code.textContent = previewLines + (content.split('\n').length > 8 ? '\n...' : '');
    preview.appendChild(code);
  }

  card.appendChild(preview);

  // footer
  const footer = document.createElement('div');
  footer.className = 'canvas-inline-footer';

  const typeBadge = document.createElement('span');
  typeBadge.className = 'canvas-inline-type canvas-header-badge ' + canvasBadgeClass(type);
  typeBadge.textContent = canvasBadgeLabel(type);

  const nameEl = document.createElement('span');
  nameEl.className = 'canvas-inline-name';
  nameEl.textContent = title;

  const openEl = document.createElement('span');
  openEl.className = 'canvas-inline-open';
  openEl.textContent = 'open ↗';

 footer.appendChild(typeBadge);
 footer.appendChild(nameEl);
 footer.appendChild(openEl);

  // add copy button
  const copyEl = document.createElement('span');
  copyEl.className = 'canvas-inline-copy';
  copyEl.textContent = 'copy';
  copyEl.style.cssText = 'margin-left:8px;cursor:pointer;font-size:10px;';
  copyEl.onclick = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(content).then(() => {
      if (typeof showToast === 'function') showToast('copied');
    });
  };
  footer.appendChild(copyEl);
 card.appendChild(footer);

  return card;
}

// ── detect canvas-worthy content in messages ──────────────────────────────
// scans a rendered message for large code blocks or HTML/SVG blocks
// and appends canvas inline cards after them

function injectCanvasCards(messageEl) {
  if (!messageEl) return;

  const msgBody = messageEl.querySelector('.msg-body');
  if (!msgBody) return;

  // check if this is the last (most recent) assistant message row
  const row = messageEl.closest('.msg-row');
  const msgContainer = messageEl.closest('#msgInner');
  let isLatest = false;
  if (row && msgContainer) {
    const allRows = msgContainer.querySelectorAll('.msg-row');
    isLatest = row === allRows[allRows.length - 1];
  }

  // find fenced code blocks
  const codeBlocks = msgBody.querySelectorAll('pre code');
  if (codeBlocks.length === 0) return;

  codeBlocks.forEach(codeEl => {
    const pre = codeEl.closest('pre');
    if (!pre) return;

    // extract language from class like "language-html"
    const langClass = Array.from(codeEl.classList).find(c => c.startsWith('language-'));
    const lang = langClass ? langClass.replace('language-', '') : '';
    const code = codeEl.textContent;

    // only add canvas cards for substantial blocks or special types
    const type = canvasTypeForLang(lang);
    const isSpecial = type === 'html' || type === 'svg' || type === 'mermaid';
    const isLong = code.split('\n').length > 12 || code.length > 500;

    if (!isSpecial && !isLong) return;

    // check if card already exists after this pre
    if (pre.nextElementSibling && pre.nextElementSibling.classList.contains('canvas-inline-card')) return;

   const title = lang ? `${lang} block` : 'code block';
   const card = createCanvasInlineCard(type, title, code);
   pre.insertAdjacentElement('afterend', card);
   // hide the original code block to avoid duplication
   pre.style.display = 'none';

   // auto-open canvas panel for visualizable content in the latest message
   if (isLatest && isSpecial) {
     openCanvas(type, title, code);
   }
  });
}

// ── detect file path references in messages ───────────────────────────────
// makes `/path/to/file.html` clickable to open in canvas

function injectCanvasFileLinks(messageEl) {
  if (!messageEl || !S.session) return;
  const msgBody = messageEl.querySelector('.msg-body');
  if (!msgBody) return;

  // find text nodes that look like file paths
  const walker = document.createTreeWalker(msgBody, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);

  const pathRe = /(?:^|\s|['"`(])(\/[\w\-\.\/]+\.\w{1,12})(?:$|\s|['"`),;])/g;

  textNodes.forEach(node => {
    const text = node.textContent;
    if (!pathRe.test(text)) return;
    pathRe.lastIndex = 0;

    const frag = document.createDocumentFragment();
    let lastIdx = 0;
    let match;
    while ((match = pathRe.exec(text)) !== null) {
      const [full, path] = match;
      const start = match.index + (full.indexOf(path));
      const end = start + path.length;

      // text before match
      if (start > lastIdx) frag.appendChild(document.createTextNode(text.slice(lastIdx, start)));

      // check if path looks like a viewable file
      const ext = fileExt(path);
      const type = canvasTypeForExt(ext);
      const isViewable = CANVAS_HTML_EXTS.has(ext) || CANVAS_SVG_EXTS.has(ext) || CANVAS_MD_EXTS.has(ext) || CANVAS_PDF_EXTS.has(ext) || CANVAS_IMAGE_EXTS.has(ext) || CANVAS_MERMAID_EXTS.has(ext);

      if (isViewable) {
        const a = document.createElement('a');
        a.href = '#';
        a.className = 'canvas-file-link';
        a.textContent = path;
        a.style.cssText = 'color:var(--blue,#6cb4ff);cursor:pointer;text-decoration:underline;';
        a.onclick = (e) => { e.preventDefault(); openFileInCanvas(path); };
        frag.appendChild(a);
      } else {
        frag.appendChild(document.createTextNode(path));
      }

      lastIdx = end;
    }

    if (lastIdx < text.length) frag.appendChild(document.createTextNode(text.slice(lastIdx)));
    if (frag.childNodes.length) node.parentNode.replaceChild(frag, node);
  });
}

// ── copy content ──────────────────────────────────────────────────────────

function copyCanvasContent() {
  const ver = Canvas._versions[Canvas._activeVersion];
  if (!ver) return;
  navigator.clipboard.writeText(ver.content).then(() => {
    showToast('copied to clipboard');
  });
}

// ── download content ──────────────────────────────────────────────────────

function downloadCanvasContent() {
  const ver = Canvas._versions[Canvas._activeVersion];
  if (!ver) return;

  const blob = new Blob([ver.content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = ver.title || 'artifact';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
}

// ── init ──────────────────────────────────────────────────────────────────

function initCanvas() {
  initCanvasResize();

  // close button
  const closeBtn = $c('canvasCloseBtn');
  if (closeBtn) closeBtn.onclick = closeCanvas;

  // fullscreen button
  const fsBtn = $c('canvasFullscreenBtn');
  if (fsBtn) fsBtn.onclick = toggleCanvasFullscreen;

  // copy button
  const copyBtn = $c('canvasCopyBtn');
  if (copyBtn) copyBtn.onclick = copyCanvasContent;

  // download button
  const dlBtn = $c('canvasDownloadBtn');
  if (dlBtn) dlBtn.onclick = downloadCanvasContent;

  // mode tabs
  document.querySelectorAll('.canvas-mode-tab').forEach(tab => {
    tab.onclick = () => setCanvasMode(tab.dataset.mode);
  });

  // keyboard shortcut: Ctrl+C / Cmd+C to copy canvas content
  // Works for focus in the canvas body area or inside the iframe
  const body = $c('canvasBody');
  if (body) {
    body.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
        if (Canvas._open) {
          copyCanvasContent();
          e.preventDefault();
        }
      }
    });
  }

  // also catch Ctrl+C when focus is inside an iframe within the canvas
  document.addEventListener('keydown', function(e) {
    if (!Canvas._open) return;
    if (!(e.ctrlKey || e.metaKey) || e.key !== 'c') return;
    // check if focus is within the canvas panel (including iframes)
    const panel = $c('canvasPanel');
    if (!panel) return;
    // If activeElement is inside the panel or is an iframe inside the panel
    if (panel.contains(document.activeElement)) {
      copyCanvasContent();
      e.preventDefault();
    }
  });
}

// ── expose globally ───────────────────────────────────────────────────────

window.Canvas = Canvas;
window.openCanvas = openCanvas;
window.closeCanvas = closeCanvas;
window.toggleCanvas = toggleCanvas;
window.openFileInCanvas = openFileInCanvas;
window.openCodeBlockInCanvas = openCodeBlockInCanvas;
window.injectCanvasCards = injectCanvasCards;
window.injectCanvasFileLinks = injectCanvasFileLinks;
window.initCanvas = initCanvas;
window.addCanvasVersion = addCanvasVersion;
window.canvasTypeForExt = canvasTypeForExt;
