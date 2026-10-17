// @vitest-environment jsdom
/**
 * /setup — the page the setup link of the initial administrator opens (accounts lot A7b, F02).
 *
 * On a hosted instance (F02) the first administrator is created without a password; its holder receives a one-time
 * link, `/setup#token=…` (A7a: `./dev.py user setup-link`). The token rides in the URL fragment, which a browser never
 * sends to the server, so it stays out of the access logs. Same pattern as `/reset-password`
 * (`src/routes/reset-password/page.test.ts`), with `SetupCard` for the form, its own line for a dead link, and a
 * different ending: the setup signs the administrator in.
 *
 * The contract (plan A7b, C1 and C3, approved 2026-10-16):
 *   - on mount the page reads the token from the fragment with `takeLinkToken(new URL(window.location.href), …)`,
 *     which takes it out of the address bar through `replaceState` of `$app/navigation`, handing it the bare path
 *     `/setup`;
 *   - no token — none in the fragment, an empty one, or one in the query, which is never read: `LinkStatusCard`
 *     `missing`, and no inspection is asked;
 *   - otherwise `POST /auth/tokens/inspect {token, purpose: 'admin_setup'}` — `checking` meanwhile; a status other than
 *     `valid` → `LinkStatusCard` with that status; a failed check → `error`, whose retry asks again;
 *   - for every dead link (missing, expired, consumed, revoked, unknown) the card's line is `auth.setup.newLinkHint`,
 *     passed as `hintKey`, never `auth.link.askAdmin`: no administrator exists yet to ask — a new link comes from the
 *     hosting provider or from `./dev.py user setup-link`;
 *   - a valid link → `SetupCard` with the token and `username` (the account the server names). The registration mode
 *     has nothing to say here: setting up the administrator is not a registration;
 *   - `ondone` (the setup answered like the login: the session cookie is set) → `auth.checkAuth()`, so the store knows
 *     who signed in, then `goto('/dashboard')`; no flash for the login page, which the administrator never passes
 *     through. `oninvalid` (the link died between the check and the submit) → `LinkStatusCard` `unknown`. A blocked
 *     instance (401, decision P16 d) stays on the card, which says so: nobody is signed in, the page goes nowhere;
 *   - the root `setup-page` (the `AuthPageFrame`), and `<meta name="referrer" content="no-referrer">`;
 *   - `hashchange` on `window`: a link pasted into a tab already on the page changes only the fragment, so nothing
 *     reloads. The page reads the fragment again: a token replaces the old one and goes through the flow of the mount
 *     (`replaceState` to the bare path, the inspection); no token changes nothing. The listener goes with the page;
 *   - `instanceConfig.load()` on mount, fire-and-forget (decision 37): the password rules come from the server, and a
 *     slow or failing request neither delays nor blocks the form.
 *
 * What runs for real: the page, `linkToken.ts`, `addressBar.ts`, `AuthPageFrame`, `LinkStatusCard` and `SetupCard`.
 * What is replaced: the generated client (the inspection and the setup, answered per test — so the global response
 * interceptor of `zodios-client.ts` is out of this file's reach), the instance configuration (a fake of the real
 * store's shape: it says registration is disabled, which must change nothing), the auth store (a fake of its shape
 * whose `checkAuth` does what the real one does after the setup: the store then holds the administrator),
 * `authFlash.ts` (spies), `$app/navigation` (`goto` and `replaceState` spies), and the frame's decoration (no-op
 * components). `$lib/i18n` keeps its real exports with the identity as translator, so a message renders as its key;
 * the values of an interpolated message are written out after it, so the username shows however the card draws it.
 *
 * No timers: every wait is a `waitFor` on a state, every negative assertion follows a positive barrier.
 *
 * Written red-first, before `routes/setup/+page.svelte` exists: every case fails on the import until it does.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const {writable} = await import('svelte/store');
    const DISABLED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'disabled', registration_locked: false}};
    /** The auth store's state, as `AuthState`: signed out until the page's `checkAuth()` reads the new session. */
    type SessionState = {user: {id: number; username: string; email: string; is_active: boolean; is_superuser: boolean; created_at: string} | null; isLoading: boolean; error: null; isInitialized: boolean};
    const SIGNED_OUT: SessionState = {user: null, isLoading: false, error: null, isInitialized: true};
    return {
        instance: reactiveBox<{config: InstanceConfig}>({config: DISABLED}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
        inspect: vi.fn().mockName('zodiosApi.inspect_link_token_api_v1_auth_tokens_inspect_post'),
        setup: vi.fn().mockName('zodiosApi.setup_admin_api_v1_auth_setup_post'),
        SIGNED_OUT,
        session: writable<SessionState>(SIGNED_OUT),
        checkAuth: vi.fn<() => Promise<string>>().mockName('auth.checkAuth'),
        goto: vi.fn((..._args: unknown[]) => Promise.resolve()).mockName('goto'),
        replaceState: vi.fn((..._args: unknown[]) => {}).mockName('replaceState'),
        setAuthFlash: vi.fn((_message: string) => {}).mockName('setAuthFlash'),
        takeAuthFlash: vi.fn(() => '').mockName('takeAuthFlash'),
        noopComponent: () => {},
    };
});

