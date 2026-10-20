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
 *     `noopener`);
 *   - the reason is a `<button type="button">`: a click on it closes the details and, when it held the focus, hands
 *     the focus back to the toggle. Only the reason: a click on the admin line or on the docs link leaves them open.
 * Collapsed (D3), a click on the line asks the sidebar to expand (`onExpand`) and opens the details, which show once
 * the parent re-renders the line expanded.
 *
 * Untouched, the details close by themselves 30 s after they open (plan 48, C3, choice (b)). The pointer anywhere on
 * the indicator (`pointerenter`/`pointerleave` on the root) holds the countdown, and so does the focus inside the
 * details (the reason, the link) — not the focus on the toggle, where a click leaves it in Chrome. Once neither holds
 * it, the countdown starts again from 30 s, never from what was left. Closing by hand cancels it, and an unmount
 * leaves nothing on the clock. Driven on a fake `setTimeout`/`clearTimeout`, counted with `vi.getTimerCount()`.
 *
 * The stores are real. A case is a page load: jsdom's URL is pointed at the page (so `window.location`, the store's
 * default location, is that page), the store is primed with `resetConnectionSecurity()` and a forced refresh, and the
 * default endpoint is programmed with the same answer — so the line's own refresh on mount, which asks only once per
 * page load, lands on the same state whatever it does. The user is set through the auth store's own seam,
 * `auth.checkAuth()` against a programmed `GET /auth/me`. `$lib/api` is mocked: nothing reaches the network.
 *
 * Written RED-FIRST against the stubs of plan 36 (step 2), and the closing cases against the line as plan 36 left it
 * (plan 48, C3): every red fails on an assertion. Never a translated string: test ids, attributes, the focus, the
 * clock and the store's values only.
 *
 * N69b, the security-attention dot, is the last describe; its contract and its doubles are written above it. The checks'
 * store (`$lib/features/settings/security/securityChecks.svelte`) is a fake for the whole file — the real one is a
 * module singleton nothing can reset between cases —, idle and empty unless a case says otherwise, so the line as it was
 * before N69b meets it unchanged.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const api = vi.hoisted(() => ({
    connection: vi.fn(),
    me: vi.fn(),
    // The checks' own request: the store is faked (below), so this is called only by a line that would ask the server
    // around the store. Pending forever, like any inert operation.
    securityChecks: vi.fn(() => new Promise<never>(() => {})).mockName('zodiosApi.list_security_checks_api_v1_security_checks_get'),
}));

/** A finding of the Security tab, as the store lists it (`securityFindings.ts`). */
interface FakeFinding {
    id: string;
    severity: 'error' | 'warning' | 'info';
    messageKey: string;
    params: Record<string, string | number>;
    source: 'server' | 'browser';
}

/**
 * The checks' store, faked over a `$state` box (`reactiveBox`), so the line re-renders when a case lands an answer. One
 * source of truth, the answer's attention findings: `findings`, `attentionCount` (errors and warnings) and
 * `attentionSeverity` (error, else warning, else null) are derived from it as the real store derives them, all empty and
 * `null` before the answer. `ensureLoaded()` does to the state it reads what the real one does — it reads the status and,
 * from idle or error, starts a request (`loading`) — so an effect that calls it without `untrack` depends on that status
 * and runs again, as it would on the real store; `reload()` always starts one. Neither ever answers: a case lands the
 * answer itself (`storeAnswers`).
 */
const securityStore = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const state = reactiveBox<{status: 'idle' | 'loading' | 'ready' | 'error'; answered: boolean; attention: FakeFinding[]}>({status: 'idle', answered: false, attention: []});
    const ensureLoaded = vi
        .fn((): Promise<void> => {
            if (state.status === 'idle' || state.status === 'error') state.status = 'loading';
            return Promise.resolve();
        })
        .mockName('securityChecks.ensureLoaded');
    const reload = vi
        .fn((): Promise<void> => {
            state.status = 'loading';
            return Promise.resolve();
        })
        .mockName('securityChecks.reload');
    const counted = (): FakeFinding[] => (state.answered ? state.attention.filter((finding) => finding.severity === 'error' || finding.severity === 'warning') : []);
    const store = {
        get status() {
            return state.status;
        },
        get checks(): never[] {
            return [];
        },
        get answered() {
            return state.answered;
        },
        get findings(): {attention: FakeFinding[]; passed: FakeFinding[]} {
            return {attention: state.answered ? state.attention : [], passed: []};
        },
        get attentionCount(): number {
            return counted().length;
        },
        get attentionSeverity(): 'error' | 'warning' | null {
            const found = counted();
            if (found.some((finding) => finding.severity === 'error')) return 'error';
            return found.length > 0 ? 'warning' : null;
        },
        ensureLoaded,
        reload,
    };
    return {state, ensureLoaded, reload, store};
});

