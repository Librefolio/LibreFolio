// @vitest-environment jsdom
/**
 * /confirm-email-change — the page the link of an owner's address change opens (lot A5-1b, developer decision of
 * 23/10/2026).
 *
 * On a managed instance the hosting provider changes the address of the paying administrator: at the next start the
 * instance emails a link to the NEW address, `/confirm-email-change#token=…`, and the address changes only after the click.
 * The page follows `/verify-email` (workstream E, lot E-25) in everything that matters:
 *   - the token rides in the fragment, is taken out of the address bar at once (`replaceState` with the bare path
 *     `/confirm-email-change`), and opening the page asks NOTHING: a mail scanner opens the links of a message too. The
 *     card is `ready`, with the button `email-change-confirm`; no token, or one in the query, is `missing`;
 *   - the click spends the link: `POST /email/email-change/confirm {token}` once, `checking` meanwhile with no button;
 *     confirmed: the login page is left the message `email.emailChange.changed`, the owner's sessions having ended, and
 *     `goto('/')`; a 400 `TOKEN_INVALID` shows its status (`expired`, `consumed`, `revoked`, `unknown`; any other status is
 *     `unknown`) and the way back to the sign-in; a blocked instance (401 / 423 `instance_blocked`) shows `blocked`; any other
 *     failure is `error`, whose retry asks again for the same token;
 *   - a link pasted into the tab already on the page (`hashchange`) replaces the token and brings the page back to `ready`;
 *   - the root `email-change-page`, `<meta name="referrer" content="no-referrer">`.
 *
 * What runs for real: the page, `linkToken.ts`, `addressBar.ts`, the API wrapper `emailChangeApi.ts`, `AuthPageFrame`
 * and `EmailChangeCard`. Replaced: the generated client's confirm alias, `authFlash.ts` (spies), `$app/navigation`
 * (`goto` and `replaceState`), the frame's decoration. `$lib/i18n`: the real exports with a translator that answers the key.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
    confirm: vi.fn().mockName('zodiosApi.confirm_owner_email_change_api_v1_email_email_change_confirm_post'),
    goto: vi.fn((..._args: unknown[]) => Promise.resolve()).mockName('goto'),
    replaceState: vi.fn((..._args: unknown[]) => {}).mockName('replaceState'),
    setAuthFlash: vi.fn((_message: string) => {}).mockName('setAuthFlash'),
    takeAuthFlash: vi.fn(() => '').mockName('takeAuthFlash'),
    translate: (key: string) => key,
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
    zodiosApi: {confirm_owner_email_change_api_v1_email_email_change_confirm_post: mocks.confirm},
}));
vi.mock('$lib/features/auth/authFlash', () => ({setAuthFlash: mocks.setAuthFlash, takeAuthFlash: mocks.takeAuthFlash}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const translator = readable(mocks.translate);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator};
});
vi.mock('$lib/components/ui/ThemeToggle.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/LanguageSelector.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/HelpMenu.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/ui/AnimatedBackground.svelte', () => ({default: mocks.noopComponent}));

import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import EmailChangePage from './+page.svelte';

const TOKEN = 'chg-Ab3_xYz09';
const NEW_TOKEN = 'chg-NEW_0456';

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** Only for an assertion that something did NOT happen: the macrotask boundary drains the microtask queue. */
async function settle(): Promise<void> {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    await tick();
}

function openAt(path: string): void {
    window.history.replaceState(null, '', path);
}

async function changeFragment(path: string): Promise<void> {
    const oldURL = window.location.href;
    window.history.replaceState(null, '', path);
    await fireEvent(window, new HashChangeEvent('hashchange', {oldURL, newURL: window.location.href}));
}

function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, data: {detail}}});
}

const tokenInvalid = (status: unknown): Error => refusal(400, {error_code: 'TOKEN_INVALID', status, message: 'This link is not valid'});

const pageRoot = () => screen.getByTestId('email-change-page');
const card = () => within(pageRoot()).getByTestId('email-change-status');

async function expectStatus(status: string): Promise<void> {
    await waitFor(() => expect(card(), `the page shows ${status}`).toHaveAttribute('data-status', status));
}

async function confirmOnPage(): Promise<void> {
    await expectStatus('ready');
    await fireEvent.click(within(card()).getByTestId('email-change-confirm'));
}

beforeEach(() => {
    assertEffectsRun();
    for (const spy of [mocks.goto, mocks.replaceState, mocks.setAuthFlash, mocks.takeAuthFlash]) spy.mockClear();
    mocks.confirm.mockReset();
    mocks.confirm.mockResolvedValue({username: 'owner_admin'});
});

afterEach(() => {
    cleanup();
    openAt('/');
});

