/**
 * Anchors that moved when the long pages of the admin guide were split (lot DOC-1).
 *
 * `admin/configuration/#csp` is now `admin/configuration_security/#csp`: a bookmark, a README or an old message that
 * still carries the old address would open the right page at its top. This script, loaded on every page, reads the
 * address: on an admin page that lost the anchor in the hash, it goes to the page that has it now. The links of the app
 * and of the documentation were updated; this is for the addresses outside them.
 *
 * `MOVED_ANCHORS` is generated from the split (page → anchor → the page that holds it now) and checked by
 * `test_docs_admin_references.py`: every anchor an old page had is still on it or listed here. No dependency.
 */
(function (root) {
    'use strict';

    var MOVED_ANCHORS = {
    "configuration": {
        "accounts": "configuration_accounts",
        "browser-protections": "configuration_security",
        "csp": "configuration_security",
        "csp-address-check": "configuration_security",
        "csp-blocked-script": "configuration_security",
        "csp-public-url": "configuration_security",
        "csp-report-only": "configuration_security",
        "frame-protection": "configuration_security",
        "initial-admin": "configuration_accounts",
        "instance-key": "configuration_secrets",
        "login-limit": "configuration_accounts",
        "optional-web-search-for-new-assets": "configuration_accounts",
        "plugin-secrets": "configuration_secrets",
        "plugin-settings": "configuration_secrets",
        "plugin-variable-lock": "configuration_secrets",
        "plugin-variables": "configuration_secrets",
        "provider-order": "configuration_accounts",
        "secret-files": "configuration_secrets",
        "secrets": "configuration_secrets",
        "shutdown": "configuration_security",
        "startup-checks": "configuration_security",
        "user-limit": "configuration_accounts"
    },
    "connection_checks": {
        "client-address": "connection_proxy",
        "reverse-proxy": "connection_proxy",
        "tailscale": "connection_proxy",
        "untrusted-proxy": "connection_proxy"
    },
    "email": {
        "activation-limits": "email_flows",
        "admin-links": "email_flows",
        "configuration-problems": "email_troubleshooting",
        "email-change-notice": "email_flows",
        "forgot-password": "email_flows",
        "logs": "email_troubleshooting",
        "public-url": "email_flows",
        "security": "email_troubleshooting",
        "sending-errors": "email_troubleshooting",
        "troubleshooting": "email_troubleshooting",
        "verification": "email_flows",
        "verification-limits": "email_flows",
        "verification-switch": "email_flows",
        "verification-waiting": "email_flows"
    },
    "service_exposure": {
        "3-startup-and-approval": "service_exposure_funnel",
        "enabling-funnel-and-acls-on-the-console": "service_exposure_funnel",
        "level-3-public-https-address-with-tailscale-funnel": "service_exposure_funnel",
        "level-4-multi-funnel-with-docker-sidecars": "service_exposure_funnel",
        "step-1-prepare-the-folder-and-the-script": "service_exposure_funnel",
        "step-1-start-the-funnel-on-the-server": "service_exposure_funnel",
        "step-2-approve-and-wait-for-propagation": "service_exposure_funnel",
        "step-2-configure-docker-compose": "service_exposure_funnel"
    },
    "sleep_wake": {
        "price-refresh": "wake_sync",
        "wake-sync": "wake_sync",
        "wake-sync-answer": "wake_sync",
        "wake-sync-blocked": "wake_sync",
        "wake-sync-jobs": "wake_sync",
        "wake-sync-token": "wake_sync",
        "wake-sync-workers": "wake_sync"
    }
};

    /** `admin/<page>/` at the end of a path, with or without `index.html`: the page, or null. */
    function adminPage(pathname) {
        var match = /\/admin\/([a-z0-9_]+)\/(?:index\.html)?$/.exec(String(pathname));
        return match ? match[1] : null;
    }

    /**
     * Where an address with an anchor of a page that lost it goes: `../<new page>/#<anchor>`, relative to the old page's folder, so
     * the language prefix and the site's base stay as they were. Null when nothing moved, or the page still has the anchor.
     */
    function movedTarget(pathname, hash, map, hasAnchor) {
        var page = adminPage(pathname);
        if (page === null || typeof hash !== 'string' || hash.charAt(0) !== '#') return null;
        var anchor;
        try {
            anchor = decodeURIComponent(hash.slice(1));
        } catch (e) {
            return null;
        }
        var moved = Object.prototype.hasOwnProperty.call(map, page) ? map[page] : null;
        if (moved === null || !Object.prototype.hasOwnProperty.call(moved, anchor)) return null;
        if (typeof hasAnchor === 'function' && hasAnchor(anchor)) return null;
        return '../' + moved[anchor] + '/' + hash;
    }

    var api = {MOVED_ANCHORS: MOVED_ANCHORS, adminPage: adminPage, movedTarget: movedTarget};
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
        return;
    }
    if (!root.location || !root.document) return;
    var target = movedTarget(root.location.pathname, root.location.hash, MOVED_ANCHORS, function (anchor) {
        return root.document.getElementById(anchor) !== null;
    });
    if (target !== null) root.location.replace(target);
})(typeof window !== 'undefined' ? window : globalThis);