vi.mock('$lib/features/settings/security/securityChecks.svelte', () => ({securityChecks: securityStore.store}));

// `$lib/api`: the operations this file programs, and an inert spy for any other a transitive import may touch —
// pending forever, so that nothing it starts can settle behind the assertions or reach the network.
vi.mock('$lib/api', () => {
    const programmed: Record<string, unknown> = {
        get_connection_security_api_v1_system_connection_get: api.connection,
        get_me_api_v1_auth_me_get: api.me,
        list_security_checks_api_v1_security_checks_get: api.securityChecks,
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
import {flushSync, tick} from 'svelte';
import {addMessages, waitLocale} from 'svelte-i18n';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import ConnectionSecurityIndicator from './ConnectionSecurityIndicator.svelte';
import {connectionSecurity, refreshConnectionSecurity, resetConnectionSecurity} from '$lib/stores/app/connectionSecurityStore';
import {connectionSecurityDocsUrl, type ConnectionLevel, type ConnectionReason, type ServerView} from '$lib/utils/security/connectionSecurity';
import {auth} from '$lib/stores/app/auth';
import {currentLanguage} from '$lib/stores/app/language';
import {_ as formatMessage} from '$lib/i18n';

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

/** The checks' store back to a page load that has asked nothing: idle, no answer, no call recorded. */
function resetSecurityStore(): void {
    securityStore.state.status = 'idle';
    securityStore.state.answered = false;
    securityStore.state.attention = [];
    securityStore.ensureLoaded.mockClear();
    securityStore.reload.mockClear();
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    api.connection.mockReset();
    api.me.mockReset();
    api.securityChecks.mockClear();
    // Unprogrammed, the endpoint fails loudly instead of answering for the case.
    api.connection.mockRejectedValue(new Error('GET /system/connection is not programmed for this case'));
    auth.reset();
    resetConnectionSecurity();
    resetSecurityStore();
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

/**
 * Closing the details (plan 48, C3). The developer: a click on the text that explains the level closes the panel, and
 * the panel closes by itself after 30 seconds. Choice (b), the coordinator's: the pointer holds the countdown anywhere
 * on the indicator, through pointer events; the focus holds it only inside the details (the reason, the link), not on
 * the toggle; once they leave, it starts again from 30 s.
 *
 * The clock is fake for `setTimeout` and `clearTimeout` only: promises, microtasks and Svelte's flushes stay real, so
 * the page-load helpers above run as they do everywhere else. Testing-library's `waitFor` does not drive the fake
 * clock: time moves with `vi.advanceTimersByTimeAsync`, a `tick()` lets Svelte apply what the timers changed, and the
 * state is read synchronously. The focus moves for real, with `.focus()` and `.blur()` (jsdom fires focusin and
 * focusout): a `fireEvent.click` never moves it.
 */
describe('ConnectionSecurityIndicator — closing the details: the reason, and 30 s untouched', () => {
    const AUTO_CLOSE_MS = 30_000;
    /** Twice the countdown: what a held countdown must outlast. */
    const HELD_MS = 2 * AUTO_CLOSE_MS;

    // Installed before the mount: the line resolves `setTimeout` from the global when it arms the countdown, so the
    // fake clock must already be there, where `vi.getTimerCount()` sees it.
    beforeEach(() => {
        vi.useFakeTimers({toFake: ['setTimeout', 'clearTimeout']});
    });

    // Inner hooks run first. A case that failed before its own unmount leaves the line mounted: unmount it while the
    // clock that issued its handles is still installed, then restore the real one — whatever is left on the fake
    // clock goes with it and can never fire.
    afterEach(() => {
        cleanup();
        vi.useRealTimers();
    });

    /** A page on the LAN, the line mounted and its details closed; `timersBefore` is the fake clock's count then. */
    async function mountOnLan() {
        await primeAt('http://lf.lan/', {clientClass: 'lan', cookieSecure: false});
        const {unmount} = await mountIndicator();
        // Any 0 ms timer the page load queued runs now: a case's own `elapse(0)` cannot take it from the baseline.
        await elapse(0);
        return {root: present('connection-security'), toggle: present('connection-security-toggle'), unmount, timersBefore: vi.getTimerCount()};
    }

    /** The same page, its details opened by a click on the toggle: the instant every countdown below counts from. */
    async function openOnLan() {
        const mounted = await mountOnLan();
        const details = await openDetails();
        return {
            ...mounted,
            details,
            reason: present('connection-security-reason', details, 'the details give the reason'),
            link: present('connection-security-docs-link', details, 'the details link the documentation'),
        };
    }

    /** Moves the fake clock `ms` forward, then lets Svelte apply what the timers changed. */
    async function elapse(ms: number): Promise<void> {
        await vi.advanceTimersByTimeAsync(ms);
        await tick();
    }

    function expectOpen(toggle: HTMLElement, when: string): void {
        expect(toggle.getAttribute('aria-expanded'), `${when}: the toggle still says expanded`).toBe('true');
        expect(screen.queryByTestId('connection-security-details'), `${when}: the details are still drawn`).not.toBeNull();
    }

    function expectClosed(toggle: HTMLElement, when: string): void {
        expect(toggle.getAttribute('aria-expanded'), `${when}: the toggle says collapsed`).toBe('false');
        expect(screen.queryByTestId('connection-security-details'), `${when}: the details are gone`).toBeNull();
    }

    /** Open `ms - 1` milliseconds after `since`, closed at `ms`. */
    async function expectClosesIn(toggle: HTMLElement, ms: number, since: string): Promise<void> {
        await elapse(ms - 1);
        expectOpen(toggle, `${ms - 1} ms after ${since}`);
        await elapse(1);
        expectClosed(toggle, `${ms} ms after ${since}, the details have closed by themselves`);
    }

    /** Twice the countdown goes by and the details are still open: something holds them. */
    async function expectHeld(toggle: HTMLElement, by: string): Promise<void> {
        await elapse(HELD_MS);
        expectOpen(toggle, `${by}, ${HELD_MS} ms later`);
    }

    /** What holds the focus: its test id, or its tag — a failure reads `body`, not a dump of the page. */
    function focusHolder(): string {
        const active = document.activeElement;
        return active === null ? 'nothing' : (active.getAttribute('data-testid') ?? active.tagName.toLowerCase());
    }

    /** A real focus (jsdom fires focus and focusin), asserted taken. */
    async function focusOn(element: HTMLElement, message: string): Promise<void> {
        element.focus();
        await tick();
        expect(focusHolder(), message).toBe(element.getAttribute('data-testid'));
    }

    /** A real blur (jsdom fires blur and focusout): the focus falls back to the page. */
    async function blurFrom(element: HTMLElement, message: string): Promise<void> {
        element.blur();
        await tick();
        expect(focusHolder(), message).toBe('body');
    }

    /** A focusable control outside the indicator, for the focus to go to; the case removes it in a `finally`. */
    function controlOutside(): HTMLButtonElement {
        const control = document.createElement('button');
        control.type = 'button';
        control.dataset.testid = 'outside-the-indicator';
        document.body.append(control);
        return control;
    }

    describe('a click on the reason', () => {
        it('the reason is a button, type="button", in the details', async () => {
            const {reason} = await openOnLan();

            expect(reason.tagName, 'the reason is a button: something to click, and the keyboard reaches it').toBe('BUTTON');
            expect(reason, 'a plain button, never a submit').toHaveAttribute('type', 'button');
        });

        it('a click on the reason closes the details', async () => {
            const {toggle, reason} = await openOnLan();

            await fireEvent.click(reason);

            expectClosed(toggle, 'a click on the reason');
        });

        it('a reason that held the focus hands it back to the toggle as the details close', async () => {
            const {toggle, reason} = await openOnLan();
            await focusOn(reason, 'the reason is a button: the keyboard reaches it');

            await fireEvent.click(reason);
            await tick();

            expectClosed(toggle, 'a click on the focused reason');
            expect(focusHolder(), 'the focus goes back to the toggle, not to the page: a keyboard user keeps their place').toBe('connection-security-toggle');
        });

        it('a click on the admin warning leaves the details open; the reason, beside it, closes them', async () => {
            await signInAs(true);
            await primeAt('https://lf.example/', {clientClass: 'public', cookieSecure: false});
            await mountIndicator();
            const details = await openDetails();
            const toggle = present('connection-security-toggle');
            const warning = present('connection-security-admin-warning', details, 'premise: a superuser with the cookie warning reads the admin line');

            await fireEvent.click(warning);
            expectOpen(toggle, 'a click on the admin warning');

            await fireEvent.click(present('connection-security-reason', details, 'the details still give the reason'));
            expectClosed(toggle, 'a click on the reason');
        });

        it('a click on the docs link leaves the details open; the reason closes them', async () => {
            const {toggle, details, link} = await openOnLan();
            // jsdom would follow the link, and report navigation as not implemented: the click is the subject here,
            // not where it leads.
            const stayOnThePage = (event: Event) => event.preventDefault();
            link.addEventListener('click', stayOnThePage, {capture: true});
            try {
                await fireEvent.click(link);
            } finally {
                link.removeEventListener('click', stayOnThePage, {capture: true});
            }
            expectOpen(toggle, 'a click on the docs link');

            await fireEvent.click(present('connection-security-reason', details, 'the details still give the reason'));
            expectClosed(toggle, 'a click on the reason');
        });
    });

    describe('30 s untouched', () => {
        it('open and untouched, the details close by themselves at 30 s, not a millisecond before', async () => {
            const {toggle} = await openOnLan();

            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'opening');
        });

        it('closing by hand cancels the countdown: reopened, the details get a whole 30 s', async () => {
            const {toggle} = await openOnLan();
            await elapse(20_000);
            expectOpen(toggle, '20 s after opening');
            await fireEvent.click(toggle);
            expectClosed(toggle, 'a second click on the toggle');

            await openDetails();

            // A countdown that survived the close would run out 10 s after the reopening.
            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'reopening');
        });
    });

    describe('what holds the countdown (choice (b))', () => {
        it('the pointer on the indicator holds them, already there when they open; once it leaves, a whole 30 s', async () => {
            const {root, toggle} = await mountOnLan();
            await fireEvent.pointerEnter(root);
            await openDetails();

            await expectHeld(toggle, 'the pointer is on the indicator');

            await fireEvent.pointerLeave(root);
            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'the pointer left the indicator');
        });

        it('a pointer that comes in at 20 s and leaves restarts the countdown from 30 s, not from the 10 s that were left', async () => {
            const {root, toggle} = await openOnLan();
            await elapse(20_000);
            expectOpen(toggle, '20 s after opening');
            await fireEvent.pointerEnter(root);
            await expectHeld(toggle, 'the pointer came in at 20 s');

            await fireEvent.pointerLeave(root);

            await elapse(10_000);
            expectOpen(toggle, '10 s after the pointer left, what was left when it came in');
            await elapse(AUTO_CLOSE_MS - 10_000 - 1);
            expectOpen(toggle, `${AUTO_CLOSE_MS - 1} ms after the pointer left`);
            await elapse(1);
            expectClosed(toggle, `${AUTO_CLOSE_MS} ms after the pointer left, the details have closed by themselves`);
        });

        it('the focus on the docs link holds them; once it leaves the indicator, the countdown restarts from 30 s, not from what was left', async () => {
            const {toggle, link} = await openOnLan();
            await elapse(20_000);
            expectOpen(toggle, '20 s after opening');
            await focusOn(link, 'premise: the docs link takes the focus');
            await expectHeld(toggle, 'the focus came to the docs link at 20 s');

            const outside = controlOutside();
            try {
                await focusOn(outside, 'premise: the focus moves to a control outside the indicator');

                await elapse(10_000);
                expectOpen(toggle, '10 s after the focus left, what was left when it came in');
                await elapse(AUTO_CLOSE_MS - 10_000 - 1);
                expectOpen(toggle, `${AUTO_CLOSE_MS - 1} ms after the focus left`);
                await elapse(1);
                expectClosed(toggle, `${AUTO_CLOSE_MS} ms after the focus left, the details have closed by themselves`);
            } finally {
                outside.remove();
            }
        });

        it('the focus on the reason holds them, and still does as it moves on to the docs link; a blur, and a whole 30 s', async () => {
            const {toggle, reason, link} = await openOnLan();
            await focusOn(reason, 'the reason is a button: the keyboard reaches it');
            await expectHeld(toggle, 'the focus is on the reason');

            await focusOn(link, 'premise: the focus moves on to the docs link');
            await expectHeld(toggle, 'the focus moved from the reason to the docs link, inside the details');

            await blurFrom(link, 'premise: the focus left the details');
            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'the focus left the details');
        });

        it('the focus on the toggle does not hold them: they close at 30 s', async () => {
            const {toggle} = await openOnLan();
            // Where a click leaves it in Chrome, and in Firefox on Windows and Linux: held there, they would never close.
            await focusOn(toggle, 'premise: the toggle takes the focus');

            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'opening, the focus on the toggle');
        });

        it('the pointer still on the indicator holds them after the focus has left the details', async () => {
            const {root, toggle, link} = await openOnLan();
            await fireEvent.pointerEnter(root);
            await focusOn(link, 'premise: the docs link takes the focus');
            await blurFrom(link, 'premise: the focus left the details');

            await expectHeld(toggle, 'the focus left, the pointer is still on the indicator');

            await fireEvent.pointerLeave(root);
            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'the pointer left too');
        });

        it('the focus still in the details holds them after the pointer has left', async () => {
            const {root, toggle, link} = await openOnLan();
            await focusOn(link, 'premise: the docs link takes the focus');
            await fireEvent.pointerEnter(root);
            await fireEvent.pointerLeave(root);

            await expectHeld(toggle, 'the pointer left, the focus is still on the docs link');

            await blurFrom(link, 'premise: the focus left the details');
            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'the focus left too');
        });

        it('closed by hand with the focus on the docs link, they hold nothing over: reopened, they close at 30 s', async () => {
            const {toggle, link} = await openOnLan();
            await focusOn(link, 'premise: the docs link takes the focus');
            // The link leaves the page with the details, and jsdom fires no focusout for that — nor does every
            // browser: whatever held the countdown must not outlive the close.
            await fireEvent.click(toggle);
            expectClosed(toggle, 'a click on the toggle');

            await openDetails();

            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'reopening, the focus that was on the docs link gone with the old details');
        });

        it('closed by the reason that held the focus, they hold nothing over: reopened, they close at 30 s', async () => {
            const {toggle, reason} = await openOnLan();
            await focusOn(reason, 'the reason is a button: the keyboard reaches it');
            await fireEvent.click(reason);
            await tick();
            expectClosed(toggle, 'a click on the focused reason');

            await openDetails();

            await expectClosesIn(toggle, AUTO_CLOSE_MS, 'reopening from the toggle');
        });
    });

    /**
     * The count is the fake clock's, its baseline read before the details open, never assumed 0. The pointer case is
     * there for the teardown that reads a `$state` handle as it was before its last write (devWiki
     * `svelte5-teardown-reads-stale-state-timers`, measured in `Tooltip.test.ts`): leaving the indicator re-arms the
     * countdown and re-renders nothing, so nothing between the restart and the unmount flushes that record away, and
     * such a teardown would clear the handle the restart replaced, not the live one. Nothing between the two re-renders
     * the line, on purpose.
     */
    describe('no countdown outlives the details', () => {
        it('unmounted with the details open, the line leaves no timer behind', async () => {
            const {unmount, timersBefore} = await openOnLan();
            expect(vi.getTimerCount(), 'positive control: opening the details put the 30 s countdown on the clock').toBeGreaterThan(timersBefore);

            unmount();

            expect(vi.getTimerCount(), 'unmounted, the line left no timer pending').toBe(timersBefore);
        });

        it('unmounted after the pointer restarted the countdown, none either', async () => {
            const {root, toggle, unmount, timersBefore} = await openOnLan();
            await fireEvent.pointerEnter(root);
            await fireEvent.pointerLeave(root);
            expectOpen(toggle, 'premise: the pointer came and went');
            expect(vi.getTimerCount(), 'positive control: the pointer leaving re-armed the countdown').toBeGreaterThan(timersBefore);

            unmount();

            expect(vi.getTimerCount(), 'unmounted, the line left no timer pending').toBe(timersBefore);
        });

        const CLOSERS: Array<[string, string]> = [
            ['the toggle', 'connection-security-toggle'],
            ['the reason', 'connection-security-reason'],
        ];

        it.each(CLOSERS)('closed by a click on %s, the details leave no timer behind', async (closer, testId) => {
            const {toggle, timersBefore} = await openOnLan();
            expect(vi.getTimerCount(), 'positive control: opening the details put the 30 s countdown on the clock').toBeGreaterThan(timersBefore);

            await fireEvent.click(present(testId));
            expectClosed(toggle, `a click on ${closer}`);
            // A focus move queues jsdom's own `selectionchange`, a 0 ms timer no component can cancel: let it fire first.
            await elapse(0);

            expect(vi.getTimerCount(), `closed by ${closer}, the countdown is cancelled`).toBe(timersBefore);
        });
    });
});

