// @vitest-environment jsdom
/**
 * ConnectionSecurityIndicator — the sidebar line of plan 36 (§2.2, D3), in jsdom.
 *
 * The line reads `connectionSecurityStore` and asks it to refresh on mount. The contract, by test id:
 *   - `connection-security`, the root: `data-level`, `data-reason` and `data-server-checked` ("true"/"false") are
 *     the store's;
 *   - `connection-security-toggle`, a button with `aria-expanded`;
 *   - `connection-security-label`, the visible label, only while the sidebar is expanded;
 *   - `connection-security-details`, only while open, holding the reason (`connection-security-reason`), the admin
 *     line (`connection-security-admin-warning`, only for a superuser with `cookieWarning`) and the docs link
 *     (`connection-security-docs-link`: an anchor to `connectionSecurityDocsUrl(current language)`, new tab,
 *     `noopener`).
 * Collapsed (D3), a click on the line asks the sidebar to expand (`onExpand`) and opens the details, which show once
 * the parent re-renders the line expanded.
 *
 * The stores are real. A case is a page load: jsdom's URL is pointed at the page (so `window.location`, the store's
 * default location, is that page), the store is primed with `resetConnectionSecurity()` and a forced refresh, and the
 * default endpoint is programmed with the same answer — so the line's own refresh on mount, which asks only once per
 * page load, lands on the same state whatever it does. The user is set through the auth store's own seam,
 * `auth.checkAuth()` against a programmed `GET /auth/me`. `$lib/api` is mocked: nothing reaches the network.
 *
 * Written RED-FIRST against the stubs of plan 36 (step 2): every red fails on an assertion. Never a translated string:
 * test ids, attributes and the store's values only.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const api = vi.hoisted(() => ({
    connection: vi.fn(),
    me: vi.fn(),
}));

// `$lib/api`: the two operations this file programs, and an inert spy for any other a transitive import may touch —
// pending forever, so that nothing it starts can settle behind the assertions or reach the network.
vi.mock('$lib/api', () => {
    const programmed: Record<string, unknown> = {
        get_connection_security_api_v1_system_connection_get: api.connection,
        get_me_api_v1_auth_me_get: api.me,
    };
    const inert = new Map<string, unknown>();
    const pending = () => new Promise(() => {});
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (operation in programmed) return programmed[operation];
                if (!inert.has(operation)) inert.set(operation, vi.fn(pending));
                return inert.get(operation);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

import {get} from 'svelte/store';
import {tick} from 'svelte';
import {waitLocale} from 'svelte-i18n';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import ConnectionSecurityIndicator from './ConnectionSecurityIndicator.svelte';
import {connectionSecurity, refreshConnectionSecurity, resetConnectionSecurity} from '$lib/stores/app/connectionSecurityStore';
import {connectionSecurityDocsUrl, type ConnectionLevel, type ConnectionReason, type ServerView} from '$lib/utils/security/connectionSecurity';
import {auth} from '$lib/stores/app/auth';
import {currentLanguage} from '$lib/stores/app/language';

/** The JSDOM instance vitest exposes in this environment: its URL is the page's `window.location`. */
const dom = (globalThis as unknown as {jsdom: {reconfigure(settings: {url: string}): void}}).jsdom;
const INITIAL_URL = window.location.href;

/** The user page, at its root, in the two languages these cases speak. */
const DOCS_HREF = {en: '/mkdocs/user/connection-security/', it: '/mkdocs/it/user/connection-security/'} as const;

/** What the server answers on this page load, or `'fails'` when the request fails. */
type ServerAnswer = ServerView | 'fails';

/** A page load at `url`: `window.location` now reads it, as the store's default location does. */
function loadAt(url: string): {protocol: string; hostname: string} {
    dom.reconfigure({url});
    return {protocol: window.location.protocol, hostname: window.location.hostname};
}

