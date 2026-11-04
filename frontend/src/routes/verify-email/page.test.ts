// @vitest-environment jsdom
/**
 * /verify-email — the page an email-verification link opens (workstream E, lots E5a and E-25; developer decision 44).
 *
 * The verification email carries `/verify-email#token=…`: the token rides in the URL fragment, which a browser never
 * sends to the server. Same pattern as `/reset-password` (`src/routes/reset-password/page.test.ts`), with nothing to
 * fill in — but the link is NOT spent by opening it (lot E-25). Corporate mail scanners (Defender Safe Links and the
 * like) open the links of a message in a sandboxed browser that runs scripts, and would verify the address in place of
 * its owner: so the page asks for a click first. The contract:
 *   - on mount the page reads the token from the fragment with `takeLinkToken(new URL(window.location.href), …)`, which
 *     takes it out of the address bar through `replaceState` of `$app/navigation`, handing it the bare path
 *     `/verify-email`, and shows `ready`: the link is read, and NOTHING is asked — not on mount, not after every effect
 *     has run. The card offers the `verify-email-confirm` button;
 *   - no token — none in the fragment, an empty one, or one in the query, which is never read: `missing`, nothing is
 *     asked, and no confirm button;
 *   - a click on the confirm button is what spends the link: `POST /email/verification/confirm {token}` once, with that
 *     token — `checking` meanwhile, with no button at all in the card, so a second click cannot happen; verified: the
 *     login page's message `$_('email.verification.verified', {values: {username}})` is left with `setAuthFlash`, then
 *     `goto('/')`; a 400 `TOKEN_INVALID` shows its status (`expired`, `consumed`, `revoked`, `unknown`; an unknown status
 *     is `unknown`): no retry, the way back to the sign-in, no message, no navigation; any other failure but the block's
 *     (below) is `error`, whose retry asks again for the same token — the retry is itself a click, so there is no
 *     second `ready` step;
 *   - on a blocked instance (lot E-10) the confirm is refused before its route: a 401 to a visitor without a session
 *     (on this public route only the block answers 401), a 423 `instance_blocked` to a signed-in browser. Either shows
 *     `blocked`, in the block's own words, once the click has been given: no retry, the way back to the sign-in, no
 *     message left, no navigation, nothing asked again; a retry of a failed check that the block answers ends there
 *     too;
 *   - `hashchange`: a link pasted into a tab already on the page changes only the fragment; the page reads it again: a
 *     token replaces the old one, leaves the address bar too (`replaceState` once more, with `/verify-email`) and brings
 *     the page back to `ready` — nothing is asked until the confirm button is clicked, and then it is the NEW token; no
 *     token changes nothing (the status stays, nothing is asked, `replaceState` is not called again);
 *   - only the latest link writes: a click whose answer is still in flight when a new link is pasted leaves the page
 *     `ready`, and that older answer, arriving late (verified or refused), neither navigates, nor leaves a message, nor
 *     changes what the page shows; the click that follows spends the new token and its answer stands;
 *   - the root `verify-email-page`, and `<meta name="referrer" content="no-referrer">`.
 *
 * What runs for real: the page, `linkToken.ts`, `addressBar.ts`, `verificationApi.ts` (its readers) with `emailApi.ts`,
 * `AuthPageFrame`, `VerifyEmailCard` and `AuthCard`. What is replaced: the generated client's confirm alias (answered per
 * test; the rest of `$lib/api` is real, `ApiError` included), `authFlash.ts` (spies), `$app/navigation` (`goto` and
 * `replaceState` spies), and the frame's decoration (no-op components). `$lib/i18n` keeps its real exports with a
 * translator that answers the key, and its values when it is given some: `email.verification.verified {username=…}`.
 * The client's response interceptor never runs (the alias is replaced): the «no navigation» of a blocked instance is
 * the page's own.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
    confirm: vi.fn().mockName('zodiosApi.confirm_email_verification_api_v1_email_verification_confirm_post'),
    goto: vi.fn((..._args: unknown[]) => Promise.resolve()).mockName('goto'),
    replaceState: vi.fn((..._args: unknown[]) => {}).mockName('replaceState'),
    setAuthFlash: vi.fn((_message: string) => {}).mockName('setAuthFlash'),
    takeAuthFlash: vi.fn(() => '').mockName('takeAuthFlash'),
    /** The key, and the values when there are some: `email.verification.verified {username=zq_alice}`. */
    translate: (key: string, options?: {values?: Record<string, unknown>}): string => {
        const values = options?.values ?? {};
        const shown = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return shown.length > 0 ? `${key} {${shown.join(', ')}}` : key;
    },
    noopComponent: () => {},
}));

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
vi.mock('$lib/api', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api')>()),
    zodiosApi: {confirm_email_verification_api_v1_email_verification_confirm_post: mocks.confirm},
}));
vi.mock('$lib/features/auth/authFlash', () => ({setAuthFlash: mocks.setAuthFlash, takeAuthFlash: mocks.takeAuthFlash}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const translator = readable(mocks.translate);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator};
});
// The frame's decoration: each reaches for stores, localStorage or the document, and none is the subject.
vi.mock('$lib/components/ui/ThemeToggle.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/LanguageSelector.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/HelpMenu.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/ui/AnimatedBackground.svelte', () => ({default: mocks.noopComponent}));

