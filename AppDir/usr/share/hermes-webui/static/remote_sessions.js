// Sessions Loader

(function() {
  'use strict';

  let _remoteSessions = [];
  let _localSessions = [];
  const REMOTE_SESSIONS_API = '/api/remote/sessions';

  // Fetch sessions from server
  async function fetchRemoteSessions() {
    try {
      console.log('[Sessions] Fetching from', REMOTE_SESSIONS_API);
      const response = await fetch(REMOTE_SESSIONS_API, { credentials: 'include' });
      if (!response.ok) {
        console.warn('[Sessions] Failed to fetch sessions:', response.status);
        return [];
      }
      const data = await response.json();
      console.log('[Sessions] API response:', data);
      if (data.ok && Array.isArray(data.sessions)) {
        console.log('[Sessions] Loaded', data.sessions.length, 'sessions from', data.source);
        if (data.errors && data.errors.length > 0) {
          console.warn('[Sessions] API errors:', data.errors);
        }
        if (data.debug && data.debug.length > 0) {
          console.log('[Sessions] Debug info:', data.debug);
        }
        // Log first few sessions for debugging
        data.sessions.slice(0, 5).forEach((s, i) => {
          console.log(`[Sessions] Session ${i}:`, s.session_id, s.title, s.source);
        });
        return data.sessions.map(s => ({
          ...s,
          _remote: true,  
          _source: data.source
        }));
      }
      console.warn('[Sessions] Invalid response format:', data);
      return [];
    } catch (e) {
      console.warn('[Sessions] Error fetching sessions:', e);
      return [];
    }
  }

  // Wrap the original renderSessionList if it exists
  function wrapRenderSessionList() {
    if (typeof window.renderSessionList === 'function' && !window._originalRenderSessionList) {
      window._originalRenderSessionList = window.renderSessionList;

      window.renderSessionList = async function() {
        // Fetch remote sessions before rendering
        _remoteSessions = await fetchRemoteSessions();

        // Call original function
        const result = await window._originalRenderSessionList.apply(this, arguments);

        // After rendering, merge remote sessions into the DOM
        mergeRemoteSessions();

        return result;
      };

      console.log('[Sessions] Wrapped renderSessionList');
    }
  }

  // Merge remote sessions into the session list in the DOM
  function mergeRemoteSessions() {
    const sessionList = document.getElementById('sessionList');
    if (!sessionList) {
      console.warn('[Sessions] sessionList element not found');
      return;
    }

    console.log('[Sessions] Merging', _remoteSessions.length, 'remote sessions into DOM');

    // Always remove old section if it exists (it may have been cleared by renderSessionList)
    let remoteSection = document.getElementById('remoteSessionsSection');
    if (remoteSection) {
      remoteSection.remove();
    }

    // Create new section if we have remote sessions
    if (_remoteSessions.length > 0) {
      remoteSection = document.createElement('div');
      remoteSection.id = 'remoteSessionsSection';
      remoteSection.className = 'session-section remote-sessions';

      // Add a header
      const header = document.createElement('div');
      header.className = 'session-section-header';
      header.innerHTML = '<span class="section-title">Remote Sessions (.250)</span>';
      header.style.cssText = 'padding: 8px 12px; font-weight: 600; color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); margin-bottom: 4px;';
      remoteSection.appendChild(header);

      // Add session items
      _remoteSessions.forEach(session => {
        const item = createSessionItem(session, true);
        remoteSection.appendChild(item);
      });

      // Insert at the top of the session list
      const firstChild = sessionList.firstChild;
      if (firstChild) {
        sessionList.insertBefore(remoteSection, firstChild);
      } else {
        sessionList.appendChild(remoteSection);
      }

      console.log('[Sessions] Added', _remoteSessions.length, 'sessions to DOM');
    } else {
      console.log('[Sessions] No remote sessions to add');
    }
  }

  // Create a session list item element
  function createSessionItem(session, isRemote) {
    const div = document.createElement('div');
    div.className = 'session-item' + (isRemote ? ' remote-session' : '');
    div.dataset.sessionId = session.session_id;
    div.dataset.isRemote = isRemote ? 'true' : 'false';

    const title = session.title || session.session_id || 'Untitled';
    const timestamp = session.updated_at || session.created_at;
    const timeStr = timestamp ? new Date(timestamp * 1000).toLocaleString() : '';

    div.innerHTML = `
      <div class="session-item-title">${escapeHtml(title)}</div>
      ${timeStr ? `<div class="session-item-time">${escapeHtml(timeStr)}</div>` : ''}
    `;

    div.onclick = () => loadRemoteSession(session);
    div.oncontextmenu = (e) => { e.preventDefault(); showSessionMenu(session, div, isRemote); };

    return div;
  }

  // Load a remote session (needs to be imported or viewed)
  async function loadRemoteSession(session) {
    try {
      showToast(`Loading session: ${session.title || session.session_id}...`);

      // Fetch full session content from remote
      const response = await fetch(`/api/remote/sessions/${encodeURIComponent(session.session_id)}`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`Failed to load remote session: ${response.status}`);
      }

      const data = await response.json();

      if (data.ok && data.session) {
        // Import the session into local storage
        const importResponse = await fetch('/api/session/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(data.session)
        });

        if (!importResponse.ok) {
          throw new Error('Failed to import remote session');
        }

        const imported = await importResponse.json();

        if (imported.ok && imported.session) {
          // Load the imported session
          if (typeof loadSession === 'function') {
            await loadSession(imported.session.session_id);
          }
          showToast('Session loaded');
          if (typeof renderSessionList === 'function') {
            await renderSessionList();
          }
        }
      }
    } catch (e) {
      console.error('[Sessions] Error loading remote session:', e);
      showToast('Error loading session: ' + e.message);
    }
  }

  // Escape HTML to prevent XSS
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Show toast notification (fallback if global function not available)
  function showToast(message) {
    if (typeof window.showToast === 'function') {
      window.showToast(message);
    } else {
      console.log('[Sessions]', message);
    }
  }

  // Handle session right-click menu
  function showSessionMenu(session, element, isRemote) {
    const existing = document.getElementById('sessionContextMenu');
    if (existing) existing.remove();

    const menu = document.createElement('div');
    menu.id = 'sessionContextMenu';
    menu.style.cssText = 'position:fixed;z-index:9999;background:var(--bg,#222);border:1px solid var(--border,#444);border-radius:6px;padding:4px 0;min-width:150px;box-shadow:0 4px 12px rgba(0,0,0,.4);';

    const renameBtn = document.createElement('div');
    renameBtn.textContent = 'Rename';
    renameBtn.style.cssText = 'padding:8px 12px;cursor:pointer;font-size:13px;color:var(--text,#eee);';
    renameBtn.onmouseover = () => renameBtn.style.background = 'var(--hover,#333)';
    renameBtn.onmouseout = () => renameBtn.style.background = '';
    renameBtn.onclick = () => { menu.remove(); promptRenameSession(session, isRemote); };

    const deleteBtn = document.createElement('div');
    deleteBtn.textContent = 'Delete';
    deleteBtn.style.cssText = 'padding:8px 12px;cursor:pointer;font-size:13px;color:#f66;';
    deleteBtn.onmouseover = () => deleteBtn.style.background = 'var(--hover,#333)';
    deleteBtn.onmouseout = () => deleteBtn.style.background = '';
    deleteBtn.onclick = () => { menu.remove(); deleteSessionFromMenu(session, isRemote); };

    menu.appendChild(renameBtn);
    menu.appendChild(deleteBtn);

    const rect = element.getBoundingClientRect();
    menu.style.left = rect.left + 'px';
    menu.style.top = (rect.bottom + 4) + 'px';
    document.body.appendChild(menu);

    const closeMenu = (e) => { if (!menu.contains(e.target)) menu.remove(); };
    setTimeout(() => document.addEventListener('click', closeMenu), 0);
    setTimeout(() => document.addEventListener('contextmenu', closeMenu), 0);
  }

  async function promptRenameSession(session, isRemote) {
    const newTitle = prompt('Enter new title:', session.title || session.session_id);
    if (!newTitle || newTitle === session.title) return;
    try {
      const res = await fetch('/api/session/rename', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({session_id: session.session_id, title: newTitle})
      });
      const d = await res.json();
      if (d.ok) { showToast('Session renamed'); renderSessionList(); }
      else { showToast('Failed to rename'); }
    } catch(e) { showToast('Error: ' + e.message); }
  }

  async function deleteSessionFromMenu(session, isRemote) {
    if (!confirm('Delete session "' + (session.title || session.session_id) + '"?')) return;
    try {
      const res = await fetch('/api/session/delete', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({session_id: session.session_id})
      });
      const d = await res.json();
      if (d.ok) { showToast('Session deleted'); renderSessionList(); }
      else { showToast('Failed to delete'); }
    } catch(e) { showToast('Error: ' + e.message); }
  }

  // Enabled - wrap renderSessionList to fetch remote sessions
  console.log('[Sessions] Module loaded (wrapping enabled)');

  // Wait for DOM to be ready then wrap
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wrapRenderSessionList);
  } else {
    wrapRenderSessionList();
  }

  // Expose for debugging
  window.Sessions = {
    fetchRemoteSessions,
    getRemoteSessions: () => _remoteSessions
  };
})();