vi.mock('$app/navigation', () => ({
    goto: mocks.goto,
    replaceState: mocks.replaceState,
    pushState: vi.fn(),
    invalidate: vi.fn(() => Promise.resolve()),
    invalidateAll: vi.fn(() => Promise.resolve()),
    preloadCode: vi.fn(() => Promise.resolve()),
    preloadData: vi.fn(() => Promise.resolve()),
    afterNavigate: vi.fn(),
    beforeNavigate: vi.fn(),
    onNavigate: vi.fn(),
}));
vi.mock('$lib/api', () => ({
    zodiosApi: {
        inspect_link_token_api_v1_auth_tokens_inspect_post: mocks.inspect,
        setup_admin_api_v1_auth_setup_post: mocks.setup,
    },
}));
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}},
    instanceConfig: {
        get config() {
            return mocks.instance.config;
        },
        get loaded() {
            return true;
        },
        get failed() {
            return false;
        },
        load: mocks.instanceLoad,
    },
}));
// The auth store, with the real one's exports: whatever the page reads of it, the session follows `checkAuth`.
vi.mock('$lib/stores/app/auth', async () => {
    const {derived, get} = await import('svelte/store');
    const session = mocks.session;
    return {
        auth: {
            subscribe: session.subscribe,
            checkAuth: mocks.checkAuth,
            login: vi.fn(() => Promise.resolve(false)),
            logout: vi.fn(() => Promise.resolve()),
            clearError: vi.fn(),
            reset: vi.fn(),
        },
        currentUser: derived(session, ($session) => $session.user),
        isAuthenticated: derived(session, ($session) => $session.user !== null),
        isAuthLoading: derived(session, ($session) => $session.isLoading),
        authError: derived(session, ($session) => $session.error),
        isAuthInitialized: derived(session, ($session) => $session.isInitialized),
        getAuthState: () => get(session),
        isSignOutRequested: () => false,
    };
});
vi.mock('$lib/features/auth/authFlash', () => ({setAuthFlash: mocks.setAuthFlash, takeAuthFlash: mocks.takeAuthFlash}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    // The identity: a message renders as its key, with the values of an interpolated one written out after it.
    const identity = readable((key: string, options?: {values?: Record<string, unknown>}) => (options?.values ? `${key} ${Object.values(options.values).join(' ')}` : key));
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});
// The frame's decoration: each reaches for stores, localStorage or the document, and none is the subject.
vi.mock('$lib/components/ui/ThemeToggle.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/LanguageSelector.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/HelpMenu.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/ui/AnimatedBackground.svelte', () => ({default: mocks.noopComponent}));

import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import SetupPage from './+page.svelte';

