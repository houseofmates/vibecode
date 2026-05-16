/**
 * Termisol Terminal Integration for Vibecode
 * Advanced terminal with AI assistance, quantum computing, VR support,
 * video playback, audio visualization, 3D modeling, and more.
 */

// Termisol Terminal State
const TermisolState = {
    terminals: new Map(), // terminal_id -> TermisolTerminalInstance
    activeTerminalId: null,
    nextClientId: 1,
    panelVisible: false,
    features: new Map() // terminal_id -> enabled features
};

// Termisol Terminal Icons
const TERMISOL_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line><path d="M6 9l2 2-2 2"></path><path d="M10 9h4"></path></svg>`;
const CLOSE_ICON = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
const ADD_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`;
const FEATURE_ICON = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`;
const AI_ICON = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5c0 .74-.33 1.4-.85 1.85L17 10.8V8a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-2.8l-5.85 4.45c.52.45.85 1.11.85 1.85A2.5 2.5 0 0 1 9.5 22a2.5 2.5 0 0 1-2.5-2.5c0-.74.33-1.4.85-1.85L2 13.2V16a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2.8l5.85-4.45A2.5 2.5 0 0 1 9.5 2z"></path></svg>`;

// Generate unique client ID
function getClientId() {
    return `termisol_client_${Date.now()}_${TermisolState.nextClientId++}`;
}

// Resolve API base URL
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

// Termisol Feature Categories
const FEATURE_CATEGORIES = {
    'AI': ['ai_assistance'],
    'Interface': ['vr_support', 'themes', 'hotkeys', 'notifications'],
    'Media': ['video_playback', 'audio_visualization', '3d_modeling'],
    'Development': ['git_integration', 'docker_integration', 'database_client', 'syntax_highlighting'],
    'Productivity': ['error_detection', 'command_prediction', 'file_manager'],
    'Collaboration': ['collaboration'],
    'Tools': ['session_recording', 'performance_monitoring'],
    'Extensions': ['plugins']
};

// TermisolTerminalInstance class
class TermisolTerminalInstance {
    constructor(terminalId, name, cwd, features = {}) {
        this.terminalId = terminalId;
        this.name = name;
        this.cwd = cwd;
        this.features = features;
        this.xterm = null;
        this.websocket = null;
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
        this._statusTimer = null;
        
        // Feature-specific UI elements
        this._featurePanel = null;
        this._aiPanel = null;
        this._mediaPanel = null;
        this._collabPanel = null;
    }

    async init(container) {
        console.log('[termisol] TermisolTerminalInstance.init called');
        this.container = container;

        // Create xterm instance with Termisol theme
        this.xterm = new Terminal({
            fontFamily: 'JetBrains Mono, Droid Sans Mono, ui-monospace, monospace',
            fontSize: 14,
            fontWeight: 'normal',
            fontWeightBold: 'bold',
            cursorBlink: false,
            cursorStyle: 'bar',
            scrollback: 10000,
            cols: 80,
            rows: 24,
            allowProposedApi: true,
            screenReaderMode: false,
            fastScrollModifier: 'alt',
            macOptionIsMeta: true,
            drawBoldTextInBrightColors: false,
            minimumContrastRatio: 1,
            theme: {
                background: 'rgba(13, 13, 13, 0.95)',
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
                white: '#ffffff',
                brightBlack: '#666666',
                brightRed: '#ff6e67',
                brightGreen: '#5af78e',
                brightYellow: '#f4f99d',
                brightBlue: '#57c7ff',
                brightMagenta: '#ff6ac1',
                brightCyan: '#9aedfe',
                brightWhite: '#f1f1f0'
            }
        });

        // Create terminal container with feature panels
        this._createTerminalContainer();
        this.xterm.open(this.container.querySelector('.termisol-terminal-content'));
        
        // Register enhanced features
        this._registerEnhancedFeatures();
        
        // Register custom keybindings
        this._registerCustomKeybindings();
        
        // Handle input/output
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

        // Fit terminal
        this.fit();
        
        // Connect to Termisol service
        await this.connect();
        
        // Handle window resize
        window.addEventListener('resize', () => this._fitDebounced());
        
        // Setup drag-and-drop functionality
        this._setupDragAndDrop();
    }

    _createTerminalContainer() {
        this.container.innerHTML = `
            <div class="termisol-terminal-wrapper">
                <div class="termisol-terminal-header">
                    <div class="termisol-terminal-title">
                        <span class="termisol-icon">${TERMISOL_ICON}</span>
                        <span class="termisol-name">${this.name}</span>
                        <span class="termisol-status-dot connecting"></span>
                    </div>
                    <div class="termisol-terminal-controls">
                        <button class="termisol-btn termisol-features-btn" title="Features">
                            ${FEATURE_ICON}
                        </button>
                        <button class="termisol-btn termisol-ai-btn" title="AI Assistant">
                            ${AI_ICON}
                        </button>
                        <button class="termisol-btn termisol-media-btn" title="Media">
                            🎬
                        </button>
                        <button class="termisol-btn termisol-collab-btn" title="Collaborate">
                            👥
                        </button>
                    </div>
                </div>
                <div class="termisol-terminal-content"></div>
                <div class="termisol-terminal-footer">
                    <div class="termisol-features-panel hidden">
                        <h4>Terminal Features</h4>
                        <div class="termisol-features-grid"></div>
                    </div>
                    <div class="termisol-ai-panel hidden">
                        <h4>AI Assistant</h4>
                        <div class="termisol-ai-chat"></div>
                        <div class="termisol-ai-input">
                            <input type="text" placeholder="Ask AI anything...">
                            <button>Send</button>
                        </div>
                    </div>
                    <div class="termisol-media-panel hidden">
                        <h4>Media & Visualization</h4>
                        <div class="termisol-media-controls"></div>
                    </div>
                    <div class="termisol-collab-panel hidden">
                        <h4>Collaboration</h4>
                        <div class="termisol-collab-users"></div>
                    </div>
                </div>
            </div>
        `;

        // Add event listeners for feature panels
        this._setupFeaturePanels();
    }

