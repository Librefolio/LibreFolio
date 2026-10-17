// @vitest-environment jsdom
/**
 * /reset-password — the page a password-reset link opens (accounts lot A5b).
 *
 * An administrator creates a reset link for an account (A5a: `POST /api/v1/users/{user_id}/password-reset-link`) and
 * hands it over, `/reset-password#token=…`: the token rides in the URL fragment, which a browser never sends to the
 * server, so it stays out of the access logs. Same pattern as `/invite` (`src/routes/invite/page.test.ts`), with
 * `ResetPasswordCard` for the form.
 *
 * The contract (plan A5b.1, with the fragment decision of 2026-10-15):
 *   - on mount the page reads the token from the fragment with `takeLinkToken(new URL(window.location.href), …)`,
 *     which takes it out of the address bar through `replaceState` of `$app/navigation`, handing it the bare path
 *     `/reset-password`;
 *   - no token — none in the fragment, an empty one, or one in the query, which is never read: `LinkStatusCard`
 *     `missing`, and no inspection is asked;
 *   - otherwise `POST /auth/tokens/inspect {token, purpose: 'password_reset'}` — `checking` meanwhile; a status other
 *     than `valid` → `LinkStatusCard` with that status; a failed check → `error`, whose retry asks again;
 *   - a valid link → `ResetPasswordCard` with the token and `username` (the account the server names, `null` when it
 *     names none). The registration mode has nothing to say here: a password is reset on an instance that closed
 *     registration too;
 *   - `ondone` → `setAuthFlash($_('auth.resetPassword.done'))`, then `goto('/')`; `oninvalid` (the link died between the
 *     check and the submit) → `LinkStatusCard` `unknown`;
 *   - the root `reset-password-page`, and `<meta name="referrer" content="no-referrer">`;
 *   - `hashchange` on `window`: a link pasted into a tab already on the page changes only the fragment, so nothing
 *     reloads. The page reads the fragment again: a token replaces the old one and goes through the flow of the mount
 *     (`replaceState` to the bare path, the inspection); no token changes nothing. The listener goes with the page.
 *
 * What runs for real: the page, `linkToken.ts`, `AuthPageFrame`, `LinkStatusCard` and `ResetPasswordCard`. What is
 * replaced: the generated client (the inspection and the reset, answered per test), the instance configuration (a fake
 * of the real store's shape, in case the page reads it: it says registration is disabled, which must change nothing),
 * `authFlash.ts` (spies), `$app/navigation` (`goto` and `replaceState` spies), and the frame's decoration (no-op
 * components). `$lib/i18n` keeps its real exports with the identity as translator, so a message renders as its key —
 * the flash included: `auth.resetPassword.done`.
 *
 * Accounts lot A6c (decision 37): the password rules are in one place, the server's — `accounts.password_rules` of the
 * public `GET /system/instance`. `PasswordStrength`, the meter of `ResetPasswordCard`, reads them from `instanceConfig`
 * and checks the built-in defaults (`DEFAULT_PASSWORD_RULES`) until the configuration is loaded. A reset link opens
 * signed out, often in a fresh tab, outside the (app) layout that loads the configuration, so the page asks for it
 * itself: `instanceConfig.load()` on mount, fire-and-forget — never awaited before the link check, so a slow or failing
 * request neither delays nor blocks the form (the real `load()` handles its own failure and never rejects). The fake
 * here carries no `password_rules`, so every case runs on the defaults. The describe «the password rules of the server»
 * pins both halves, written red-first: its first case fails until the page calls `load()`; its second passes before
 * and after, and fails the day the call is awaited.
 *
 * Written red-first, before `routes/reset-password/+page.svelte` exists: the file fails on the import until it does.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const DISABLED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'disabled', registration_locked: false}};
    return {
        instance: reactiveBox<{config: InstanceConfig}>({config: DISABLED}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
        inspect: vi.fn().mockName('zodiosApi.inspect_link_token_api_v1_auth_tokens_inspect_post'),
        reset: vi.fn().mockName('zodiosApi.reset_password_with_link_api_v1_auth_password_reset_post'),
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
        reset_password_with_link_api_v1_auth_password_reset_post: mocks.reset,
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
import ResetPasswordPage from './+page.svelte';

const TOKEN = 'rst-Ab3_xYz09';
/** Satisfies all five password rules. */
const GOOD_PASSWORD = 'Str0ng!pass';