const TOKEN = 'setup-Ab3_xYz09';
/** The account the link sets up: a value no message key contains. */
const USERNAME = 'carla.rossi';
/** Satisfies all five password rules. */
const GOOD_PASSWORD = 'Str0ng!pass';
/** The line of a dead setup link: no administrator exists yet to ask for a new one. */
const SETUP_HINT = 'auth.setup.newLinkHint';
/** The line of the other link pages, which has no place here. */
const ASK_ADMIN = 'auth.link.askAdmin';

/** What `POST /auth/tokens/inspect` answers for a valid setup link; `extra` adds or overrides fields. */
function validSetupLink(extra: Record<string, unknown> = {}) {
    return {status: 'valid', purpose: 'admin_setup', expires_at: '2026-10-17T08:00:00Z', username: USERNAME, ...extra};
}

/** The administrator the setup signed in: the user of the login's answer, and what the store holds afterwards. */
const ADMIN = {id: 1, username: USERNAME, email: 'carla@example.com', is_active: true, is_superuser: true, created_at: '2026-10-16T18:00:00Z'};
/** What `POST /auth/setup` answers on success: the login's answer, the session cookie riding with it. */
const SIGNED_IN = {user: ADMIN, user_settings: null, message: 'Setup complete', show_donation_popup: false};

/** A promise this test settles by hand, so "in flight" is a state it controls. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** Puts `path` in jsdom's address bar, as the link would. */
function openAt(path: string): void {
    window.history.replaceState(null, '', path);
}

/**
 * What the browser does when only the fragment of the address changes — a link to this page pasted into the tab, an
 * in-page anchor: no reload; the address takes the new fragment and `hashchange` fires on `window`. jsdom fires nothing
 * for a `history.replaceState`, so the test does both halves, with the two URLs a browser puts in the event.
 */
async function changeFragment(path: string): Promise<void> {
    const oldURL = window.location.href;
    window.history.replaceState(null, '', path);
    await fireEvent(window, new HashChangeEvent('hashchange', {oldURL, newURL: window.location.href}));
}

const pageRoot = () => screen.getByTestId('setup-page');
const linkStatus = () => within(pageRoot()).queryByTestId('link-status');
const setupCard = () => within(pageRoot()).queryByTestId('setup-card');
/** The line under a dead link's message, `''` when the page draws none. */
const hintShown = () => within(pageRoot()).queryByTestId('link-status-hint')?.textContent?.trim() ?? '';

/** Waits for the page to show a `LinkStatusCard` with this status. */
async function expectStatus(status: string): Promise<void> {
    await waitFor(() => expect(linkStatus(), `the page shows LinkStatusCard ${status}`).toHaveAttribute('data-status', status));
}

/** Waits for the setup form, inside the page. */
async function formShown(): Promise<HTMLElement> {
    await waitFor(() => expect(setupCard(), 'the page shows the setup form').not.toBeNull());
    return setupCard()!;
}

/** Types a good password twice and submits. */
async function chooseAdminPassword(): Promise<void> {
    await fireEvent.input(screen.getByTestId('setup-new'), {target: {value: GOOD_PASSWORD}});
    await fireEvent.input(screen.getByTestId('setup-confirm'), {target: {value: GOOD_PASSWORD}});
    await fireEvent.click(screen.getByTestId('setup-submit'));
}

