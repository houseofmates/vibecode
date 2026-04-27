// Workspace layering system
const MACHINES = [
  { id: 'ubuntu', label: 'ubuntu home', hostname: '192.168.4.250', default_workspace: '/home/house', color: 'blue' },
  { id: 'pop_os', label: 'pop! os home', hostname: '192.168.4.233', default_workspace: '/home/house', color: 'yellow' }
];

function getWsMachines() {
  try { return JSON.parse(localStorage.getItem('hermes_ws_machines') || '{}'); } catch(e) { return {}; }
}

function setWsMachine(path, mid) {
  const a = getWsMachines();
  a[path] = mid;
  localStorage.setItem('hermes_ws_machines', JSON.stringify(a));
}

function getMachines() { return MACHINES; }

const _origLoadWorkspacesPanel = window.loadWorkspacesPanel;
window.loadWorkspacesPanel = async function() {
  const panel = document.getElementById('workspacesPanel');
  if (!panel) return;
  // Clear cache to ensure fresh data
  localStorage.removeItem('hermes-workspaces-cache');
  // Always load workspaces regardless of session
  const data = await loadWorkspaceList();
  const workspaces = data.workspaces || [];
  const assignments = getWsMachines();
  for (const ws of workspaces) {
    if (!assignments[ws.path]) {
      if (ws._machine) {
        setWsMachine(ws.path, ws._machine);
      } else {
        setWsMachine(ws.path, 'ubuntu');
      }
    }
  }
  const updated = getWsMachines();
  const wsByMachine = {};
  for (const ws of workspaces) {
    const mid = updated[ws.path] || ws._machine || 'ubuntu';
    if (!wsByMachine[mid]) wsByMachine[mid] = [];
    wsByMachine[mid].push(ws);
  }
  renderMachinePanel(panel, MACHINES, wsByMachine);
};

function renderMachinePanel(panel, machines, wsByMachine) {
  panel.innerHTML = '';
  for (const m of machines) {
    const card = document.createElement('div');
    card.className = 'ws-machine-card ' + m.color;
    card.dataset.machineId = m.id;
    
    const hdr = document.createElement('div');
    hdr.className = 'ws-machine-header';
    hdr.innerHTML = '<span class="ws-machine-icon">' + li('monitor',14) + '</span>' +
      '<span class="ws-machine-label">' + esc(m.label) + '</span>' +
      '<span class="ws-machine-ip">' + esc(m.hostname) + '</span>';
    
    // Click to go to /home/house of that machine
    hdr.onclick = async function() { 
      showToast('Switching to ' + m.label + ' /home/house...');
      await switchToWorkspace(m.default_workspace, m.label, m.id); 
    };
    
    // Right-click for context menu
    hdr.oncontextmenu = function(e) { 
      e.preventDefault(); 
      e.stopPropagation(); 
      showMachineMenu(m, e.clientX, e.clientY); 
    };
    
    card.appendChild(hdr);
    
    const wsList = wsByMachine[m.id] || [];
    const ch = document.createElement('div');
    ch.className = 'ws-machine-children';
    
    for (const w of wsList) {
      const row = document.createElement('div');
      row.className = 'ws-row';
      row.dataset.path = w.path;
      row.style.cssText = 'padding:8px 12px;border-radius:10px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);cursor:pointer;margin-bottom:6px;';

      row.innerHTML = '<div style="flex:1;min-width:0;"><div style="font-size:13px;color:var(--text);font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + esc(w.name) + '</div>' +
        '<div style="font-size:11px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + esc(w.path) + '</div></div>';

      // Left-click to switch
      row.onclick = function(e) {
        if (e.button === 2) return;
        switchToWorkspace(w.path, w.name, m.id);
      };

      // Right-click context menu with rename and remove
      row.oncontextmenu = function(e) {
        e.preventDefault();
        e.stopPropagation();
        showWorkspaceContextMenu(e, w.path, w.name, m.id);
      };

      ch.appendChild(row);
    }
    
    card.appendChild(ch);
    panel.appendChild(card);
  }
}

var _machineMenu = null;
var _workspaceMenu = null;

function showWorkspaceContextMenu(e, path, name, machineId) {
  hideWorkspaceMenu();
  var menu = document.createElement('div');
  menu.className = 'context-menu machine-context-menu';
  menu.style.cssText = 'position:fixed;background:#0a0a0a;border:1px solid rgba(255,255,255,0.1);border-radius:8px;box-shadow:0 4px 24px rgba(0,0,0,.6);z-index:1000;min-width:160px;overflow:hidden;';
  menu.style.left = e.clientX + 'px';
  menu.style.top = e.clientY + 'px';

  // Rename option
  var renameOpt = document.createElement('div');
  renameOpt.style.cssText = 'padding:8px 14px;font-size:12px;color:var(--text);cursor:pointer;transition:background .12s;text-transform:lowercase;';
  renameOpt.textContent = 'rename';
  renameOpt.onmouseover = function() { this.style.background = 'rgba(255,255,255,.05)'; };
  renameOpt.onmouseout = function() { this.style.background = ''; };
  renameOpt.onclick = function() {
    hideWorkspaceMenu();
    renameWorkspaceCard(path, name);
  };
  menu.appendChild(renameOpt);

  // Remove option
  var removeOpt = document.createElement('div');
  removeOpt.style.cssText = 'padding:8px 14px;font-size:12px;color:#f87171;cursor:pointer;transition:background .12s;text-transform:lowercase;border-top:1px solid rgba(255,255,255,0.05);';
  removeOpt.textContent = 'remove';
  removeOpt.onmouseover = function() { this.style.background = 'rgba(248,113,113,.08)'; };
  removeOpt.onmouseout = function() { this.style.background = ''; };
  removeOpt.onclick = function() {
    hideWorkspaceMenu();
    deleteWorkspaceCard(path);
  };
  menu.appendChild(removeOpt);

  document.body.appendChild(menu);
  _workspaceMenu = menu;
  setTimeout(function() { document.addEventListener('click', hideWorkspaceMenu, {once:true}); }, 10);
}

