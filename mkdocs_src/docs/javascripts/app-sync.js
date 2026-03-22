/**
 * App ↔ MkDocs Sync
 *
 * Synchronizes theme preference between the SvelteKit frontend app
 * and MkDocs Material docs. Both run on the same origin so localStorage
 * is shared.
 *
 * Frontend keys:
 *   - librefolio-theme: 'light' | 'dark' | '' (auto)
 *   - gallery-lang: 'en' | 'it' | 'fr' | 'es' (already used by lang selector)
 *
 * MkDocs Material key:
 *   - {path}.__palette: JSON with {index, color: {scheme, primary, accent}}
 *     where index 0 = light/default, index 1 = dark/slate
 *
 * This script runs BEFORE site-lang-selector.js to prevent theme flash.
 */
(function () {
    'use strict';

    // ── Theme sync ───────────────────────────────────────────────

    /**
     * Find the MkDocs Material palette localStorage key.
     * Material uses `{basePath}/.__palette` as key.
     */
    function findPaletteKey() {
        // Try common patterns
        var candidates = ['.__palette', '/.__palette', '/mkdocs/.__palette'];
        for (var i = 0; i < candidates.length; i++) {
            if (localStorage.getItem(candidates[i]) !== null) {
                return candidates[i];
            }
        }
        // Try to derive from current path
        var base = window.location.pathname.split('/')[1];
        if (base) {
            var key = '/' + base + '/.__palette';
            return key;
        }
        return '.__palette';
    }

    /**
     * Sync theme from frontend app (librefolio-theme) to MkDocs Material.
     */
    function syncTheme() {
        var appTheme = localStorage.getItem('librefolio-theme');
        if (!appTheme) return;   // auto or not set — let MkDocs use its own preference

        var isDark = appTheme === 'dark';
        var paletteKey = findPaletteKey();

        // Read current MkDocs palette to check if already synced
        var currentRaw = localStorage.getItem(paletteKey);
        var current = null;
        try {
            current = currentRaw ? JSON.parse(currentRaw) : null;
        } catch (e) { /* ignore */ }

        var targetIndex = isDark ? 1 : 0;
        var targetScheme = isDark ? 'slate' : 'default';

        // Only update if needed (avoid unnecessary page flicker)
        if (current && current.index === targetIndex) return;

        // Write the palette to localStorage
        var palette = {
            index: targetIndex,
            color: {
                scheme: targetScheme,
                primary: 'custom',
                accent: 'custom'
            }
        };
        localStorage.setItem(paletteKey, JSON.stringify(palette));

        // Apply immediately to the DOM to prevent flash of wrong theme
        document.body.setAttribute('data-md-color-scheme', targetScheme);

        // Also try to update the toggle button state
        var toggles = document.querySelectorAll('[data-md-component=palette] input');
        if (toggles.length > 1) {
            toggles[targetIndex].click();
        }
    }

    // ── Run sync on page load (as early as possible) ─────────────

    // Theme: sync immediately (even before DOMContentLoaded)
    syncTheme();

    // Also sync after DOM is ready (in case body wasn't available yet)
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', syncTheme);
    }
})();