/** What `POST /auth/tokens/inspect` answers for a valid reset link; `extra` adds or overrides fields. */
function validResetLink(extra: Record<string, unknown> = {}) {
    return {status: 'valid', purpose: 'password_reset', expires_at: '2026-10-16T08:00:00Z', username: 'alice', ...extra};
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

const pageRoot = () => screen.getByTestId('reset-password-page');
const linkStatus = () => within(pageRoot()).queryByTestId('link-status');
const resetCard = () => within(pageRoot()).queryByTestId('reset-password-modal');

/** Waits for the page to show a `LinkStatusCard` with this status. */
async function expectStatus(status: string): Promise<void> {
    await waitFor(() => expect(linkStatus(), `the page shows LinkStatusCard ${status}`).toHaveAttribute('data-status', status));
}

/** Waits for the reset form, inside the page. */
async function formShown(): Promise<HTMLElement> {
    await waitFor(() => expect(resetCard(), 'the page shows the reset form').not.toBeNull());
    return resetCard()!;
}

/** Types a good new password twice and submits. */
async function chooseNewPassword(): Promise<void> {
    await fireEvent.input(screen.getByTestId('reset-password-new'), {target: {value: GOOD_PASSWORD}});
    await fireEvent.input(screen.getByTestId('reset-password-confirm'), {target: {value: GOOD_PASSWORD}});
    await fireEvent.click(screen.getByTestId('reset-password-submit'));
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
    mocks.inspect.mockResolvedValue(validResetLink());
    mocks.reset.mockReset();
    mocks.reset.mockResolvedValue({message: 'Password reset successfully'});
});

afterEach(() => {
    cleanup();
    openAt('/');
});

describe('/reset-password — the token, read once', () => {
    it('reads the token from the fragment, takes it out of the address bar, and asks what the reset link is worth', async () => {
        const inspection = deferred<unknown>();
        mocks.inspect.mockReturnValue(inspection.promise);
        openAt(`/reset-password#token=${TOKEN}`);

        render(ResetPasswordPage);

        await waitFor(() => expect(mocks.inspect).toHaveBeenCalledTimes(1));
        expect(mocks.inspect.mock.calls[0][0]).toStrictEqual({token: TOKEN, purpose: 'password_reset'});
        expect(mocks.replaceState, 'the token leaves the address bar, once').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState.mock.calls[0][0], 'replaced by the bare path: no fragment, no query').toBe('/reset-password');
        await expectStatus('checking');

        inspection.resolve(validResetLink());

        await formShown();
        expect(linkStatus()).toBeNull();
    });

    it.each([
        ['no token at all', '/reset-password'],
        ['an empty token', '/reset-password#token='],
        ['a fragment without a token', '/reset-password#lang=it'],
        // The old shape: a token in the query has reached the server's access log, so it is never read.
        ['a token in the query, never read', `/reset-password?token=${TOKEN}`],
    ])('shows missing for %s, and asks for no inspection', async (_label, path) => {
        openAt(path);

        render(ResetPasswordPage);

        await expectStatus('missing');
        expect(mocks.inspect).not.toHaveBeenCalled();
        expect(resetCard()).toBeNull();
    });

    it('keeps its token out of the Referer of any link followed from it', () => {
        openAt(`/reset-password#token=${TOKEN}`);

        render(ResetPasswordPage);

        expect(document.head.querySelector('meta[name="referrer"]')).toHaveAttribute('content', 'no-referrer');
    });
});