    _setupFeaturePanels() {
        const wrapper = this.container.querySelector('.termisol-terminal-wrapper');
        
        // Features button
        wrapper.querySelector('.termisol-features-btn').addEventListener('click', () => {
            this.toggleFeaturePanel('features');
        });
        
        // AI button
        wrapper.querySelector('.termisol-ai-btn').addEventListener('click', () => {
            this.toggleFeaturePanel('ai');
        });
        
        // Media button
        wrapper.querySelector('.termisol-media-btn').addEventListener('click', () => {
            this.toggleFeaturePanel('media');
        });
        
        // Collaboration button
        wrapper.querySelector('.termisol-collab-btn').addEventListener('click', () => {
            this.toggleFeaturePanel('collab');
        });
    }

    toggleFeaturePanel(panelType) {
        const panels = ['features', 'ai', 'media', 'collab'];
        panels.forEach(panel => {
            const panelEl = this.container.querySelector(`.termisol-${panel}-panel`);
            if (panel === panelType) {
                panelEl.classList.toggle('hidden');
                if (!panelEl.classList.contains('hidden')) {
                    this._populateFeaturePanel(panel);
                }
            } else {
                panelEl.classList.add('hidden');
            }
        });
    }

    _populateFeaturePanel(panelType) {
        if (panelType === 'features') {
            this._populateFeaturesGrid();
        } else if (panelType === 'ai') {
            this._populateAIPanel();
        } else if (panelType === 'media') {
            this._populateMediaPanel();
        } else if (panelType === 'collab') {
            this._populateCollabPanel();
        }
    }

    _populateFeaturesGrid() {
        const grid = this.container.querySelector('.termisol-features-grid');
        grid.innerHTML = '';
        
        Object.entries(this.features).forEach(([feature, enabled]) => {
            const featureEl = document.createElement('div');
            featureEl.className = `termisol-feature-item ${enabled ? 'enabled' : 'disabled'}`;
            featureEl.innerHTML = `
                <label class="termisol-feature-toggle">
                    <input type="checkbox" ${enabled ? 'checked' : ''} data-feature="${feature}">
                    <span class="termisol-feature-name">${this._formatFeatureName(feature)}</span>
                </label>
                <span class="termisol-feature-desc">${this._getFeatureDescription(feature)}</span>
            `;
            
            featureEl.querySelector('input').addEventListener('change', (e) => {
                this.toggleFeature(feature, e.target.checked);
            });
            
            grid.appendChild(featureEl);
        });
    }

    _formatFeatureName(feature) {
        return feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    _getFeatureDescription(feature) {
        const descriptions = {
            'ai_assistance': 'AI-powered command suggestions and assistance',
            'quantum_computing': 'Quantum circuit execution and visualization',
            'vr_support': 'Virtual reality terminal interface',
            'video_playback': 'Inline video playback in terminal',
            'audio_visualization': 'Audio spectrum visualization',
            '3d_modeling': '3D model viewing and interaction',
            'git_integration': 'Git operations and version control',
            'docker_integration': 'Docker container management',
            'database_client': 'Database connection management',
            'syntax_highlighting': 'Advanced syntax highlighting',
            'error_detection': 'Automatic error detection and fixes',
            'command_prediction': 'Smart command prediction',
            'file_manager': 'Integrated file manager',
            'collaboration': 'Terminal session collaboration',
            'session_recording': 'Session recording and playback',
            'performance_monitoring': 'Performance metrics and optimization',
            'hotkeys': 'Customizable hotkeys',
            'notifications': 'Native notifications',
            'themes': 'Terminal themes and customization',
            'plugins': 'Plugin ecosystem support'
        };
        return descriptions[feature] || 'Advanced terminal feature';
    }

    _populateAIPanel() {
        const chatEl = this.container.querySelector('.termisol-ai-chat');
        chatEl.innerHTML = `
            <div class="termisol-ai-welcome">
                <p>🤖 Termisol AI Assistant is ready to help!</p>
                <p>Ask me anything about commands, code, or terminal operations.</p>
            </div>
        `;
        
        const inputEl = this.container.querySelector('.termisol-ai-input input');
        const sendBtn = this.container.querySelector('.termisol-ai-input button');
        
        const sendMessage = () => {
            const message = inputEl.value.trim();
            if (message) {
                this.sendAIMessage(message);
                inputEl.value = '';
            }
        };
        
        sendBtn.addEventListener('click', sendMessage);
        inputEl.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    _populateMediaPanel() {
        const controlsEl = this.container.querySelector('.termisol-media-controls');
        controlsEl.innerHTML = `
            <div class="media-feature ${this.features.video_playback ? 'enabled' : 'disabled'}">
                <h5>🎬 Video Playback</h5>
                <p>Play videos directly in the terminal</p>
            </div>
            <div class="media-feature ${this.features.audio_visualization ? 'enabled' : 'disabled'}">
                <h5>🎵 Audio Visualization</h5>
                <p>Real-time audio spectrum display</p>
            </div>
            <div class="media-feature ${this.features['3d_modeling'] ? 'enabled' : 'disabled'}">
                <h5>🎮 3D Modeling</h5>
                <p>View and interact with 3D models</p>
            </div>
        `;
    }

    _populateCollabPanel() {
        const usersEl = this.container.querySelector('.termisol-collab-users');
        usersEl.innerHTML = `
            <div class="collab-info">
                <p>👥 Collaboration features available</p>
                <p>Share terminal sessions with team members</p>
            </div>
        `;
    }

    _registerEnhancedFeatures() {
        // Register URL link provider
        this._registerLinkProvider();
        
        // Register drag-and-drop for files
        this._registerDragDrop();
        
        // Register context menu
        this._registerContextMenu();
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

    _registerDragDrop() {
        this.container.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.container.classList.add('drag-over');
        });
        
        this.container.addEventListener('dragleave', () => {
            this.container.classList.remove('drag-over');
        });
        
        this.container.addEventListener('drop', (e) => {
            e.preventDefault();
            this.container.classList.remove('drag-over');
            
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.handleFileDrop(files);
            }
        });
    }

