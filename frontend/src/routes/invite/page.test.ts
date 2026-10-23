// @vitest-environment jsdom
/**
 * /invite — the page an invitation link opens (accounts lot A5b).
 *
 * An administrator creates an invitation (A5a: `POST /api/v1/users/invites`) and sends its link, `/invite#token=…`:
 * the token rides in the URL fragment, which a browser never sends to the server, so it stays out of uvicorn's access
 * log and of any reverse proxy's. The page is served by the SPA fallback, signed out, and decides between two things:
 * the registration form, for an invitation the server calls valid on an instance that has not closed registration; a
 * `LinkStatusCard` for every other outcome.
 *
 * The contract (plan A5b.1, with the fragment decision of 2026-10-15):
 *   - on mount the page reads the token from the fragment with `takeLinkToken(new URL(window.location.href), …)`,
 *     which takes it out of the address bar through `replaceState` of `$app/navigation`, handing it the bare path
 *     `/invite`;
 *   - no token — none in the fragment, an empty one, or one in the query, which is never read: `LinkStatusCard`
 *     `missing`, and no inspection is asked;
 *   - otherwise `POST /auth/tokens/inspect {token, purpose: 'invite'}` and `instanceConfig.load()`, together — the card
 *     says `checking` until both have answered;
 *   - a status other than `valid` → `LinkStatusCard` with that status; a valid invitation on an instance whose mode is
 *     `disabled` → `closed`; a failed check → `error`, whose retry asks again;
 *   - a valid invitation → `RegisterCard` with `inviteToken`, `initialEmail` (the address the invitation suggests, `''`
 *     when none) and `grantsAdmin` (`false` when the server says nothing);
 *   - the card's `gotoLogin`: with a message (an account was created) → `setAuthFlash(message)`, then `goto('/')`; with
 *     none → `goto('/')`;
 *   - the root `invite-page`, and `<meta name="referrer" content="no-referrer">`, so a link followed from the page does
 *     not carry the token in its Referer;
 *   - `hashchange` on `window`: a link pasted into a tab already on the page changes only the fragment, so nothing
 *     reloads. The page reads the fragment again: a token replaces the old one and goes through the flow of the mount
 *     (`replaceState` to the bare path, the inspection); no token changes nothing. The listener goes with the page.
 *
 * What runs for real: the page, `linkToken.ts`, `AuthPageFrame`, `LinkStatusCard` and `RegisterCard` — the props the
 * page hands over are asserted where the user meets them, in the form. What is replaced: the generated client (the
 * inspection and the registration, answered per test), the instance configuration (a fake with the real store's
 * shape: a `config` getter over `$state`, and a `load` spy), `authFlash.ts` (spies: the order of the flash and the
 * navigation is the subject), `$app/navigation` (`goto` and `replaceState` spies), and the frame's decoration
 * (ThemeToggle, LanguageSelector, HelpMenu, AnimatedBackground: no-op components). `$lib/i18n` keeps its real exports
 * with the identity as translator, so a message renders as its key.
 *
 * The address is jsdom's own: each test sets it with `history.replaceState` before mounting, and puts `/` back after.
 * `assertEffectsRun` guards the negative assertions: `onMount` is an effect, and under the wrong environment "nothing
 * was asked" would pass vacuously.
 *
 * Written red-first, before `routes/invite/+page.svelte` exists: the file fails on the import until it does.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const config = (registration_mode: 'open' | 'invite' | 'disabled'): InstanceConfig => ({profile: 'selfhosted', accounts: {registration_mode, registration_locked: false}});
    return {
        config,
        instance: reactiveBox<{config: InstanceConfig}>({config: config('invite')}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
        inspect: vi.fn().mockName('zodiosApi.inspect_link_token_api_v1_auth_tokens_inspect_post'),
        register: vi.fn().mockName('zodiosApi.register_api_v1_auth_register_post'),
        goto: vi.fn((..._args: unknown[]) => Promise.resolve()).mockName('goto'),
        replaceState: vi.fn((..._args: unknown[]) => {}).mockName('replaceState'),
        setAuthFlash: vi.fn((_message: string, _tone?: 'success' | 'warning') => {}).mockName('setAuthFlash'),
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
        register_api_v1_auth_register_post: mocks.register,
    },
}));
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: mocks.config('open'),
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
vi.mock('$lib/features/auth/authFlash', () => ({setAuthFlash: mocks.setAuthFlash, takeAuthFlash: mocks.takeAuthFlash}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const identity = readable((key: string) => key);
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
import InvitePage from './+page.svelte';

const TOKEN = 'inv-Ab3_xYz09';
/** Satisfies all five password rules. */
const GOOD_PASSWORD = 'Str0ng!pass';