import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import VerifyEmailPage from './+page.svelte';

const TOKEN = 'vfy-Ab3_xYz09';
const NEW_TOKEN = 'vfy-NEW_0456';

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
 * did NOT happen, which has no event to wait for: the macrotask boundary drains the whole microtask queue, and no time
 * passes that anything here depends on.
 */
async function settle(): Promise<void> {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    await tick();
}

/** Puts `path` in jsdom's address bar, as the link would. */
function openAt(path: string): void {
    window.history.replaceState(null, '', path);
}

/** What the browser does when only the fragment changes: the address takes it, and `hashchange` fires on `window`. */
async function changeFragment(path: string): Promise<void> {
    const oldURL = window.location.href;
    window.history.replaceState(null, '', path);
    await fireEvent(window, new HashChangeEvent('hashchange', {oldURL, newURL: window.location.href}));
}

/** An axios-shaped refusal carrying `response.status` and `response.data.detail`. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, data: {detail}}});
}

/** What `POST /email/verification/confirm` answers for a link of an address that is no longer the account's, and the like. */
function tokenInvalid(status: unknown): Error {
    return refusal(400, {error_code: 'TOKEN_INVALID', status, message: 'This verification link is not valid'});
}

/** How a blocked instance refuses the confirm (`refuse_when_blocked`, workstream H), before its route: one per caller. */
const BLOCKED_REFUSALS: Array<[string, () => Error]> = [
    ['a visitor without a session, refused with a 401', () => refusal(401, 'Not authenticated')],
    ['a signed-in browser, refused with a 423 instance_blocked', () => refusal(423, {code: 'instance_blocked', message: 'This instance is blocked by its hosting provider'})],
];

const pageRoot = () => screen.getByTestId('verify-email-page');
const card = () => within(pageRoot()).getByTestId('verify-email-status');

/** Waits for the card to show this status. */
async function expectStatus(status: string): Promise<void> {
    await waitFor(() => expect(card(), `the page shows ${status}`).toHaveAttribute('data-status', status));
}

/** Waits for the page to be `ready` for the click, then gives it: the one thing that spends the link. */
async function confirmOnPage(): Promise<void> {
    await expectStatus('ready');
    await fireEvent.click(within(card()).getByTestId('verify-email-confirm'));
}

beforeEach(() => {
    // Negative assertions below would pass vacuously in an environment where effects (onMount) never run.
    assertEffectsRun();
    for (const spy of [mocks.goto, mocks.replaceState, mocks.setAuthFlash, mocks.takeAuthFlash]) spy.mockClear();
    mocks.confirm.mockReset();
    mocks.confirm.mockResolvedValue({username: 'zq_alice'});
});

afterEach(() => {
    cleanup();
    openAt('/');
});