/** The store as a page load at `url` leaves it, the default endpoint programmed with the same `answer`. */
async function primeAt(url: string, answer: ServerAnswer): Promise<void> {
    const location = loadAt(url);
    if (answer === 'fails') api.connection.mockRejectedValue(new Error('GET /system/connection failed'));
    else api.connection.mockResolvedValue({client_class: answer.clientClass, cookie_secure: answer.cookieSecure});
    resetConnectionSecurity();
    await refreshConnectionSecurity({
        location,
        fetchServerView: () => (answer === 'fails' ? Promise.reject(new Error('GET /system/connection failed')) : Promise.resolve(answer)),
        force: true,
    });
}

/** Signs a user in through the auth store's own seam: `checkAuth()` against a programmed `GET /auth/me`. */
async function signInAs(isSuperuser: boolean): Promise<void> {
    api.me.mockResolvedValueOnce({
        user: {id: 36, username: 'connection-security', email: 'connection-security@example.com', is_active: true, is_superuser: isSuperuser, created_at: '2026-10-09T00:00:00Z'},
    });
    expect(await auth.checkAuth(), 'premise: the auth store signed the user in').toBe('authenticated');
    expect(get(auth).user?.is_superuser, 'premise: the signed-in user is the one this case needs').toBe(isSuperuser);
}

async function mountIndicator(props: {collapsed?: boolean; onExpand?: () => void} = {}) {
    const result = render(ConnectionSecurityIndicator, props);
    await tick();
    return result;
}

/** The element with `testId` inside `scope`, asserted present: a missing one fails here, on an assertion. */
function present(testId: string, scope: HTMLElement = document.body, message = `${testId} is drawn`): HTMLElement {
    const element = within(scope).queryByTestId(testId);
    expect(element, message).not.toBeNull();
    return element as HTMLElement;
}

/** The root's three attributes, as strings. */
function rootAttributes(): {level: string | null; reason: string | null; serverChecked: string | null} {
    const root = present('connection-security');
    return {level: root.getAttribute('data-level'), reason: root.getAttribute('data-reason'), serverChecked: root.getAttribute('data-server-checked')};
}

/** Clicks the toggle and returns the details it opened. */
async function openDetails(): Promise<HTMLElement> {
    const toggle = present('connection-security-toggle');
    expect(toggle, 'premise: the details start closed').toHaveAttribute('aria-expanded', 'false');
    await fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    return present('connection-security-details', document.body, 'a click on the toggle opens the details');
}

function expectDocsLink(link: HTMLElement, lang: keyof typeof DOCS_HREF): void {
    const href = connectionSecurityDocsUrl(lang);
    expect(href, 'premise: the pure module builds the localized page (pinned in connectionSecurity.test.ts)').toBe(DOCS_HREF[lang]);
    expect(link.tagName, 'the docs link is an anchor').toBe('A');
    expect(link, 'the user page, in the current language').toHaveAttribute('href', href);
    expect(link, 'in a new tab').toHaveAttribute('target', '_blank');
    expect((link.getAttribute('rel') ?? '').split(/\s+/), 'without a window.opener').toContain('noopener');
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    api.connection.mockReset();
    api.me.mockReset();
    // Unprogrammed, the endpoint fails loudly instead of answering for the case.
    api.connection.mockRejectedValue(new Error('GET /system/connection is not programmed for this case'));
    auth.reset();
    resetConnectionSecurity();
});

afterEach(() => {
    resetConnectionSecurity();
    auth.reset();
    dom.reconfigure({url: INITIAL_URL});
});

