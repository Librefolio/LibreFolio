/**
 * LibreFolio JS Library Loader with Fallback
 *
 * Strategy:
 * 1. Try loading from local vendor/ (cached by scripts/update_js_cache.py, copied by the docs build)
 * 2. Fallback to CDN if local not available
 *
 * This ensures documentation works both:
 * - In Docker containers (offline, local files)
 * - During development (CDN available)
 *
 * Note: Polyfill.io removed - modern browsers (2020+) don't need ES6 polyfills.
 * MathJax 3 works on all modern browsers without polyfills.
 */

(function () {
    'use strict';

    // This file's own address. MkDocs links it with a path relative to each page
    // (`../../javascripts/lib-loader.js`), so it always points under the site's root,
    // whatever the page's depth, its language folder or the path the site is served at
    // (`/mkdocs/` in LibreFolio). Read now: it is null once this script has run.
    const SELF = document.currentScript ? new URL(document.currentScript.src, window.location.href) : null;
    const SELF_PATH = '/javascripts/lib-loader.js';

    const LIBRARIES = [
        {
            name: 'mathjax',
            // Local path, relative to the site's root
            local: 'javascripts/vendor/mathjax/tex-mml-chtml.js',
            cdn: 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js',
            test: function () {
                return typeof MathJax !== 'undefined';
            }
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
     * The site's root URL, where `javascripts/vendor/` lives.
     *
     * The page's own folder is right only for the pages at the root: on every nested page
     * it pointed below the page, the local copy answered 404 and MathJax came from the CDN,
     * so the formulas did not show offline.
     */
    function getBasePath() {
        if (SELF) {
            const at = SELF.pathname.lastIndexOf(SELF_PATH);
            if (at !== -1) {
                return SELF.origin + SELF.pathname.slice(0, at + 1);
            }
        }
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
