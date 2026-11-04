// @vitest-environment jsdom
/**
 * VerifyEmailCard — what the page of a verification link shows (workstream E, lots E5a and E-25; developer decision 44).
 *
 * The contract under test:
 *   - the card is the `verify-email-status` card of `AuthCard`, carrying its status in `data-status`, and words each of
 *     the nine statuses of the page with `VERIFY_PAGE_KEYS[status]` (`email.verification.page.<status>`) in
 *     `verify-email-message`, a polite live region;
 *   - `ready` (lot E-25): the link is read but not spent — a corporate mail scanner opens links in a sandboxed browser
 *     that runs scripts, so only a click may spend it. The card then shows a primary «confirm»
 *     (`verify-email-confirm`, `email.verification.page.confirm`), only when the page gave an `onconfirm`: a click calls
 *     it once and goes nowhere; and a hint for whoever did not sign up (`verify-email-hint`,
 *     `email.verification.page.notSignedUp`), with or without `onconfirm`. There is no «try again» and no way back to
 *     the sign-in: the only thing to do is confirm. Without an `onconfirm` there is no button at all, as with a retry
 *     without an `onretry`;
 *   - the «confirm» and the hint appear in `ready` and nowhere else, `onconfirm` given or not;
 *   - «back to the sign-in» (`verify-email-goto-login`, `auth.backToLogin`) goes to `/`, offered for every status but
 *     `checking` and `ready` — a dead link is never the end: signing in offers a new one, and nothing sends anyone to
 *     an administrator;
 *   - «try again» (`verify-email-retry`, `common.retry`) only for `error`, and only when the page gave an `onretry`; a
 *     click calls it once and goes nowhere;
 *   - a blocked instance (lot E-10): `blocked` is worded like the others, `email.verification.page.blocked`, and offers
 *     the way back to the sign-in but no «try again», even with the `onretry` the page always gives: trying again
 *     changes nothing while the instance is blocked;
 *   - the card follows its props and the language: a new status, or a new translator, rewords it in place; leaving
 *     `ready` takes the «confirm» and the hint away from the same card.
 *
 * Mocks: `$app/navigation` (`goto`, a spy); `$lib/i18n`: `_` is a writable translator owned by this file, answering
 * `[<language>] <key>`, so an assertion names the key the card chose, never a sentence of the catalogue. What runs for
 * real: the card, `AuthCard` and `emailText.ts`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const fake = vi.hoisted(() => ({
    /** The translator of one language: `[it] email.verification.page.expired`. */
    translatorFor: (language: string) => (key: string) => `[${language}] ${key}`,
    goto: vi.fn((..._args: unknown[]) => Promise.resolve()).mockName('goto'),
}));

vi.mock('$app/navigation', () => ({goto: fake.goto}));
vi.mock('$lib/i18n', async () => {
    const {writable} = await import('svelte/store');
    return {_: writable(fake.translatorFor('en'))};
});

import VerifyEmailCard from './VerifyEmailCard.svelte';
import {_} from '$lib/i18n';
import type {VerifyPageStatus} from './emailText';

const translator = _ as unknown as Writable<(key: string) => string>;

const STATUSES: VerifyPageStatus[] = ['checking', 'ready', 'expired', 'consumed', 'revoked', 'unknown', 'missing', 'error', 'blocked'];
/** Every status but the wait and the click still to come: the card then offers the way back to the sign-in. */
const SETTLED = STATUSES.filter((status) => status !== 'checking' && status !== 'ready');
/** Every status but `ready`: the «confirm» and the hint belong to the click still to come, and to nothing else. */
const NOT_READY = STATUSES.filter((status) => status !== 'ready');

const card = () => screen.getByTestId('verify-email-status');
const message = () => screen.getByTestId('verify-email-message');
const backToLogin = () => screen.queryByTestId('verify-email-goto-login');
const retry = () => screen.queryByTestId('verify-email-retry');
const confirmButton = () => screen.queryByTestId('verify-email-confirm');
const hint = () => screen.queryByTestId('verify-email-hint');

beforeAll(() => {
    // The absences asserted below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
});

