/**
 * Terminal panel with xterm.js integration
 * Supports multiple tabs, workspace sync, right-click context menu,
 * URL link provider, search, connection status, and smart reconnection.
 */

// Terminal state
const TerminalState = {
    terminals: new Map(), // terminal_id -> TerminalInstance
    activeTerminalId: null,
    nextClientId: 1,
    panelVisible: false
};

// Terminal icon SVG
const TERMINAL_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>`;

// Terminal close icon
const CLOSE_ICON = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;

// Terminal add icon
const ADD_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`;

// Search icon
const SEARCH_ICON = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`;

// Generate unique client ID
function getClientId() {
    return `client_${Date.now()}_${TerminalState.nextClientId++}`;
}

// Resolve API base URL — never fall back to localhost in production
function getApiBase() {
    return window.HERMES_API_BASE || (location.origin + '/');
}

// Debounce helper
function debounce(fn, ms) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), ms);
    };
}

// TerminalInstance class
class TerminalInstance {
    constructor(terminalId, name, cwd) {
        this.terminalId = terminalId;
        this.name = name;
        this.cwd = cwd;
        this.xterm = null;
        this.eventSource = null;
        this.clientId = getClientId();
        this.container = null;
        this.tabElement = null;
        this.connected = false;
        this._reconnectAttempts = 0;
        this._maxReconnects = 10;
        this._reconnectDelay = 1000;
        this._reconnectTimer = null;
        this._fitDebounced = debounce(() => this.fit(), 100);
        this._outputBuffer = []; // buffer output while disconnected
        this._searchOverlay = null;
        this._statusTimer = null;
    }

    async init(container) {
        console.log('[terminal] TerminalInstance.init called, container:', container);
        console.log('[terminal] Terminal class available:', typeof Terminal !== 'undefined');
        if (typeof Terminal === 'undefined') {
            console.error('[terminal] Terminal class not available - xterm.js not loaded');
            container.innerHTML = '<div style="padding:20px;color:#e94560;font-size:13px;">xterm.js failed to load. Please refresh the page.</div>';
            return;
        }
        this.container = container;

        // Create xterm instance — optimized for snappiness
        this.xterm = new Terminal({
            fontFamily: 'JetBrains Mono, Droid Sans Mono, ui-monospace, monospace',
            fontSize: 14,
            fontWeight: 'normal',
            fontWeightBold: 'bold',
            cursorBlink: false,
            cursorStyle: 'bar',
            scrollback: 5000,
            cols: 80,
            rows: 24,
            allowProposedApi: true,
            screenReaderMode: false,
            fastScrollModifier: 'alt',
            macOptionIsMeta: true,
            drawBoldTextInBrightColors: false,
            minimumContrastRatio: 1,
            theme: {
                background: '#0d0d0d',
                foreground: '#ffd45f',
                cursor: '#35c7ff',
                selection: '#35c7ff33',
                black: '#000000',
                red: '#ff5f56',
                green: '#27c93f',
                yellow: '#f6b012',
                blue: '#35c7ff',
                magenta: '#ff5f98',
                cyan: '#28b9ff',
                white: '#ffffff'
            }
        });
        console.log('[terminal] xterm instance created');

        // Create fit addon container
        const termContainer = document.createElement('div');
        termContainer.style.cssText = 'width: 100%; height: 100%; padding: 8px;';
        container.appendChild(termContainer);
        console.log('[terminal] termContainer appended to container');

        this.xterm.open(termContainer);
        console.log('[terminal] xterm opened');

        // Register URL link provider
        this._registerLinkProvider();

        // Custom terminal hotkeys for copy, paste, select-all, search, clear, and terminal interrupt.
        this.xterm.attachCustomKeyEventHandler((e) => {
            const isMac = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
            const isCtrl = isMac ? e.metaKey : e.ctrlKey;
            const isShift = e.shiftKey;
            const key = e.key.toLowerCase();

            if (!isCtrl || e.altKey) return true;

            // Ctrl+Shift+A: select all
            if (key === 'a' && isShift) {
                this.xterm.selectAll();
                this._setStatus('selected all');
                e.preventDefault();
                return false;
            }

            // Ctrl+Shift+F: toggle search
            if (key === 'f' && isShift) {
                this.toggleSearch();
                e.preventDefault();
                return false;
            }

            // Ctrl+Shift+K: clear terminal
            if (key === 'k' && isShift) {
                this.xterm.clear();
                this._setStatus('cleared');
                e.preventDefault();
                return false;
            }

            // Ctrl+V: paste
            if (key === 'v' && !isShift) {
                navigator.clipboard.readText().then(text => {
                    if (text) {
                        this.sendInput(text);
                        this._setStatus('pasted');
                    }
                }).catch(() => {});
                e.preventDefault();
                return false;
            }

            // Ctrl+C: copy if selection, else pass through
            if (key === 'c') {
                if (isShift) {
                    this.sendInput('\x03');
                    this._setStatus('sent SIGINT');
                    e.preventDefault();
                    return false;
                }
                const selection = this.xterm.getSelection();
                if (selection) {
                    navigator.clipboard.writeText(selection).catch(() => {});
                    this._setStatus('copied');
                    e.preventDefault();
                    return false;
                }
                return true;
            }

            return true;
        });

        // Handle input
        this.xterm.onData((data) => {
            if (this.connected) {
                this.sendInput(data);
            } else {
                // Queue input while disconnected
                this._outputBuffer.push({ type: 'input', data });
            }
        });

        // Handle resize
        this.xterm.onResize(({ cols, rows }) => {
            if (this.connected) {
                this.resize(cols, rows);
            }
        });

        // Fit terminal to container
        this.fit();

        // Connect to SSE stream
        this.connect();

        // Handle window resize
        window.addEventListener('resize', () => this._fitDebounced());
    }

    _registerLinkProvider() {
        if (!this.xterm || typeof this.xterm.registerLinkProvider !== 'function') return;
        const urlRegex = /(https?:\/\/[^\s"'<>(){}\[\]]+)/g;
        this.xterm.registerLinkProvider({
            provideLinks: (y, callback) => {
                const line = this.xterm.buffer.active.getLine(y);
                if (!line) return callback(undefined);
                const text = line.translateToString(true);
                const links = [];
                let m;
                while ((m = urlRegex.exec(text)) !== null) {
                    links.push({
                        range: { start: { x: m.index, y }, end: { x: m.index + m[0].length, y } },
                        text: m[0],
                        activate: () => window.open(m[0], '_blank')
                    });
                }
                callback(links);
            }
        });
    }

    _setStatus(msg) {
        const term = this;
        if (term.tabElement) {
            const statusEl = term.tabElement.querySelector('.terminal-tab-status');
            if (statusEl) {
                statusEl.textContent = msg;
                statusEl.style.opacity = '1';
                clearTimeout(term._statusTimer);
                term._statusTimer = setTimeout(() => {
                    statusEl.style.opacity = '0';
                }, 1200);
            }
        }
    }

    _updateConnectionStatus(status) {
        if (!this.tabElement) return;
        const dot = this.tabElement.querySelector('.terminal-status-dot');
        if (!dot) return;
        dot.classList.remove('connected', 'connecting', 'disconnected');
        dot.classList.add(status);
    }

    connect() {
        this._reconnectAttempts = 0;
        this._baseCandidateIndex = 0;
        // Build candidate list using the same logic as window.api
        let candidates = [getApiBase()];
        if (typeof window._getApiBaseCandidates === 'function') {
            try {
                const isCapacitorApp = !!(window.Capacitor || window.__capacitor || location.protocol==='capacitor:' || document.documentElement.classList.contains('capacitor'));
                const isTauri = !isCapacitorApp && (
                    window.__TAURI__ ||
                    location.protocol==='tauri:' ||
                    location.protocol==='file:' ||
                    location.hostname==='tauri.localhost' ||
                    location.host==='tauri.localhost' ||
                    location.hostname.includes('tauri')
                );
                candidates = window._getApiBaseCandidates(isCapacitorApp, isTauri);
            } catch (e) {}
        }
        const seen = new Set();
        this._baseCandidates = candidates.filter(c => { if (!c || seen.has(c)) return false; seen.add(c); return true; });
        this._doConnect();
    }

    _doConnect() {
        if (this._baseCandidateIndex >= this._baseCandidates.length) {
            // All candidates exhausted — start a retry cycle
            this._baseCandidateIndex = 0;
            this._reconnectAttempts++;
            if (this._reconnectAttempts > this._maxReconnects) {
                this.xterm.writeln('\r\n\x1b[31m● connection failed after multiple retries. close and reopen the terminal.\x1b[0m');
                return;
            }
            const baseDelay = this._reconnectDelay * Math.pow(1.5, this._reconnectAttempts - 1);
            const jitter = Math.random() * 500;
            const delay = Math.min(30000, baseDelay + jitter);
            console.log(`[terminal] all candidates failed, retrying in ${Math.round(delay)}ms (attempt ${this._reconnectAttempts})`);
            this._reconnectTimer = setTimeout(() => {
                if (TerminalState.terminals.has(this.terminalId)) {
                    this._doConnect();
                }
            }, delay);
            return;
        }

        const base = this._baseCandidates[this._baseCandidateIndex];
        const url = new URL('api/terminal/stream', base);
        url.searchParams.set('terminal_id', this.terminalId);
        url.searchParams.set('client_id', this.clientId);

        console.log(`[terminal] Connecting SSE to ${url.href} (candidate ${this._baseCandidateIndex + 1}/${this._baseCandidates.length})`);
        this.eventSource = new EventSource(url.href, { withCredentials: true });
        this._updateConnectionStatus('connecting');

        this.eventSource.addEventListener('open', () => {
            console.log('[terminal] SSE transport open');
        });

        this.eventSource.addEventListener('ready', (e) => {
            const data = JSON.parse(e.data);
            console.log('[terminal] Connected:', data.terminal_id);
            this.connected = true;
            this._reconnectAttempts = 0;
            this._baseCandidateIndex = 0;
            this._updateConnectionStatus('connected');
            this.xterm.writeln(`\r\n\x1b[38;2;246;176;18m● connected to ${data.name}\x1b[0m\r\n`);
            // Flush any buffered input
            const buffered = this._outputBuffer.filter(o => o.type === 'input');
            this._outputBuffer = [];
            for (const item of buffered) {
                this.sendInput(item.data);
            }
        });

        this.eventSource.addEventListener('output', (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'output') {
                this.xterm.write(data.data);
            } else if (data.type === 'exit') {
                this.xterm.writeln(`\r\n\x1b[31m● terminal exited (code: ${data.code})\x1b[0m`);
                this.connected = false;
                this._updateConnectionStatus('disconnected');
            }
        });

        this.eventSource.addEventListener('heartbeat', () => {
            // Heartbeat received, connection is alive
        });

        this.eventSource.addEventListener('error', (e) => {
            const wasConnected = this.connected;
            this.connected = false;
            this._updateConnectionStatus('disconnected');

            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }

            if (wasConnected) {
                // Mid-stream drop — reset candidates and reconnect after delay
                this.xterm.writeln(`\r\n\x1b[33m● connection lost\x1b[0m`);
                this._reconnectAttempts++;
                if (this._reconnectAttempts > this._maxReconnects) {
                    this.xterm.writeln('\r\n\x1b[31m● connection failed after multiple retries. close and reopen the terminal.\x1b[0m');
                    return;
                }
                const baseDelay = this._reconnectDelay * Math.pow(1.5, this._reconnectAttempts - 1);
                const jitter = Math.random() * 500;
                const delay = Math.min(30000, baseDelay + jitter);
                this.xterm.writeln(`\x1b[33m  reconnecting in ${Math.round(delay/1000)}s… (attempt ${this._reconnectAttempts}/${this._maxReconnects})\x1b[0m`);
                this._baseCandidateIndex = 0;
                this._reconnectTimer = setTimeout(() => {
                    if (TerminalState.terminals.has(this.terminalId)) {
                        this._doConnect();
                    }
                }, delay);
            } else {
                // First-connect failure — try next candidate immediately
                console.log(`[terminal] Candidate ${this._baseCandidateIndex + 1} failed, trying next`);
                this._baseCandidateIndex++;
                clearTimeout(this._reconnectTimer);
                this._reconnectTimer = setTimeout(() => {
                    if (TerminalState.terminals.has(this.terminalId)) {
                        this._doConnect();
                    }
                }, 100);
            }
        });
    }

    async sendInput(data) {
        try {
            const _api = typeof window.api === 'function' ? window.api : null;
            if (_api) {
                await _api(`api/terminal/${this.terminalId}/write`, {
                    method: 'POST',
                    body: JSON.stringify({ data })
                });
            } else {
                await fetch(new URL(`api/terminal/${this.terminalId}/write`, getApiBase()).href, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ data })
                });
            }
        } catch (e) {
            console.error('[terminal] Failed to send input:', e);
        }
    }

    async resize(cols, rows) {
        try {
            const _api = typeof window.api === 'function' ? window.api : null;
            if (_api) {
                await _api(`api/terminal/${this.terminalId}/resize`, {
                    method: 'POST',
                    body: JSON.stringify({ cols, rows })
                });
            } else {
                await fetch(new URL(`api/terminal/${this.terminalId}/resize`, getApiBase()).href, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cols, rows })
                });
            }
        } catch (e) {
            console.error('[terminal] Failed to resize:', e);
        }
    }

    fit() {
        if (!this.xterm || !this.container) return;

        const container = this.container.querySelector('div');
        if (!container) return;

        // Calculate cols/rows based on container size
        // Use xterm's measured dimensions when available; fallback to sensible defaults
        let charWidth = 9;
        let charHeight = 18;
        try {
            const dims = this.xterm._core?._renderService?.dimensions;
            if (dims?.actualCellWidth) charWidth = dims.actualCellWidth;
            if (dims?.actualCellHeight) charHeight = dims.actualCellHeight;
        } catch (_) {}

        const width = container.clientWidth - 16; // minus padding
        const height = container.clientHeight - 16;

        const cols = Math.floor(width / charWidth);
        const rows = Math.floor(height / charHeight);

        if (cols > 0 && rows > 0 && (cols !== this.xterm.cols || rows !== this.xterm.rows)) {
            this.xterm.resize(cols, rows);
        }
    }

    toggleSearch() {
        if (this._searchOverlay && this._searchOverlay.parentNode) {
            this._searchOverlay.remove();
            this._searchOverlay = null;
            this.focus();
            return;
        }
        const overlay = document.createElement('div');
        overlay.className = 'terminal-search-overlay';
        overlay.style.cssText = `
            position: absolute;
            top: 8px; right: 8px;
            background: rgba(13,13,13,0.95);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 8px;
            display: flex; align-items: center; gap: 6px;
            z-index: 100; font-size: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        `;
        overlay.innerHTML = `
            <span style="color:var(--muted);">${SEARCH_ICON}</span>
            <input type="text" placeholder="search…" style="
                background:transparent; border:none; color:var(--text);
                outline:none; font-size:12px; width:140px;
            ">
            <span class="ts-count" style="color:var(--muted);font-size:11px;"></span>
            <button class="ts-close" style="
                background:none; border:none; color:var(--muted);
                cursor:pointer; font-size:14px; line-height:1;
            ">×</button>
        `;
        this.container.style.position = 'relative';
        this.container.appendChild(overlay);

        const input = overlay.querySelector('input');
        const countEl = overlay.querySelector('.ts-count');
        const closeBtn = overlay.querySelector('.ts-close');

        let currentMatch = -1;
        let matches = [];

        const doSearch = () => {
            const query = input.value;
            if (!query) {
                countEl.textContent = '';
                this.xterm.clearSelection();
                matches = [];
                currentMatch = -1;
                return;
            }
            matches = [];
            const buffer = this.xterm.buffer.active;
            for (let y = buffer.viewportY; y < buffer.length; y++) {
                const line = buffer.getLine(y);
                if (!line) continue;
                const text = line.translateToString(true);
                let idx = text.toLowerCase().indexOf(query.toLowerCase());
                while (idx !== -1) {
                    matches.push({ x: idx, y, len: query.length });
                    idx = text.toLowerCase().indexOf(query.toLowerCase(), idx + 1);
                }
            }
            countEl.textContent = matches.length ? `${matches.length}` : '0';
            currentMatch = matches.length ? 0 : -1;
            if (currentMatch >= 0) {
                const m = matches[currentMatch];
                this.xterm.select(m.x, m.y, m.len);
            }
        };

        const nextMatch = () => {
            if (!matches.length) return;
            currentMatch = (currentMatch + 1) % matches.length;
            const m = matches[currentMatch];
            this.xterm.select(m.x, m.y, m.len);
            this.xterm.scrollLines(m.y - this.xterm.buffer.active.viewportY);
        };

        input.addEventListener('input', doSearch);
        input.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter') { ev.preventDefault(); nextMatch(); }
            if (ev.key === 'Escape') { ev.preventDefault(); this.toggleSearch(); }
        });
        closeBtn.addEventListener('click', () => this.toggleSearch());
        input.focus();

        this._searchOverlay = overlay;
    }

    focus() {
        if (this.xterm) {
            this.xterm.focus();
        }
    }

    destroy() {
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
        }
        if (this.eventSource) {
            this.eventSource.close();
        }
        if (this.xterm) {
            this.xterm.dispose();
        }
        if (this.container && this.container.parentNode) {
            this.container.remove();
        }
    }
}

// Initialize terminal panel
function initTerminalPanel() {
    if (TerminalState._initialized) return;
    TerminalState._initialized = true;

    console.log('[terminal] initTerminalPanel called');
    const tabsContainer = document.getElementById('terminalTabs');
    const termContainer = document.getElementById('terminalContainer');
    console.log('[terminal] tabsContainer:', tabsContainer, 'termContainer:', termContainer);
    if (!tabsContainer || !termContainer) {
        console.error('[terminal] Missing containers');
        return;
    }

    // Bind events to existing buttons
    const panelNewBtn = document.getElementById('btnNewTerminal');
    const panelCloseBtn = document.getElementById('btnCloseTerminal');
    if (panelNewBtn) panelNewBtn.addEventListener('click', () => createNewTerminal());
    if (panelCloseBtn) panelCloseBtn.addEventListener('click', () => {
        // Toggle panel off via switchPanel so button state stays in sync
        if (typeof switchPanel === 'function') {
            switchPanel('terminal');
        } else {
            closeActiveTerminal();
        }
    });

    // Load existing terminals
    loadTerminals();
}

// Load terminals from server
async function loadTerminals() {
    try {
        const _api = typeof window.api === 'function' ? window.api : null;
        let data;
        if (_api) {
            data = await _api('api/terminal/list');
        } else {
            const resp = await fetch(new URL('api/terminal/list', getApiBase()).href, { credentials: 'include' });
            data = await resp.json();
        }

        if (data.terminals && data.terminals.length > 0) {
            for (const term of data.terminals) {
                // Skip terminals already loaded in this session
                if (!TerminalState.terminals.has(term.terminal_id)) {
                    await createTerminalTab(term.terminal_id, term.name, term.cwd);
                }
            }
        } else {
            // Create default terminal only if none exist yet
            if (TerminalState.terminals.size === 0) {
                await createNewTerminal();
            }
        }
    } catch (e) {
        console.error('[terminal] Failed to load terminals:', e);
        if (TerminalState.terminals.size === 0) {
            await createNewTerminal();
        }
    }
}

// Get current workspace directory
function getCurrentWorkspace() {
    // Try to get from session
    if (window.S && window.S.session && window.S.session.workspace) {
        return window.S.session.workspace;
    }
    // Try to get from currentDir
    if (window.S && window.S.currentDir) {
        return window.S.currentDir;
    }
    // Default to home
    return '~';
}

// Detect APK/Capacitor mode
function _isApkMode() {
    return !!(window.Capacitor || window.__capacitor || location.protocol === 'capacitor:' ||
              document.documentElement.classList.contains('capacitor') ||
              document.documentElement.hasAttribute('data-capacitor'));
}

// Create a new terminal
async function createNewTerminal() {
    const cwd = getCurrentWorkspace();
    const sessionId = (window.S && window.S.session && window.S.session.session_id) || 'anonymous';
    const payload = { cwd, session_id: sessionId };
    if (_isApkMode()) {
        payload.ssh_host = 'house@192.168.4.250';
    }

    try {
        const _api = typeof window.api === 'function' ? window.api : null;
        let data;
        if (_api) {
            data = await _api('api/terminal/create', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
        } else {
            const resp = await fetch(new URL('api/terminal/create', getApiBase()).href, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            data = await resp.json();
        }
        if (data.terminal_id) {
            await createTerminalTab(data.terminal_id, data.name, data.cwd);
        }
    } catch (e) {
        console.error('[terminal] Failed to create terminal:', e);
        showToast('Failed to create terminal', 3000);
    }
}

// Create terminal tab
async function createTerminalTab(terminalId, name, cwd) {
    const container = document.createElement('div');
    container.className = 'terminal-instance';
    container.style.cssText = 'width: 100%; height: 100%; display: none;';
    container.id = `term-container-${terminalId}`;

    const termContainer = document.getElementById('terminalContainer');
    if (!termContainer) {
        console.error('[terminal] terminalContainer not found');
        return;
    }
    termContainer.appendChild(container);

    const term = new TerminalInstance(terminalId, name, cwd);
    TerminalState.terminals.set(terminalId, term);

    await term.init(container);
    createTabElement(terminalId, name);
    activateTerminal(terminalId);
}

// Create tab element
function createTabElement(terminalId, name) {
    const tabsContainer = document.getElementById('terminalTabs');

    const tab = document.createElement('div');
    tab.className = 'terminal-tab';
    tab.id = `terminal-tab-${terminalId}`;
    tab.innerHTML = `
        <span class="terminal-status-dot connecting" title="connection status"></span>
        <span class="terminal-tab-name">${escapeHtml(name)}</span>
        <span class="terminal-tab-status"></span>
        <span class="terminal-tab-close">${CLOSE_ICON}</span>
    `;

    // Click to activate
    tab.addEventListener('click', (e) => {
        if (!e.target.closest('.terminal-tab-close')) {
            activateTerminal(terminalId);
        }
    });

    // Close button
    tab.querySelector('.terminal-tab-close').addEventListener('click', (e) => {
        e.stopPropagation();
        closeTerminal(terminalId);
    });

    // Right-click context menu
    tab.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showTerminalContextMenu(e, terminalId);
    });

    tabsContainer.appendChild(tab);

    const term = TerminalState.terminals.get(terminalId);
    if (term) {
        term.tabElement = tab;
    }
}

// Activate terminal
function activateTerminal(terminalId) {
    console.log('[terminal] activateTerminal called for:', terminalId);
    // Hide all terminals
    TerminalState.terminals.forEach((term, id) => {
        if (term.container) {
            term.container.style.display = 'none';
        }
        if (term.tabElement) {
            term.tabElement.classList.remove('active');
        }
    });

    // Show active terminal
    const term = TerminalState.terminals.get(terminalId);
    console.log('[terminal] term to activate:', term);
    if (term) {
        if (term.container) {
            term.container.style.display = 'block';
            console.log('[terminal] container display set to block');
        }
        if (term.tabElement) {
            term.tabElement.classList.add('active');
        }
        if (term.xterm) {
            // Defer fit one frame so the browser has computed the container size
            requestAnimationFrame(() => {
                term.fit();
                term.focus();
            });
            console.log('[terminal] xterm fit + focused');
        }
    }

    TerminalState.activeTerminalId = terminalId;
}

// Close terminal
async function closeTerminal(terminalId) {
    const term = TerminalState.terminals.get(terminalId);
    if (!term) return;

    try {
        const _api = typeof window.api === 'function' ? window.api : null;
        if (_api) {
            await _api(`api/terminal/${terminalId}/close`, {
                method: 'POST'
            });
        } else {
            await fetch(new URL(`api/terminal/${terminalId}/close`, getApiBase()).href, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });
        }
    } catch (e) {
        console.error('[terminal] Failed to close terminal:', e);
    }

    // Remove from UI
    term.destroy();
    TerminalState.terminals.delete(terminalId);

    if (term.tabElement && term.tabElement.parentNode) {
        term.tabElement.remove();
    }

    // Activate another terminal if this was active
    if (TerminalState.activeTerminalId === terminalId) {
        const remaining = Array.from(TerminalState.terminals.keys());
        if (remaining.length > 0) {
            activateTerminal(remaining[0]);
        } else {
            TerminalState.activeTerminalId = null;
            // Create new terminal if none left
            await createNewTerminal();
        }
    }
}

// Close active terminal
function closeActiveTerminal() {
    if (TerminalState.activeTerminalId) {
        closeTerminal(TerminalState.activeTerminalId);
    }
}

// Show context menu for terminal tab
function showTerminalContextMenu(e, terminalId) {
    const term = TerminalState.terminals.get(terminalId);
    if (!term) return;

    // Remove existing menu
    const existing = document.querySelector('.terminal-context-menu');
    if (existing) existing.remove();

    const menu = document.createElement('div');
    menu.className = 'terminal-context-menu';
    menu.style.cssText = `
        position: fixed;
        left: ${e.clientX}px;
        top: ${e.clientY}px;
        background: var(--sidebar);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 4px 0;
        z-index: 1000;
        min-width: 160px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;

    menu.innerHTML = `
        <div class="terminal-menu-item" data-action="rename">rename</div>
        <div class="terminal-menu-item" data-action="close">close</div>
        <div class="terminal-menu-separator"></div>
        <div class="terminal-menu-item" data-action="clear">clear</div>
        <div class="terminal-menu-item" data-action="new">new terminal</div>
    `;

    menu.addEventListener('click', async (ev) => {
        const action = ev.target.dataset.action;
        if (action === 'rename') {
            const newName = prompt('Terminal name:', term.name);
            if (newName && newName.trim()) {
                await renameTerminal(terminalId, newName.trim());
            }
        } else if (action === 'close') {
            await closeTerminal(terminalId);
        } else if (action === 'clear') {
            if (term.xterm) term.xterm.clear();
        } else if (action === 'new') {
            await createNewTerminal();
        }
        menu.remove();
    });

    document.body.appendChild(menu);

    // Close menu on click outside
    const closeMenu = (ev) => {
        if (!menu.contains(ev.target)) {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }
    };
    setTimeout(() => document.addEventListener('click', closeMenu), 10);
}

// Rename terminal
async function renameTerminal(terminalId, name) {
    try {
        const _api = typeof window.api === 'function' ? window.api : null;
        if (_api) {
            await _api(`api/terminal/${terminalId}/rename`, {
                method: 'POST',
                body: JSON.stringify({ name })
            });
        } else {
            await fetch(new URL(`api/terminal/${terminalId}/rename`, getApiBase()).href, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
        }

        const term = TerminalState.terminals.get(terminalId);
        if (term) {
            term.name = name;
            if (term.tabElement) {
                const nameEl = term.tabElement.querySelector('.terminal-tab-name');
                if (nameEl) nameEl.textContent = name;
            }
        }
    } catch (e) {
        console.error('[terminal] Failed to rename terminal:', e);
    }
}

// Escape HTML helper
function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Show toast notification (fallback if ui.js not loaded)
function showToast(msg, ms) {
    if (typeof window.showToast === 'function' && window.showToast !== showToast) {
        window.showToast(msg, ms);
        return;
    }

    const el = document.createElement('div');
    el.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--sidebar);
        color: var(--text);
        padding: 10px 20px;
        border-radius: 6px;
        border: 1px solid var(--border);
        z-index: 1000;
        font-size: 13px;
    `;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), ms || 2800);
}

// Initialize on panel switch
function onTerminalPanelShow() {
    TerminalState.panelVisible = true;
    // Defensive: clear any stuck inline styles from old cached code
    const bottomPanel = document.getElementById('bottomPanel');
    const panelTerminal = document.getElementById('panelTerminal');
    if (bottomPanel) {
        bottomPanel.style.display = '';
        bottomPanel.style.opacity = '';
        bottomPanel.style.visibility = '';
        bottomPanel.style.pointerEvents = '';
    }
    if (panelTerminal) {
        panelTerminal.style.display = '';
        panelTerminal.style.opacity = '';
        panelTerminal.style.visibility = '';
        panelTerminal.style.pointerEvents = '';
    }
    const term = TerminalState.terminals.get(TerminalState.activeTerminalId);
    if (term) {
        setTimeout(() => {
            term.fit();
            term.focus();
        }, 100);
    }
}

function onTerminalPanelHide() {
    TerminalState.panelVisible = false;
}

// Expose to global
typeof window !== 'undefined' && (window.TerminalPanel = {
    init: initTerminalPanel,
    create: createNewTerminal,
    activate: activateTerminal,
    onShow: onTerminalPanelShow,
    onHide: onTerminalPanelHide,
    state: TerminalState
});
