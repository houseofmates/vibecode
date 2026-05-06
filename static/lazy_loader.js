/**
 * Advanced lazy loading system for UI components.
 * Implements intersection observer, prefetching, and progressive loading.
 */

// Lazy loading state
const LazyLoader = (function() {
    // Configuration
    const config = {
        rootMargin: '50px',
        threshold: 0.1,
        loadingDelay: 100,
        prefetchDelay: 2000,
        maxConcurrentLoads: 3,
        retryAttempts: 3,
        retryDelay: 1000
    };

    // State tracking
    const state = {
        observer: null,
        loadingQueue: [],
        activeLoads: new Set(),
        loadedComponents: new Set(),
        prefetchCache: new Map(),
        retryCount: new Map(),
        loadingStats: {
            total: 0,
            successful: 0,
            failed: 0,
            cached: 0
        }
    };

    // Component registry
    const componentRegistry = new Map();

    /**
     * Register a lazy component
     */
    function registerComponent(componentId, loader, options = {}) {
        componentRegistry.set(componentId, {
            loader,
            options: { ...config, ...options },
            loaded: false,
            loading: false,
            element: null
        });
    }

    /**
     * Initialize intersection observer
     */
    function initializeObserver() {
        if ('IntersectionObserver' in window) {
            state.observer = new IntersectionObserver(handleIntersection, {
                rootMargin: config.rootMargin,
                threshold: config.threshold
            });
        } else {
            // Fallback for older browsers
            initializeScrollListener();
        }
    }

    /**
     * Handle intersection observer callbacks
     */
    function handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const componentId = element.dataset.lazyComponent;
                
                if (componentId && !state.activeLoads.has(componentId)) {
                    queueLoad(componentId, element);
                }
            }
        });
    }

    /**
     * Fallback scroll listener for older browsers
     */
    function initializeScrollListener() {
        let scrollTimer = null;
        
        function checkVisibility() {
            document.querySelectorAll('[data-lazy-component]').forEach(element => {
                const rect = element.getBoundingClientRect();
                const isVisible = (
                    rect.top < window.innerHeight + config.rootMargin &&
                    rect.bottom > -config.rootMargin &&
                    rect.left < window.innerWidth + config.rootMargin &&
                    rect.right > -config.rootMargin
                );
                
                if (isVisible) {
                    const componentId = element.dataset.lazyComponent;
                    if (componentId && !state.activeLoads.has(componentId)) {
                        queueLoad(componentId, element);
                    }
                }
            });
        }

        window.addEventListener('scroll', () => {
            if (scrollTimer) clearTimeout(scrollTimer);
            scrollTimer = setTimeout(checkVisibility, config.loadingDelay);
        }, { passive: true });

        // Initial check
        setTimeout(checkVisibility, 100);
    }

    /**
     * Queue component for loading
     */
    function queueLoad(componentId, element) {
        const component = componentRegistry.get(componentId);
        if (!component) return;

        component.element = element;
        state.loadingQueue.push({ componentId, element, component });
        processLoadQueue();
    }

    /**
     * Process loading queue
     */
    async function processLoadQueue() {
        while (state.loadingQueue.length > 0 && state.activeLoads.size < config.maxConcurrentLoads) {
            const { componentId, element, component } = state.loadingQueue.shift();
            
            if (state.loadedComponents.has(componentId)) {
                // Already loaded, just show it
                showComponent(componentId, element);
                continue;
            }

            loadComponent(componentId, element, component);
        }
    }

    /**
     * Load a component
     */
    async function loadComponent(componentId, element, component) {
        state.activeLoads.add(componentId);
        component.loading = true;

        // Show loading indicator
        showLoadingIndicator(element, componentId);

        try {
            const startTime = performance.now();
            
            // Check prefetch cache first
            let content = state.prefetchCache.get(componentId);
            let fromCache = !!content;
            
            if (!content) {
                content = await component.loader(componentId, component.options);
            }
            
            const loadTime = performance.now() - startTime;
            
            // Cache the content
            if (!fromCache) {
                state.prefetchCache.set(componentId, content);
                // Schedule prefetch of related components
                schedulePrefetch(componentId);
            }
            
            // Update stats
            state.loadingStats.total++;
            if (fromCache) {
                state.loadingStats.cached++;
            } else {
                state.loadingStats.successful++;
            }
            
            // Show component
            await showComponent(componentId, element, content);
            
            // Mark as loaded
            component.loaded = true;
            component.loading = false;
            state.loadedComponents.add(componentId);
            
            // Log performance
            console.log(`[LazyLoader] Loaded ${componentId} in ${loadTime.toFixed(2)}ms ${fromCache ? '(cached)' : '(network)'}`);
            
            // Continue processing queue
            setTimeout(processLoadQueue, 10);
            
        } catch (error) {
            console.error(`[LazyLoader] Failed to load ${componentId}:`, error);
            
            // Retry logic
            const retryCount = state.retryCount.get(componentId) || 0;
            if (retryCount < config.retryAttempts) {
                state.retryCount.set(componentId, retryCount + 1);
                setTimeout(() => {
                    state.activeLoads.delete(componentId);
                    processLoadQueue();
                }, config.retryDelay * (retryCount + 1));
            } else {
                // Show error state
                showError(element, componentId, error);
                state.loadingStats.failed++;
            }
        } finally {
            state.activeLoads.delete(componentId);
            component.loading = false;
        }
    }

    /**
     * Show component content
     */
    async function showComponent(componentId, element, content) {
        // Remove loading indicator
        hideLoadingIndicator(element);
        
        if (typeof content === 'string') {
            element.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            element.innerHTML = '';
            element.appendChild(content);
        } else if (content && typeof content.then === 'function') {
            // Handle promise-based content
            try {
                const resolved = await content;
                element.innerHTML = '';
                if (typeof resolved === 'string') {
                    element.innerHTML = resolved;
                } else if (resolved instanceof HTMLElement) {
                    element.appendChild(resolved);
                }
            } catch (error) {
                showError(element, componentId, error);
            }
        }
        
        // Remove lazy attribute
        delete element.dataset.lazyComponent;
        element.classList.remove('lazy-loading');
        element.classList.add('lazy-loaded');
        
        // Trigger custom event
        element.dispatchEvent(new CustomEvent('lazyLoaded', {
            detail: { componentId, element }
        }));
    }

    /**
     * Show loading indicator
     */
    function showLoadingIndicator(element, componentId) {
        element.classList.add('lazy-loading');
        
        // Create or update loading indicator
        let indicator = element.querySelector('.lazy-loading-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'lazy-loading-indicator';
            indicator.innerHTML = `
                <div class="lazy-spinner"></div>
                <div class="lazy-text">Loading...</div>
            `;
            element.style.position = 'relative';
            element.appendChild(indicator);
        }
        
        indicator.dataset.componentId = componentId;
    }

    /**
     * Hide loading indicator
     */
    function hideLoadingIndicator(element) {
        const indicator = element.querySelector('.lazy-loading-indicator');
        if (indicator) {
            indicator.remove();
        }
        element.classList.remove('lazy-loading');
    }

    /**
     * Show error state
     */
    function showError(element, componentId, error) {
        hideLoadingIndicator(element);
        element.classList.add('lazy-error');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'lazy-error-indicator';
        errorDiv.innerHTML = `
            <div class="lazy-error-icon">⚠️</div>
            <div class="lazy-error-message">Failed to load component</div>
            <button class="lazy-retry-btn" data-component-id="${componentId}">Retry</button>
        `;
        
        element.appendChild(errorDiv);
        
        // Add retry handler
        errorDiv.querySelector('.lazy-retry-btn').addEventListener('click', () => {
            errorDiv.remove();
            element.classList.remove('lazy-error');
            state.retryCount.delete(componentId);
            queueLoad(componentId, element);
        });
    }

    /**
     * Schedule prefetching of related components
     */
    function schedulePrefetch(componentId) {
        setTimeout(() => {
            // Find related components based on common patterns
            componentRegistry.forEach((component, id) => {
                if (id !== componentId && !component.loaded && !state.prefetchCache.has(id)) {
                    // Simple heuristic: same prefix or similar naming
                    if (isRelatedComponent(componentId, id)) {
                        prefetchComponent(id);
                    }
                }
            });
        }, config.prefetchDelay);
    }

    /**
     * Check if components are related
     */
    function isRelatedComponent(id1, id2) {
        // Same prefix (e.g., 'panel-' prefix)
        const prefix1 = id1.split('-')[0];
        const prefix2 = id2.split('-')[0];
        
        if (prefix1 === prefix2) return true;
        
        // Common patterns
        const patterns = [
            ['sessions', 'session-detail'],
            ['workspace', 'workspace-files'],
            ['swarm', 'swarm-detail'],
            ['terminal', 'terminal-session']
        ];
        
        return patterns.some(pattern => 
            pattern.includes(id1.toLowerCase()) && pattern.includes(id2.toLowerCase())
        );
    }

    /**
     * Prefetch a component
     */
    async function prefetchComponent(componentId) {
        const component = componentRegistry.get(componentId);
        if (!component || state.prefetchCache.has(componentId)) return;
        
        try {
            const content = await component.loader(componentId, { ...component.options, prefetch: true });
            state.prefetchCache.set(componentId, content);
            console.log(`[LazyLoader] Prefetched ${componentId}`);
        } catch (error) {
            console.warn(`[LazyLoader] Prefetch failed for ${componentId}:`, error);
        }
    }

    /**
     * Get loading statistics
     */
    function getStats() {
        return {
            ...state.loadingStats,
            queueLength: state.loadingQueue.length,
            activeLoads: state.activeLoads.size,
            loadedComponents: state.loadedComponents.size,
            cacheSize: state.prefetchCache.size,
            registrySize: componentRegistry.size
        };
    }

    /**
     * Clear cache
     */
    function clearCache() {
        state.prefetchCache.clear();
        console.log('[LazyLoader] Cache cleared');
    }

    /**
     * Prefetch components based on user behavior
     */
    function initializeBehavioralPrefetching() {
        // Track user interactions to predict likely components
        let interactionTimer = null;
        
        document.addEventListener('mouseover', (e) => {
            const target = e.target.closest('[data-lazy-component]');
            if (target) {
                const componentId = target.dataset.lazyComponent;
                if (componentId && !state.prefetchCache.has(componentId)) {
                    clearTimeout(interactionTimer);
                    interactionTimer = setTimeout(() => {
                        prefetchComponent(componentId);
                    }, 500); // Prefetch after 500ms hover
                }
            }
        }, { passive: true });
    }

    /**
     * Initialize lazy loading system
     */
    function initialize() {
        initializeObserver();
        initializeBehavioralPrefetching();
        
        // Observe all lazy elements
        document.querySelectorAll('[data-lazy-component]').forEach(element => {
            if (state.observer) {
                state.observer.observe(element);
            }
        });
        
        console.log('[LazyLoader] Initialized');
    }

    /**
     * Public API
     */
    return {
        initialize,
        registerComponent,
        loadComponent: queueLoad,
        prefetchComponent,
        getStats,
        clearCache,
        
        // Expose state for debugging
        _state: () => state
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', LazyLoader.initialize);
} else {
    LazyLoader.initialize();
}

// Export for global access
window.LazyLoader = LazyLoader;