beforeEach(() => {
    fake.goto.mockClear();
    translator.set(fake.translatorFor('en'));
});

afterEach(() => {
    cleanup();
});

describe('VerifyEmailCard — one card per status', () => {
    it.each(STATUSES)('VEC-01: %s — the card carries its status, and words it with its own key in a polite live region', (status) => {
        render(VerifyEmailCard, {props: {status}});

        expect(card()).toHaveAttribute('data-status', status);
        expect(message()).toHaveTextContent(`[en] email.verification.page.${status}`);
        expect(message()).toHaveAttribute('aria-live', 'polite');
        expect(within(card()).queryAllByRole('link'), 'no link: nothing sends anyone elsewhere, to an administrator least of all').toEqual([]);
    });

    it('VEC-02: while checking, there is nothing to do — no way back, no retry, no confirm, even with both callbacks', () => {
        render(VerifyEmailCard, {props: {status: 'checking', onretry: vi.fn(), onconfirm: vi.fn()}});

        expect(backToLogin()).toBeNull();
        expect(retry()).toBeNull();
        expect(confirmButton(), 'the click is already given: it is spent once').toBeNull();
        expect(within(card()).queryAllByRole('button')).toEqual([]);
    });

    it.each(SETTLED)('VEC-03: %s — the way back to the sign-in goes to /', async (status) => {
        render(VerifyEmailCard, {props: {status}});

        expect(backToLogin()).toHaveTextContent('[en] auth.backToLogin');
        await fireEvent.click(backToLogin()!);

        expect(fake.goto).toHaveBeenCalledTimes(1);
        expect(fake.goto).toHaveBeenCalledWith('/');
    });
});

describe('VerifyEmailCard — «try again», for a check that failed', () => {
    it('VEC-04: error with an onretry — the retry calls it once and goes nowhere', async () => {
        const onretry = vi.fn();
        render(VerifyEmailCard, {props: {status: 'error', onretry}});

        expect(retry()).toHaveTextContent('[en] common.retry');
        await fireEvent.click(retry()!);

        expect(onretry).toHaveBeenCalledTimes(1);
        expect(fake.goto).not.toHaveBeenCalled();
        expect(within(card()).getAllByRole('button')).toHaveLength(2);
    });

    it('VEC-05: error without an onretry — no retry, the way back only', () => {
        render(VerifyEmailCard, {props: {status: 'error'}});

        expect(retry()).toBeNull();
        expect(backToLogin()).not.toBeNull();
    });

    it.each(SETTLED.filter((status) => status !== 'error'))('VEC-06: %s — only a check that failed is tried again: no retry even with an onretry', (status) => {
        render(VerifyEmailCard, {props: {status, onretry: vi.fn(), onconfirm: vi.fn()}});

        expect(retry()).toBeNull();
        expect(within(card()).getAllByRole('button'), 'the way back is all there is: no retry, no confirm').toHaveLength(1);
    });
});

describe('VerifyEmailCard — it follows its props and the language', () => {
    it('VEC-07: a new status rewords the card in place, and a change of language rewords it again', async () => {
        const view = render(VerifyEmailCard, {props: {status: 'checking'}});
        const before = card();

        await view.rerender({status: 'expired'});

        expect(card(), 'the same card, not a new one').toBe(before);
        expect(card()).toHaveAttribute('data-status', 'expired');
        expect(message()).toHaveTextContent('[en] email.verification.page.expired');
        expect(backToLogin()).not.toBeNull();

        translator.set(fake.translatorFor('it'));
        await view.rerender({status: 'expired'});

        expect(message()).toHaveTextContent('[it] email.verification.page.expired');
        expect(backToLogin()).toHaveTextContent('[it] auth.backToLogin');
    });
});