describe('/confirm-email-change — the token, read at once and spent only by a click', () => {
    it('ECP-01: reads the token from the fragment, takes it out of the address bar, asks nothing: ready, for the click', async () => {
        openAt(`/confirm-email-change#token=${TOKEN}`);

        render(EmailChangePage);

        await waitFor(() => expect(mocks.replaceState).toHaveBeenCalledTimes(1));
        await settle();
        expect(mocks.confirm, 'opening the page never spends the link').not.toHaveBeenCalled();
        expect(mocks.replaceState.mock.calls[0][0]).toBe('/confirm-email-change');
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
        await expectStatus('ready');
        expect(within(card()).getByTestId('email-change-message')).toHaveTextContent('email.emailChange.page.ready');
        expect(within(card()).getByTestId('email-change-confirm')).toBeInTheDocument();
    });

    it('ECP-02: confirmed by the click — one request with that token, the login page told that the address changed, then /', async () => {
        openAt(`/confirm-email-change#token=${TOKEN}`);
        render(EmailChangePage);

        await confirmOnPage();

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledWith('/'));
        expect(mocks.confirm).toHaveBeenCalledTimes(1);
        expect(mocks.confirm).toHaveBeenCalledWith({token: TOKEN});
        expect(mocks.setAuthFlash).toHaveBeenCalledTimes(1);
        expect(mocks.setAuthFlash).toHaveBeenCalledWith('email.emailChange.changed');
    });

    it.each(['', '#', '#token=', '?token=chg-InQuery'])('ECP-03: no usable token (%j) → missing, nothing asked, no confirm button', async (suffix) => {
        openAt(`/confirm-email-change${suffix}`);

        render(EmailChangePage);

        await expectStatus('missing');
        await settle();
        expect(mocks.confirm).not.toHaveBeenCalled();
        expect(within(card()).queryByTestId('email-change-confirm')).toBeNull();
    });

    it('ECP-04: while the answer is awaited the card is checking, with no button to click twice', async () => {
        const pending = deferred<{username: string}>();
        mocks.confirm.mockReturnValue(pending.promise);
        openAt(`/confirm-email-change#token=${TOKEN}`);
        render(EmailChangePage);

        await confirmOnPage();

        await expectStatus('checking');
        expect(within(card()).queryByTestId('email-change-confirm')).toBeNull();
        pending.resolve({username: 'owner_admin'});
        await waitFor(() => expect(mocks.goto).toHaveBeenCalledWith('/'));
    });
});

describe('/confirm-email-change — a link that cannot be used (ECP-05…08)', () => {
    it.each(['expired', 'consumed', 'revoked', 'unknown'])('ECP-05: a 400 TOKEN_INVALID %s → that status, the way back to the sign-in, no message left, no navigation', async (status) => {
        mocks.confirm.mockRejectedValue(tokenInvalid(status));
        openAt(`/confirm-email-change#token=${TOKEN}`);
        render(EmailChangePage);

        await confirmOnPage();

        await expectStatus(status);
        expect(within(card()).getByTestId('email-change-message')).toHaveTextContent(`email.emailChange.page.${status}`);
        expect(within(card()).getByTestId('email-change-goto-login')).toBeInTheDocument();
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
    });

    it('ECP-06: a status the page does not know is unknown', async () => {
        mocks.confirm.mockRejectedValue(tokenInvalid('something-new'));
        openAt(`/confirm-email-change#token=${TOKEN}`);
        render(EmailChangePage);

        await confirmOnPage();

        await expectStatus('unknown');
    });

    it.each([
        ['a 401 to a visitor', () => refusal(401, 'Not authenticated')],
        ['a 423 instance_blocked to a signed-in browser', () => refusal(423, {code: 'instance_blocked', message: 'blocked'})],
    ])('ECP-07: a blocked instance (%s) → blocked, no retry, nothing left, no navigation', async (_label, make) => {
        mocks.confirm.mockRejectedValue(make());
        openAt(`/confirm-email-change#token=${TOKEN}`);
        render(EmailChangePage);

        await confirmOnPage();

        await expectStatus('blocked');
        expect(within(card()).queryByTestId('email-change-retry')).toBeNull();
        expect(mocks.setAuthFlash).not.toHaveBeenCalled();
        expect(mocks.goto).not.toHaveBeenCalled();
    });

    it('ECP-08: any other failure is error, and its retry asks again for the same token', async () => {
        mocks.confirm.mockRejectedValueOnce(refusal(500, 'boom')).mockResolvedValueOnce({username: 'owner_admin'});
        openAt(`/confirm-email-change#token=${TOKEN}`);
        render(EmailChangePage);

        await confirmOnPage();
        await expectStatus('error');
        await fireEvent.click(within(card()).getByTestId('email-change-retry'));

        await waitFor(() => expect(mocks.goto).toHaveBeenCalledWith('/'));
        expect(mocks.confirm).toHaveBeenCalledTimes(2);
        expect(mocks.confirm).toHaveBeenNthCalledWith(2, {token: TOKEN});
    });
});

describe('/confirm-email-change — a link pasted into the tab already open (ECP-09)', () => {
    it('ECP-09: hashchange replaces the token, leaves the address bar and brings the page back to ready; the click then spends the NEW token', async () => {
        openAt(`/confirm-email-change#token=${TOKEN}`);
        render(EmailChangePage);
        await expectStatus('ready');

        await changeFragment(`/confirm-email-change#token=${NEW_TOKEN}`);
        await waitFor(() => expect(mocks.replaceState).toHaveBeenCalledTimes(2));
        await expectStatus('ready');
        expect(mocks.confirm).not.toHaveBeenCalled();
        await fireEvent.click(within(card()).getByTestId('email-change-confirm'));

        await waitFor(() => expect(mocks.confirm).toHaveBeenCalledWith({token: NEW_TOKEN}));
        expect(mocks.confirm).toHaveBeenCalledTimes(1);
    });
});

describe('/confirm-email-change — the page itself (ECP-10)', () => {
    it('ECP-10: its root, and no referrer', async () => {
        openAt(`/confirm-email-change#token=${TOKEN}`);

        render(EmailChangePage);

        await expectStatus('ready');
        expect(pageRoot()).toBeInTheDocument();
        expect(document.head.querySelector('meta[name="referrer"]')?.getAttribute('content')).toBe('no-referrer');
    });
});