function hideWorkspaceMenu() {
  if (_workspaceMenu) {
    _workspaceMenu.remove();
    _workspaceMenu = null;
  }
}

async function renameWorkspaceCard(path, oldName) {
  var result = await showPromptDialog({
    title: 'rename workspace',
    message: 'enter new name:',
    confirmLabel: 'rename',
    cancelLabel: 'cancel',
    placeholder: oldName,
    value: oldName
  });

  if (!result || !result.trim() || result.trim() === oldName) return;

  var customWs = getCustomWorkspaces();
  var ws = customWs.find(function(w) { return w.path === path; });
  if (ws) {
    ws.name = result.trim();
    localStorage.setItem('hermes_custom_workspaces', JSON.stringify(customWs));
    showToast('workspace renamed');
    await loadWorkspacesPanel();
  }
}

function showMachineMenu(machine, x, y) {
  hideMachineMenu();
  var menu = document.createElement('div');
  menu.className = 'context-menu machine-context-menu';
  menu.style.position = 'fixed';
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';
  
  var addOpt = document.createElement('div');
  addOpt.className = 'cm-item';
  addOpt.innerHTML = '<span class="cm-icon">' + li('plus',12) + '</span><span>add</span>';
  addOpt.onclick = function() { 
    hideMachineMenu(); 
    promptAddWorkspace(machine); 
  };
  menu.appendChild(addOpt);
  
  document.body.appendChild(menu);
  _machineMenu = menu;
  setTimeout(function() { document.addEventListener('click', hideMachineMenu, {once:true}); }, 10);
}

function hideMachineMenu() { 
  if(_machineMenu) { 
    _machineMenu.remove(); 
    _machineMenu=null; 
  } 
}

async function promptAddWorkspace(machine) {
  var result = await showPromptDialog({ 
    title: 'add workspace to ' + machine.label, 
    message: 'enter the path to add at ' + machine.hostname + ':', 
    confirmLabel: 'add', 
    placeholder: '/home/house/myproject' 
  });
  
  if (!result || !result.trim()) return;
  
  var cleanPath = result.trim();
  
  // Clear all caches to ensure fresh data
  localStorage.removeItem('hermes-workspaces-cache');
  localStorage.removeItem('hermes_custom_workspaces');
  
  try {
    var data = await api('/api/workspaces/add', { method: 'POST', body: JSON.stringify({ path: cleanPath }) });
    setWsMachine(cleanPath, machine.id);
    showToast('workspace added to ' + machine.label);
    await loadWorkspacesPanel();
  } catch(e) {
    console.error('Failed to add workspace:', e);
    showToast('failed to add workspace: ' + e.message);
  }
}

function getCustomWorkspaces() {
  try { return JSON.parse(localStorage.getItem('hermes_custom_workspaces') || '[]'); } catch(e) { return []; }
}

async function deleteWorkspaceCard(path) {
  // Remove from localStorage
  var customWs = getCustomWorkspaces();
  customWs = customWs.filter(function(w) { return w.path !== path; });
  localStorage.setItem('hermes_custom_workspaces', JSON.stringify(customWs));

  var machines = getWsMachines();
  delete machines[path];
  localStorage.setItem('hermes_ws_machines', JSON.stringify(machines));

  // Clear workspace cache to prevent stale data
  localStorage.removeItem('hermes-workspaces-cache');

  // Also remove from backend workspace list
  try {
    await api('/api/workspaces/remove', { method: 'POST', body: JSON.stringify({ path: path }) });
  } catch(e) {
    console.warn('Failed to remove workspace from backend:', e);
  }

  showToast('workspace removed');
  await loadWorkspacesPanel();
}

var _origSwitch = window.switchToWorkspace;
window.switchToWorkspace = async function(path, name, machineId) {
  // If no session, let the original function handle creating one
  if (!S || !S.session) {
    return await _origSwitch(path, name, machineId);
  }

  if (machineId) {
    var machine = MACHINES.find(function(m) { return m.id === machineId; });
    if (machine) {
      S.session.machine_id = machine.id;
      S.session.machine_hostname = machine.hostname;
    }
  }

  // Use the correct API endpoint
  await api('/api/session/update', { method: 'POST', body: JSON.stringify({
    session_id: S.session.session_id, workspace: path, model: S.session.model
  })});
  S.session.workspace = path;
  syncTopbar();
  syncWorkspaceDisplays();
  if (typeof openWorkspacePanel === 'function') {
    openWorkspacePanel('browse');
  }
  await loadDir('.');
  showToast('switched to ' + (name || path));
};

console.log('workspace layering loaded');