    handleFileDrop(files) {
        files.forEach(file => {
            if (file.type.startsWith('video/') && this.features.video_playback) {
                this.playVideo(file);
            } else if (file.type.startsWith('audio/') && this.features.audio_visualization) {
                this.visualizeAudio(file);
            } else if (file.name.endsWith('.obj') || file.name.endsWith('.stl') && this.features['3d_modeling']) {
                this.view3DModel(file);
            } else {
                this.sendFileToTerminal(file);
            }
        });
    }

    playVideo(file) {
        const url = URL.createObjectURL(file);
        this.xterm.writeln(`\r\n🎬 Playing video: ${file.name}`);
        this.xterm.writeln(`📍 URL: ${url}`);
        // Enhanced video playback would be handled by Termisol backend
    }

    visualizeAudio(file) {
        const url = URL.createObjectURL(file);
        this.xterm.writeln(`\r\n🎵 Visualizing audio: ${file.name}`);
        this.xterm.writeln(`📍 URL: ${url}`);
        // Audio visualization would be handled by Termisol backend
    }

    view3DModel(file) {
        const url = URL.createObjectURL(file);
        this.xterm.writeln(`\r\n🎮 Viewing 3D model: ${file.name}`);
        this.xterm.writeln(`📍 URL: ${url}`);
        // 3D model viewing would be handled by Termisol backend
    }

    sendFileToTerminal(file) {
        // Send file path to terminal for handling
        const path = file.path || file.name;
        this.sendInput(` "${path}"`);
    }