describe('/reset-password — a link the server does not call valid', () => {
    it.each(['expired', 'consumed', 'revoked', 'unknown'])('shows %s, and no form', async (status) => {
        mocks.inspect.mockResolvedValue({status, purpose: 'password_reset'});
        openAt(`/reset-password#token=${TOKEN}`);

        render(ResetPasswordPage);

        await expectStatus(status);
        expect(resetCard()).toBeNull();
    });

    it('shows error with a retry when the check failed, and the retry asks again', async () => {
        mocks.inspect.mockRejectedValueOnce(new Error('Network Error')).mockResolvedValueOnce(validResetLink());
        openAt(`/reset-password#token=${TOKEN}`);

        render(ResetPasswordPage);

        await expectStatus('error');
        await fireEvent.click(within(pageRoot()).getByTestId('link-status-retry'));

        await formShown();
        expect(mocks.inspect).toHaveBeenCalledTimes(2);
        expect(mocks.inspect.mock.calls[1][0], 'the same question again').toStrictEqual({token: TOKEN, purpose: 'password_reset'});
    });
});

describe('/reset-password — a valid link opens the reset form', () => {
    it('names the account the server named', async () => {
        openAt(`/reset-password#token=${TOKEN}`);

        render(ResetPasswordPage);

        const form = await formShown();
        expect(within(form).getByTestId('reset-password-account')).toHaveTextContent('alice');
    });

    it('opens it on an instance that disabled registration too: a reset is not a registration', async () => {
        // The instance configuration of this file says `disabled` throughout.
        expect(mocks.instance.config.accounts.registration_mode, 'premise').toBe('disabled');
        openAt(`/reset-password#token=${TOKEN}`);

        render(ResetPasswordPage);

        await formShown();
        expect(linkStatus()).toBeNull();
    });

    it('spends the link of the address bar with the new password', async () => {
        openAt(`/reset-password#token=${TOKEN}`);
        render(ResetPasswordPage);
        await formShown();

        await chooseNewPassword();

        await waitFor(() => expect(mocks.reset).toHaveBeenCalledTimes(1));
        expect(mocks.reset.mock.calls[0][0]).toStrictEqual({token: TOKEN, new_password: GOOD_PASSWORD});
    });
});

describe('/reset-password — after the reset', () => {
    it('hands the login page the message of a changed password, then goes to /', async () => {
        openAt(`/reset-password#token=${TOKEN}`);
        render(ResetPasswordPage);
        await formShown();

        await chooseNewPassword();

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.goto.mock.calls[0][0]).toBe('/');
        expect(mocks.setAuthFlash).toHaveBeenCalledTimes(1);
        expect(mocks.setAuthFlash, 'auth.resetPassword.done, through the translator').toHaveBeenCalledWith('auth.resetPassword.done');
        expect(mocks.setAuthFlash.mock.invocationCallOrder[0], 'the flash is left before the page goes').toBeLessThan(mocks.goto.mock.invocationCallOrder[0]);
    });

    it('shows the link as unknown when the server says it died in the meantime (TOKEN_INVALID)', async () => {
        mocks.reset.mockRejectedValue(refusal(400, {error_code: 'TOKEN_INVALID', message: 'This link is not valid'}));
        openAt(`/reset-password#token=${TOKEN}`);
        render(ResetPasswordPage);
        await formShown();

        await chooseNewPassword();

        await expectStatus('unknown');
        expect(resetCard()).toBeNull();
        expect(mocks.goto).not.toHaveBeenCalled();
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
    });
});