describe('VerifyEmailCard — a blocked instance (lot E-10)', () => {
    it('VEC-08: blocked, with the onretry the page always gives — the block’s own words, the way back to the sign-in, and no retry', async () => {
        const onretry = vi.fn();
        render(VerifyEmailCard, {props: {status: 'blocked', onretry}});

        expect(card()).toHaveAttribute('data-status', 'blocked');
        expect(message()).toHaveTextContent('[en] email.verification.page.blocked');
        expect(retry(), 'trying again changes nothing while the instance is blocked').toBeNull();
        expect(backToLogin()).toHaveTextContent('[en] auth.backToLogin');
        expect(within(card()).getAllByRole('button'), 'the way back is all there is to do').toHaveLength(1);

        await fireEvent.click(backToLogin()!);

        expect(fake.goto).toHaveBeenCalledTimes(1);
        expect(fake.goto).toHaveBeenCalledWith('/');
        expect(onretry).not.toHaveBeenCalled();
    });
});

describe('VerifyEmailCard — «confirm», the click that spends the link (lot E-25)', () => {
    it('VEC-09: ready with an onconfirm — a primary confirm and the hint, no retry, no way back; the click calls onconfirm once and goes nowhere', async () => {
        const onconfirm = vi.fn();
        render(VerifyEmailCard, {props: {status: 'ready', onconfirm, onretry: vi.fn()}});

        expect(card()).toHaveAttribute('data-status', 'ready');
        expect(confirmButton(), 'the click that spends the link').not.toBeNull();
        expect(confirmButton()).toHaveTextContent('[en] email.verification.page.confirm');
        expect(hint(), 'a line for whoever did not sign up').not.toBeNull();
        expect(hint()).toHaveTextContent('[en] email.verification.page.notSignedUp');
        expect(message()).toHaveTextContent('[en] email.verification.page.ready');
        expect(retry(), 'there is nothing to try again before the first click').toBeNull();
        expect(backToLogin(), 'the only thing to do is confirm').toBeNull();
        expect(within(card()).getAllByRole('button')).toHaveLength(1);

        await fireEvent.click(confirmButton()!);

        expect(onconfirm).toHaveBeenCalledTimes(1);
        expect(fake.goto).not.toHaveBeenCalled();
    });

    it('VEC-10: ready without an onconfirm — no confirm button, no way back, and the hint still shown', () => {
        render(VerifyEmailCard, {props: {status: 'ready'}});

        expect(card()).toHaveAttribute('data-status', 'ready');
        expect(hint(), 'the hint does not depend on the callback').not.toBeNull();
        expect(hint()).toHaveTextContent('[en] email.verification.page.notSignedUp');
        expect(message()).toHaveTextContent('[en] email.verification.page.ready');
        expect(confirmButton(), 'no callback, no button').toBeNull();
        expect(retry()).toBeNull();
        expect(backToLogin(), 'a missing callback is no way out either').toBeNull();
        expect(within(card()).queryAllByRole('button')).toEqual([]);
    });

    it.each(NOT_READY)('VEC-11: %s — no confirm and no hint, even with an onconfirm: they belong to ready alone', (status) => {
        render(VerifyEmailCard, {props: {status, onconfirm: vi.fn()}});

        expect(card(), 'the card is there: the absences below are not an empty page').toHaveAttribute('data-status', status);
        expect(message()).toHaveTextContent(`[en] email.verification.page.${status}`);
        expect(confirmButton()).toBeNull();
        expect(hint()).toBeNull();
    });

    it('VEC-12: leaving ready takes the confirm and the hint away from the same card, and a change of language rewords them while they are there', async () => {
        const onconfirm = vi.fn();
        const view = render(VerifyEmailCard, {props: {status: 'ready', onconfirm}});
        const before = card();
        expect(confirmButton(), 'ready offers the confirm').not.toBeNull();
        expect(confirmButton()).toHaveTextContent('[en] email.verification.page.confirm');

        translator.set(fake.translatorFor('it'));
        await view.rerender({status: 'ready', onconfirm});

        expect(confirmButton()).toHaveTextContent('[it] email.verification.page.confirm');
        expect(hint()).toHaveTextContent('[it] email.verification.page.notSignedUp');

        await view.rerender({status: 'checking', onconfirm});

        expect(card(), 'the same card, not a new one').toBe(before);
        expect(card()).toHaveAttribute('data-status', 'checking');
        expect(confirmButton(), 'once clicked, it cannot be clicked again').toBeNull();
        expect(hint()).toBeNull();
        expect(within(card()).queryAllByRole('button')).toEqual([]);
    });
});
