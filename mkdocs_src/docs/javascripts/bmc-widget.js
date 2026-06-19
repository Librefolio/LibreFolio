/**
 * Buy Me a Coffee integration for MkDocs.
 *
 * 1. Adds a "Buy Me a Coffee ☕" link in the MkDocs header bar.
 * 2. Adds a BMC image button before the footer.
 */
(function () {
    'use strict';

    var BMC_URL = 'https://www.buymeacoffee.com/librefolio';

    var labels = {
        en: 'Buy Me a Coffee',
        it: 'Offrimi un Caffè',
        fr: 'Offrez-moi un Café',
        es: 'Invítame a un Café'
    };

    /** Detect current locale from URL path (e.g. /LibreFolio/it/...) */
    function getLocale() {
        var match = window.location.pathname.match(/\/(?:mkdocs\/|LibreFolio\/)(it|fr|es)(?:\/|$)/);
        return match ? match[1] : 'en';
    }

    function getLabel() {
        return labels[getLocale()] || labels.en;
    }

    /* ---------- 1. Header Coffee Link + Label ---------- */
    function addHeaderButton() {
        var headerInner = document.querySelector('.md-header__inner');
        if (!headerInner) return;

        var link = document.createElement('a');
        link.href = BMC_URL;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.className = 'md-header__button bmc-header-btn';
        var label = getLabel();
        link.title = label;
        link.setAttribute('aria-label', label);
        // Label first, then Coffee SVG (Lucide)
        link.innerHTML =
            '<span class="bmc-header-label">' + label + '</span>' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 8h1a4 4 0 1 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/><line x1="6" x2="6" y1="2" y2="4"/><line x1="10" x2="10" y1="2" y2="4"/><line x1="14" x2="14" y1="2" y2="4"/></svg>';

        // Insert before the header options (theme/search buttons)
        var options = headerInner.querySelector('.md-header__option');
        if (options) {
            options.parentNode.insertBefore(link, options);
        } else {
            headerInner.appendChild(link);
        }
    }

    /* ---------- 2. Footer BMC Image Button ---------- */
    function addFooterBmc() {
        var contentInner = document.querySelector('.md-content__inner');
        if (!contentInner) return;

        var container = document.createElement('div');
        container.className = 'bmc-footer-container';
        container.innerHTML =
            '<a href="' + BMC_URL + '" target="_blank" rel="noopener noreferrer">' +
            '<img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Buy Me a Coffee" style="height:60px !important;width:217px !important;" />' +
            '</a>';

        contentInner.appendChild(container);
    }

    // Run when DOM is ready
    function init() {
        addHeaderButton();
        addFooterBmc();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