describe('ConnectionSecurityIndicator — the root publishes the store', () => {
    const CASES: Array<{label: string; url: string; answer: ServerAnswer; level: ConnectionLevel; reason: ConnectionReason; serverChecked: 'true' | 'false'}> = [
        {label: 'https, the server answered', url: 'https://lf.example/', answer: {clientClass: 'public', cookieSecure: true}, level: 'secure', reason: 'https', serverChecked: 'true'},
        {label: 'http on localhost', url: 'http://localhost/', answer: {clientClass: 'loopback', cookieSecure: false}, level: 'secure', reason: 'localhost', serverChecked: 'true'},
        {label: 'http on a tailnet name', url: 'http://server.tailnet-abc.ts.net/', answer: {clientClass: 'vpn', cookieSecure: false}, level: 'secure', reason: 'vpn', serverChecked: 'true'},
        {label: 'http on a .lan name', url: 'http://lf.lan/', answer: {clientClass: 'lan', cookieSecure: false}, level: 'local', reason: 'lan', serverChecked: 'true'},
        {label: 'http on a public name, the server sees the loopback', url: 'http://lf.example/', answer: {clientClass: 'loopback', cookieSecure: false}, level: 'local', reason: 'uncertain', serverChecked: 'true'},
        {label: 'http on a public name, the server sees a public client', url: 'http://lf.example/', answer: {clientClass: 'public', cookieSecure: false}, level: 'insecure', reason: 'internet', serverChecked: 'true'},
        {label: 'http on a .lan name, the server did not answer', url: 'http://lf.lan/', answer: 'fails', level: 'local', reason: 'lan', serverChecked: 'false'},
    ];

    it.each(CASES.map((testCase): [string, (typeof CASES)[number]] => [`${testCase.label} → ${testCase.level} / ${testCase.reason}, server checked ${testCase.serverChecked}`, testCase]))('%s', async (_title, {url, answer, level, reason, serverChecked}) => {
        await primeAt(url, answer);
        await mountIndicator();

        await waitFor(() => expect(rootAttributes(), `the store holds ${JSON.stringify(get(connectionSecurity))}`).toEqual({level, reason, serverChecked}));
        const state = get(connectionSecurity);
        expect(rootAttributes(), 'the root follows the store').toEqual({level: state.level, reason: state.reason, serverChecked: String(state.serverChecked)});
    });

    it('on a fresh page load the line asks the server itself, once, from the page’s own location', async () => {
        loadAt('http://lf.lan/');
        api.connection.mockResolvedValue({client_class: 'public', cookie_secure: false});

        await mountIndicator();

        await waitFor(() => expect(rootAttributes(), 'the mount’s refresh folded the default endpoint’s answer in').toEqual({level: 'local', reason: 'uncertain', serverChecked: 'true'}));
        expect(api.connection, 'GET /api/v1/system/connection, once').toHaveBeenCalledTimes(1);
    });
});

describe('ConnectionSecurityIndicator — expanded sidebar: the details open in line', () => {
    it('the toggle opens the details, with the reason and the docs link, and a second click closes them', async () => {
        await primeAt('http://lf.lan/', {clientClass: 'lan', cookieSecure: false});
        await mountIndicator({collapsed: false});
        const toggle = present('connection-security-toggle');
        expect(toggle.tagName, 'the toggle is a button').toBe('BUTTON');
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        expect(screen.queryByTestId('connection-security-details'), 'the details start closed').toBeNull();

        await fireEvent.click(toggle);

        expect(toggle).toHaveAttribute('aria-expanded', 'true');
        const details = present('connection-security-details', document.body, 'a click opens the details');
        expect(details).toBeVisible();
        present('connection-security-reason', details, 'the details give the reason');
        expectDocsLink(present('connection-security-docs-link', details, 'the details link the documentation'), 'en');

        await fireEvent.click(toggle);

        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        await waitFor(() => expect(screen.queryByTestId('connection-security-details'), 'a second click closes them').toBeNull());
        present('connection-security-label', document.body, 'expanded, the line shows its label');
    });

    it('the docs link follows the current language', async () => {
        currentLanguage.set('it');
        await waitLocale('it');
        try {
            await primeAt('http://lf.lan/', {clientClass: 'lan', cookieSecure: false});
            await mountIndicator();

            const details = await openDetails();

            expectDocsLink(present('connection-security-docs-link', details, 'the details link the documentation'), 'it');
        } finally {
            currentLanguage.set('en');
            await waitLocale('en');
        }
    });
});