/**
 * N69b — the security-attention dot (N69 point 1; the developer's answers D1 a, D2 a, D3 a). The «1» of the Settings ›
 * Security tab — `securityChecks.attentionCount`, the errors and warnings of `GET /api/v1/security/checks` plus the
 * browser's open-registration warning — is seen by an administrator from anywhere, on this line:
 *   - for an administrator (`$auth.user?.is_superuser === true`) the line calls `securityChecks.ensureLoaded()`, once,
 *     from an effect; for anybody else never: no request to the checks;
 *   - `attention` is the store's `attentionCount` for an administrator, 0 for anybody else; the severity is the store's
 *     `attentionSeverity` while `attention > 0`, none otherwise;
 *   - the root `connection-security` publishes `data-security-attention` (the number) and `data-security-severity`
 *     (`error` | `warning` | `none`);
 *   - the dot, `connection-security-attention-dot`: inside the toggle, `aria-hidden="true"`, `data-severity` the severity,
 *     only while `attention > 0`, with the sidebar expanded and collapsed;
 *   - the toggle's accessible name while `attention > 0`: «‹level label› — ‹attention text›», expanded and collapsed, and
 *     the `title` the same when collapsed; the attention text is `$_('connectionSecurity.attention', {values: {count}})`.
 *     Without attention, today's: the level label as `aria-label` and `title` when collapsed, neither when expanded;
 *   - in the details, after the reason: `connection-security-attention-link`, an `<a href="/settings?tab=security">` whose
 *     text is the attention text, only while `attention > 0`; a click on it closes the details.
 *
 * The doubles. The checks' store is the fake at the top of the file: a case lands its answer by hand (`storeAnswers`),
 * and `ensureLoaded`/`reload` are spies, so «asks» and «never asks» are counted calls; the generated client's own
 * operation is a spy too, for a line that would go around the store. The attention key is given the test's own ICU
 * plural (`addMessages`, English is the cases' locale), so a name or a link reads `⟦key·branch·count⟧`: the key, the
 * plural branch and the count passed, never a translation — a call without `values` would print the raw ICU message. The
 * level label is what the line's own `$_` gives for the level's key, never written here.
 */
