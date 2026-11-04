/**
 * movedAnchors.test.ts — the pure half of `mkdocs_src/docs/javascripts/moved-anchors.js` (DOC-1).
 *
 * DOC-1 split the long admin pages: `admin/configuration/#csp` is now `admin/configuration_security/#csp`. The script, loaded
 * on every page of the documentation, sends an address whose anchor moved to the page that has it now. This file pins what
 * needs no browser:
 *
 *   - `adminPage(pathname)`: the page of a path that ENDS in `/admin/<page>/` (`<page>` is `[a-z0-9_]+`), with or without
 *     `index.html`, whatever comes before it (the `/mkdocs/` mount, the `/LibreFolio/` base, a language folder). A deeper
 *     path, a path that merely has `admin` in it, and a name outside the alphabet are not an admin page: `null`;
 *   - `movedTarget(pathname, hash, map, hasAnchor)`: `../<new page>/#<anchor>` — relative to the old page's folder, so the
 *     language prefix and the site's base stay as they were, and the hash is kept as it was written — when the page is an admin
 *     page, the hash names an anchor the map moves, and the page itself does not have it (`hasAnchor(anchor)` is falsy or
 *     absent); `null` in every other case: not an admin page, no hash (`''`, `'#'`, no `#`, not a string), a malformed `%`
 *     escape, a page or an anchor the map does not know, the anchor still on the page. The map is read by OWN keys:
 *     `constructor`, `__proto__`, `hasOwnProperty` and the like — as an anchor or as a page — never match;
 *   - `MOVED_ANCHORS`: every entry answers through `movedTarget` as `../<target>/#<anchor>`;
 *   - the file itself: a classic script with no dependency (no `import`, `export` or `require`), exporting through
 *     `module.exports` only when `module` exists, and run in node (no `window`, no `location`) without throwing.
 *
 * The redirect on a page needs a DOM: `movedAnchors.dom.test.ts`. The completeness of the map against the pages is the
 * backend's `test_docs_admin_references.py`.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {describe, expect, it, vi} from 'vitest';
import {loadScript, runAsBrowserScript, scriptSource, type MovedMap} from './__tests__/movedAnchorsScript';

const MAP: MovedMap = {
    configuration: {csp: 'configuration_security', secrets: 'configuration_secrets'},
    email: {logs: 'email_troubleshooting'},
};

describe('adminPage', () => {
    const {adminPage} = loadScript();

    it.each([
        ['/mkdocs/admin/configuration/', 'configuration'],
        ['/LibreFolio/it/admin/configuration/index.html', 'configuration'],
        ['/admin/x/', 'x'],
        ['/admin/service_exposure_funnel/', 'service_exposure_funnel'],
        ['/admin/page2/index.html', 'page2'],
        ['https://librefolio.github.io/LibreFolio/admin/email/', 'email'],
    ])('%s → %s', (pathname, page) => {
        expect(adminPage(pathname)).toBe(page);
    });

    it.each(['/admin/configuration/foo/', '/admin/configuration/foo/index.html', '/developer/admin/', '/admin/', '/admin/configuration', '/admin/Configuration/', '/admin/con-figuration/', '/xadmin/configuration/', '/admin/configuration/index.htm', '/user/configuration/', ''])(
        '%j → null',
        (pathname) => {
            expect(adminPage(pathname)).toBeNull();
        },
    );

    it('takes whatever it is given as text, never throws', () => {
        expect(adminPage(undefined as unknown as string)).toBeNull();
        expect(adminPage(null as unknown as string)).toBeNull();
        expect(adminPage({toString: () => '/admin/x/'} as unknown as string)).toBe('x');
    });
});

describe('movedTarget', () => {
    const {movedTarget} = loadScript();

    it('a moved anchor goes to the new page, relative to the old one', () => {
        expect(movedTarget('/mkdocs/admin/configuration/', '#csp', MAP)).toBe('../configuration_security/#csp');
        expect(movedTarget('/mkdocs/admin/configuration/', '#secrets', MAP)).toBe('../configuration_secrets/#secrets');
        expect(movedTarget('/mkdocs/admin/email/', '#logs', MAP)).toBe('../email_troubleshooting/#logs');
    });

    it('keeps the language prefix and the base: the target is relative, the path is never rewritten', () => {
        expect(movedTarget('/mkdocs/it/admin/configuration/', '#csp', MAP)).toBe('../configuration_security/#csp');
        expect(movedTarget('/LibreFolio/fr/admin/configuration/index.html', '#csp', MAP)).toBe('../configuration_security/#csp');
    });

    it('keeps the hash as it was written, decoded only to find the anchor', () => {
        expect(movedTarget('/admin/configuration/', '#cs%70', MAP)).toBe('../configuration_security/#cs%70');
    });

    it('asks the page whether it still has the anchor, with the anchor decoded and without the #', () => {
        const has = vi.fn(() => false);
        expect(movedTarget('/admin/configuration/', '#cs%70', MAP, has)).toBe('../configuration_security/#cs%70');
        expect(has).toHaveBeenCalledTimes(1);
        expect(has).toHaveBeenCalledWith('csp');
    });

    it('an anchor the page still has stays where it is', () => {
        expect(movedTarget('/admin/configuration/', '#csp', MAP, () => true)).toBeNull();
        expect(movedTarget('/admin/configuration/', '#csp', MAP, () => false)).toBe('../configuration_security/#csp');
        expect(movedTarget('/admin/configuration/', '#csp', MAP, undefined)).toBe('../configuration_security/#csp');
    });

    it('does not ask the page about an anchor that did not move', () => {
        const has = vi.fn(() => false);
        expect(movedTarget('/admin/configuration/', '#main-options', MAP, has)).toBeNull();
        expect(movedTarget('/admin/settings/', '#csp', MAP, has)).toBeNull();
        expect(has).not.toHaveBeenCalled();
    });

    it('nothing moved: an anchor of the page that stays, a page the map does not know, an anchor of another page', () => {
        expect(movedTarget('/admin/configuration/', '#create-the-env-file', MAP)).toBeNull();
        expect(movedTarget('/admin/settings/', '#csp', MAP)).toBeNull();
        expect(movedTarget('/admin/email/', '#csp', MAP)).toBeNull();
        expect(movedTarget('/admin/configuration/', '#logs', MAP)).toBeNull();
        expect(movedTarget('/admin/configuration/', '#CSP', MAP)).toBeNull();
    });

    it('not an admin page: no redirect, whatever the hash says', () => {
        expect(movedTarget('/user/configuration/', '#csp', MAP)).toBeNull();
        expect(movedTarget('/admin/configuration/deeper/', '#csp', MAP)).toBeNull();
        expect(movedTarget('/developer/admin/', '#csp', MAP)).toBeNull();
        expect(movedTarget('/', '#csp', MAP)).toBeNull();
    });

    it.each([
        ['an empty hash', ''],
        ['a bare #', '#'],
        ['no # at all', 'csp'],
        ['a malformed escape', '#%E0%A4%A'],
        ['a lone %', '#%'],
        ['null', null],
        ['undefined', undefined],
        ['a number', 7 as unknown as string],
    ])('%s → null', (_label, hash) => {
        expect(movedTarget('/admin/configuration/', hash as string, MAP)).toBeNull();
    });

    it.each(['#constructor', '#__proto__', '#hasOwnProperty', '#toString', '#valueOf', '#isPrototypeOf', '#__defineGetter__'])('the anchor %s is never one the map moves', (hash) => {
        expect(movedTarget('/admin/configuration/', hash, MAP)).toBeNull();
        expect(movedTarget('/admin/configuration/', hash, {configuration: {}})).toBeNull();
        expect(movedTarget('/admin/configuration/', hash, MAP, () => false)).toBeNull();
    });

    it.each(['constructor', '__proto__', 'tostring', 'valueof'])('the page %s is not a page of the map', (page) => {
        expect(movedTarget(`/admin/${page}/`, '#csp', MAP)).toBeNull();
        expect(movedTarget(`/admin/${page}/`, '#constructor', MAP)).toBeNull();
        expect(movedTarget(`/admin/${page}/`, '#__proto__', {})).toBeNull();
    });

    it('a map that has an own entry for such a key does match it: own keys, not a ban on names', () => {
        const own = JSON.parse('{"configuration": {"constructor": "moved_page", "__proto__": "moved_proto"}}') as MovedMap;
        expect(movedTarget('/admin/configuration/', '#constructor', own)).toBe('../moved_page/#constructor');
        expect(movedTarget('/admin/configuration/', '#__proto__', own)).toBe('../moved_proto/#__proto__');
    });
});

describe('MOVED_ANCHORS', () => {
    const {MOVED_ANCHORS, movedTarget} = loadScript();

    it('moves the anchors of the five split pages', () => {
        expect(Object.keys(MOVED_ANCHORS).sort()).toEqual(expect.arrayContaining(['configuration', 'connection_checks', 'email', 'service_exposure', 'sleep_wake']));
        expect(Object.values(MOVED_ANCHORS).reduce((sum, entries) => sum + Object.keys(entries).length, 0)).toBeGreaterThanOrEqual(20);
    });

    it('every entry answers through movedTarget as ../<target>/#<anchor>, a flat page of the same folder', () => {
        const entries = Object.entries(MOVED_ANCHORS).flatMap(([page, anchors]) => Object.entries(anchors).map(([anchor, target]) => ({page, anchor, target})));
        expect(entries.length, 'barrier: there are entries to check').toBeGreaterThan(0);
        for (const {page, anchor, target} of entries) {
            expect(target, `${page}#${anchor}`).toMatch(/^[a-z0-9_]+$/);
            expect(target, `${page}#${anchor} points at its own page`).not.toBe(page);
            expect(movedTarget(`/mkdocs/admin/${page}/`, `#${anchor}`, MOVED_ANCHORS), `${page}#${anchor}`).toBe(`../${target}/#${anchor}`);
            expect(
                movedTarget(`/mkdocs/it/admin/${page}/index.html`, `#${anchor}`, MOVED_ANCHORS, () => true),
                `${page}#${anchor}, still on the page`,
            ).toBeNull();
        }
    });

    it('moves the anchor the 11 guides of the Security tab used to point at', () => {
        expect(movedTarget('/mkdocs/admin/configuration/', '#csp', MOVED_ANCHORS)).toBe('../configuration_security/#csp');
        expect(movedTarget('/mkdocs/admin/configuration/', '#login-limit', MOVED_ANCHORS)).toBe('../configuration_accounts/#login-limit');
        expect(movedTarget('/mkdocs/admin/connection_checks/', '#untrusted-proxy', MOVED_ANCHORS)).toBe('../connection_proxy/#untrusted-proxy');
        expect(movedTarget('/mkdocs/admin/configuration/', '#secrets', MOVED_ANCHORS)).toBe('../configuration_secrets/#secrets');
    });

    it('leaves the anchors that stayed alone: session-cookie is still on connection_checks', () => {
        expect(movedTarget('/mkdocs/admin/connection_checks/', '#session-cookie', MOVED_ANCHORS)).toBeNull();
    });
});

describe('the file', () => {
    it('is a classic script: no import, export or require', () => {
        const source = scriptSource();
        expect(source).not.toMatch(/^\s*import\s/m);
        expect(source).not.toMatch(/^\s*export\s/m);
        expect(source).not.toMatch(/\brequire\s*\(/);
    });

    it('exports the three pieces through module.exports when module exists', () => {
        const exported = loadScript();
        expect(typeof exported.adminPage).toBe('function');
        expect(typeof exported.movedTarget).toBe('function');
        expect(typeof exported.MOVED_ANCHORS).toBe('object');
        expect(exported.MOVED_ANCHORS).not.toBeNull();
    });

    it('runs with no module in a host with no window or location (node) without throwing', () => {
        expect(typeof window).toBe('undefined');
        expect(() => runAsBrowserScript()).not.toThrow();
    });

    it('runs with a module in node without throwing, and again: each run has its own exports', () => {
        const first = loadScript();
        const second = loadScript();
        expect(second).not.toBe(first);
        expect(second.MOVED_ANCHORS).toEqual(first.MOVED_ANCHORS);
    });
});