/** An axios-shaped refusal carrying `response.status` and `response.data.detail`. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {
        isAxiosError: true,
        response: {status, data: {detail}},
    });
}

beforeEach(() => {
    // Negative assertions below would pass vacuously in an environment where effects (onMount) never run.
    assertEffectsRun();
    for (const spy of [mocks.goto, mocks.replaceState, mocks.setAuthFlash, mocks.takeAuthFlash]) spy.mockClear();
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockResolvedValue(undefined);
    mocks.inspect.mockReset();
    mocks.inspect.mockResolvedValue(validSetupLink());
    mocks.setup.mockReset();
    mocks.setup.mockResolvedValue(SIGNED_IN);
    mocks.session.set(mocks.SIGNED_OUT);
    mocks.checkAuth.mockReset();
    // What the real `checkAuth()` does once the setup has set the session cookie: `GET /auth/me` answers the
    // administrator, and the store holds it.
    mocks.checkAuth.mockImplementation(async () => {
        mocks.session.set({user: ADMIN, isLoading: false, error: null, isInitialized: true});
        return 'authenticated';
    });
});

afterEach(() => {
    cleanup();
    openAt('/');
});

describe('/setup — the token, read once', () => {
    // red until A7b
    it('reads the token from the fragment, takes it out of the address bar, and asks what the setup link is worth', async () => {
        const inspection = deferred<unknown>();
        mocks.inspect.mockReturnValue(inspection.promise);
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        await waitFor(() => expect(mocks.inspect).toHaveBeenCalledTimes(1));
        expect(mocks.inspect.mock.calls[0][0], 'the purpose of the setup link').toStrictEqual({token: TOKEN, purpose: 'admin_setup'});
        expect(mocks.replaceState, 'the token leaves the address bar, once').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState.mock.calls[0][0], 'replaced by the bare path: no fragment, no query').toBe('/setup');
        await expectStatus('checking');

        inspection.resolve(validSetupLink());

        await formShown();
        expect(linkStatus()).toBeNull();
    });

    // red until A7b
    it.each([
        ['no token at all', '/setup'],
        ['an empty token', '/setup#token='],
        ['a fragment without a token', '/setup#lang=it'],
        // A token in the query has reached the server's access log, so it is never read.
        ['a token in the query, never read', `/setup?token=${TOKEN}`],
    ])('shows missing for %s, and asks for no inspection', async (_label, path) => {
        openAt(path);

        render(SetupPage);

        await expectStatus('missing');
        expect(mocks.inspect).not.toHaveBeenCalled();
        expect(setupCard()).toBeNull();
    });

    // red until A7b
    it('keeps its token out of the Referer of any link followed from it', () => {
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        expect(document.head.querySelector('meta[name="referrer"]')).toHaveAttribute('content', 'no-referrer');
    });
});

describe('/setup — a link the server does not call valid', () => {
    // red until A7b
    it.each(['expired', 'consumed', 'revoked', 'unknown'])('shows %s, and no form', async (status) => {
        mocks.inspect.mockResolvedValue({status, purpose: 'admin_setup'});
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        await expectStatus(status);
        expect(setupCard()).toBeNull();
    });

    // red until A7b
    it('shows error with a retry when the check failed, and the retry asks again', async () => {
        mocks.inspect.mockRejectedValueOnce(new Error('Network Error')).mockResolvedValueOnce(validSetupLink());
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        await expectStatus('error');
        await fireEvent.click(within(pageRoot()).getByTestId('link-status-retry'));

        await formShown();
        expect(mocks.inspect).toHaveBeenCalledTimes(2);
        expect(mocks.inspect.mock.calls[1][0], 'the same question again').toStrictEqual({token: TOKEN, purpose: 'admin_setup'});
    });
});

describe('/setup — the way to a new link: no administrator exists yet to ask', () => {
    // red until A7b
    it.each(['expired', 'consumed', 'revoked', 'unknown'])('says where a new setup link comes from when the link is %s: auth.setup.newLinkHint, not auth.link.askAdmin', async (status) => {
        mocks.inspect.mockResolvedValue({status, purpose: 'admin_setup'});
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        await expectStatus(status);
        expect(hintShown(), 'the line of link-status-hint').toBe(SETUP_HINT);
        expect(pageRoot().innerHTML, 'there is no administrator to ask').not.toContain(ASK_ADMIN);
    });

    // red until A7b
    it('says the same when the page was opened without a token', async () => {
        openAt('/setup');

        render(SetupPage);

        await expectStatus('missing');
        expect(hintShown()).toBe(SETUP_HINT);
        expect(pageRoot().innerHTML).not.toContain(ASK_ADMIN);
    });
});

describe('/setup — a valid link opens the setup form', () => {
    // red until A7b
    it('names the account the server named', async () => {
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        const form = await formShown();
        expect(within(form).getByTestId('setup-account')).toHaveTextContent(USERNAME);
    });

    // red until A7b
    it('opens it on an instance that disabled registration too: setting up the administrator is not a registration', async () => {
        // The instance configuration of this file says `disabled` throughout.
        expect(mocks.instance.config.accounts.registration_mode, 'premise').toBe('disabled');
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        await formShown();
        expect(linkStatus()).toBeNull();
    });

    // red until A7b
    it('spends the link of the address bar with the chosen password', async () => {
        openAt(`/setup#token=${TOKEN}`);
        render(SetupPage);
        await formShown();

        await chooseAdminPassword();

        await waitFor(() => expect(mocks.setup).toHaveBeenCalledTimes(1));
        expect(mocks.setup.mock.calls[0][0]).toStrictEqual({token: TOKEN, new_password: GOOD_PASSWORD});
    });
});

describe('/setup — after the setup', () => {
    // red until A7b
    it('reads the new session with auth.checkAuth(), then goes to /dashboard, and leaves no flash', async () => {
        openAt(`/setup#token=${TOKEN}`);
        render(SetupPage);
        await formShown();

        await chooseAdminPassword();

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.goto.mock.calls[0][0], 'into the app').toBe('/dashboard');
        expect(mocks.checkAuth, 'the store learns who signed in: the setup set the session cookie').toHaveBeenCalledTimes(1);
        expect(mocks.setup.mock.invocationCallOrder[0], 'the session is read after the setup').toBeLessThan(mocks.checkAuth.mock.invocationCallOrder[0]);
        expect(mocks.checkAuth.mock.invocationCallOrder[0], 'and before the page goes').toBeLessThan(mocks.goto.mock.invocationCallOrder[0]);
        expect(mocks.setAuthFlash, 'no message for the login page: the administrator does not pass through it').not.toHaveBeenCalled();
    });

    // red until A7b
    it('shows the link as unknown when the server says it is no longer valid (TOKEN_INVALID), with the way to a new one', async () => {
        mocks.setup.mockRejectedValue(refusal(400, {error_code: 'TOKEN_INVALID', message: 'This setup link is not valid'}));
        openAt(`/setup#token=${TOKEN}`);
        render(SetupPage);
        await formShown();

        await chooseAdminPassword();

        await expectStatus('unknown');
        expect(setupCard()).toBeNull();
        expect(hintShown()).toBe(SETUP_HINT);
        expect(mocks.checkAuth).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
    });

    // red until A7b
    it('stays on the setup card when the instance is blocked (401): the card says so, nobody is signed in, the page goes nowhere', async () => {
        // P16 (d): `tokens/inspect` answers on a blocked instance, so the link checks valid and the form opens; the setup
        // itself gets the 401 of a caller without a session. The client is mocked here: what the global response
        // interceptor of `zodios-client.ts` does with that 401 in a browser is not observable from this file.
        mocks.setup.mockRejectedValue(refusal(401, 'Not authenticated'));
        openAt(`/setup#token=${TOKEN}`);
        render(SetupPage);
        await formShown();

        await chooseAdminPassword();

        await waitFor(() => expect(within(pageRoot()).queryByTestId('setup-blocked'), 'the message of a blocked instance').not.toBeNull());
        expect(within(pageRoot()).getByTestId('setup-blocked')).toHaveTextContent('auth.setup.blocked');
        expect(setupCard(), 'the card stays').not.toBeNull();
        expect(linkStatus(), 'the link is not the problem').toBeNull();
        expect(mocks.checkAuth).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
    });
});

describe('/setup — a link pasted into the tab already on the page (hashchange)', () => {
    const NEW_TOKEN = 'setup-NEW_0456';

    // red until A7b
    it('reads the new token of the fragment, inspects it, and the page follows the new answer', async () => {
        // The first link has expired; the provider sends a fresh one, pasted into the same tab.
        mocks.inspect.mockImplementation(async (body: {token: string}) => (body.token === NEW_TOKEN ? validSetupLink({username: 'root.admin'}) : {status: 'expired', purpose: 'admin_setup'}));
        openAt(`/setup#token=${TOKEN}`);
        render(SetupPage);
        await expectStatus('expired');
        expect(mocks.replaceState, 'premise: the first token left the address bar').toHaveBeenCalledTimes(1);

        await changeFragment(`/setup#token=${NEW_TOKEN}`);

        const form = await formShown();
        expect(linkStatus()).toBeNull();
        expect(mocks.inspect, 'a second inspection').toHaveBeenCalledTimes(2);
        expect(mocks.inspect.mock.calls[1][0], 'of the new token, for the same purpose').toStrictEqual({token: NEW_TOKEN, purpose: 'admin_setup'});
        expect(mocks.replaceState, 'the new token leaves the address bar too').toHaveBeenCalledTimes(2);
        expect(mocks.replaceState.mock.calls[1][0], 'replaced by the bare path').toBe('/setup');
        expect(within(form).getByTestId('setup-account'), 'the account of the new link').toHaveTextContent('root.admin');

        await chooseAdminPassword();

        await waitFor(() => expect(mocks.setup).toHaveBeenCalledTimes(1));
        expect(mocks.setup.mock.calls[0][0], 'the new token replaced the old one').toStrictEqual({token: NEW_TOKEN, new_password: GOOD_PASSWORD});
    });

    // red until A7b
    it('changes nothing when the new fragment carries no token', async () => {
        openAt(`/setup#token=${TOKEN}`);
        render(SetupPage);
        const form = await formShown();
        await fireEvent.input(within(form).getByTestId('setup-new'), {target: {value: GOOD_PASSWORD}});

        // An in-page anchor: the fragment changes, and there is no token in it. The page reads a fragment and inspects
        // a token synchronously, in the listener: once the event is handled and Svelte has flushed, the quiet below is
        // the page's answer.
        await changeFragment('/setup#main');
        await tick();

        expect(mocks.inspect, 'no new inspection').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState, 'nothing to take out of the address bar').toHaveBeenCalledTimes(1);
        expect(setupCard(), 'the very same form, not a new one').toBe(form);
        expect(within(form).getByTestId('setup-new'), 'with what the user typed in it').toHaveValue(GOOD_PASSWORD);
        expect(linkStatus()).toBeNull();

        // Control: the listener was there all along, so the quiet above is the page's answer — a fragment that does
        // carry a token is read.
        await changeFragment(`/setup#token=${NEW_TOKEN}`);
        await waitFor(() => expect(mocks.inspect).toHaveBeenCalledTimes(2));
        expect(mocks.inspect.mock.calls[1][0]).toStrictEqual({token: NEW_TOKEN, purpose: 'admin_setup'});
    });
});

describe('/setup — the password rules of the server', () => {
    // red until A7b
    it("asks for the instance configuration once the page mounts, so the meter checks the server's rules", async () => {
        // The link opens signed out, outside the (app) layout that loads the configuration: nothing else on this page
        // asks for `accounts.password_rules`.
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        // The barrier: the mount went all the way through (token read, link checked, form drawn), so a missing call is
        // the page's answer, not a call still to come.
        await formShown();
        expect(mocks.instanceLoad, 'GET /system/instance, asked by the page itself').toHaveBeenCalled();
    });

    // red until A7b
    it('does not wait for it: a valid link opens the setup form though the configuration request never answers', async () => {
        // `load()` is fire-and-forget: a slow or failing configuration request must never delay or block the form; the
        // meter keeps the built-in rules until an answer lands.
        mocks.instanceLoad.mockReturnValue(new Promise<void>(() => {}));
        openAt(`/setup#token=${TOKEN}`);

        render(SetupPage);

        await formShown();
        expect(linkStatus()).toBeNull();
    });
});
