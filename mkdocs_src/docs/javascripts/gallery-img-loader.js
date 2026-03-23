/**
 * Gallery Image Loader
 *
 * Automatically resolves gallery screenshot paths for any page in the docs.
 * Images use `data-category` and `data-name` attributes, and optionally
 * `data-gallery="desktop|mobile"` (defaults to "desktop").
 *
 * Detects the MkDocs site base path dynamically (works with subpath deploys).
 * Reacts to theme changes (light/dark) and language changes from the gallery selector.
 *
 * Includes fallback: if the requested lang image returns 404, falls back to 'en'.
 */
(function () {
    'use strict';

    var FALLBACK_LANG = 'en';

    /**
     * Detect site base path from the current page URL.
     * MkDocs Material serves pages under site_url (e.g. /LibreFolio/).
     * We detect the base by finding known path segments in the current URL.
     *
     * Known top-level segments in our docs nav:
     *   gallery/, developer/, user-manual/, admin-manual/, getting-started/,
     *   tutorials/, financial-theory/, poc-ux/, faq/, ...
     *
     * If the current URL is: /LibreFolio/gallery/desktop/
     * then the base path is: /LibreFolio
     */
    function getBasePath() {
        var pathname = window.location.pathname;

        // Strip i18n language prefix added by mkdocs-static-i18n
        // e.g. /LibreFolio/it/gallery/ → /LibreFolio/gallery/
        var i18nLangs = ['it', 'fr', 'es'];
        for (var li = 0; li < i18nLangs.length; li++) {
            var langPrefix = '/' + i18nLangs[li] + '/';
            var langIdx = pathname.indexOf(langPrefix);
            if (langIdx >= 0) {
                // Remove the /XX/ segment: everything before + everything after
                pathname = pathname.substring(0, langIdx) + pathname.substring(langIdx + langPrefix.length - 1);
                break;
            }
        }

        // Known top-level doc sections that appear right after the base path
        var knownSegments = [
            '/gallery/', '/developer/', '/user/', '/admin/',
            '/getting-started/', '/tutorials/', '/financial-theory/',
            '/POC_UX/', '/credits-legal/', '/faq/'
        ];

        for (var i = 0; i < knownSegments.length; i++) {
            var idx = pathname.indexOf(knownSegments[i]);
            if (idx >= 0) {
                // Everything before this segment is the base path
                return pathname.substring(0, idx);  // e.g. "/LibreFolio" or "" if at root
            }
        }

        // Fallback: if we're on the homepage (e.g. /LibreFolio/)
        // Remove trailing slash and last segment if it looks like a file
        var clean = pathname.replace(/\/+$/, '');
        if (clean && !clean.includes('.')) {
            // Could be the homepage: /LibreFolio → return /LibreFolio
            return clean;
        }

        return '';
    }

    var _basePath = null;

    function basePath() {
        if (_basePath === null) {
            _basePath = getBasePath();
        }
        return _basePath;
    }

    function getCurrentLang() {
        // Gallery screenshot language is controlled by the custom site-lang-selector
        // (stored in localStorage), NOT by the i18n page URL prefix.
        // This lets users view any language screenshots regardless of the page locale.
        return localStorage.getItem('gallery-lang') || 'en';
    }

    function getMkDocsTheme() {
        var scheme = document.body.getAttribute('data-md-color-scheme');
        return scheme === 'slate' ? 'dark' : 'light';
    }

    function buildSrc(viewport, lang, theme, category, name) {
        return basePath() + '/gallery/' + viewport + '/' + lang + '/' + theme + '/' + category + '/' + name + '.png';
    }

    function updateImages() {
        var images = document.querySelectorAll('.gallery-img');
        if (images.length === 0) return;

        var lang = getCurrentLang();
        var theme = getMkDocsTheme();

        images.forEach(function (img) {
            var category = img.dataset.category;
            var name = img.dataset.name;
            if (!category || !name) return;

            // Detect viewport: gallery pages derive from URL, other pages default to 'desktop'
            var viewport = img.dataset.gallery || 'desktop';
            var path = window.location.pathname;
            if (path.includes('/gallery/mobile')) viewport = 'mobile';
            else if (path.includes('/gallery/desktop')) viewport = 'desktop';

            var newSrc = buildSrc(viewport, lang, theme, category, name);
            if (img.getAttribute('src') === newSrc) return; // Already set

            // Set the image src. If it fails (404), fall back to 'en'.
            img.onerror = function () {
                if (lang !== FALLBACK_LANG) {
                    var fallbackSrc = buildSrc(viewport, FALLBACK_LANG, theme, category, name);
                    if (img.getAttribute('src') !== fallbackSrc) {
                        img.onerror = null; // Prevent infinite loop
                        img.src = fallbackSrc;
                    }
                }
            };
            img.src = newSrc;
        });
    }

    function init() {
        updateImages();

        // React to language changes (from site-lang-selector.js)
        window.addEventListener('gallery-lang-change', updateImages);

        // React to theme changes
        var observer = new MutationObserver(updateImages);
        observer.observe(document.body, {attributes: true, attributeFilter: ['data-md-color-scheme']});
    }

    // Run on DOMContentLoaded or immediately
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