describe('/verify-email — the token, read at once and spent only by a click', () => {
    it('VEP-01: reads the token from the fragment and takes it out of the address bar, but asks nothing: ready, for the click', async () => {
        openAt(`/verify-email#token=${TOKEN}`);

        render(VerifyEmailPage);

        // The token leaving the address bar proves the mount ran: the absences below are not an effect that never started.
        await waitFor(() => expect(mocks.replaceState).toHaveBeenCalledTimes(1));
        await settle();
        expect(mocks.confirm, 'opening the page never spends the link: a mail scanner opens it too, scripts and all').not.toHaveBeenCalled();
        expect(mocks.replaceState, 'the token leaves the address bar, once').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState.mock.calls[0][0], 'replaced by the bare path: no fragment, no query').toBe('/verify-email');
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
        await expectStatus('ready');
        expect(within(card()).getByTestId('verify-email-message')).toHaveTextContent('email.verification.page.ready');
        expect(within(card()).getByTestId('verify-email-confirm'), 'the click that spends the link is the card’s').toBeInTheDocument();
    });

    it('VEP-02: verified by the click — leaves the login page the message naming the account, then goes to /', async () => {
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);

        await confirmOnPage();

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.goto.mock.calls[0][0]).toBe('/');
        expect(mocks.setAuthFlash).toHaveBeenCalledTimes(1);
        expect(mocks.setAuthFlash).toHaveBeenCalledWith('email.verification.verified {username=zq_alice}');
        expect(mocks.setAuthFlash.mock.invocationCallOrder[0], 'the message is left before the page goes').toBeLessThan(mocks.goto.mock.invocationCallOrder[0]);
    });

    it.each([
        ['no token at all', '/verify-email'],
        ['an empty token', '/verify-email#token='],
        ['a fragment without a token', '/verify-email#lang=it'],
        // A token in the query has reached the server's access log: it is never read.
        ['a token in the query, never read', `/verify-email?token=${TOKEN}`],
    ])('VEP-03: %s — missing, nothing is asked, and nothing to confirm', async (_label, path) => {
        openAt(path);

        render(VerifyEmailPage);

        await expectStatus('missing');
        await settle();
        expect(mocks.confirm).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
        expect(within(card()).queryByTestId('verify-email-confirm'), 'no link, nothing to spend').toBeNull();
    });

    it('VEP-04: keeps its token out of the Referer of any link followed from it, under the root verify-email-page', () => {
        openAt(`/verify-email#token=${TOKEN}`);

        render(VerifyEmailPage);

        expect(pageRoot()).toBeInTheDocument();
        expect(document.head.querySelector('meta[name="referrer"]')).toHaveAttribute('content', 'no-referrer');
    });

    it('VEP-13: the click asks the server once, with the token — checking meanwhile, with nothing left to click', async () => {
        const answer = deferred<unknown>();
        mocks.confirm.mockReturnValue(answer.promise);
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);

        await confirmOnPage();

        await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(1));
        expect(mocks.confirm.mock.calls[0][0]).toStrictEqual({token: TOKEN});
        await expectStatus('checking');
        expect(within(card()).queryByTestId('verify-email-confirm'), 'in flight the confirm is gone: a second click cannot spend the link twice').toBeNull();
        expect(within(card()).queryAllByRole('button'), 'nothing to do while checking').toEqual([]);
        await settle();
        expect(mocks.confirm, 'once, with nothing started again meanwhile').toHaveBeenCalledTimes(1);

        answer.resolve({username: 'zq_alice'});
        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
    });
});

describe('/verify-email — a link the server refuses', () => {
    it.each(['expired', 'consumed', 'revoked', 'unknown'])('VEP-05: %s — shown as such after the click; no message, nowhere to go but back to the sign-in', async (status) => {
        mocks.confirm.mockRejectedValue(tokenInvalid(status));
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);

        await confirmOnPage();

        await expectStatus(status);
        expect(within(card()).queryByTestId('verify-email-retry'), 'a refused link is not retried').toBeNull();
        expect(within(card()).queryByTestId('verify-email-confirm'), 'a refused link is not confirmed again').toBeNull();
        expect(within(card()).getByTestId('verify-email-goto-login')).toBeInTheDocument();
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
    });

    it('VEP-06: a TOKEN_INVALID with a status the page does not know is unknown', async () => {
        mocks.confirm.mockRejectedValue(tokenInvalid('something-new'));
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);

        await confirmOnPage();

        await expectStatus('unknown');
    });

    it.each([
        ['a request that reached no server', () => new Error('Network Error')],
        ['a server error', () => refusal(500, 'Internal Server Error')],
        ['TOKEN_INVALID with a 409', () => refusal(409, {error_code: 'TOKEN_INVALID', status: 'expired'})],
    ])('VEP-07: %s — error, whose retry asks again for the same token, and then verifies', async (_label, fail) => {
        mocks.confirm.mockRejectedValueOnce(fail()).mockResolvedValueOnce({username: 'zq_alice'});
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);
        await confirmOnPage();
        await expectStatus('error');
        expect(mocks.goto).not.toHaveBeenCalled();
        expect(within(card()).queryByTestId('verify-email-confirm'), 'the retry is the only click offered').toBeNull();

        // The retry is itself a click: it spends the link, with no second `ready` step in between.
        await fireEvent.click(within(card()).getByTestId('verify-email-retry'));

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.confirm).toHaveBeenCalledTimes(2);
        expect(mocks.confirm.mock.calls[1][0], 'the same token again').toStrictEqual({token: TOKEN});
        expect(mocks.setAuthFlash).toHaveBeenCalledWith('email.verification.verified {username=zq_alice}');
    });
});