/** What `POST /auth/tokens/inspect` answers for a valid invitation; `extra` adds or overrides fields. */
function validInvitation(extra: Record<string, unknown> = {}) {
    return {status: 'valid', purpose: 'invite', expires_at: '2026-10-22T08:00:00Z', grants_admin: false, email: null, ...extra};
}

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

/**
 * Lets every promise chain already started run to its end, then flushes Svelte. Only for an assertion that something
 * did NOT happen yet, which has no event to wait for: the macrotask boundary drains the whole microtask queue, and no
 * time passes that anything here depends on.
 */
async function settle(): Promise<void> {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    await tick();
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

const pageRoot = () => screen.getByTestId('invite-page');
const linkStatus = () => within(pageRoot()).queryByTestId('link-status');
const registerCard = () => within(pageRoot()).queryByTestId('register-modal');

/** Waits for the page to show a `LinkStatusCard` with this status. */
async function expectStatus(status: string): Promise<void> {
    await waitFor(() => expect(linkStatus(), `the page shows LinkStatusCard ${status}`).toHaveAttribute('data-status', status));
}

/** Waits for the registration form, inside the page. */
async function formShown(): Promise<HTMLElement> {
    await waitFor(() => expect(registerCard(), 'the page shows the registration form').not.toBeNull());
    return registerCard()!;
}

async function fill(testId: string, value: string): Promise<void> {
    await fireEvent.input(screen.getByTestId(testId), {target: {value}});
}

/** Fills the rest of the form (the address is the invitation's) and submits it. */
async function registerAs(form: HTMLElement, username: string): Promise<void> {
    await fill('register-username', username);
    await fill('register-password', GOOD_PASSWORD);
    await fill('register-confirm-password', GOOD_PASSWORD);
    await fireEvent.submit(within(form).getByTestId('register-form'));
}

beforeEach(() => {
    // Negative assertions below would pass vacuously in an environment where effects (onMount) never run.
    assertEffectsRun();
    mocks.instance.config = mocks.config('invite');
    for (const spy of [mocks.goto, mocks.replaceState, mocks.setAuthFlash, mocks.takeAuthFlash]) spy.mockClear();
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockResolvedValue(undefined);
    mocks.inspect.mockReset();
    mocks.inspect.mockResolvedValue(validInvitation());
    mocks.register.mockReset();
    mocks.register.mockResolvedValue({user: {id: 7, username: 'eve'}, message: 'Registration successful'});
});

afterEach(() => {
    cleanup();
    openAt('/');
});

describe('/invite — the token, read once', () => {
    it('reads the token from the fragment, takes it out of the address bar, and asks what it is worth together with the instance configuration', async () => {
        const inspection = deferred<unknown>();
        const configuration = deferred<void>();
        mocks.inspect.mockReturnValue(inspection.promise);
        mocks.instanceLoad.mockReturnValue(configuration.promise);
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        await waitFor(() => expect(mocks.inspect).toHaveBeenCalledTimes(1));
        expect(mocks.inspect.mock.calls[0][0]).toStrictEqual({token: TOKEN, purpose: 'invite'});
        expect(mocks.instanceLoad, 'asked together with the inspection: neither has answered yet').toHaveBeenCalled();
        expect(mocks.replaceState, 'the token leaves the address bar, once').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState.mock.calls[0][0], 'replaced by the bare path: no fragment, no query').toBe('/invite');
        await expectStatus('checking');

        inspection.resolve(validInvitation());
        configuration.resolve();

        await formShown();
        expect(linkStatus()).toBeNull();
    });

    it('waits for the instance configuration too before it chooses', async () => {
        const configuration = deferred<void>();
        mocks.instanceLoad.mockReturnValue(configuration.promise);
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);
        await waitFor(() => expect(mocks.inspect).toHaveBeenCalledTimes(1));
        await settle();

        await expectStatus('checking');
        expect(registerCard(), 'a valid link, but the registration mode is not known yet').toBeNull();

        configuration.resolve();

        await formShown();
    });

    it.each([
        ['no token at all', '/invite'],
        ['an empty token', '/invite#token='],
        ['a fragment without a token', '/invite#lang=it'],
        // The old shape: a token in the query has reached the server's access log, so it is never read.
        ['a token in the query, never read', `/invite?token=${TOKEN}`],
    ])('shows missing for %s, and asks for no inspection', async (_label, path) => {
        openAt(path);

        render(InvitePage);

        await expectStatus('missing');
        expect(mocks.inspect).not.toHaveBeenCalled();
        expect(registerCard()).toBeNull();
    });

    it('keeps its token out of the Referer of any link followed from it', () => {
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        expect(document.head.querySelector('meta[name="referrer"]')).toHaveAttribute('content', 'no-referrer');
    });
});

