/**
 * Dashboard Connectivity Check
 *
 * Adds a 🚀 dashboard icon in the MkDocs header, between the Buy Me a Coffee
 * link and the search box (where the theme toggle used to sit: the toggle now
 * sits beside the language selector, as in the app's header). The icon is hidden
 * by default and only shown when the LibreFolio server is online (health check
 * passes).
 */
(function () {
    'use strict';

    var healthUrl = '/api/v1/system/health';
    var dashboardUrl = '/';

    function injectStyles() {
        var style = document.createElement('style');
        style.textContent = `
            .dashboard-header-icon {
                display: none;
                align-items: center;
                margin-left: 0.4rem;
            }
            .dashboard-header-icon.online {
                display: flex;
            }
            .dashboard-header-icon a {
                display: flex;
                align-items: center;
                padding: 0.4rem 0.5rem;
                background: transparent;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                color: var(--md-header-fg-color, white);
                font-size: 1.1rem;
                text-decoration: none;
                transition: all 0.2s;
                line-height: 1;
            }
            .dashboard-header-icon a:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        `;
        document.head.appendChild(style);
    }

    function createDashboardIcon() {
        var container = document.createElement('div');
        container.className = 'dashboard-header-icon';
        container.innerHTML = '<a href="' + dashboardUrl + '" title="Go to Dashboard">🚀</a>';
        return container;
    }

    function init() {
        injectStyles();

        // Create header icon
        var headerInner = document.querySelector('.md-header__inner');
        if (!headerInner) return;

        var icon = createDashboardIcon();

        // Insert right before the search box: the search toggle label is its first element
        var searchToggle = headerInner.querySelector('label[for="__search"]');
        if (searchToggle) {
            searchToggle.parentNode.insertBefore(icon, searchToggle);
        } else {
            headerInner.appendChild(icon);
        }

        // Health check
        fetch(healthUrl)
            .then(function (response) {
                if (!response.ok) throw new Error('Server not OK');
                return response.json();
            })
            .then(function (data) {
                if (data.status !== 'ok') throw new Error('Invalid status');

                console.log('Dashboard status: ONLINE');

                // Show header icon
                icon.classList.add('online');
            })
            .catch(function (error) {
                console.log('Dashboard status: OFFLINE');
                console.log('Dashboard server not reachable:', error.message);
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
