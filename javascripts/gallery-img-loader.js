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
    // GitHub Pages URL for remote fallback when screenshots are not built locally
    var GITHUB_PAGES_BASE = 'https://alfystar.github.io/LibreFolio';

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
            '/POC_UX/', '/community/'
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

    function buildGithubSrc(viewport, lang, theme, category, name) {
        return GITHUB_PAGES_BASE + '/gallery/' + viewport + '/' + lang + '/' + theme + '/' + category + '/' + name + '.png';
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

            // Cascading fallback chain:
            // 1. Local: requested lang
            // 2. Local: fallback lang (en)
            // 3. GitHub Pages: requested lang
            // 4. GitHub Pages: fallback lang (en)
            img.onerror = function () {
                var currentSrc = img.getAttribute('src');
                if (currentSrc === newSrc && lang !== FALLBACK_LANG) {
                    // Step 2: try local fallback lang
                    img.onerror = function () {
                        // Step 3: try GitHub Pages with requested lang
                        var ghSrc = buildGithubSrc(viewport, lang, theme, category, name);
                        img.onerror = function () {
                            if (lang !== FALLBACK_LANG) {
                                // Step 4: try GitHub Pages with fallback lang
                                var ghFallback = buildGithubSrc(viewport, FALLBACK_LANG, theme, category, name);
                                img.onerror = null; // Prevent infinite loop
                                img.src = ghFallback;
                            } else {
                                img.onerror = null;
                            }
                        };
                        img.src = ghSrc;
                    };
                    img.src = buildSrc(viewport, FALLBACK_LANG, theme, category, name);
                } else {
                    // Already on fallback lang locally → try GitHub Pages
                    var ghSrc = buildGithubSrc(viewport, lang !== FALLBACK_LANG ? lang : FALLBACK_LANG, theme, category, name);
                    img.onerror = function () {
                        if (lang !== FALLBACK_LANG) {
                            var ghFallback = buildGithubSrc(viewport, FALLBACK_LANG, theme, category, name);
                            img.onerror = null;
                            img.src = ghFallback;
                        } else {
                            img.onerror = null;
                        }
                    };
                    img.src = ghSrc;
                }
            };
            img.src = newSrc;
        });
    }

    function initScreenshotCarousels() {
        var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        var carousels = document.querySelectorAll('.lf-screenshot-carousel');
        carousels.forEach(function (carousel) {
            if (carousel.dataset.carouselInitialized === 'true') return;
            carousel.dataset.carouselInitialized = 'true';

            var items = Array.prototype.slice.call(
                carousel.querySelectorAll('.lf-screenshot-carousel-item')
            );

            if (items.length <= 1) return;

            var intervalMs = Number(carousel.dataset.carouselInterval || 4500);
            var currentIndex = items.findIndex(function (item) {
                return item.classList.contains('is-active');
            });

            if (currentIndex < 0) currentIndex = 0;
            var timer = null;
            var isHovered = false;

            var dotsContainer = document.createElement('div');
            dotsContainer.className = 'lf-screenshot-carousel-dots';
            carousel.appendChild(dotsContainer);

            var showTitles = carousel.getAttribute('data-show-titles') === 'true';
            var titleContainer = null;
            if (showTitles) {
                titleContainer = document.createElement('div');
                titleContainer.className = 'lf-screenshot-carousel-title';
                titleContainer.innerHTML = items[currentIndex].getAttribute('data-title') || items[currentIndex].getAttribute('alt') || '';
                carousel.appendChild(titleContainer);
            }

            var dots = items.map(function (item, index) {
                var dot = document.createElement('button');
                dot.className = 'lf-screenshot-carousel-dot';
                dot.setAttribute('aria-label', 'Go to slide ' + (index + 1));
                if (index === currentIndex) {
                    dot.classList.add('is-active');
                    dot.setAttribute('aria-current', 'true');
                }
                dot.addEventListener('click', function () {
                    goTo(index, true);
                });
                dotsContainer.appendChild(dot);
                return dot;
            });

            var arrowPrev = document.createElement('button');
            arrowPrev.className = 'lf-screenshot-carousel-arrow prev';
            arrowPrev.innerHTML = '<svg viewBox="0 0 24 24"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>';
            arrowPrev.setAttribute('aria-label', 'Previous slide');
            arrowPrev.onclick = function() { goTo((currentIndex - 1 + items.length) % items.length, true); };
            carousel.appendChild(arrowPrev);

            var arrowNext = document.createElement('button');
            arrowNext.className = 'lf-screenshot-carousel-arrow next';
            arrowNext.innerHTML = '<svg viewBox="0 0 24 24"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>';
            arrowNext.setAttribute('aria-label', 'Next slide');
            arrowNext.onclick = function() { goTo((currentIndex + 1) % items.length, true); };
            carousel.appendChild(arrowNext);

            function syncDots() {
                dots.forEach(function (dot, index) {
                    if (index === currentIndex) {
                        dot.classList.add('is-active');
                        dot.setAttribute('aria-current', 'true');
                    } else {
                        dot.classList.remove('is-active');
                        dot.removeAttribute('aria-current');
                    }
                });
            }

            function updateTransforms() {
                items.forEach(function (item, index) {
                    item.classList.remove('is-active', 'is-prev', 'is-next', 'is-hidden');
                    item.onclick = null;
                    
                    if (index === currentIndex) {
                        item.classList.add('is-active');
                    } else if (items.length === 2) {
                        item.classList.add('is-hidden');
                        // non clickable when hidden behind
                    } else if (index === (currentIndex - 1 + items.length) % items.length) {
                        item.classList.add('is-prev');
                        item.onclick = function() { goTo(index, true); };
                    } else if (index === (currentIndex + 1) % items.length) {
                        item.classList.add('is-next');
                        item.onclick = function() { goTo(index, true); };
                    } else {
                        item.classList.add('is-hidden');
                    }
                });
            }

            // Initialize position without transition
            items.forEach(function(item) { item.style.setProperty('transition', 'none', 'important'); });
            updateTransforms();
            carousel.offsetHeight; // force reflow
            items.forEach(function(item) { item.style.removeProperty('transition'); });

            function goTo(index, manual) {
                if (index === currentIndex) return;

                if (manual) stop();

                currentIndex = index;
                syncDots();
                
                if (showTitles && titleContainer) {
                    titleContainer.innerHTML = items[currentIndex].getAttribute('data-title') || items[currentIndex].getAttribute('alt') || '';
                }
                
                updateTransforms();

                if (manual && !reduceMotion && !isHovered) {
                    start();
                }
            }

            function showNext() {
                var nextIndex = (currentIndex + 1) % items.length;
                goTo(nextIndex, false);
            }

            function start() {
                if (reduceMotion) return;
                if (timer) return;
                timer = window.setInterval(showNext, intervalMs);
            }

            function stop() {
                if (!timer) return;
                window.clearInterval(timer);
                timer = null;
            }

            carousel.addEventListener('mouseenter', function() {
                isHovered = true;
                stop();
            });
            carousel.addEventListener('mouseleave', function() {
                isHovered = false;
                start();
            });
            carousel.addEventListener('focusin', stop);
            carousel.addEventListener('focusout', function() {
                if (!isHovered) start();
            });

            if ('IntersectionObserver' in window && !reduceMotion) {
                var observer = new IntersectionObserver(function (entries) {
                    entries.forEach(function (entry) {
                        if (entry.isIntersecting && !isHovered) start();
                        else stop();
                    });
                }, { threshold: 0.25 });
                observer.observe(carousel);
            } else {
                start();
            }
        });
    }

    function init() {
        updateImages();
        initScreenshotCarousels();

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

    // Support for MkDocs Material instant loading
    if (typeof document$ !== 'undefined') {
        document$.subscribe(function() {
            init();
        });
    }
})();