describe('/verify-email — a link pasted into the tab already on the page (hashchange)', () => {
    it('VEP-08: a new token replaces the old one, leaves the address bar, and leaves the page ready: only the click asks, with the new token; a fragment without a token changes nothing', async () => {
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);
        await expectStatus('ready');
        expect(mocks.replaceState).toHaveBeenCalledTimes(1);

        await changeFragment('/verify-email#main');
        await settle();
        expect(card(), 'no token in the new fragment: the page stays as it was').toHaveAttribute('data-status', 'ready');
        expect(mocks.confirm, 'no token in the new fragment: nothing asked').not.toHaveBeenCalled();
        expect(mocks.replaceState, 'no token in the new fragment: the address bar is left alone').toHaveBeenCalledTimes(1);

        await changeFragment(`/verify-email#token=${NEW_TOKEN}`);
        await settle();
        expect(mocks.replaceState, 'the new token leaves the address bar too').toHaveBeenCalledTimes(2);
        expect(mocks.replaceState.mock.calls[1][0]).toBe('/verify-email');
        expect(card()).toHaveAttribute('data-status', 'ready');
        expect(mocks.confirm, 'a pasted link is no click: nothing asked until the confirm').not.toHaveBeenCalled();

        await confirmOnPage();

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.confirm).toHaveBeenCalledTimes(1);
        expect(mocks.confirm.mock.calls[0][0], 'the new token, never the old one').toStrictEqual({token: NEW_TOKEN});
    });

    it('VEP-09: an older token verified late, after a new link was pasted, changes nothing — the page stays ready; the click then spends the new token, whose answer stands', async () => {
        const older = deferred<unknown>();
        const newer = deferred<unknown>();
        mocks.confirm.mockImplementation((body: {token: string}) => (body.token === TOKEN ? older.promise : newer.promise));
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);
        await confirmOnPage();
        await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(1));
        await changeFragment(`/verify-email#token=${NEW_TOKEN}`);
        await expectStatus('ready');

        older.resolve({username: 'zq_alice'});
        await settle();

        expect(mocks.setAuthFlash, 'the older link’s message is not left').not.toHaveBeenCalled();
        expect(mocks.goto, 'the older link’s answer does not navigate').not.toHaveBeenCalled();
        expect(card(), 'the late answer does not change what the page shows').toHaveAttribute('data-status', 'ready');
        expect(mocks.confirm, 'nothing asked for the new link yet').toHaveBeenCalledTimes(1);

        await confirmOnPage();
        await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(2));
        expect(mocks.confirm.mock.calls[1][0]).toStrictEqual({token: NEW_TOKEN});
        newer.reject(tokenInvalid('revoked'));
        await expectStatus('revoked');

        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
    });

    it('VEP-10: an older token refused late, after a new link was pasted, changes nothing — the page stays ready; the click then verifies the new one', async () => {
        const older = deferred<unknown>();
        mocks.confirm.mockImplementation((body: {token: string}) => (body.token === TOKEN ? older.promise : Promise.resolve({username: 'zq_bob'})));
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);
        await confirmOnPage();
        await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(1));
        await changeFragment(`/verify-email#token=${NEW_TOKEN}`);
        await expectStatus('ready');

        older.reject(tokenInvalid('expired'));
        await settle();

        expect(card(), 'the late refusal of the older link is not shown').toHaveAttribute('data-status', 'ready');
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();

        await confirmOnPage();

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.confirm.mock.calls[1][0]).toStrictEqual({token: NEW_TOKEN});
        expect(mocks.setAuthFlash.mock.calls).toEqual([['email.verification.verified {username=zq_bob}']]);
    });

    it('VEP-14: a new link pasted after a refusal brings the page back to ready — nothing asked until the click, then the new token is spent; a fragment without a token changes nothing', async () => {
        mocks.confirm.mockImplementation(async (body: {token: string}) => {
            if (body.token === NEW_TOKEN) return {username: 'zq_alice'};
            throw tokenInvalid('expired');
        });
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);
        await confirmOnPage();
        await expectStatus('expired');

        await changeFragment('/verify-email#main');
        await settle();
        expect(mocks.confirm, 'no token in the new fragment: nothing asked').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState).toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-status', 'expired');

        await changeFragment(`/verify-email#token=${NEW_TOKEN}`);
        await expectStatus('ready');
        await settle();
        expect(mocks.confirm, 'a pasted link is no click: still only the first, refused ask').toHaveBeenCalledTimes(1);
        expect(mocks.replaceState, 'the new token leaves the address bar too').toHaveBeenCalledTimes(2);
        expect(mocks.replaceState.mock.calls[1][0]).toBe('/verify-email');

        await confirmOnPage();

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.confirm).toHaveBeenCalledTimes(2);
        expect(mocks.confirm.mock.calls[1][0]).toStrictEqual({token: NEW_TOKEN});
        expect(mocks.setAuthFlash).toHaveBeenCalledWith('email.verification.verified {username=zq_alice}');
    });

    it('VEP-15: a fragment without a token, while the check is in flight, changes nothing — its answer still stands', async () => {
        const answer = deferred<unknown>();
        mocks.confirm.mockReturnValue(answer.promise);
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);
        await confirmOnPage();
        await expectStatus('checking');

        await changeFragment('/verify-email#main');
        await settle();

        expect(card(), 'no token in the new fragment: the page keeps waiting').toHaveAttribute('data-status', 'checking');
        expect(mocks.confirm).toHaveBeenCalledTimes(1);
        expect(mocks.replaceState).toHaveBeenCalledTimes(1);

        answer.resolve({username: 'zq_alice'});

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledTimes(1));
        expect(mocks.setAuthFlash).toHaveBeenCalledWith('email.verification.verified {username=zq_alice}');
    });
});