describe('/invite — a link the server does not call valid', () => {
    it.each(['expired', 'consumed', 'revoked', 'unknown'])('shows %s, and no form', async (status) => {
        mocks.inspect.mockResolvedValue({status, purpose: 'invite'});
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        await expectStatus(status);
        expect(registerCard()).toBeNull();
    });

    it('says the link is dead before it says registration is closed', async () => {
        mocks.inspect.mockResolvedValue({status: 'expired', purpose: 'invite'});
        mocks.instance.config = mocks.config('disabled');
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        await expectStatus('expired');
    });
});

describe('/invite — the instance decides too', () => {
    it('shows closed for a valid invitation on an instance that disabled registration', async () => {
        mocks.instance.config = mocks.config('disabled');
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        await expectStatus('closed');
        expect(registerCard()).toBeNull();
    });

    it('still uses the invitation on an open instance: the form, as an invitation', async () => {
        mocks.instance.config = mocks.config('open');
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        const form = await formShown();
        expect(within(form).getByTestId('register-invite-notice')).toBeInTheDocument();
    });
});

describe('/invite — a check that failed', () => {
    it('shows error with a retry, and the retry asks again', async () => {
        mocks.inspect.mockRejectedValueOnce(new Error('Network Error')).mockResolvedValueOnce(validInvitation());
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        await expectStatus('error');
        await fireEvent.click(within(pageRoot()).getByTestId('link-status-retry'));

        await formShown();
        expect(mocks.inspect).toHaveBeenCalledTimes(2);
        expect(mocks.inspect.mock.calls[1][0], 'the same question again').toStrictEqual({token: TOKEN, purpose: 'invite'});
    });
});

describe('/invite — a valid invitation opens the registration form', () => {
    it('hands the form the invitation: its token, its address and its role', async () => {
        mocks.inspect.mockResolvedValue(validInvitation({email: 'eve@example.com', grants_admin: true}));
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        const form = await formShown();
        expect(within(form).getByTestId('register-email'), 'the address the invitation suggests').toHaveValue('eve@example.com');
        expect(within(form).getByTestId('register-invite-notice')).toBeInTheDocument();
        expect(within(form).getByTestId('register-invite-admin-notice'), 'an administrator invitation says so').toBeInTheDocument();

        await registerAs(form, 'eve');

        await waitFor(() => expect(mocks.register).toHaveBeenCalledTimes(1));
        expect(mocks.register.mock.calls[0][0]).toStrictEqual({username: 'eve', email: 'eve@example.com', password: GOOD_PASSWORD, invite_token: TOKEN});
    });

    it('leaves the address empty and the administrator notice out when the invitation names neither', async () => {
        mocks.inspect.mockResolvedValue(validInvitation({email: null, grants_admin: null}));
        openAt(`/invite#token=${TOKEN}`);

        render(InvitePage);

        const form = await formShown();
        expect(within(form).getByTestId('register-email')).toHaveValue('');
        expect(within(form).getByTestId('register-invite-notice')).toBeInTheDocument();
        expect(within(form).queryByTestId('register-invite-admin-notice')).toBeNull();
    });
});

