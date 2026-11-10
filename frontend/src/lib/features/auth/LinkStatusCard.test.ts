// @vitest-environment jsdom
/**
 * LinkStatusCard — what an invitation or password-reset link page shows instead of its form (accounts lot A5b).
 *
 * The two link pages show a form only for a link the server calls valid. Every other outcome is this card: while the
 * server is asked, when the link is spent or unknown, when the page was opened with no token, when the instance has
 * closed registration, and when the check itself failed.
 *
 * The contract (plan A5b.1):
 *   - the root `link-status`, with `data-status` among `checking`, `expired`, `consumed`, `revoked`, `unknown`,
 *     `missing`, `closed` and `error` — the handle the pages and the E2E specs read, since the message is translated;
 *   - the message: `auth.link.<status>` for expired, consumed, revoked, unknown and missing; `auth.link.checkFailed`
 *     for error; `auth.registrationDisabled` for closed; `common.loading` while checking;
 *   - `auth.link.askAdmin` beside the message of the five dead-link statuses: only an administrator can send a new link.
 *     Not while checking, and not for a failed check, where the remedy is the retry;
 *   - `link-status-goto-login` goes to `/` (`goto` of `$app/navigation`);
 *   - `link-status-retry` only for `error`, and only when the page passed `onretry`, which it calls.
 *
 * On not asserting translated text. `$lib/i18n` keeps its real exports with the translator replaced by the identity,
 * so a message renders as its key. Every assertion names a key, stable in EN/IT/FR/ES; `keysShown` reads which of the
 * card's known keys are on screen, so a red names all of them at once.
 *
 * Written red-first, before `LinkStatusCard.svelte` exists: the file fails on the import until it does.
 *
 * Accounts lot A7b (F02, the initial administrator; plan A7b, C1): where a new link comes from depends on the page. On
 * `/invite` and `/reset-password` an administrator sends one, hence `auth.link.askAdmin`; on `/setup` no administrator
 * exists yet — the setup link comes from the hosting provider, or from `./dev.py user setup-link` — so that page passes
 * its own line, `auth.setup.newLinkHint`. The contract: an optional prop `hintKey` (default `auth.link.askAdmin`), drawn
 * for the same five dead-link statuses as before and for no other, in `link-status-hint`. The describe «the hint, the
 * page's to choose» is red until A7b: today the line has no test id and the prop does not exist. The cases above keep
 * pinning the default.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

const mocks = vi.hoisted(() => ({
    goto: vi.fn((..._args: unknown[]) => Promise.resolve()).mockName('goto'),
}));

vi.mock('$app/navigation', () => ({goto: mocks.goto, replaceState: vi.fn(), pushState: vi.fn(), invalidate: vi.fn(), invalidateAll: vi.fn(), preloadCode: vi.fn(), preloadData: vi.fn(), afterNavigate: vi.fn(), beforeNavigate: vi.fn(), onNavigate: vi.fn()}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const identity = readable((key: string) => key);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});

import LinkStatusCard from './LinkStatusCard.svelte';

type LinkStatus = 'checking' | 'expired' | 'consumed' | 'revoked' | 'unknown' | 'missing' | 'closed' | 'error';

const STATUSES: LinkStatus[] = ['checking', 'expired', 'consumed', 'revoked', 'unknown', 'missing', 'closed', 'error'];
/** The links that will never work again: only an administrator can send a new one. */
const DEAD_LINKS: LinkStatus[] = ['expired', 'consumed', 'revoked', 'unknown', 'missing'];
const ASK_ADMIN = 'auth.link.askAdmin';

/** The message of each status, by key. */
const MESSAGE: Record<LinkStatus, string> = {
    checking: 'common.loading',
    expired: 'auth.link.expired',
    consumed: 'auth.link.consumed',
    revoked: 'auth.link.revoked',
    unknown: 'auth.link.unknown',
    missing: 'auth.link.missing',
    closed: 'auth.registrationDisabled',
    error: 'auth.link.checkFailed',
};