describe('/reset-password — a link pasted into the tab already on the page (hashchange)', () => {
    const NEW_TOKEN = 'rst-NEW_0456';

    it('reads the new token of the fragment, inspects it, and the page follows the new answer', async () => {
        // The first link has expired; the administrator sends a fresh one, pasted into the same tab.
        mocks.inspect.mockImplementation(async (body: {token: string}) => (body.token === NEW_TOKEN ? validResetLink({username: 'bob'}) : {status: 'expired', purpose: 'password_reset'}));
        openAt(`/reset-password#token=${TOKEN}`);
        render(ResetPasswordPage);
        await expectStatus('expired');
        expect(mocks.replaceState, 'premise: the first token left the address bar').toHaveBeenCalledTimes(1);

        await changeFragment(`/reset-password#token=${NEW_TOKEN}`);

        const form = await formShown();
        expect(linkStatus()).toBeNull();
        expect(mocks.inspect, 'a second inspection').toHaveBeenCalledTimes(2);
        expect(mocks.inspect.mock.calls[1][0], 'of the new token, for the same purpose').toStrictEqual({token: NEW_TOKEN, purpose: 'password_reset'});
        expect(mocks.replaceState, 'the new token leaves the address bar too').toHaveBeenCalledTimes(2);
        expect(mocks.replaceState.mock.calls[1][0], 'replaced by the bare path').toBe('/reset-password');
        expect(within(form).getByTestId('reset-password-account'), 'the account of the new link').toHaveTextContent('bob');

        await chooseNewPassword();

        await waitFor(() => expect(mocks.reset).toHaveBeenCalledTimes(1));
        expect(mocks.reset.mock.calls[0][0], 'the new token replaced the old one').toStrictEqual({token: NEW_TOKEN, new_password: GOOD_PASSWORD});
    });

    it('changes nothing when the new fragment carries no token', async () => {
        openAt(`/reset-password#token=${TOKEN}`);
        render(ResetPasswordPage);
        const form = await formShown();
        await fireEvent.input(within(form).getByTestId('reset-password-new'), {target: {value: GOOD_PASSWORD}});

        // An in-page anchor: the fragment changes, and there is no token in it.
        await changeFragment('/reset-password#main');
        await settle();

        expect(mocks.inspect, 'no new inspection').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState, 'nothing to take out of the address bar').toHaveBeenCalledTimes(1);
        expect(resetCard(), 'the very same form, not a new one').toBe(form);
        expect(within(form).getByTestId('reset-password-new'), 'with what the user typed in it').toHaveValue(GOOD_PASSWORD);
        expect(linkStatus()).toBeNull();

        // Control: the listener was there all along, so the quiet above is the page's answer — a fragment that does
        // carry a token is read.
        await changeFragment(`/reset-password#token=${NEW_TOKEN}`);
        await waitFor(() => expect(mocks.inspect).toHaveBeenCalledTimes(2));
        expect(mocks.inspect.mock.calls[1][0]).toStrictEqual({token: NEW_TOKEN, purpose: 'password_reset'});
    });
});

describe('/reset-password — the password rules of the server', () => {
    it("asks for the instance configuration once the page mounts, so the meter checks the server's rules", async () => {
        // Red before the A6c fix, and only because the page never calls `instanceConfig.load()`: the form opens, and
        // the request that brings `accounts.password_rules` was never made. Nothing else on this page makes it — the
        // link opens signed out, outside the (app) layout — so the meter would check the built-in defaults. Green once
        // `onMount` calls `void instanceConfig.load()`.
        openAt(`/reset-password#token=${TOKEN}`);

        render(ResetPasswordPage);

        // The barrier: the mount went all the way through (token read, link checked, form drawn), so a missing call is
        // the page's answer, not a call still to come.
        await formShown();
        expect(mocks.instanceLoad, 'GET /system/instance, asked by the page itself').toHaveBeenCalled();
    });

    it('does not wait for it: a valid link opens the reset form though the configuration request never answers', async () => {
        // Green before the fix (the page asks for nothing yet) and must stay green after it: `load()` is
        // fire-and-forget. This is the case that turns red if the call is ever awaited before the link check — a slow
        // or failing configuration request must never delay or block the form; the meter keeps the defaults until an
        // answer lands. That the call is made at all is the case above.
        mocks.instanceLoad.mockReturnValue(new Promise<void>(() => {}));
        openAt(`/reset-password#token=${TOKEN}`);

        render(ResetPasswordPage);

        await formShown();
        expect(linkStatus()).toBeNull();
    });
});