describe('/invite — leaving for the login page', () => {
    it('hands the login page the message of a created account, then goes to /', async () => {
        mocks.inspect.mockResolvedValue(validInvitation({email: 'eve@example.com'}));
        openAt(`/invite#token=${TOKEN}`);
        render(InvitePage);
        const form = await formShown();

        await registerAs(form, 'eve');

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.goto.mock.calls[0][0]).toBe('/');
        expect(mocks.setAuthFlash).toHaveBeenCalledTimes(1);
        expect(mocks.setAuthFlash, 'the message RegisterCard sends with gotoLogin').toHaveBeenCalledWith('auth.accountCreated');
        expect(mocks.setAuthFlash.mock.invocationCallOrder[0], 'the flash is left before the page goes').toBeLessThan(mocks.goto.mock.invocationCallOrder[0]);
    });

    it('leaves the message of a held activation email as a warning (lot E-26 (b)), the tone second, before it goes to /', async () => {
        mocks.inspect.mockResolvedValue(validInvitation({email: 'eve@example.com'}));
        mocks.register.mockResolvedValue({user: {id: 9, username: 'eve'}, message: 'ok', verification_required: true, verification_email: 'held'});
        openAt(`/invite#token=${TOKEN}`);
        render(InvitePage);
        const form = await formShown();

        await registerAs(form, 'eve');

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.setAuthFlash).toHaveBeenCalledTimes(1);
        expect(mocks.setAuthFlash).toHaveBeenCalledWith('email.verification.registeredHeld', 'warning');
        expect(mocks.setAuthFlash.mock.invocationCallOrder[0]).toBeLessThan(mocks.goto.mock.invocationCallOrder[0]);
    });

    it('goes to / with nothing to say when the user follows the login link of the form', async () => {
        openAt(`/invite#token=${TOKEN}`);
        render(InvitePage);
        const form = await formShown();

        await fireEvent.click(within(form).getByTestId('goto-login'));

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.goto.mock.calls[0][0]).toBe('/');
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.register).not.toHaveBeenCalled();
    });
});

describe('/invite — a link pasted into the tab already on the page (hashchange)', () => {
    const NEW_TOKEN = 'inv-NEW_0456';

    it('reads the new token of the fragment, inspects it, and the page follows the new answer', async () => {
        // The first link has expired; the administrator sends a fresh one, pasted into the same tab.
        mocks.inspect.mockImplementation(async (body: {token: string}) => (body.token === NEW_TOKEN ? validInvitation({email: 'eve@example.com'}) : {status: 'expired', purpose: 'invite'}));
        openAt(`/invite#token=${TOKEN}`);
        render(InvitePage);
        await expectStatus('expired');
        expect(mocks.replaceState, 'premise: the first token left the address bar').toHaveBeenCalledTimes(1);

        await changeFragment(`/invite#token=${NEW_TOKEN}`);

        const form = await formShown();
        expect(linkStatus()).toBeNull();
        expect(mocks.inspect, 'a second inspection').toHaveBeenCalledTimes(2);
        expect(mocks.inspect.mock.calls[1][0], 'of the new token, for the same purpose').toStrictEqual({token: NEW_TOKEN, purpose: 'invite'});
        expect(mocks.replaceState, 'the new token leaves the address bar too').toHaveBeenCalledTimes(2);
        expect(mocks.replaceState.mock.calls[1][0], 'replaced by the bare path').toBe('/invite');
        expect(within(form).getByTestId('register-email'), 'the form of the new invitation').toHaveValue('eve@example.com');

        await registerAs(form, 'eve');

        await waitFor(() => expect(mocks.register).toHaveBeenCalledTimes(1));
        expect(mocks.register.mock.calls[0][0], 'the new token replaced the old one').toStrictEqual({username: 'eve', email: 'eve@example.com', password: GOOD_PASSWORD, invite_token: NEW_TOKEN});
    });

    it('changes nothing when the new fragment carries no token', async () => {
        openAt(`/invite#token=${TOKEN}`);
        render(InvitePage);
        const form = await formShown();
        await fill('register-username', 'eve');

        // An in-page anchor: the fragment changes, and there is no token in it.
        await changeFragment('/invite#main');
        await settle();

        expect(mocks.inspect, 'no new inspection').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState, 'nothing to take out of the address bar').toHaveBeenCalledTimes(1);
        expect(registerCard(), 'the very same form, not a new one').toBe(form);
        expect(within(form).getByTestId('register-username'), 'with what the user typed in it').toHaveValue('eve');
        expect(linkStatus()).toBeNull();

        // Control: the listener was there all along, so the quiet above is the page's answer — a fragment that does
        // carry a token is read.
        await changeFragment(`/invite#token=${NEW_TOKEN}`);
        await waitFor(() => expect(mocks.inspect).toHaveBeenCalledTimes(2));
        expect(mocks.inspect.mock.calls[1][0]).toStrictEqual({token: NEW_TOKEN, purpose: 'invite'});
    });
});
