// Sessions Loader - with aggressive caching for .250 remote sessions

(function() {
  'use strict';

  let _remoteSessions = [];
  let _localSessions = [];
  // Detect Tauri and use the configured local backend URL
  const isCapacitorApp = !!(window.Capacitor || window.__capacitor || location.protocol==='capacitor:' || document.documentElement.classList.contains('apk-force-mobile'));
  const isTauri = !isCapacitorApp && (window.__TAURI__ || location.protocol==='tauri:' || location.protocol==='file:' || location.hostname==='tauri.localhost' || location.host==='tauri.localhost');
  const TAURI_API_BASE = window.HERMES_API_BASE || (()=>{ try{ return localStorage.getItem('hermes-api-base'); }catch(e){ return null; } })() || (()=>{ try{ return localStorage.getItem('hermes-api-origin'); }catch(e){ return null; } })() || 'http://localhost:8786';
  const API_BASE = isTauri ? TAURI_API_BASE : (window.HERMES_API_BASE || (isCapacitorApp && window.HERMES_DOMAIN ? `https://vc.${window.HERMES_DOMAIN}/` : location.origin));
  const REMOTE_SESSIONS_API = API_BASE.replace(/\/$/, '') + '/api/remote/sessions';

  // Cache configuration
  const CACHE_TTL_MS = 30000; // 30 seconds - background refresh interval
  let _lastFetchTime = 0;
  let _isFetching = false;
  let _pendingFetch = null;

  // Track recently deleted sessions to prevent re-adding from remote cache
  // Persist to localStorage to survive page reloads
  const _recentlyDeleted = new Set();
  const DELETED_STORAGE_KEY = 'hermes-deleted-sessions';

  function _loadDeletedSessions() {
    try {
      const stored = localStorage.getItem(DELETED_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Filter out entries older than 7 days to prevent infinite growth
        const now = Date.now();
        const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
        const validEntries = parsed.filter(entry => {
          // Handle both simple IDs and timestamped entries
          if (typeof entry === 'string') return true; // Legacy format, keep for now
          if (entry && entry.id && entry.deletedAt) {
            return (now - entry.deletedAt) < maxAge;
          }
          return true;
        }).map(entry => typeof entry === 'string' ? entry : entry.id);
        validEntries.forEach(id => _recentlyDeleted.add(id));
      }
    } catch (e) {
      console.warn('[Sessions] Failed to load deleted sessions from storage:', e);
    }
  }

  function _saveDeletedSessions() {
    try {
      const now = Date.now();
      // Load existing entries to preserve their timestamps
      let existing = [];
      try {
        existing = JSON.parse(localStorage.getItem(DELETED_STORAGE_KEY) || '[]');
      } catch (e) {}
      
      // Create map of existing entries by ID to preserve timestamps
      const existingMap = new Map();
      for (const entry of existing) {
        if (typeof entry === 'string') {
          existingMap.set(entry, now); // Legacy format, use current time
        } else if (entry && entry.id) {
          existingMap.set(entry.id, entry.deletedAt || now);
        }
      }
      
      // Merge: use existing timestamp if present, otherwise use now
      const entries = [..._recentlyDeleted].map(id => ({ 
        id, 
        deletedAt: existingMap.get(id) || now 
      }));
      
      localStorage.setItem(DELETED_STORAGE_KEY, JSON.stringify(entries));
    } catch (e) {
      console.warn('[Sessions] Failed to save deleted sessions to storage:', e);
    }
  }

  // Load deleted sessions on initialization
  _loadDeletedSessions();

  // Fetch sessions from remote .250/.233 for unified list
  async function fetchRemoteSessions(force = false) {
    const now = Date.now();
    
    // Return cached if fresh and not forced
    if (!force && _remoteSessions.length > 0 && (now - _lastFetchTime) < CACHE_TTL_MS) {
      console.log('[Sessions] Using cached remote sessions:', _remoteSessions.length);
      return _remoteSessions;
    }
    
    // Dedupe concurrent fetches
    if (_isFetching) {
      console.log('[Sessions] Fetch in progress, waiting...');
      return _pendingFetch || _remoteSessions;
    }
    
    _isFetching = true;
    _pendingFetch = _doFetchRemoteSessions().finally(() => {
      _isFetching = false;
      _pendingFetch = null;
    });
    
    return _pendingFetch;
  }
  
  // Internal fetch implementation
  async function _doFetchRemoteSessions() {
    try {
      console.log('[Sessions] Fetching from', REMOTE_SESSIONS_API);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);
      const response = await fetch(REMOTE_SESSIONS_API, { credentials: 'include', signal: controller.signal });
      console.log('[Sessions] Fetch URL:', REMOTE_SESSIONS_API, 'isTauri:', isTauri);
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        console.warn('[Sessions] Failed to fetch sessions:', response.status);
        return _remoteSessions; // Return stale cache on error
      }
      
      const data = await response.json();
      if (data.ok && Array.isArray(data.sessions)) {
        const limited = data.sessions.slice(0, 200);
        console.log('[Sessions] Loaded', limited.length, 'remote sessions from', data.source);
        
        _remoteSessions = limited.map(s => ({
          ...s,
          _remote: true,
          _source: data.source,
          title: s.title || s.session_id,
          pinned: s.pinned || false,
          archived: s.archived || false,
          updated_at: s.updated_at || s.created_at || Date.now()/1000,
          created_at: s.created_at || Date.now()/1000
        }));
        
        _lastFetchTime = Date.now();
        return _remoteSessions;
      }
      return _remoteSessions;
    } catch (e) {
      console.warn('[Sessions] Error fetching sessions:', e);
      return _remoteSessions; // Return stale cache on error
    }
  }

  // Wrap the original renderSessionList to merge remote sessions
  function wrapRenderSessionList() {
    console.log('[remote_sessions] wrapRenderSessionList checking:', typeof window.renderSessionList, !!window._originalRenderSessionList);
    if (typeof window.renderSessionList === 'function' && !window._originalRenderSessionList) {
      window._originalRenderSessionList = window.renderSessionList;
      window.renderSessionList = async function() {
        console.log('[remote_sessions] renderSessionList called');
        // Fetch remote in parallel, but do not block local session rendering.
        fetchRemoteSessions().then(remote => {
          _remoteSessions = remote;
          console.log('[remote_sessions] Fetched remote:', remote.length);
          mergeRemoteSessions();
        }).catch(e => {
          console.warn('[remote_sessions] Remote fetch failed:', e);
        });
        // Call original function (loads local sessions)
        const result = await window._originalRenderSessionList.apply(this, arguments);
        console.log('[remote_sessions] After original, window._allSessions:', window._allSessions?.length);
        // Try a merge immediately as well in case remote sessions were cached.
        mergeRemoteSessions();
        return result;
      };
      console.log('[Sessions] Wrapped renderSessionList for unified session list');
    }
  }

  // Merge remote sessions into _allSessions for unified list display
  function mergeRemoteSessions() {
    // Access _allSessions from sessions.js scope (now on window)
    const allSess = window._allSessions;
    const allProj = window._allProjects;
    if (!allSess || !Array.isArray(allSess)) {
      console.warn('[Sessions] _allSessions not available for merging');
      return;
    }
    
    if (_remoteSessions.length === 0) {
      console.log('[Sessions] No remote sessions to merge');
      return;
    }
    
    // Get existing session IDs to avoid duplicates
    const existingIds = new Set(allSess.map(s => s.session_id));
    let added = 0;
    
    for (const remote of _remoteSessions) {
      // Skip if already exists locally or was recently deleted
      if (!existingIds.has(remote.session_id) && !_recentlyDeleted.has(remote.session_id)) {
        // Add required fields for compatibility with sessions.js
        const session = {
          ...remote,
          pinned: remote.pinned || false,
          archived: remote.archived || false,
          updated_at: remote.updated_at || remote.created_at || Date.now()/1000,
          profile: remote.profile || 'default'  // Required for profile filter
        };
        allSess.push(session);
        added++;
      }
    }

    console.log('[Sessions] Merged', added, 'remote sessions into unified list (total:', allSess.length, ')');

    // Don't clear recently deleted set - persist to localStorage to prevent re-adding on reload

    // Only re-render if we actually added something
    if (added > 0 && typeof renderSessionListFromCache === 'function') {
      console.log('[remote_sessions] Calling renderSessionListFromCache');
      renderSessionListFromCache();
    }
  }

  // Create a session list item element
  function createSessionItem(session, isRemote) {
    const div = document.createElement('div');
    const isActive = S.session && session.session_id === S.session.session_id;
    div.className = 'session-item' + (isActive ? ' active' : '') + (isRemote ? ' remote-session' : '');
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

  // Load a remote session - backend now handles importing via _get_or_import_session
  async function loadRemoteSession(session) {
    try {
      // Loading session...
      
      // Just use the standard loadSession - backend will import if needed
      if (typeof loadSession === 'function') {
        await loadSession(session.session_id);
      } else {
        // Fallback: navigate to session
        window.location.hash = '#' + session.session_id;
      }
    } catch (e) {
      console.error('[Sessions] Error loading session:', e);
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
    renameBtn.textContent = 'rename';
    renameBtn.style.cssText = 'padding:8px 12px;cursor:pointer;font-size:13px;color:var(--text,#eee);';
    renameBtn.onmouseover = () => renameBtn.style.background = 'var(--hover,#333)';
    renameBtn.onmouseout = () => renameBtn.style.background = '';
    renameBtn.onclick = () => { menu.remove(); promptRenameSession(session, isRemote); };

    const deleteBtn = document.createElement('div');
    deleteBtn.textContent = 'delete';
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
    
    // Optimistic update: update cache immediately
    const sessionIndex = _remoteSessions.findIndex(s => s.session_id === session.session_id);
    if (sessionIndex !== -1) {
      _remoteSessions[sessionIndex].title = newTitle;
      _remoteSessions[sessionIndex].updated_at = Date.now() / 1000;
    }
    
    // Update window._allSessions if present
    if (window._allSessions) {
      const allIndex = window._allSessions.findIndex(s => s.session_id === session.session_id);
      if (allIndex !== -1) {
        window._allSessions[allIndex].title = newTitle;
        window._allSessions[allIndex].updated_at = Date.now() / 1000;
      }
    }
    
    // Re-render immediately from cache
    if (typeof renderSessionListFromCache === 'function') {
      renderSessionListFromCache();
    }
    
    // Background API call
    try {
      const res = await fetch(API_BASE + '/api/session/rename', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({session_id: session.session_id, title: newTitle, remote: isRemote})
      });
      const d = await res.json();
      if (!d.ok) {
        // Revert on failure
        if (sessionIndex !== -1) _remoteSessions[sessionIndex].title = session.title;
        showToast('Failed to rename - reverted');
        renderSessionListFromCache();
      }
    } catch(e) { 
      showToast('Error: ' + e.message); 
    }
  }

  async function deleteSessionFromMenu(session, isRemote) {
    if (!confirm('Delete session "' + (session.title || session.session_id) + '"?')) return;

    // Track this session as deleted to prevent remote cache from re-adding it
    _recentlyDeleted.add(session.session_id);
    _saveDeletedSessions(); // Persist to localStorage

    // Optimistic update: remove from cache immediately
    _remoteSessions = _remoteSessions.filter(s => s.session_id !== session.session_id);

    // Update window._allSessions if present
    if (window._allSessions) {
      window._allSessions = window._allSessions.filter(s => s.session_id !== session.session_id);
    }
    
    // Remove from open tabs if present
    removeFromOpenSessions(session.session_id);
    
    // Re-render immediately from cache
    if (typeof renderSessionListFromCache === 'function') {
      renderSessionListFromCache();
    }
    
    // Background API call
    try {
      const res = await fetch(API_BASE + '/api/session/delete', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({session_id: session.session_id, remote: isRemote})
      });
      const d = await res.json();
      if (!d.ok) {
        // Revert on failure - add back to cache and remove from deleted set
        _recentlyDeleted.delete(session.session_id);
        _remoteSessions.push(session);
        if (window._allSessions) window._allSessions.push(session);
        showToast('Failed to delete - reverted');
        renderSessionListFromCache();
      }
    } catch(e) { 
      showToast('Error: ' + e.message); 
    }
  }

  // Unified session list - remote sessions appear alongside local sessions
  console.log('[Sessions] Module loaded (unified list mode)');
  
  // Wait for DOM to be ready then wrap
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wrapRenderSessionList);
  } else {
    wrapRenderSessionList();
  }

  // Force refresh - call this when user wants fresh data
  async function forceRefresh() {
    // Refreshing remote sessions...
    const sessions = await fetchRemoteSessions(true); // force = true
    // Merge into _allSessions
    if (window._allSessions && sessions.length > 0) {
      const existingIds = new Set(window._allSessions.map(s => s.session_id));
      for (const s of sessions) {
        if (!existingIds.has(s.session_id)) {
          window._allSessions.push(s);
        }
      }
      if (typeof renderSessionListFromCache === 'function') {
        renderSessionListFromCache();
      }
    }
    // Remote sessions refreshed
    return sessions;
  }

  // Expose for debugging and manual refresh
  window.Sessions = {
    fetchRemoteSessions,
    getRemoteSessions: () => _remoteSessions,
    forceRefresh,
    invalidateCache: () => { _lastFetchTime = 0; },
    _recentlyDeleted  // Exposed so deleteSession can use it
  };
})();
