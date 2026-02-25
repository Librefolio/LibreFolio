/**
 * Gallery Image Loader
 *
 * Automatically resolves gallery screenshot paths for any page in the docs.
 * Images use `data-category` and `data-name` attributes, and optionally
 * `data-gallery="desktop|mobile"` (defaults to "desktop").
 *
 * Uses absolute paths from site root for reliability across all pages.
 * Reacts to theme changes (light/dark) and language changes from the gallery selector.
 *
 * Includes fallback: if the requested lang image returns 404, falls back to 'en'.
 */
(function () {
    'use strict';

    var FALLBACK_LANG = 'en';

    function getCurrentLang() {
        return localStorage.getItem('gallery-lang') || 'en';
    }

    function getMkDocsTheme() {
        var scheme = document.body.getAttribute('data-md-color-scheme');
        return scheme === 'slate' ? 'dark' : 'light';
    }

    function buildSrc(viewport, lang, theme, category, name) {
        return '/gallery/' + viewport + '/' + lang + '/' + theme + '/' + category + '/' + name + '.png';
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

        // React to language changes (from gallery-lang-selector.js)
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