describe('/verify-email — on a blocked instance (lot E-10)', () => {
    it.each(BLOCKED_REFUSALS)('VEP-11: %s — blocked after the click, in the block’s own words: the way back only, no retry, no message, no navigation, nothing asked again', async (_label, fail) => {
        mocks.confirm.mockRejectedValue(fail());
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);

        await confirmOnPage();

        await expectStatus('blocked');
        await settle();
        expect(card(), 'still blocked once everything already started has run').toHaveAttribute('data-status', 'blocked');
        expect(within(card()).getByTestId('verify-email-message')).toHaveTextContent('email.verification.page.blocked');
        expect(within(card()).queryByTestId('verify-email-retry'), 'trying again changes nothing while the instance is blocked').toBeNull();
        expect(within(card()).queryByTestId('verify-email-confirm'), 'nor does confirming again').toBeNull();
        expect(within(card()).getByTestId('verify-email-goto-login')).toBeInTheDocument();
        expect(mocks.confirm, 'asked once, never again').toHaveBeenCalledTimes(1);
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
    });

    it.each(BLOCKED_REFUSALS)('VEP-12: a check that failed, tried again and answered by the block — %s — ends on blocked: its retry withdrawn', async (_label, fail) => {
        mocks.confirm.mockRejectedValueOnce(new Error('Network Error')).mockRejectedValueOnce(fail());
        openAt(`/verify-email#token=${TOKEN}`);
        render(VerifyEmailPage);
        await confirmOnPage();
        await expectStatus('error');

        await fireEvent.click(within(card()).getByTestId('verify-email-retry'));

        await expectStatus('blocked');
        await settle();
        expect(mocks.confirm).toHaveBeenCalledTimes(2);
        expect(mocks.confirm.mock.calls[1][0], 'the same token again').toStrictEqual({token: TOKEN});
        expect(within(card()).queryByTestId('verify-email-retry'), 'the retry the error offered is withdrawn').toBeNull();
        expect(within(card()).getByTestId('verify-email-goto-login')).toBeInTheDocument();
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
    });
});
