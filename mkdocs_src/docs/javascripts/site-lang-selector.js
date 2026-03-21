/**
 * Site Language Selector  (Solution B — "URL is king + redirect for default")
 *
 * Adds a language dropdown to the MkDocs header for all pages.
 * Controls mkdocs-static-i18n page navigation AND gallery screenshot language.
 *
 * Rules:
 *  - Translatable pages: URL is the source of truth.
 *      • Explicit lang prefix (/it/, /fr/, /es/) → sync localStorage to URL.
 *      • Default URL (no prefix = en) + stored preference ≠ en → redirect.
 *  - EN-only pages (Developer, POC UX): readonly English, localStorage untouched.
 *  - Selector click: navigate to target lang URL + update localStorage.
 */
(function () {
    'use strict';

    const LANGUAGES = [
        {code: 'en', name: 'English', flag: '🇬🇧'},
        {code: 'it', name: 'Italiano', flag: '🇮🇹'},
        {code: 'fr', name: 'Français', flag: '🇫🇷'},
        {code: 'es', name: 'Español', flag: '🇪🇸'}
    ];

    /** Non-default language codes (those that get a URL prefix). */
    const I18N_LANGS = LANGUAGES.filter(l => l.code !== 'en').map(l => l.code);

    const STORAGE_KEY = 'gallery-lang';

    // ── URL helpers ─────────────────────────────────────────────

    /**
     * Detect the site base path (e.g. "/LibreFolio" or "" for root deploys).
     * Mirrors the logic in gallery-img-loader.js.
     */
    function getBasePath() {
        var pathname = window.location.pathname;

        // Strip i18n prefix so we can find the known segment
        for (var i = 0; i < I18N_LANGS.length; i++) {
            var pfx = '/' + I18N_LANGS[i] + '/';
            var idx = pathname.indexOf(pfx);
            if (idx >= 0) {
                pathname = pathname.substring(0, idx) + pathname.substring(idx + pfx.length - 1);
                break;
            }
        }

        var segs = [
            '/gallery/', '/developer/', '/user/', '/admin/',
            '/getting-started/', '/tutorials/', '/financial-theory/',
            '/POC_UX/', '/credits-legal/', '/faq/'
        ];
        for (var i = 0; i < segs.length; i++) {
            var idx = pathname.indexOf(segs[i]);
            if (idx >= 0) return pathname.substring(0, idx);
        }

        // Homepage fallback
        var clean = pathname.replace(/\/+$/, '');
        return (clean && !clean.includes('.')) ? clean : '';
    }

    /**
     * Detect page language from the URL path.
     * Checks the first segment after the base path for a lang prefix.
     * Returns 'it'|'fr'|'es' if found, otherwise 'en' (default, no prefix).
     */
    function getLangFromUrl() {
        var afterBase = window.location.pathname.substring(getBasePath().length);
        var pattern = new RegExp('^\\/(' + I18N_LANGS.join('|') + ')(\\/|$)');
        var m = afterBase.match(pattern);
        return m ? m[1] : 'en';
    }

    /**
     * Navigate to the target language version of the current page.
     */
    function navigateToLang(targetLang) {
        var path = window.location.pathname;
        var base = getBasePath();
        var currentLang = getLangFromUrl();

        if (currentLang === targetLang) return;

        // Extract content path (everything after base + optional lang prefix)
        var afterBase = path.substring(base.length);
        var contentPath = (currentLang !== 'en')
            ? afterBase.substring(('/' + currentLang).length)   // strip /it → /user/...
            : afterBase;                                         // already /user/...

        var newPath = (targetLang === 'en')
            ? base + contentPath
            : base + '/' + targetLang + contentPath;

        window.location.href = window.location.origin + newPath
            + window.location.search + window.location.hash;
    }

    // ── EN-only detection ───────────────────────────────────────

    function isEnOnlyPage() {
        var p = window.location.pathname;
        return p.includes('/developer/') || p.includes('/POC_UX/');
    }

    // ── Language state ──────────────────────────────────────────

    function getStoredLang() {
        return localStorage.getItem(STORAGE_KEY) || 'en';
    }

    function saveLang(lang) {
        localStorage.setItem(STORAGE_KEY, lang);
        window.dispatchEvent(new CustomEvent('gallery-lang-change', {detail: {lang}}));
    }

    function getLangByCode(code) {
        return LANGUAGES.find(l => l.code === code) || LANGUAGES[0];
    }

    /**
     * Visually update the selector button (without touching localStorage).
     */
    function displayLang(container, lang) {
        var d = getLangByCode(lang);
        var btn = container.querySelector('.site-lang-btn');
        if (btn) {
            btn.querySelector('.lang-flag').textContent = d.flag;
            btn.querySelector('.lang-name').textContent = d.name;
        }
        container.querySelectorAll('.site-lang-option').forEach(function (o) {
            o.classList.toggle('active', o.dataset.lang === lang);
        });
    }

    // ── Selector widget ─────────────────────────────────────────

    /**
     * Build the dropdown DOM.
     * @param {string} [initialLang] – language to display; defaults to stored pref.
     */
    function createSelector(initialLang) {
        var lang = getLangByCode(initialLang || getStoredLang());

        var container = document.createElement('div');
        container.className = 'site-lang-selector';
        container.innerHTML = `
            <button class="site-lang-btn" aria-label="Select language" title="Language">
                <span class="lang-flag">${lang.flag}</span>
                <span class="lang-name">${lang.name}</span>
                <svg class="lang-chevron" viewBox="0 0 24 24" width="16" height="16">
                    <path fill="currentColor" d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
                </svg>
            </button>
            <div class="site-lang-dropdown">
                ${LANGUAGES.map(l => `
                    <button class="site-lang-option ${l.code === lang.code ? 'active' : ''}" data-lang="${l.code}">
                        <span class="lang-flag">${l.flag}</span>
                        <span class="lang-name">${l.name}</span>
                    </button>
                `).join('')}
            </div>
        `;

        container.querySelector('.site-lang-btn').addEventListener('click', function (e) {
            e.stopPropagation();
            container.classList.toggle('open');
        });

        container.querySelectorAll('.site-lang-option').forEach(function (opt) {
            opt.addEventListener('click', function () {
                var target = opt.dataset.lang;
                container.classList.remove('open');
                saveLang(target);
                navigateToLang(target);
            });
        });

        document.addEventListener('click', function () {
            container.classList.remove('open');
        });

        return container;
    }

    // ── Inject selector into header ─────────────────────────────

    function injectSelector(selector) {
        var headerSource = document.querySelector('.md-header__source');
        if (headerSource) {
            headerSource.parentNode.insertBefore(selector, headerSource);
        } else {
            var headerInner = document.querySelector('.md-header__inner');
            if (headerInner) headerInner.appendChild(selector);
        }
    }

    // ── Styles ──────────────────────────────────────────────────

    function injectStyles() {
        var style = document.createElement('style');
        style.textContent = `
            .site-lang-selector {
                position: relative;
                margin-left: 0.5rem;
            }
            .site-lang-btn {
                display: flex;
                align-items: center;
                gap: 0.4rem;
                padding: 0.4rem 0.6rem;
                background: transparent;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                color: var(--md-header-fg-color, white);
                font-size: 0.8rem;
                transition: all 0.2s;
            }
            .site-lang-btn:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            .lang-chevron {
                transition: transform 0.2s;
                color: var(--md-header-fg-color, white);
            }
            .site-lang-selector.open .lang-chevron {
                transform: rotate(180deg);
            }
            .site-lang-dropdown {
                position: absolute;
                top: 100%;
                right: 0;
                margin-top: 4px;
                background: var(--md-default-bg-color);
                border-radius: 4px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                opacity: 0;
                visibility: hidden;
                transform: translateY(-8px);
                transition: all 0.2s;
                z-index: 100;
                min-width: 140px;
            }
            .site-lang-selector.open .site-lang-dropdown {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }
            .site-lang-option {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                width: 100%;
                padding: 0.5rem 0.75rem;
                background: transparent;
                border: none;
                cursor: pointer;
                color: var(--md-default-fg-color);
                font-size: 0.85rem;
                text-align: left;
                transition: background 0.15s;
            }
            .site-lang-option:hover {
                background: var(--md-code-bg-color);
            }
            .site-lang-option.active {
                background: var(--md-primary-fg-color--transparent);
                color: var(--md-primary-fg-color);
            }
            .site-lang-option:first-child {
                border-radius: 4px 4px 0 0;
            }
            .site-lang-option:last-child {
                border-radius: 0 0 4px 4px;
            }
            .lang-flag {
                font-size: 1rem;
            }
            /* Readonly mode for EN-only pages */
            .site-lang-selector.lang-readonly {
                opacity: 0.4;
                pointer-events: none;
            }
            .site-lang-selector.lang-readonly .lang-chevron {
                display: none;
            }
            /* Mobile */
            @media (max-width: 600px) {
                .site-lang-btn .lang-name {
                    display: none;
                }
                .site-lang-dropdown {
                    right: 0;
                    left: auto;
                    min-width: 130px;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // ── Init ────────────────────────────────────────────────────

    function init() {
        injectStyles();
        if (!document.querySelector('.md-header__inner')) return;

        // ── EN-only pages: show English readonly, preserve localStorage ──
        if (isEnOnlyPage()) {
            var sel = createSelector('en');
            injectSelector(sel);
            sel.classList.add('lang-readonly');
            return;
        }

        // ── Translatable pages ──
        var urlLang = getLangFromUrl();
        var storedLang = getStoredLang();

        // Default URL (English, no prefix) + different stored preference → redirect
        if (urlLang === 'en' && storedLang !== 'en') {
            navigateToLang(storedLang);
            return;   // page will reload at the correct URL
        }

        // Sync localStorage to URL language (handles explicit /fr/ URLs etc.)
        saveLang(urlLang);

        // Create selector showing the (now-synced) URL language
        var sel = createSelector(urlLang);
        injectSelector(sel);
    }

    // ── Bootstrap ───────────────────────────────────────────────

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