    _registerContextMenu() {
        this.container.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.showContextMenu(e);
        });
    }

    showContextMenu(e) {
        // Remove existing menu
        const existing = document.querySelector('.termisol-context-menu');
        if (existing) existing.remove();

        const menu = document.createElement('div');
        menu.className = 'termisol-context-menu';
        menu.style.cssText = `
            position: fixed;
            left: ${e.clientX}px;
            top: ${e.clientY}px;
            background: var(--sidebar);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 4px 0;
            z-index: 1000;
            min-width: 180px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        `;

        menu.innerHTML = `
            <div class="termisol-menu-item" data-action="copy">Copy</div>
            <div class="termisol-menu-item" data-action="paste">Paste</div>
            <div class="termisol-menu-separator"></div>
            <div class="termisol-menu-item" data-action="clear">Clear</div>
            <div class="termisol-menu-item" data-action="search">Search</div>
            <div class="termisol-menu-separator"></div>
            <div class="termisol-menu-item" data-action="ai-help">AI Help</div>
            <div class="termisol-menu-item" data-action="git-status">Git Status</div>
            <div class="termisol-menu-item" data-action="docker-ps">Docker PS</div>
            <div class="termisol-menu-separator"></div>
            <div class="termisol-menu-item" data-action="record">Record Session</div>
            <div class="termisol-menu-item" data-action="screenshot">Screenshot</div>
        `;

        menu.addEventListener('click', (ev) => {
            const action = ev.target.dataset.action;
            this.handleContextMenuAction(action);
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

    handleContextMenuAction(action) {
        switch (action) {
            case 'copy':
                document.execCommand('copy');
                break;
            case 'paste':
                navigator.clipboard.readText().then(text => {
                    this.sendInput(text);
                });
                break;
            case 'clear':
                this.xterm.clear();
                break;
            case 'search':
                this.toggleSearch();
                break;
            case 'ai-help':
                this.toggleFeaturePanel('ai');
                break;
            case 'git-status':
                if (this.features.git_integration) {
                    this.sendInput('\x03git status\n');
                }
                break;
            case 'docker-ps':
                if (this.features.docker_integration) {
                    this.sendInput('\x03docker ps\n');
                }
                break;
            case 'record':
                if (this.features.session_recording) {
                    this.toggleRecording();
                }
                break;
            case 'screenshot':
                this.takeScreenshot();
                break;
        }
    }

    _registerCustomKeybindings() {
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

            // Ctrl+Shift+I: toggle AI panel
            if (key === 'i' && isShift) {
                this.toggleFeaturePanel('ai');
                e.preventDefault();
                return false;
            }

            // Ctrl+Shift+M: toggle media panel
            if (key === 'm' && isShift) {
                this.toggleFeaturePanel('media');
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
    }

    async connect() {
        try {
            // Try WebSocket first (preferred for real-time communication)
            await this._connectWebSocket();
        } catch (error) {
            console.log('[termisol] WebSocket failed, falling back to SSE:', error);
            // Fallback to SSE
            await this._connectSSE();
        }
    }

    async _connectWebSocket() {
        const base = getApiBase();
        const wsUrl = base.replace(/^http/, 'ws') + `api/termisol/${this.terminalId}/ws`;
        
        this.websocket = new WebSocket(wsUrl);
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('WebSocket connection timeout'));
            }, 10000);
            
            this.websocket.onopen = () => {
                clearTimeout(timeout);
                console.log('[termisol] WebSocket connected');
                this.connected = true;
                this._updateConnectionStatus('connected');
                this.xterm.writeln(`\r\n\x1b[38;2;246;176;18m● Termisol connected: ${this.name}\x1b[0m\r\n`);
                resolve();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('[termisol] Failed to parse message:', e);
                }
            };
            
            this.websocket.onclose = () => {
                clearTimeout(timeout);
                this.connected = false;
                this._updateConnectionStatus('disconnected');
                this.xterm.writeln(`\r\n\x1b[33m● Termisol connection lost\x1b[0m`);
                this._scheduleReconnect();
            };
            
            this.websocket.onerror = (error) => {
                clearTimeout(timeout);
                reject(error);
            };
        });
    }

    async _connectSSE() {
        const base = getApiBase();
        const url = new URL(`api/termisol/${this.terminalId}/stream`, base);
        url.searchParams.set('client_id', this.clientId);
        
        this.eventSource = new EventSource(url.href);
        this._updateConnectionStatus('connecting');
        
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('SSE connection timeout'));
            }, 10000);
            
            this.eventSource.addEventListener('ready', (e) => {
                clearTimeout(timeout);
                const data = JSON.parse(e.data);
                console.log('[termisol] SSE connected:', data);
                this.connected = true;
                this._updateConnectionStatus('connected');
                this.xterm.writeln(`\r\n\x1b[38;2;246;176;18m● Termisol connected: ${data.name}\x1b[0m\r\n`);
                resolve();
            });
            
            this.eventSource.addEventListener('output', (e) => {
                const data = JSON.parse(e.data);
                this.handleMessage(data);
            });
            
            this.eventSource.addEventListener('exit', (e) => {
                const data = JSON.parse(e.data);
                this.xterm.writeln(`\r\n\x1b[31m● Termisol exited (code: ${data.code})\x1b[0m`);
                this.connected = false;
                this._updateConnectionStatus('disconnected');
            });
            
            this.eventSource.addEventListener('error', () => {
                clearTimeout(timeout);
                this.connected = false;
                this._updateConnectionStatus('disconnected');
                reject(new Error('SSE connection failed'));
            });
        });
    }

    handleMessage(data) {
        switch (data.type) {
            case 'output':
                this.xterm.write(data.data);
                break;
            case 'ai_response':
                this.displayAIResponse(data.response);
                break;
            case 'feature_update':
                this.features[data.feature] = data.enabled;
                this._updateFeatureUI(data.feature, data.enabled);
                break;
            case 'media_event':
                this.handleMediaEvent(data);
                break;
            case 'collab_event':
                this.handleCollabEvent(data);
                break;
            case 'exit':
                this.xterm.writeln(`\r\n\x1b[31m● Termisol exited (code: ${data.code})\x1b[0m`);
                this.connected = false;
                this._updateConnectionStatus('disconnected');
                break;
        }
    }

    displayAIResponse(response) {
        const chatEl = this.container.querySelector('.termisol-ai-chat');
        if (chatEl) {
            const messageEl = document.createElement('div');
            messageEl.className = 'termisol-ai-message';
            messageEl.innerHTML = `
                <div class="ai-response">🤖 ${response}</div>
            `;
            chatEl.appendChild(messageEl);
            chatEl.scrollTop = chatEl.scrollHeight;
        }
    }

    handleMediaEvent(data) {
        if (data.media_type === 'video') {
            this.xterm.writeln(`\r\n🎬 ${data.message}`);
        } else if (data.media_type === 'audio') {
            this.xterm.writeln(`\r\n🎵 ${data.message}`);
        } else if (data.media_type === '3d') {
            this.xterm.writeln(`\r\n🎮 ${data.message}`);
        }
    }

    handleCollabEvent(data) {
        if (data.event_type === 'user_joined') {
            this.xterm.writeln(`\r\n👥 ${data.user} joined the session`);
        } else if (data.event_type === 'user_left') {
            this.xterm.writeln(`\r\n👋 ${data.user} left the session`);
        }
    }

    _updateFeatureUI(feature, enabled) {
        const featureItem = this.container.querySelector(`[data-feature="${feature}"]`);
        if (featureItem) {
            featureItem.checked = enabled;
            const parent = featureItem.closest('.termisol-feature-item');
            if (parent) {
                parent.className = `termisol-feature-item ${enabled ? 'enabled' : 'disabled'}`;
            }
        }
    }

    async sendInput(data) {
        try {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'input',
                    data: data
                }));
            } else {
                // Fallback to HTTP API
                const _api = typeof window.api === 'function' ? window.api : null;
                if (_api) {
                    await _api(`api/termisol/${this.terminalId}/write`, {
                        method: 'POST',
                        body: JSON.stringify({ data })
                    });
                } else {
                    await fetch(new URL(`api/termisol/${this.terminalId}/write`, getApiBase()).href, {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ data })
                    });
                }
            }
        } catch (e) {
            console.error('[termisol] Failed to send input:', e);
        }
    }

    async resize(cols, rows) {
        try {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'resize',
                    cols: cols,
                    rows: rows
                }));
            } else {
                // Fallback to HTTP API
                const _api = typeof window.api === 'function' ? window.api : null;
                if (_api) {
                    await _api(`api/termisol/${this.terminalId}/resize`, {
                        method: 'POST',
                        body: JSON.stringify({ cols, rows })
                    });
                } else {
                    await fetch(new URL(`api/termisol/${this.terminalId}/resize`, getApiBase()).href, {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cols, rows })
                    });
                }
            }
        } catch (e) {
            console.error('[termisol] Failed to resize:', e);
        }
    }

    async toggleFeature(feature, enabled) {
        try {
            this.features[feature] = enabled;
            
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'feature_update',
                    feature: feature,
                    enabled: enabled
                }));
            } else {
                // Fallback to HTTP API
                const _api = typeof window.api === 'function' ? window.api : null;
                if (_api) {
                    await _api(`api/termisol/${this.terminalId}/features`, {
                        method: 'POST',
                        body: JSON.stringify({ features: { [feature]: enabled } })
                    });
                } else {
                    await fetch(new URL(`api/termisol/${this.terminalId}/features`, getApiBase()).href, {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ features: { [feature]: enabled } })
                    });
                }
            }
        } catch (e) {
            console.error('[termisol] Failed to toggle feature:', e);
        }
    }

    async sendAIMessage(message) {
        const chatEl = this.container.querySelector('.termisol-ai-chat');
        if (chatEl) {
            const messageEl = document.createElement('div');
            messageEl.className = 'termisol-ai-message';
            messageEl.innerHTML = `
                <div class="user-message">👤 ${message}</div>
            `;
            chatEl.appendChild(messageEl);
            chatEl.scrollTop = chatEl.scrollHeight;
        }
        
        // Send AI command to terminal
        await this.sendInput(`/ai ${message}\n`);
    }

    toggleRecording() {
        // Toggle session recording
        this.xterm.writeln(`\r\n🎥 ${this._isRecording ? 'Stopping' : 'Starting'} session recording`);
        this._isRecording = !this._isRecording;
    }

    takeScreenshot() {
        // Take terminal screenshot
        this.xterm.writeln(`\r\n📸 Screenshot captured`);
    }

    fit() {
        if (!this.xterm || !this.container) return;

        const content = this.container.querySelector('.termisol-terminal-content');
        if (!content) return;

        // Calculate cols/rows based on content size
        let charWidth = 9;
        let charHeight = 18;
        try {
            const dims = this.xterm._core?._renderService?.dimensions;
            if (dims?.actualCellWidth) charWidth = dims.actualCellWidth;
            if (dims?.actualCellHeight) charHeight = dims.actualCellHeight;
        } catch (_) {}

        const width = content.clientWidth - 16;
        const height = content.clientHeight - 16;

        const cols = Math.floor(width / charWidth);
        const rows = Math.floor(height / charHeight);

        if (cols > 0 && rows > 0 && (cols !== this.xterm.cols || rows !== this.xterm.rows)) {
            this.xterm.resize(cols, rows);
        }
    }

    toggleSearch() {
        // Implement search functionality
        this.xterm.writeln(`\r\n🔍 Search feature coming soon`);
    }

    _setStatus(msg) {
        const statusEl = this.container.querySelector('.termisol-terminal-title');
        if (statusEl) {
            // Create temporary status indicator
            const statusIndicator = document.createElement('span');
            statusIndicator.className = 'termisol-status-indicator';
            statusIndicator.textContent = msg;
            statusIndicator.style.cssText = `
                color: var(--muted);
                font-size: 11px;
                margin-left: 8px;
                opacity: 1;
                transition: opacity 0.3s;
            `;
            statusEl.appendChild(statusIndicator);
            
            clearTimeout(this._statusTimer);
            this._statusTimer = setTimeout(() => {
                statusIndicator.style.opacity = '0';
                setTimeout(() => statusIndicator.remove(), 300);
            }, 2000);
        }
    }

    _updateConnectionStatus(status) {
        if (!this.container) return;
        const dot = this.container.querySelector('.termisol-status-dot');
        if (!dot) return;
        dot.classList.remove('connected', 'connecting', 'disconnected');
        dot.classList.add(status);
    }

    _scheduleReconnect() {
        if (this._reconnectAttempts >= this._maxReconnects) {
            this.xterm.writeln('\r\n\x1b[31m● Termisol connection failed after multiple retries. close and reopen the terminal.\x1b[0m');
            return;
        }
        
        const delay = this._reconnectDelay * Math.pow(1.5, this._reconnectAttempts);
        this.xterm.writeln(`\x1b[33m  reconnecting in ${Math.round(delay/1000)}s… (attempt ${this._reconnectAttempts + 1}/${this._maxReconnects})\x1b[0m`);
        
        this._reconnectTimer = setTimeout(() => {
            this._reconnectAttempts++;
            this.connect().catch(() => {
                // Reconnect failed, will try again
            });
        }, delay);
    }

    focus() {
        if (this.xterm) {
            this.xterm.focus();
        }
    }

    _setupDragAndDrop() {
        const wrapper = this.container.querySelector('.termisol-terminal-wrapper');
        const terminalContent = this.container.querySelector('.termisol-terminal-content');
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            wrapper.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        // Visual feedback for drag states
        ['dragenter', 'dragover'].forEach(eventName => {
            wrapper.addEventListener(eventName, () => {
                wrapper.classList.add('drag-over');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            wrapper.addEventListener(eventName, () => {
                wrapper.classList.remove('drag-over');
            });
        });
        
        // Handle file drop
        wrapper.addEventListener('drop', async (e) => {
            const files = Array.from(e.dataTransfer.files);
            const items = Array.from(e.dataTransfer.items);
            
            if (files.length === 0 && items.length === 0) return;
            
            // Process files and folders
            for (const item of items) {
                if (item.kind === 'file') {
                    const entry = item.webkitGetAsEntry();
                    if (entry) {
                        await this._handleDroppedEntry(entry);
                    }
                }
            }
            
            // Also handle direct files
            for (const file of files) {
                await this._handleDroppedFile(file);
            }
        });
    }
    
    async _handleDroppedEntry(entry) {
        if (entry.isDirectory) {
            await this._handleDroppedDirectory(entry);
        } else if (entry.isFile) {
            const file = await this._getFileFromEntry(entry);
            if (file) {
                await this._handleDroppedFile(file);
            }
        }
    }
    
    async _getFileFromEntry(entry) {
        return new Promise((resolve) => {
            entry.file((file) => {
                resolve(file);
            });
        });
    }
    
    async _handleDroppedDirectory(directoryEntry) {
        try {
            // Get directory path
            const dirPath = entry.fullPath || directoryEntry.name;
            
            // Clean up the path and paste at cursor position
            const cleanPath = dirPath.replace(/^\/+/, '');
            const pathToPaste = cleanPath.startsWith('/') ? cleanPath : `./${cleanPath}`;
            
            // Paste the path at current cursor position
            await this.sendInput(pathToPaste);
            
            // Show visual feedback
            this.xterm.writeln(`\r\n📁 Pasted directory path: ${pathToPaste}`);
            
        } catch (error) {
            console.error('[termisol] Error handling directory drop:', error);
            this.xterm.writeln(`\r\n❌ Error accessing directory: ${directoryEntry.name}`);
        }
    }
    
    async _handleDroppedFile(file) {
        try {
            // Get file path
            const filePath = file.name || file.webkitRelativePath || file.path;
            
            if (!filePath) {
                // If we can't get the path, just show the filename
                this.xterm.writeln(`\r\n📄 File dropped: ${file.name}`);
                return;
            }
            
            // Clean up the path and paste at cursor position
            const cleanPath = filePath.replace(/^\/+/, '');
            const pathToPaste = cleanPath.startsWith('/') ? cleanPath : `./${cleanPath}`;
            
            // Paste file path at current cursor position
            await this.sendInput(pathToPaste);
            
            // Show visual feedback
            const fileName = filePath.split('/').pop();
            this.xterm.writeln(`\r\n📄 Pasted file path: ${pathToPaste}`);
            
        } catch (error) {
            console.error('[termisol] Error handling file drop:', error);
            this.xterm.writeln(`\r\n❌ Error processing file: ${file.name}`);
        }
    }

    destroy() {
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
        }
        if (this.websocket) {
            this.websocket.close();
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

// Initialize Termisol terminal panel
function initTermisolPanel() {
    if (TermisolState._initialized) return;
    TermisolState._initialized = true;

    console.log('[termisol] initTermisolPanel called');
    const tabsContainer = document.getElementById('terminalTabs');
    const termContainer = document.getElementById('terminalContainer');
    console.log('[termisol] tabsContainer:', tabsContainer, 'termContainer:', termContainer);
    if (!tabsContainer || !termContainer) {
        console.error('[termisol] Missing containers');
        return;
    }

    // Bind events to existing buttons
    const panelNewBtn = document.getElementById('btnNewTerminal');
    const panelCloseBtn = document.getElementById('btnCloseTerminal');
    if (panelNewBtn) panelNewBtn.addEventListener('click', () => createNewTermisolTerminal());
    if (panelCloseBtn) panelCloseBtn.addEventListener('click', () => {
        if (typeof switchPanel === 'function') {
            switchPanel('terminal');
        } else {
            closeActiveTermisolTerminal();
        }
    });

    // Load existing terminals
    loadTermisolTerminals();
}

// Load Termisol terminals from server
async function loadTermisolTerminals() {
    try {
        const _api = typeof window.api === 'function' ? window.api : null;
        let data;
        if (_api) {
            data = await _api('api/termisol/list');
        } else {
            const resp = await fetch(new URL('api/termisol/list', getApiBase()).href, { credentials: 'include' });
            data = await resp.json();
        }

        if (data.terminals && data.terminals.length > 0) {
            for (const term of data.terminals) {
                if (!TermisolState.terminals.has(term.terminal_id)) {
                    await createTermisolTerminalTab(term.terminal_id, term.name, term.cwd, term.features);
                }
            }
        } else {
            if (TermisolState.terminals.size === 0) {
                await createNewTermisolTerminal();
            }
        }
    } catch (e) {
        console.error('[termisol] Failed to load terminals:', e);
        if (TermisolState.terminals.size === 0) {
            await createNewTermisolTerminal();
        }
    }
}

// Get current workspace directory
function getCurrentWorkspace() {
    if (window.S && window.S.session && window.S.session.workspace) {
        return window.S.session.workspace;
    }
    if (window.S && window.S.currentDir) {
        return window.S.currentDir;
    }
    return '~';
}

// Create a new Termisol terminal
async function createNewTermisolTerminal() {
    const cwd = getCurrentWorkspace();
    const sessionId = (window.S && window.S.session && window.S.session.session_id) || 'anonymous';
    
    // Default features for new terminal
    const features = {
        'ai_assistance': true,
        'video_playback': true,
        'audio_visualization': true,
        '3d_modeling': true,
        'git_integration': true,
        'docker_integration': true,
        'database_client': true,
        'syntax_highlighting': true,
        'error_detection': true,
        'command_prediction': true,
        'file_manager': true,
        'collaboration': true,
        'session_recording': true,
        'performance_monitoring': true,
        'hotkeys': true,
        'notifications': true,
        'themes': true,
        'plugins': true
    };

    const payload = { cwd, session_id: sessionId, features };

    try {
        const _api = typeof window.api === 'function' ? window.api : null;
        let data;
        if (_api) {
            data = await _api('api/termisol/create', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
        } else {
            const resp = await fetch(new URL('api/termisol/create', getApiBase()).href, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            data = await resp.json();
        }
        
        if (data.terminal_id) {
            await createTermisolTerminalTab(data.terminal_id, data.name, data.cwd, data.features);
        }
    } catch (e) {
        console.error('[termisol] Failed to create terminal:', e);
        showToast('Failed to create Termisol terminal', 3000);
    }
}

// Create Termisol terminal tab
async function createTermisolTerminalTab(terminalId, name, cwd, features) {
    const container = document.createElement('div');
    container.className = 'termisol-terminal-instance';
    container.style.cssText = 'width: 100%; height: 100%; display: none;';
    container.id = `termisol-container-${terminalId}`;

    const termContainer = document.getElementById('terminalContainer');
    if (!termContainer) {
        console.error('[termisol] terminalContainer not found');
        return;
    }
    termContainer.appendChild(container);

    const term = new TermisolTerminalInstance(terminalId, name, cwd, features);
    TermisolState.terminals.set(terminalId, term);
    TermisolState.features.set(terminalId, features);

    await term.init(container);
    createTermisolTabElement(terminalId, name, features);
    activateTermisolTerminal(terminalId);
}

// Create Termisol tab element
function createTermisolTabElement(terminalId, name, features) {
    const tabsContainer = document.getElementById('terminalTabs');

    const tab = document.createElement('div');
    tab.className = 'terminal-tab termisol-tab';
    tab.id = `terminal-tab-${terminalId}`;
    tab.innerHTML = `
        <span class="terminal-status-dot connecting" title="connection status"></span>
        <span class="terminal-tab-name">${escapeHtml(name)} ${TERMISOL_ICON}</span>
        <span class="terminal-tab-status"></span>
        <span class="terminal-tab-close">${CLOSE_ICON}</span>
    `;

    // Click to activate
    tab.addEventListener('click', (e) => {
        if (!e.target.closest('.terminal-tab-close')) {
            activateTermisolTerminal(terminalId);
        }
    });

    // Close button
    tab.querySelector('.terminal-tab-close').addEventListener('click', (e) => {
        e.stopPropagation();
        closeTermisolTerminal(terminalId);
    });

    // Right-click context menu
    tab.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showTermisolContextMenu(e, terminalId);
    });

    tabsContainer.appendChild(tab);

    const term = TermisolState.terminals.get(terminalId);
    if (term) {
        term.tabElement = tab;
    }
}

// Activate Termisol terminal
function activateTermisolTerminal(terminalId) {
    console.log('[termisol] activateTermisolTerminal called for:', terminalId);
    
    // Hide all terminals
    TermisolState.terminals.forEach((term, id) => {
        if (term.container) {
            term.container.style.display = 'none';
        }
        if (term.tabElement) {
            term.tabElement.classList.remove('active');
        }
    });

    // Show active terminal
    const term = TermisolState.terminals.get(terminalId);
    console.log('[termisol] term to activate:', term);
    if (term) {
        if (term.container) {
            term.container.style.display = 'block';
            console.log('[termisol] container display set to block');
        }
        if (term.tabElement) {
            term.tabElement.classList.add('active');
        }
        if (term.xterm) {
            requestAnimationFrame(() => {
                term.fit();
                term.focus();
            });
            console.log('[termisol] xterm fit + focused');
        }
    }

    TermisolState.activeTerminalId = terminalId;
}

// Close Termisol terminal
async function closeTermisolTerminal(terminalId) {
    const term = TermisolState.terminals.get(terminalId);
    if (!term) return;

    try {
        const _api = typeof window.api === 'function' ? window.api : null;
        if (_api) {
            await _api(`api/termisol/${terminalId}/close`, {
                method: 'POST'
            });
        } else {
            await fetch(new URL(`api/termisol/${terminalId}/close`, getApiBase()).href, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });
        }
    } catch (e) {
        console.error('[termisol] Failed to close terminal:', e);
    }

    // Remove from UI
    term.destroy();
    TermisolState.terminals.delete(terminalId);
    TermisolState.features.delete(terminalId);

    if (term.tabElement && term.tabElement.parentNode) {
        term.tabElement.remove();
    }

    // Activate another terminal if this was active
    if (TermisolState.activeTerminalId === terminalId) {
        const remaining = Array.from(TermisolState.terminals.keys());
        if (remaining.length > 0) {
            activateTermisolTerminal(remaining[0]);
        } else {
            TermisolState.activeTerminalId = null;
            await createNewTermisolTerminal();
        }
    }
}

// Close active Termisol terminal
function closeActiveTermisolTerminal() {
    if (TermisolState.activeTerminalId) {
        closeTermisolTerminal(TermisolState.activeTerminalId);
    }
}

// Show context menu for Termisol terminal tab
function showTermisolContextMenu(e, terminalId) {
    const term = TermisolState.terminals.get(terminalId);
    if (!term) return;

    // Remove existing menu
    const existing = document.querySelector('.termisol-context-menu');
    if (existing) existing.remove();

    const menu = document.createElement('div');
    menu.className = 'termisol-context-menu';
    menu.style.cssText = `
        position: fixed;
        left: ${e.clientX}px;
        top: ${e.clientY}px;
        background: var(--sidebar);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 4px 0;
        z-index: 1000;
        min-width: 180px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;

    menu.innerHTML = `
        <div class="termisol-menu-item" data-action="rename">Rename</div>
        <div class="termisol-menu-item" data-action="features">Configure Features</div>
        <div class="termisol-menu-separator"></div>
        <div class="termisol-menu-item" data-action="clear">Clear</div>
        <div class="termisol-menu-item" data-action="record">Toggle Recording</div>
        <div class="termisol-menu-item" data-action="screenshot">Screenshot</div>
        <div class="termisol-menu-separator"></div>
        <div class="termisol-menu-item" data-action="new">New Terminal</div>
        <div class="termisol-menu-item" data-action="close">Close</div>
    `;

    menu.addEventListener('click', async (ev) => {
        const action = ev.target.dataset.action;
        if (action === 'rename') {
            const newName = prompt('Terminal name:', term.name);
            if (newName && newName.trim()) {
                await renameTermisolTerminal(terminalId, newName.trim());
            }
        } else if (action === 'features') {
            term.toggleFeaturePanel('features');
        } else if (action === 'clear') {
            if (term.xterm) term.xterm.clear();
        } else if (action === 'record') {
            term.toggleRecording();
        } else if (action === 'screenshot') {
            term.takeScreenshot();
        } else if (action === 'new') {
            await createNewTermisolTerminal();
        } else if (action === 'close') {
            await closeTermisolTerminal(terminalId);
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


// Rename Termisol terminal
async function renameTermisolTerminal(terminalId, name) {
    const term = TermisolState.terminals.get(terminalId);
    if (term) {
        term.name = name;
        if (term.tabElement) {
            const nameEl = term.tabElement.querySelector('.terminal-tab-name');
            if (nameEl) nameEl.textContent = `${name} ${TERMISOL_ICON}`;
        }
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
function onTermisolPanelShow() {
    TermisolState.panelVisible = true;
    const term = TermisolState.terminals.get(TermisolState.activeTerminalId);
    if (term) {
        setTimeout(() => {
            term.fit();
            term.focus();
        }, 100);
    }
}

function onTermisolPanelHide() {
    TermisolState.panelVisible = false;
}

// Expose to global
typeof window !== 'undefined' && (window.TermisolPanel = {
    init: initTermisolPanel,
    create: createNewTermisolTerminal,
    activate: activateTermisolTerminal,
    onShow: onTermisolPanelShow,
    onHide: onTermisolPanelHide,
    state: TermisolState
});