/** Every message key the card can show, the advice included. */
const KNOWN_KEYS = [...new Set([...Object.values(MESSAGE), ASK_ADMIN])];

const root = () => screen.getByTestId('link-status');

/**
 * The card's known keys it draws, in a fixed order: as text or as an accessible name (a spinner may say
 * `common.loading` through `aria-label` alone), hence the markup rather than `textContent`.
 */
function keysShown(): string[] {
    const markup = root().innerHTML;
    return KNOWN_KEYS.filter((key) => markup.includes(key));
}

beforeEach(() => {
    mocks.goto.mockClear();
});

afterEach(cleanup);

describe('LinkStatusCard — the status, as data-status', () => {
    it.each(STATUSES)('publishes data-status="%s" on link-status', (status) => {
        render(LinkStatusCard, {props: {status}});

        expect(root()).toHaveAttribute('data-status', status);
    });

    it('follows the status the page passes, without a remount', async () => {
        const {rerender} = render(LinkStatusCard, {props: {status: 'checking' as LinkStatus, onretry: vi.fn()}});
        expect(root()).toHaveAttribute('data-status', 'checking');

        await rerender({status: 'error'});

        expect(root()).toHaveAttribute('data-status', 'error');
        expect(screen.getByTestId('link-status-retry')).toBeInTheDocument();
    });
});

describe('LinkStatusCard — what it says', () => {
    it.each(STATUSES)('says the message of %s', (status) => {
        render(LinkStatusCard, {props: {status}});

        expect(keysShown()).toContain(MESSAGE[status]);
    });

    it.each(DEAD_LINKS)('adds the advice to ask an administrator for a new link when the link is %s', (status) => {
        render(LinkStatusCard, {props: {status}});

        expect(keysShown()).toEqual([MESSAGE[status], ASK_ADMIN]);
    });

    it.each(['checking', 'error'] as LinkStatus[])('gives no such advice while %s: nothing is wrong with the link', (status) => {
        render(LinkStatusCard, {props: {status}});

        expect(keysShown()).toEqual([MESSAGE[status]]);
    });

    it('says registration is closed, and nothing about the link, when the instance has closed it', () => {
        render(LinkStatusCard, {props: {status: 'closed'}});

        expect(keysShown()).toEqual([MESSAGE.closed]);
    });
});

describe("LinkStatusCard — the hint, the page's to choose (A7b)", () => {
    /** The line `/setup` passes: no administrator exists yet to ask for a new link. */
    const SETUP_HINT = 'auth.setup.newLinkHint';

    /** The hint line, by its test id; `null` when the card draws none. */
    const hint = () => within(root()).queryByTestId('link-status-hint');

    // red until A7b
    it.each(DEAD_LINKS)('draws auth.link.askAdmin in link-status-hint when the page passes no hintKey and the link is %s', (status) => {
        render(LinkStatusCard, {props: {status}});

        expect(hint(), 'the hint line, by its test id').not.toBeNull();
        expect(hint()?.textContent?.trim(), 'the default: an administrator sends the new link').toBe(ASK_ADMIN);
    });

    // red until A7b
    it.each(DEAD_LINKS)("draws the page's hintKey in its place when the link is %s, and not auth.link.askAdmin", (status) => {
        render(LinkStatusCard, {props: {status, hintKey: SETUP_HINT}});

        expect(hint(), 'the hint line, by its test id').not.toBeNull();
        expect(hint()?.textContent?.trim(), 'the key the page passed').toBe(SETUP_HINT);
        expect(root().innerHTML, 'the default is replaced, not added to').not.toContain(ASK_ADMIN);
        expect(keysShown(), 'the message itself does not change').toEqual([MESSAGE[status]]);
    });

    // red until A7b
    it.each(['checking', 'closed', 'error'] as LinkStatus[])('draws no hint while %s, though the page passed one; the same card draws it once the link turns out expired', async (status) => {
        const {rerender} = render(LinkStatusCard, {props: {status, hintKey: SETUP_HINT, onretry: vi.fn()}});

        expect(root(), 'premise: the card is drawn').toHaveAttribute('data-status', status);
        expect(keysShown(), 'premise: with its message').toContain(MESSAGE[status]);
        expect(hint()).toBeNull();
        expect(root().innerHTML).not.toContain(SETUP_HINT);

        // The control: the absence above is the status's doing, not a hint line that is never drawn.
        await rerender({status: 'expired'});

        expect(hint()?.textContent?.trim()).toBe(SETUP_HINT);
    });
});

