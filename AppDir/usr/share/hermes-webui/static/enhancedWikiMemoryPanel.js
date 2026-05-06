/**
 * Enhanced Wiki / Memory / SP Browser Panel v2.0
 * Rich viewer with tabbed interface, search, filtering, and detail views
 * 
 * Replaces panelMemory with a comprehensive data browser integrating:
 * - Memster memories (with categories, filtering, search)
 * - Wiki pages (with categories, backlinks, outgoing links)
 * - Simply Plural headmates (with colors, pronouns, front history)
 */

const EnhancedWikiMemoryPanel = (function() {
    'use strict';
    
    // State management
    const state = {
        view: 'memories', // 'memories' | 'wiki' | 'sp'
        memories: [],
        wikiPages: [],
        headmates: [],
        spStatus: null,
        spHistory: [],
        selected: null,
        search: '',
        filter: 'all',
        loading: false,
        lastRefresh: null,
        autoRefreshInterval: null
    };
    
    // Configuration
    const CONFIG = {
        refreshInterval: 60000, // 60s auto-refresh
        searchDebounce: 300,
        previewLength: 80,
        detailLength: 2000
    };
    
    // UI References (populated in init)
    let ui = {};
    let searchTimeout;
    
    // Category configurations
    const MEMORY_CATEGORIES = {
        all: { label: 'all', color: 'var(--neutral)' },
        world: { label: 'world', color: '#4CAF50' },
        experience: { label: 'experience', color: '#2196F3' },
        opinion: { label: 'opinion', color: '#FF9800' },
        observation: { label: 'observation', color: '#9C27B0' }
    };
    
    const WIKI_CATEGORIES = {
        all: { label: 'all', color: 'var(--neutral)' },
        infrastructure: { label: 'infrastructure', color: '#607D8B' },
        projects: { label: 'projects', color: '#3F51B5' },
        preferences: { label: 'preferences', color: '#E91E63' },
        system: { label: 'system', color: '#795548' },
        apps: { label: 'apps', color: '#00BCD4' },
        people: { label: 'people', color: '#FF5722' },
        notes: { label: 'notes', color: '#9E9E9E' }
    };
    
    // ============================================
    // Initialization
    // ============================================
    
    function init(containerId) {
        const container = document.getElementById(containerId || 'wikiMemoryBrowser');
        if (!container) {
            console.error('[EWM] Container not found:', containerId);
            return false;
        }
        
        // Inject HTML structure
        container.innerHTML = buildHTML();
        
        // Cache UI elements
        ui.container = container;
        ui.tabs = container.querySelectorAll('[data-tab]');
        ui.searchInput = container.querySelector('#ewm-search');
        ui.filterSelect = container.querySelector('#ewm-filter');
        ui.content = container.querySelector('#ewm-content');
        ui.detail = container.querySelector('#ewm-detail');
        ui.detailBody = container.querySelector('#ewm-detail-body');
        ui.fronter = container.querySelector('#ewm-fronter');
        ui.loading = container.querySelector('#ewm-loading');
        ui.empty = container.querySelector('#ewm-empty');
        ui.count = container.querySelector('#ewm-count');
        
        // Bind events
        bindEvents();
        
        // Initial data load
        refreshAll();
        
        // Setup auto-refresh
        if (state.autoRefreshInterval) clearInterval(state.autoRefreshInterval);
        state.autoRefreshInterval = setInterval(refreshAll, CONFIG.refreshInterval);
        
        console.log('[EWM] Panel initialized');
        return true;
    }
    
    function buildHTML() {
        return `
            <div id="ewm-panel" class="ewm-panel">
                <!-- Header with tabs and fronter -->
                <div class="ewm-header">
                    <div class="ewm-tabs">
                        <button class="ewm-tab active" data-tab="memories" title="Browse memster memories">
                            <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
                            memories
                        </button>
                        <button class="ewm-tab" data-tab="wiki" title="Browse wiki pages">
                            <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M12 3L1 9l4 20h14l4-20L12 3zm0 2.8L20.5 9l-.5.8-8-2-8 2-.5-.8L12 5.8z"/></svg>
                            wiki
                        </button>
                        <button class="ewm-tab" data-tab="sp" title="Browse SP headmates">
                            <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5s-3 1.34-3 3 .34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
                            headmates
                        </button>
                    </div>
                    <div id="ewm-fronter" class="ewm-fronter">
                        <span class="ewm-fronter-dot"></span>
                        <span class="ewm-fronter-name">checking...</span>
                    </div>
                </div>
                
                <!-- Search and filters -->
                <div class="ewm-controls">
                    <div class="ewm-search-wrap">
                        <svg class="ewm-search-icon" viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5z"/></svg>
                        <input type="text" id="ewm-search" placeholder="search..." class="ewm-search-input" autocomplete="off">
                    </div>
                    <select id="ewm-filter" class="ewm-filter">
                        <option value="all">all categories</option>
                    </select>
                    <button class="ewm-refresh" id="ewm-refresh" title="refresh data">
                        <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
                    </button>
                </div>
                
                <!-- Loading state -->
                <div id="ewm-loading" class="ewm-loading" style="display:none;">
                    <div class="ewm-spinner"></div>
                    <span>loading...</span>
                </div>
                
                <!-- Empty state -->
                <div id="ewm-empty" class="ewm-empty" style="display:none;">
                    <svg viewBox="0 0 24 24" width="32" height="32"><path fill="currentColor" opacity="0.5" d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                    <p>nothing found</p>
                </div>
                
                <!-- Content area -->
                <div id="ewm-content" class="ewm-content"></div>
                
                <!-- Status bar -->
                <div class="ewm-status">
                    <span id="ewm-count">0 items</span>
                    <span id="ewm-last-refresh"></span>
                </div>
            </div>
            
            <!-- Detail view overlay -->
            <div id="ewm-detail" class="ewm-detail" style="display:none;">
                <div class="ewm-detail-header">
                    <button id="ewm-back" class="ewm-back-btn">
                        <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
                        back
                    </button>
                    <div class="ewm-detail-actions">
                        <button id="ewm-detail-copy" title="copy content">
                            <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                        </button>
                        <button id="ewm-detail-close" title="close">
                            <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                        </button>
                    </div>
                </div>
                <div id="ewm-detail-body" class="ewm-detail-body"></div>
            </div>
        `;
    }
    
    // ============================================
    // Event Binding
    // ============================================
    
    function bindEvents() {
        // Tab switching
        ui.tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const view = tab.dataset.tab;
                switchView(view);
            });
        });
        
        // Search with debounce
        ui.searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                state.search = e.target.value.trim();
                renderContent();
            }, CONFIG.searchDebounce);
        });
        
        // Filter change
        ui.filterSelect.addEventListener('change', (e) => {
            state.filter = e.target.value;
            renderContent();
        });
        
        // Refresh button
        ui.container.querySelector('#ewm-refresh').addEventListener('click', refreshAll);
        
        // Content click delegation
        ui.content.addEventListener('click', handleContentClick);
        
        // Detail view controls
        ui.container.querySelector('#ewm-back').addEventListener('click', closeDetail);
        ui.container.querySelector('#ewm-detail-close').addEventListener('click', closeDetail);
        ui.container.querySelector('#ewm-detail-copy').addEventListener('click', copyDetail);
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && state.selected) {
                closeDetail();
            }
        });
    }
    
    function handleContentClick(e) {
        const card = e.target.closest('.ewm-card');
        if (!card) return;
        
        const type = card.dataset.type;
        const id = card.dataset.id;
        
        if (type === 'memory') {
            const memory = state.memories.find(m => String(m.id) === id);
            if (memory) showDetail(memory, 'memory');
        } else if (type === 'wiki') {
            fetch((window.HERMES_API_BASE || location.origin) + `/api/wiki/pages/${encodeURIComponent(id)}`)
                .then(r => r.json())
                .then(data => {
                    if (data.ok) showDetail(data.page, 'wiki');
                });
        } else if (type === 'headmate') {
            const headmate = state.headmates.find(h => h.uid === id);
            if (headmate) showDetail(headmate, 'headmate');
        }
    }
    
    // ============================================
    // View Management
    // ============================================
    
    function switchView(view) {
        state.view = view;
        state.selected = null;
        state.search = '';
        ui.searchInput.value = '';
        
        // Update tab UI
        ui.tabs.forEach(t => {
            t.classList.toggle('active', t.dataset.tab === view);
        });
        
        // Update filter options
        updateFilterOptions();
        
        // Render
        renderContent();
    }
    
    function updateFilterOptions() {
        const categories = state.view === 'memories' ? MEMORY_CATEGORIES : 
                          state.view === 'wiki' ? WIKI_CATEGORIES : { all: { label: 'all' } };
        
        const options = Object.entries(categories).map(([key, cfg]) => 
            `<option value="${key}">${cfg.label}</option>`
        ).join('');
        
        ui.filterSelect.innerHTML = options;
    }
    
    // ============================================
    // Data Loading
    // ============================================
    
    async function refreshAll() {
        // First, load from cache and render immediately for instant display
        let cachedMemories = null;
        let cachedWiki = null;
        try { cachedMemories = localStorage.getItem('hermes-memories-cache'); } catch (e) {}
        try { cachedWiki = localStorage.getItem('hermes-wiki-cache'); } catch (e) {}
        let hasCachedData = false;

        if (cachedMemories && state.memories.length === 0) {
            try {
                state.memories = JSON.parse(cachedMemories);
                hasCachedData = true;
            } catch (e) {}
        }
        if (cachedWiki && state.wikiPages.length === 0) {
            try {
                state.wikiPages = JSON.parse(cachedWiki);
                hasCachedData = true;
            } catch (e) {}
        }

        // Render cached data immediately if available
        if (hasCachedData) {
            ui.loading.style.display = 'none';
            ui.content.style.display = '';
            renderContent();
        } else {
            // No cache, show loading
            state.loading = true;
            ui.loading.style.display = 'flex';
            ui.content.style.display = 'none';
        }
        ui.empty.style.display = 'none';

        // Fetch fresh data in background
        await Promise.all([
            loadMemories(),
            loadWikiPages(),
            loadHeadmates(),
            loadSPStatus()
        ]);

        state.loading = false;
        state.lastRefresh = new Date();

        ui.loading.style.display = 'none';
        ui.content.style.display = '';

        updateFronter();
        renderContent();
        updateStatus();
    }
    
    async function loadMemories() {
        // Load from cache instantly if available
        let cached = null;
        try { cached = localStorage.getItem('hermes-memories-cache'); } catch (e) {}
        if (cached && state.memories.length === 0) {
            try {
                state.memories = JSON.parse(cached);
            } catch (e) { /* ignore parse errors */ }
        }
        try {
            const resp = await fetch((window.HERMES_API_BASE || location.origin) + '/api/memories?limit=100');
            const data = await resp.json();
            state.memories = data.memories || [];
            // Cache for instant load next time
            try { localStorage.setItem('hermes-memories-cache', JSON.stringify(state.memories)); } catch (e) {}
        } catch (e) {
            console.error('[EWM] Failed to load memories:', e);
            if (state.memories.length === 0) state.memories = [];
        }
    }

    async function loadWikiPages() {
        // Load from cache instantly if available
        let cached = null;
        try { cached = localStorage.getItem('hermes-wiki-cache'); } catch (e) {}
        if (cached && state.wikiPages.length === 0) {
            try {
                state.wikiPages = JSON.parse(cached);
            } catch (e) { /* ignore parse errors */ }
        }
        try {
            const resp = await fetch((window.HERMES_API_BASE || location.origin) + '/api/wiki/pages');
            const data = await resp.json();
            state.wikiPages = data.pages || [];
            // Cache for instant load next time
            try { localStorage.setItem('hermes-wiki-cache', JSON.stringify(state.wikiPages)); } catch (e) {}
        } catch (e) {
            console.error('[EWM] Failed to load wiki:', e);
            if (state.wikiPages.length === 0) state.wikiPages = [];
        }
    }
    
    async function loadHeadmates() {
        try {
            const resp = await fetch((window.HERMES_API_BASE || location.origin) + '/api/sp/members');
            const data = await resp.json();
            state.headmates = data.members || [];
        } catch (e) {
            console.error('[EWM] Failed to load headmates:', e);
            state.headmates = [];
        }
    }
    
    async function loadSPStatus() {
        try {
            const resp = await fetch((window.HERMES_API_BASE || location.origin) + '/api/sp/status');
            const data = await resp.json();
            state.spStatus = data.status;
        } catch (e) {
            console.error('[EWM] Failed to load SP status:', e);
            state.spStatus = null;
        }
    }
    
    function updateFronter() {
        const status = state.spStatus;
        const dot = ui.fronter.querySelector('.ewm-fronter-dot');
        const name = ui.fronter.querySelector('.ewm-fronter-name');
        
        if (status?.current_member) {
            const color = status.current_member.color || '#888';
            dot.style.background = color;
            dot.style.boxShadow = `0 0 8px ${color}`;
            name.textContent = status.current_member.name || 'unknown';
            ui.fronter.style.opacity = '1';
        } else {
            dot.style.background = 'var(--muted)';
            dot.style.boxShadow = 'none';
            name.textContent = 'no front';
            ui.fronter.style.opacity = '0.6';
        }
    }
    
    // ============================================
    // Rendering
    // ============================================
    
    function renderContent() {
        let content = '';
        
        switch (state.view) {
            case 'memories':
                content = renderMemories();
                break;
            case 'wiki':
                content = renderWiki();
                break;
            case 'sp':
                content = renderSP();
                break;
        }
        
        if (!content) {
            ui.content.style.display = 'none';
            ui.empty.style.display = 'flex';
        } else {
            ui.content.innerHTML = content;
            ui.content.style.display = '';
            ui.empty.style.display = 'none';
        }
        
        updateCount();
    }
    
    function renderMemories() {
        let items = [...state.memories];
        
        // Filter by category
        if (state.filter !== 'all') {
            items = items.filter(m => (m.category || 'observation') === state.filter);
        }
        
        // Search
        if (state.search) {
            const q = state.search.toLowerCase();
            items = items.filter(m => (m.content || '').toLowerCase().includes(q));
        }
        
        if (!items.length) return '';
        
        return items.map(m => {
            const cat = m.category || 'observation';
            const catCfg = MEMORY_CATEGORIES[cat] || MEMORY_CATEGORIES.observation;
            const content = (m.content || 'empty').substring(0, CONFIG.previewLength);
            const importance = m.importance || 50;
            const date = m.updated_at ? formatDate(m.updated_at) : '';
            
            return `
                <div class="ewm-card" data-type="memory" data-id="${m.id}">
                    <div class="ewm-card-header">
                        <span class="ewm-card-category" style="color:${catCfg.color}">${catCfg.label}</span>
                        <span class="ewm-card-importance" title="importance: ${importance}%">
                            ${'●'.repeat(Math.ceil(importance / 25)) || '○'}
                        </span>
                    </div>
                    <div class="ewm-card-body">${escapeHtml(content)}</div>
                    <div class="ewm-card-footer">
                        <span class="ewm-card-date">${date}</span>
                        ${m.tags && m.tags.length ? `<span class="ewm-card-tags">${m.tags.slice(0, 2).map(t => `#${t}`).join(' ')}</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    function renderWiki() {
        let items = [...state.wikiPages];
        
        // Filter by category
        if (state.filter !== 'all') {
            items = items.filter(p => (p.category || 'notes') === state.filter);
        }
        
        // Search
        if (state.search) {
            const q = state.search.toLowerCase();
            items = items.filter(p => 
                (p.title || '').toLowerCase().includes(q) ||
                (p.content || '').toLowerCase().includes(q)
            );
        }
        
        if (!items.length) return '';
        
        // Group by category
        const byCat = {};
        items.forEach(p => {
            const cat = p.category || 'notes';
            byCat[cat] = byCat[cat] || [];
            byCat[cat].push(p);
        });
        
        return Object.entries(byCat).map(([cat, pages]) => {
            const catCfg = WIKI_CATEGORIES[cat] || WIKI_CATEGORIES.notes;
            const header = `<div class="ewm-section-header" style="--cat-color:${catCfg.color}">
                <span class="ewm-section-dot" style="background:${catCfg.color}"></span>
                ${cat}
            </div>`;
            
            const cards = pages.map(p => {
                const title = p.title || p.slug;
                const snippet = (p.snippet || '').substring(0, 120);
                const wc = p.word_count || 0;
                const links = (p.link_count_out || 0) + (p.link_count_in || 0);
                
                return `
                    <div class="ewm-card" data-type="wiki" data-id="${p.slug}">
                        <div class="ewm-card-header">
                            <span class="ewm-card-title">${escapeHtml(title)}</span>
                        </div>
                        <div class="ewm-card-body">${escapeHtml(snippet)}...</div>
                        <div class="ewm-card-footer">
                            <span>${wc} words</span>
                            <span>${links} links</span>
                        </div>
                    </div>
                `;
            }).join('');
            
            return header + cards;
        }).join('');
    }
    
    function renderSP() {
        let items = [...state.headmates];
        
        // Sort: current first, then by name
        items.sort((a, b) => {
            if (a.is_current && !b.is_current) return -1;
            if (!a.is_current && b.is_current) return 1;
            return (a.name || '').localeCompare(b.name || '');
        });
        
        // Search
        if (state.search) {
            const q = state.search.toLowerCase();
            items = items.filter(h => (h.name || '').toLowerCase().includes(q));
        }
        
        if (!items.length) return '';
        
        return items.map(h => {
            const color = h.color || '#888';
            const initial = (h.name || '?')[0].toUpperCase();
            const status = h.is_current ? '<span class="ewm-current-badge">current</span>' : '';
            
            return `
                <div class="ewm-card ewm-headmate" data-type="headmate" data-id="${h.uid}">
                    <div class="ewm-headmate-avatar" style="background:${color};color:${getContrastYIQ(color)}">
                        ${initial}
                    </div>
                    <div class="ewm-headmate-info">
                        <div class="ewm-headmate-name">${escapeHtml(h.name)} ${status}</div>
                        <div class="ewm-headmate-pronouns">${h.pronouns || ''}</div>
                        <div class="ewm-headmate-desc">${escapeHtml((h.description || '').substring(0, 60))}</div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    // ============================================
    // Detail View
    // ============================================
    
    function showDetail(item, type) {
        state.selected = { item, type };
        
        let html = '';
        
        if (type === 'memory') {
            const cat = item.category || 'observation';
            const catCfg = MEMORY_CATEGORIES[cat] || MEMORY_CATEGORIES.observation;
            
            html = `
                <div class="ewm-detail-type" style="color:${catCfg.color}">
                    <span class="ewm-detail-dot" style="background:${catCfg.color}"></span>
                    ${cat} memory
                </div>
                <div class="ewm-detail-title">memory #${item.id}</div>
                <div class="ewm-detail-content">${escapeHtml(item.content || '')}</div>
                <div class="ewm-detail-meta">
                    <div>importance: ${item.importance || 50}%</div>
                    <div>tier: ${item.tier || 'L4'}</div>
                    <div>created: ${formatFullDate(item.created_at)}</div>
                    <div>updated: ${formatFullDate(item.updated_at)}</div>
                    ${item.tags && item.tags.length ? `<div>tags: ${item.tags.map(t => `#${t}`).join(' ')}</div>` : ''}
                </div>
            `;
        } else if (type === 'wiki') {
            const cat = item.category || 'notes';
            
            html = `
                <div class="ewm-detail-type">${cat} page</div>
                <div class="ewm-detail-title">${escapeHtml(item.title || item.slug)}</div>
                <div class="ewm-detail-content ewm-wiki-content">${escapeHtml(item.content || '')}</div>
                <div class="ewm-detail-meta">
                    <div>${item.word_count || 0} words</div>
                    <div>updated: ${formatFullDate(item.updated_at)}</div>
                    ${item.outgoing_links?.length ? `<div>links to: ${item.outgoing_links.slice(0, 5).join(', ')}</div>` : ''}
                    ${item.backlinks?.length ? `<div>linked from: ${item.backlinks.slice(0, 5).join(', ')}</div>` : ''}
                </div>
            `;
        } else if (type === 'headmate') {
            const color = item.color || '#888';
            const status = item.is_current ? '<span class="ewm-current-badge">currently fronting</span>' : '';
            
            html = `
                <div class="ewm-detail-type" style="color:${color}">
                    <span class="ewm-detail-dot" style="background:${color}"></span>
                    headmate ${status}
                </div>
                <div class="ewm-detail-title">
                    <div class="ewm-headmate-avatar-large" style="background:${color};color:${getContrastYIQ(color)}">
                        ${(item.name || '?')[0].toUpperCase()}
                    </div>
                    ${escapeHtml(item.name)}
                </div>
                <div class="ewm-headmate-meta">
                    ${item.pronouns ? `<span>${item.pronouns}</span>` : ''}
                    <span>${item.color_name || item.color || 'no color'}</span>
                </div>
                <div class="ewm-detail-content">${escapeHtml(item.description || 'no description')}</div>
            `;
        }
        
        ui.detailBody.innerHTML = html;
        ui.detail.style.display = 'flex';
    }
    
    function closeDetail() {
        state.selected = null;
        ui.detail.style.display = 'none';
    }
    
    function copyDetail() {
        if (!state.selected) return;
        const content = state.selected.item.content || '';
        navigator.clipboard.writeText(content).then(() => {
            // Visual feedback could go here
        });
    }
    
    // ============================================
    // Utilities
    // ============================================
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function formatDate(ts) {
        if (!ts) return '';
        const d = new Date(ts);
        const now = new Date();
        const diff = now - d;
        const days = Math.floor(diff / 86400000);
        
        if (days < 1) return 'today';
        if (days === 1) return 'yesterday';
        if (days < 7) return `${days}d ago`;
        if (days < 30) return `${Math.floor(days / 7)}w ago`;
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }
    
    function formatFullDate(ts) {
        if (!ts) return 'unknown';
        return new Date(ts).toLocaleString();
    }
    
    function getContrastYIQ(hex) {
        hex = hex.replace('#', '');
        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);
        const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
        return yiq >= 128 ? '#000' : '#fff';
    }
    
    function updateCount() {
        let count = 0;
        if (state.view === 'memories') count = state.memories.length;
        else if (state.view === 'wiki') count = state.wikiPages.length;
        else count = state.headmates.length;
        
        ui.count.textContent = `${count} items`;
    }
    
    function updateStatus() {
        const el = ui.container.querySelector('#ewm-last-refresh');
        if (state.lastRefresh) {
            el.textContent = `refreshed ${formatDate(state.lastRefresh.toISOString())}`;
        }
    }
    
    // ============================================
    // Public API
    // ============================================
    
    return {
        init,
        refreshAll,
        switchView,
        getState: () => ({ ...state })
    };
})();

// Auto-init with retry
document.addEventListener('DOMContentLoaded', function initEWM() {
    const el = document.getElementById('wikiMemoryBrowser');
    if (el) {
        EnhancedWikiMemoryPanel.init('wikiMemoryBrowser');
    } else {
        // Retry after short delay if DOM not ready
        setTimeout(initEWM, 100);
    }
});

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedWikiMemoryPanel;
}
