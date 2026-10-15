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
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '$test/component';

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