/**
 * The admin line: the browser is on HTTPS but the session cookie is not marked Secure (`cookieWarning`), and only a
 * superuser can fix that (reverse proxy or SESSION_COOKIE_SECURE). It sits in the details; the level stays secure.
 * Not reachable in the E2E lane, which serves plain HTTP: this is where it is covered.
 */
describe('ConnectionSecurityIndicator — the admin warning', () => {
    const COOKIE_NOT_SECURE: ServerView = {clientClass: 'public', cookieSecure: false};
    const COOKIE_SECURE: ServerView = {clientClass: 'public', cookieSecure: true};

    /** Signs the user in first, so that whatever a session change resets happens before the page's state is primed. */
    async function openDetailsAs(isSuperuser: boolean, answer: ServerView): Promise<HTMLElement> {
        await signInAs(isSuperuser);
        await primeAt('https://lf.example/', answer);
        await mountIndicator();
        const details = await openDetails();
        present('connection-security-docs-link', details, 'presence barrier: the details are drawn');
        return details;
    }

    it('an admin, on HTTPS with a session cookie not marked Secure: the warning is in the details', async () => {
        const details = await openDetailsAs(true, COOKIE_NOT_SECURE);

        expect(get(connectionSecurity), 'premise: the store raised the cookie warning').toMatchObject({level: 'secure', reason: 'https', cookieWarning: true});
        present('connection-security-admin-warning', details, 'a superuser is told how to fix the cookie');
    });

    it('a non-admin, with the same cookie warning: no warning', async () => {
        await openDetailsAs(false, COOKIE_NOT_SECURE);

        expect(get(connectionSecurity), 'premise: the store raised the cookie warning').toMatchObject({level: 'secure', reason: 'https', cookieWarning: true});
        expect(screen.queryByTestId('connection-security-admin-warning'), 'only a superuser can fix it, so only a superuser is told').toBeNull();
    });

    it('an admin, with a Secure session cookie: no warning', async () => {
        await openDetailsAs(true, COOKIE_SECURE);

        expect(get(connectionSecurity), 'premise: nothing to warn about').toMatchObject({level: 'secure', reason: 'https', cookieWarning: false});
        expect(screen.queryByTestId('connection-security-admin-warning'), 'no cookie warning, no admin line').toBeNull();
    });
});

describe('ConnectionSecurityIndicator — collapsed sidebar (D3)', () => {
    it('icon only; a click asks the sidebar to expand, once, and opens the details, which show once the parent expands the line', async () => {
        await primeAt('http://lf.lan/', {clientClass: 'lan', cookieSecure: false});
        const onExpand = vi.fn();
        const {rerender} = await mountIndicator({collapsed: true, onExpand});
        const toggle = present('connection-security-toggle', document.body, 'presence barrier: the collapsed line still offers its toggle');
        expect(screen.queryByTestId('connection-security-label'), 'collapsed, the line shows its icon only').toBeNull();
        expect(toggle).toHaveAttribute('aria-expanded', 'false');

        await fireEvent.click(toggle);

        expect(onExpand, 'a click on the collapsed line asks the sidebar to expand, once').toHaveBeenCalledTimes(1);
        expect(toggle).toHaveAttribute('aria-expanded', 'true');

        await rerender({collapsed: false});

        expect(present('connection-security-toggle'), 'the details stay open across the expansion').toHaveAttribute('aria-expanded', 'true');
        expect(present('connection-security-details', document.body, 'expanded by the parent, the line shows the details')).toBeVisible();
        present('connection-security-label', document.body, 'and its label');
        expect(onExpand, 'the expansion came from the parent: no second request').toHaveBeenCalledTimes(1);
    });
});