describe('LinkStatusCard — the way back to the login page', () => {
    it.each(['expired', 'missing', 'closed', 'error'] as LinkStatus[])('goes to / from %s', async (status) => {
        render(LinkStatusCard, {props: {status, onretry: vi.fn()}});

        await fireEvent.click(screen.getByTestId('link-status-goto-login'));

        expect(mocks.goto).toHaveBeenCalledTimes(1);
        expect(mocks.goto.mock.calls[0][0]).toBe('/');
    });
});

describe('LinkStatusCard — the retry, for a check that failed', () => {
    it('offers it for error when the page can retry, and calls the page back', async () => {
        const onretry = vi.fn();
        render(LinkStatusCard, {props: {status: 'error', onretry}});

        await fireEvent.click(screen.getByTestId('link-status-retry'));

        expect(onretry).toHaveBeenCalledTimes(1);
        expect(mocks.goto, 'a retry stays on the page').not.toHaveBeenCalled();
    });

    it('offers no retry for error when the page passed none', () => {
        render(LinkStatusCard, {props: {status: 'error'}});

        expect(root(), 'premise: the card is drawn').toHaveAttribute('data-status', 'error');
        expect(screen.queryByTestId('link-status-retry')).toBeNull();
    });

    it.each(STATUSES.filter((status) => status !== 'error'))('offers no retry for %s, even with onretry passed', (status) => {
        render(LinkStatusCard, {props: {status, onretry: vi.fn()}});

        expect(root(), 'premise: the card is drawn').toHaveAttribute('data-status', status);
        expect(screen.queryByTestId('link-status-retry')).toBeNull();
    });
});

describe('LinkStatusCard — the support link (A5-6)', () => {
    const SUPPORT_LABEL = 'auth.setup.supportLink';

    it('draws a link to the page passed as supportHref, under the hint, with its own test id', () => {
        render(LinkStatusCard, {props: {status: 'expired', hintKey: 'auth.setup.expiredManagedSupportHint', supportHref: 'https://support.example.com/help'}});

        const link = within(root()).getByTestId('link-status-support');
        expect(link).toHaveAttribute('href', 'https://support.example.com/help');
        expect(link.textContent).toContain(SUPPORT_LABEL);
        expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
    });

    it('opens a mailto in the mail program: no new tab', () => {
        render(LinkStatusCard, {props: {status: 'expired', supportHref: 'mailto:help@example.com'}});

        const link = within(root()).getByTestId('link-status-support');
        expect(link).toHaveAttribute('href', 'mailto:help@example.com');
        expect(link).not.toHaveAttribute('target');
    });

    it("draws none without supportHref: today's card is unchanged", () => {
        render(LinkStatusCard, {props: {status: 'expired'}});

        expect(within(root()).queryByTestId('link-status-support')).toBeNull();
    });

    it.each(['checking', 'error', 'closed'] as LinkStatus[])('draws none while %s, whatever the page passes: nothing is wrong with the link', (status) => {
        render(LinkStatusCard, {props: {status, supportHref: 'mailto:help@example.com'}});

        expect(within(root()).queryByTestId('link-status-support')).toBeNull();
    });
});
