/**
 * Terminal panel with xterm.js integration
 * Supports multiple tabs, workspace sync, and right-click context menu
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

// Generate unique client ID
function getClientId() {
    return `client_${Date.now()}_${TerminalState.nextClientId++}`;
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
        this._maxReconnects = 5;
        this._reconnectDelay = 2000;
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

        // Create xterm instance
        this.xterm = new Terminal({
            fontFamily: 'Droid Sans Mono, ui-monospace, monospace',
            fontSize: 14,
            cursorBlink: true,
            cursorStyle: 'block',
            scrollback: 10000,
            cols: 80,
            rows: 24,
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

        // Custom terminal hotkeys for copy, paste, select-all, and terminal interrupt.
        this.xterm.attachCustomKeyEventHandler((e) => {
            const isMac = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
            const isCtrl = isMac ? e.metaKey : e.ctrlKey;
            const isShift = e.shiftKey;
            const key = e.key.toLowerCase();

            if (!isCtrl || e.altKey) return true;

            if (key === 'a' && isShift) {
                this.xterm.selectAll();
                e.preventDefault();
                return false;
            }

            if (key === 'v' && !isShift) {
                navigator.clipboard.readText().then(text => {
                    if (text) {
                        this.sendInput(text);
                    }
                }).catch(() => {});
                e.preventDefault();
                return false;
            }

            if (key === 'c') {
                if (isShift) {
                    this.sendInput('\x03');
                    e.preventDefault();
                    return false;
                }
                const selection = this.xterm.getSelection();
                if (selection) {
                    navigator.clipboard.writeText(selection).catch(() => {});
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
        window.addEventListener('resize', () => {
            this.fit();
        });
    }

    connect() {
        const base = window.HERMES_API_BASE || 'http://localhost:8786/';
        const url = new URL('api/terminal/stream', base);
        url.searchParams.set('terminal_id', this.terminalId);
        url.searchParams.set('client_id', this.clientId);

        this.eventSource = new EventSource(url.href, { withCredentials: true });

        this.eventSource.addEventListener('ready', (e) => {
            const data = JSON.parse(e.data);
            console.log('[terminal] Connected:', data.terminal_id);
            this.connected = true;
            this._reconnectAttempts = 0;
            this.xterm.writeln(`\r\n\x1b[32mConnected to terminal: ${data.name}\x1b[0m\r\n`);
        });

        this.eventSource.addEventListener('output', (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'output') {
                this.xterm.write(data.data);
            } else if (data.type === 'exit') {
                this.xterm.writeln(`\r\n\x1b[31mTerminal exited (code: ${data.code})\x1b[0m`);
                this.connected = false;
            }
        });

        this.eventSource.addEventListener('heartbeat', () => {
            // Heartbeat received, connection is alive
        });

        this.eventSource.addEventListener('error', (e) => {
            console.error('[terminal] SSE error:', e);
            this.connected = false;
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }
            this._reconnectAttempts++;
            if (this._reconnectAttempts > this._maxReconnects) {
                this.xterm.writeln('\r\n\x1b[31mConnection failed after multiple retries. Please close and reopen the terminal.\x1b[0m');
                return;
            }
            const delay = Math.min(30000, this._reconnectDelay * Math.pow(1.5, this._reconnectAttempts - 1));
            this.xterm.writeln(`\r\n\x1b[31mConnection lost. Reconnecting in ${Math.round(delay/1000)}s... (attempt ${this._reconnectAttempts}/${this._maxReconnects})\x1b[0m`);

            setTimeout(() => {
                if (TerminalState.terminals.has(this.terminalId)) {
                    this.connect();
                }
            }, delay);
        });
    }

    async sendInput(data) {
        try {
            const _api = typeof window.api === 'function' ? window.api : null;
            if (_api) {
                await _api('api/terminal/input', {
                    method: 'POST',
                    body: JSON.stringify({ terminal_id: this.terminalId, data })
                });
            } else {
                await fetch(new URL('api/terminal/input', window.HERMES_API_BASE || 'http://localhost:8786/').href, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ terminal_id: this.terminalId, data })
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
                await _api('api/terminal/resize', {
                    method: 'POST',
                    body: JSON.stringify({ terminal_id: this.terminalId, cols, rows })
                });
            } else {
                await fetch(new URL('api/terminal/resize', window.HERMES_API_BASE || 'http://localhost:8786/').href, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ terminal_id: this.terminalId, cols, rows })
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
        const charWidth = this.xterm._core._renderService.dimensions.actualCellWidth || 9;
        const charHeight = this.xterm._core._renderService.dimensions.actualCellHeight || 18;

        const width = container.clientWidth - 16; // minus padding
        const height = container.clientHeight - 16;

        const cols = Math.floor(width / charWidth);
        const rows = Math.floor(height / charHeight);

        if (cols > 0 && rows > 0) {
            this.xterm.resize(cols, rows);
        }
    }

    focus() {
        if (this.xterm) {
            this.xterm.focus();
        }
    }

    destroy() {
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
    if (panelCloseBtn) panelCloseBtn.addEventListener('click', () => closeActiveTerminal());

    // Load existing terminals
    loadTerminals();
}

// Load terminals from server
async function loadTerminals() {
    try {
        const _api = typeof window.api === 'function' ? window.api : null;
        let data;
        if (_api) {
            data = await _api('api/terminals');
        } else {
            const resp = await fetch(new URL('api/terminals', window.HERMES_API_BASE || 'http://localhost:8786/').href, { credentials: 'include' });
            data = await resp.json();
        }

        if (data.terminals && data.terminals.length > 0) {
            for (const term of data.terminals) {
                await createTerminalTab(term.terminal_id, term.name, term.cwd);
            }
        } else {
            // Create default terminal
            await createNewTerminal();
        }
    } catch (e) {
        console.error('[terminal] Failed to load terminals:', e);
        await createNewTerminal();
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
            const resp = await fetch(new URL('api/terminal/create', window.HERMES_API_BASE || 'http://localhost:8786/').href, {
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
        <span class="terminal-tab-name">${escapeHtml(name)}</span>
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
            term.focus();
            console.log('[terminal] xterm focused');
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
            await _api('api/terminal/close', {
                method: 'POST',
                body: JSON.stringify({ terminal_id: terminalId })
            });
        } else {
            await fetch(new URL('api/terminal/close', window.HERMES_API_BASE || 'http://localhost:8786/').href, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ terminal_id: terminalId })
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
        min-width: 140px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;

    menu.innerHTML = `
        <div class="terminal-menu-item" data-action="rename">rename</div>
        <div class="terminal-menu-item" data-action="close">close</div>
        <div class="terminal-menu-separator"></div>
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
            await _api('api/terminal/rename', {
                method: 'POST',
                body: JSON.stringify({ terminal_id: terminalId, name })
            });
        } else {
            await fetch(new URL('api/terminal/rename', window.HERMES_API_BASE || 'http://localhost:8786/').href, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ terminal_id: terminalId, name })
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
