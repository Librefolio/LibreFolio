/**
 * Gallery Language Selector
 *
 * Adds a language dropdown to the MkDocs header for gallery pages.
 * Similar to the language selector in the LibreFolio frontend.
 *
 * Works together with the gallery pages to switch screenshot languages.
 */
(function() {
    'use strict';

    const LANGUAGES = [
        { code: 'en', name: 'English', flag: '🇬🇧' },
        { code: 'it', name: 'Italiano', flag: '🇮🇹' },
        { code: 'fr', name: 'Français', flag: '🇫🇷' },
        { code: 'es', name: 'Español', flag: '🇪🇸' }
    ];

    const STORAGE_KEY = 'gallery-lang';

    // Only run on gallery pages
    function isGalleryPage() {
        return window.location.pathname.includes('/gallery/');
    }

    function getCurrentLang() {
        return localStorage.getItem(STORAGE_KEY) || 'en';
    }

    function setCurrentLang(lang) {
        localStorage.setItem(STORAGE_KEY, lang);
        // Dispatch custom event for gallery pages to listen
        window.dispatchEvent(new CustomEvent('gallery-lang-change', { detail: { lang } }));
    }

    function getLangByCode(code) {
        return LANGUAGES.find(l => l.code === code) || LANGUAGES[0];
    }

    function createSelector() {
        const currentLang = getLangByCode(getCurrentLang());

        // Container
        const container = document.createElement('div');
        container.className = 'gallery-lang-selector';
        container.innerHTML = `
            <button class="gallery-lang-btn" aria-label="Select language" title="Gallery Language">
                <span class="lang-flag">${currentLang.flag}</span>
                <span class="lang-name">${currentLang.name}</span>
                <svg class="lang-chevron" viewBox="0 0 24 24" width="16" height="16">
                    <path fill="currentColor" d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
                </svg>
            </button>
            <div class="gallery-lang-dropdown">
                ${LANGUAGES.map(l => `
                    <button class="gallery-lang-option ${l.code === currentLang.code ? 'active' : ''}" data-lang="${l.code}">
                        <span class="lang-flag">${l.flag}</span>
                        <span class="lang-name">${l.name}</span>
                    </button>
                `).join('')}
            </div>
        `;

        // Event handlers
        const btn = container.querySelector('.gallery-lang-btn');
        const dropdown = container.querySelector('.gallery-lang-dropdown');
        const options = container.querySelectorAll('.gallery-lang-option');

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            container.classList.toggle('open');
        });

        options.forEach(opt => {
            opt.addEventListener('click', () => {
                const lang = opt.dataset.lang;
                const langData = getLangByCode(lang);

                // Update button display
                btn.querySelector('.lang-flag').textContent = langData.flag;
                btn.querySelector('.lang-name').textContent = langData.name;

                // Update active state
                options.forEach(o => o.classList.remove('active'));
                opt.classList.add('active');

                // Close dropdown
                container.classList.remove('open');

                // Save and notify
                setCurrentLang(lang);
            });
        });

        // Close on click outside
        document.addEventListener('click', () => {
            container.classList.remove('open');
        });

        return container;
    }

    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .gallery-lang-selector {
                position: relative;
                margin-left: 0.5rem;
            }
            
            .gallery-lang-btn {
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
            
            .gallery-lang-btn:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            
            .lang-chevron {
                transition: transform 0.2s;
                color: var(--md-header-fg-color, white);
            }
            
            .gallery-lang-selector.open .lang-chevron {
                transform: rotate(180deg);
            }
            
            .gallery-lang-dropdown {
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
            
            .gallery-lang-selector.open .gallery-lang-dropdown {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }
            
            .gallery-lang-option {
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
            
            .gallery-lang-option:hover {
                background: var(--md-code-bg-color);
            }
            
            .gallery-lang-option.active {
                background: var(--md-primary-fg-color--transparent);
                color: var(--md-primary-fg-color);
            }
            
            .gallery-lang-option:first-child {
                border-radius: 4px 4px 0 0;
            }
            
            .gallery-lang-option:last-child {
                border-radius: 0 0 4px 4px;
            }
            
            .lang-flag {
                font-size: 1rem;
            }
            
            /* Hide on non-gallery pages */
            body:not([data-gallery-page]) .gallery-lang-selector {
                display: none;
            }
            
            /* Mobile responsive - dropdown opens to left to avoid truncation */
            @media (max-width: 600px) {
                .gallery-lang-btn .lang-name {
                    display: none;
                }
                .gallery-lang-dropdown {
                    right: 0;
                    left: auto;
                    min-width: 130px;
                }
            }
        `;
        document.head.appendChild(style);
    }

    function init() {
        if (!isGalleryPage()) return;

        // Mark body for CSS
        document.body.setAttribute('data-gallery-page', 'true');

        injectStyles();

        // Find the header actions area (where theme toggle is)
        const headerInner = document.querySelector('.md-header__inner');
        if (!headerInner) return;

        // Find the right side of header (where icons are)
        const headerSource = document.querySelector('.md-header__source');
        const insertTarget = headerSource || headerInner;

        const selector = createSelector();

        // Insert before the source/repo link or at end
        if (headerSource) {
            headerSource.parentNode.insertBefore(selector, headerSource);
        } else {
            headerInner.appendChild(selector);
        }
    }

    // Run on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