describe('ConnectionSecurityIndicator — the security-attention dot (N69b)', () => {
    const ATTENTION_KEY = 'connectionSecurity.attention';
    const ATTENTION_MESSAGE = `{count, plural, one {⟦${ATTENTION_KEY}·one·#⟧} other {⟦${ATTENTION_KEY}·other·#⟧}}`;
    /** Between the level label and the attention text, as the header's menu label already writes «— insecure». */
    const SEPARATOR = ' — ';
    const LAN_PAGE = 'http://lf.lan/';
    const LAN: ServerView = {clientClass: 'lan', cookieSecure: false};
    const SECURITY_TAB = '/settings?tab=security';

    const finding = (id: string, severity: FakeFinding['severity']): FakeFinding => ({id, severity, messageKey: `test.${id}`, params: {}, source: 'server'});
    /** Two warnings and an info: 2, warning. */
    const WARNINGS = [finding('platform.jwt_secret', 'warning'), finding('accounts.login_limit', 'warning'), finding('platform.log_level', 'info')];
    /** An error, a warning and an info: 2, error. */
    const WITH_ERROR = [finding('platform.instance_key', 'error'), finding('email.smtp_encryption', 'warning'), finding('email.links', 'info')];
    /** One warning: 1, warning — the singular. */
    const ONE_WARNING = [finding('platform.session_cookie', 'warning')];
    /** Infos only: listed in the tab, counted nowhere. */
    const INFOS_ONLY = [finding('platform.log_level', 'info'), finding('email.links', 'info')];

    /** The attention text for `count`, as the test's own message renders it. */
    function attentionText(count: number): string {
        return `⟦${ATTENTION_KEY}·${count === 1 ? 'one' : 'other'}·${count}⟧`;
    }

    /** The level label, as the line's own `$_` gives it for the level's key. */
    function levelLabel(level: ConnectionLevel): string {
        return get(formatMessage)(`connectionSecurity.level.${level}`);
    }

    /** The checks' answer lands in the store, as `ensureLoaded()` or `reload()` lands it. */
    async function storeAnswers(attention: FakeFinding[]): Promise<void> {
        securityStore.state.attention = attention;
        securityStore.state.answered = true;
        securityStore.state.status = 'ready';
        flushSync();
        await tick();
    }

    /** The root's two N69b attributes, as strings. */
    function attentionRoot(): {attention: string | null; severity: string | null} {
        const root = present('connection-security');
        return {attention: root.getAttribute('data-security-attention'), severity: root.getAttribute('data-security-severity')};
    }

    /** A click on a link, kept on the page: jsdom would follow it and report navigation as not implemented. */
    async function clickWithoutNavigating(link: HTMLElement): Promise<void> {
        const stayOnThePage = (event: Event) => event.preventDefault();
        link.addEventListener('click', stayOnThePage, {capture: true});
        try {
            await fireEvent.click(link);
        } finally {
            link.removeEventListener('click', stayOnThePage, {capture: true});
        }
    }

    /** An administrator or a member on a LAN page, the store already holding `attention` when the line mounts. */
    async function pageWith(isSuperuser: boolean, attention: FakeFinding[] | null): Promise<void> {
        await signInAs(isSuperuser);
        await primeAt(LAN_PAGE, LAN);
        expect(get(connectionSecurity).level, 'premise: a LAN page, the level local').toBe('local');
        if (attention) await storeAnswers(attention);
    }

    beforeAll(() => {
        addMessages('en', {[ATTENTION_KEY]: ATTENTION_MESSAGE});
        expect(get(formatMessage)(ATTENTION_KEY, {values: {count: 2}}), 'premise: the attention key renders the test’s own marker').toBe(attentionText(2));
    });

    // red until N69b
    it('an administrator with warnings: the root says 2 and warning, the dot in the toggle, the count in the name, and the link to Settings › Security, which closes the details', async () => {
        await pageWith(true, WARNINGS);
        expect([securityStore.store.attentionCount, securityStore.store.attentionSeverity], 'premise: the store holds two warnings').toEqual([2, 'warning']);

        await mountIndicator();

        expect(attentionRoot(), 'the root publishes what the administrator has to look at').toEqual({attention: '2', severity: 'warning'});
        const toggle = present('connection-security-toggle');
        const dot = present('connection-security-attention-dot', toggle, 'the dot sits inside the toggle, on its icon');
        expect(dot, 'the dot is decoration: the count is in the name').toHaveAttribute('aria-hidden', 'true');
        expect(dot).toHaveAttribute('data-severity', 'warning');
        expect(toggle.getAttribute('aria-label'), 'expanded too, the count is in the accessible name: colour alone is not enough').toBe(`${levelLabel('local')}${SEPARATOR}${attentionText(2)}`);

        const details = await openDetails();
        const reason = present('connection-security-reason', details, 'the details give the reason');
        const link = present('connection-security-attention-link', details, 'the details link the Security tab');
        expect(link.tagName, 'the attention link is an anchor').toBe('A');
        expect(link, 'to Settings › Security').toHaveAttribute('href', SECURITY_TAB);
        expect(link.textContent?.replace(/\s+/g, ' ').trim(), 'its text is the attention text').toBe(attentionText(2));
        expect(reason.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING, 'the link comes after the reason').not.toBe(0);
        present('connection-security-docs-link', details, 'the rest of the details is unchanged: the docs link is still there');

        await clickWithoutNavigating(link);

        expect(toggle.getAttribute('aria-expanded'), 'a click on the link closes the details').toBe('false');
        expect(screen.queryByTestId('connection-security-details'), 'the details are gone').toBeNull();
    });

    // red until N69b
    it('an administrator with an error among the warnings: the severity is error, on the root and on the dot', async () => {
        await pageWith(true, WITH_ERROR);
        expect([securityStore.store.attentionCount, securityStore.store.attentionSeverity], 'premise: an error beats the warning').toEqual([2, 'error']);

        await mountIndicator();

        expect(attentionRoot()).toEqual({attention: '2', severity: 'error'});
        const dot = present('connection-security-attention-dot', present('connection-security-toggle'), 'the dot sits inside the toggle');
        expect(dot).toHaveAttribute('data-severity', 'error');
        expect(dot).toHaveAttribute('aria-hidden', 'true');
        const details = await openDetails();
        expect(present('connection-security-attention-link', details, 'an error is linked like a warning'), 'to Settings › Security').toHaveAttribute('href', SECURITY_TAB);
    });

    // red until N69b
    it('an administrator with nothing to look at (infos only): the root says 0 and none, no dot, no link, and the name as today, expanded and collapsed', async () => {
        await pageWith(true, INFOS_ONLY);
        expect(securityStore.store.attentionCount, 'premise: infos are listed, never counted').toBe(0);

        const {rerender} = await mountIndicator();

        expect(attentionRoot(), 'nothing to look at').toEqual({attention: '0', severity: 'none'});
        const toggle = present('connection-security-toggle', document.body, 'presence barrier: the line is drawn');
        expect(within(toggle).queryByTestId('connection-security-attention-dot'), 'no attention, no dot').toBeNull();
        expect([toggle.getAttribute('aria-label'), toggle.getAttribute('title')], 'expanded, as today: the visible label names it').toEqual([null, null]);
        const details = await openDetails();
        present('connection-security-reason', details, 'presence barrier: the details are drawn');
        expect(within(details).queryByTestId('connection-security-attention-link'), 'no attention, no link').toBeNull();

        await rerender({collapsed: true});

        const collapsed = present('connection-security-toggle');
        expect([collapsed.getAttribute('aria-label'), collapsed.getAttribute('title')], 'collapsed, as today: the level label alone').toEqual([levelLabel('local'), levelLabel('local')]);
        expect(within(collapsed).queryByTestId('connection-security-attention-dot'), 'collapsed, no dot either').toBeNull();
    });

    // red until N69b
    it('a member, the store holding an administrator’s warnings: the root says 0, no dot, no link, the name as today — and the line never asks the checks', async () => {
        await pageWith(false, WARNINGS);
        expect(securityStore.store.attentionCount, 'premise: the store holds two warnings, left by an administrator earlier in this runtime').toBe(2);

        await mountIndicator();

        expect(attentionRoot(), 'only an administrator is shown the checks').toEqual({attention: '0', severity: 'none'});
        const toggle = present('connection-security-toggle', document.body, 'presence barrier: the line is drawn');
        expect(within(toggle).queryByTestId('connection-security-attention-dot'), 'a member gets no dot').toBeNull();
        expect(toggle.getAttribute('aria-label'), 'expanded, as today: no aria-label').toBeNull();
        const details = await openDetails();
        present('connection-security-reason', details, 'presence barrier: the details are drawn');
        expect(within(details).queryByTestId('connection-security-attention-link'), 'a member gets no link').toBeNull();
        expect(securityStore.ensureLoaded, 'a member’s line never asks the checks').not.toHaveBeenCalled();
        expect(securityStore.reload, 'nor forces a read').not.toHaveBeenCalled();
        expect(api.securityChecks, 'no request to GET /api/v1/security/checks').not.toHaveBeenCalled();
    });

    // red until N69b
    it('collapsed: the dot is still on the icon, and the count is in the name and in the title — one warning, the singular', async () => {
        await pageWith(true, ONE_WARNING);
        const onExpand = vi.fn();

        await mountIndicator({collapsed: true, onExpand});

        expect(attentionRoot()).toEqual({attention: '1', severity: 'warning'});
        const toggle = present('connection-security-toggle');
        expect(screen.queryByTestId('connection-security-label'), 'premise: collapsed, the line is its icon').toBeNull();
        expect(present('connection-security-attention-dot', toggle, 'collapsed, the dot is still drawn'), 'the dot’s severity').toHaveAttribute('data-severity', 'warning');
        const name = `${levelLabel('local')}${SEPARATOR}${attentionText(1)}`;
        expect(toggle.getAttribute('aria-label'), 'the count is in the accessible name').toBe(name);
        expect(toggle.getAttribute('title'), 'and in the title, the only text a pointer gets').toBe(name);
        expect(onExpand, 'premise: nothing was clicked').not.toHaveBeenCalled();
    });

    // red until N69b
    it('an administrator: the line asks the store once, from its own mount, and follows the answer when it lands', async () => {
        await pageWith(true, null);
        expect(securityStore.state.status, 'premise: nothing has asked the checks on this page load').toBe('idle');

        await mountIndicator();

        expect(securityStore.ensureLoaded, 'an administrator’s line asks the checks').toHaveBeenCalledTimes(1);
        expect(securityStore.state.status, 'premise: the store started its request').toBe('loading');
        expect(attentionRoot(), 'until the answer lands, nothing to show').toEqual({attention: '0', severity: 'none'});
        expect(screen.queryByTestId('connection-security-attention-dot'), 'no dot before the answer').toBeNull();

        await storeAnswers(WARNINGS);

        expect(attentionRoot(), 'the line follows the answer').toEqual({attention: '2', severity: 'warning'});
        expect(present('connection-security-attention-dot', present('connection-security-toggle'), 'the dot appears with the answer')).toHaveAttribute('data-severity', 'warning');
        expect(securityStore.ensureLoaded, 'once: the store changing under the line does not make it ask again').toHaveBeenCalledTimes(1);
        expect(securityStore.reload, 'the line never forces a read').not.toHaveBeenCalled();
        expect(api.securityChecks, 'and never goes around the store').not.toHaveBeenCalled();
    });
});
