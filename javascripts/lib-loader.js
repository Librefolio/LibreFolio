/**
 * LibreFolio JS Library Loader with Fallback
 *
 * Strategy:
 * 1. Try loading from local vendor/ (populated at server startup)
 * 2. Fallback to CDN if local not available
 *
 * This ensures documentation works both:
 * - In Docker containers (offline, local files)
 * - During development (CDN available)
 *
 * Note: Polyfill.io removed - modern browsers (2020+) don't need ES6 polyfills.
 * MathJax 3 works on all modern browsers without polyfills.
 */

(function() {
    'use strict';

    const LIBRARIES = [
        {
            name: 'mathjax',
            // Local path - populated by backend/dev.sh at startup
            local: 'javascripts/vendor/mathjax/tex-mml-chtml.js',
            cdn: 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js',
            test: function() { return typeof MathJax !== 'undefined'; }
        }
    ];

    /**
     * Load a script and return a promise
     */
    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.async = true;
            script.onload = () => resolve(src);
            script.onerror = () => reject(new Error(`Failed to load: ${src}`));
            document.head.appendChild(script);
        });
    }

    /**
     * Get base path for documentation
     */
    function getBasePath() {
        const baseEl = document.querySelector('base');
        if (baseEl && baseEl.href) {
            return baseEl.href;
        }
        return window.location.href.replace(/\/[^\/]*$/, '/');
    }

    /**
     * Load library with fallback
     */
    async function loadLibrary(lib) {
        const basePath = getBasePath();
        const localPath = basePath + lib.local;

        // Try local first
        try {
            await loadScript(localPath);
            if (lib.test()) {
                console.log(`[LibreFolio] Loaded ${lib.name} from local cache`);
                return true;
            }
        } catch (e) {
            console.warn(`[LibreFolio] Local ${lib.name} not available, trying CDN...`);
        }

        // Fallback to CDN
        if (lib.cdn) {
            try {
                await loadScript(lib.cdn);
                if (lib.test()) {
                    console.log(`[LibreFolio] Loaded ${lib.name} from CDN`);
                    return true;
                }
            } catch (e) {
                console.error(`[LibreFolio] Failed to load ${lib.name} from CDN`);
            }
        }

        return false;
    }

    /**
     * Initialize all libraries
     */
    async function initLibraries() {
        for (const lib of LIBRARIES) {
            await loadLibrary(lib);
        }
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLibraries);
    } else {
        initLibraries();
    }
})();
