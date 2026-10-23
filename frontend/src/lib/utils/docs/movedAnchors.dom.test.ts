// @vitest-environment jsdom
//
// The docblock above is load-bearing: the script reads `window.location` and `document.getElementById`. jsdom provides the
// document; no real navigation happens — `location` is replaced by a stub that only records calls to `replace`.
/**
 * movedAnchors.dom.test.ts — the browser half of `mkdocs_src/docs/javascripts/moved-anchors.js` (DOC-1).
 *
 * Loaded as a classic `<script>` (no `module`), on a page whose address is `pathname` + `hash`, the script:
 *
 *   - calls `location.replace('../<new page>/#<anchor>')` exactly once when the page is an admin page, the hash names an
 *     anchor the map moves, and NO element of the page has that id (the anchor is not on this page, whatever the map says);
 *   - calls nothing when an element with that id exists, when the page is not an admin page (a page of the manual, a deeper
 *     path, `/developer/admin/`), when there is no hash or an empty one, when the anchor did not move, when the page is
 *     not one the map knows, when the hash is a malformed escape; the language prefix and `index.html` change nothing;
 *   - does not touch the page when `module` exists (the exports host), and does not throw on a page with no `location`.
 *
 * `location` is replaced by `{pathname, hash, replace}` with `vi.stubGlobal`, the way `searchLanguage.dom.test.ts` stands in
 * for it (the script reads it from `window`, which in this environment is the global). The script runs again for every test.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {loadScript, runAsBrowserScript} from './__tests__/movedAnchorsScript';

let replace: ReturnType<typeof vi.fn>;

beforeEach(() => {
    replace = vi.fn();
    document.body.innerHTML = '';
});

afterEach(() => {
    vi.unstubAllGlobals();
    document.body.innerHTML = '';
});

/** Opens a page: the stubbed address, the body, the script run as the browser runs it. */
function openPage(pathname: string, hash: string, body = ''): void {
    vi.stubGlobal('location', {pathname, hash, replace});
    document.body.innerHTML = body;
    runAsBrowserScript();
}

describe('the redirect of a moved anchor', () => {
    it('a moved anchor of an admin page with no such element → location.replace once, to the new page', () => {
        openPage('/mkdocs/admin/configuration/', '#csp', '<h2 id="other">Other</h2>');
        expect(replace).toHaveBeenCalledTimes(1);
        expect(replace).toHaveBeenCalledWith('../configuration_security/#csp');
    });

    it.each([
        ['/mkdocs/admin/configuration/', '#secrets', '../configuration_secrets/#secrets'],
        ['/mkdocs/admin/configuration/', '#login-limit', '../configuration_accounts/#login-limit'],
        ['/mkdocs/admin/connection_checks/', '#untrusted-proxy', '../connection_proxy/#untrusted-proxy'],
        ['/mkdocs/admin/email/', '#forgot-password', '../email_flows/#forgot-password'],
        ['/mkdocs/admin/sleep_wake/', '#wake-sync', '../wake_sync/#wake-sync'],
        ['/mkdocs/admin/service_exposure/', '#3-startup-and-approval', '../service_exposure_funnel/#3-startup-and-approval'],
    ])('%s%s → %s', (pathname, hash, target) => {
        openPage(pathname, hash);
        expect(replace).toHaveBeenCalledTimes(1);
        expect(replace).toHaveBeenCalledWith(target);
    });

    it('the language prefix and index.html change nothing: the target is relative', () => {
        openPage('/LibreFolio/it/admin/configuration/index.html', '#csp');
        expect(replace).toHaveBeenCalledTimes(1);
        expect(replace).toHaveBeenCalledWith('../configuration_security/#csp');
    });

    it('the hash is kept as it was written', () => {
        openPage('/mkdocs/admin/configuration/', '#cs%70');
        expect(replace).toHaveBeenCalledWith('../configuration_security/#cs%70');
    });
});

describe('no redirect', () => {
    it('an element of the page has that id: the anchor is here, not moved', () => {
        openPage('/mkdocs/admin/configuration/', '#csp', '<h2 id="csp">CSP</h2>');
        expect(replace).not.toHaveBeenCalled();
    });

    it('the element is found by the decoded id', () => {
        openPage('/mkdocs/admin/configuration/', '#cs%70', '<h2 id="csp">CSP</h2>');
        expect(replace).not.toHaveBeenCalled();
    });

    it('a page that is not an admin page', () => {
        openPage('/mkdocs/user/configuration/', '#csp');
        openPage('/mkdocs/admin/configuration/deeper/', '#csp');
        openPage('/mkdocs/developer/admin/', '#csp');
        openPage('/mkdocs/', '#csp');
        expect(replace).not.toHaveBeenCalled();
    });

    it.each([
        ['no hash', ''],
        ['a bare #', '#'],
        ['an anchor that stayed', '#create-the-env-file'],
        ['a malformed escape', '#%E0%A4%A'],
        ['a prototype key', '#constructor'],
        ['a prototype key, the other', '#__proto__'],
    ])('on an admin page with %s', (_label, hash) => {
        openPage('/mkdocs/admin/configuration/', hash);
        expect(replace).not.toHaveBeenCalled();
    });

    it('an admin page the map does not know', () => {
        openPage('/mkdocs/admin/settings/', '#csp');
        openPage('/mkdocs/admin/constructor/', '#csp');
        expect(replace).not.toHaveBeenCalled();
    });

    it('with a module (the exports host) the script reads no address and never redirects', () => {
        vi.stubGlobal('location', {pathname: '/mkdocs/admin/configuration/', hash: '#csp', replace});
        loadScript();
        expect(replace).not.toHaveBeenCalled();
    });

    it('a page with no location does not throw', () => {
        vi.stubGlobal('location', undefined);
        expect(() => runAsBrowserScript()).not.toThrow();
    });
});
