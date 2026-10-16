// @vitest-environment jsdom
/**
 * VerifyEmailCard — what the page of a verification link shows (workstream E, lot E5a; developer decision 44).
 *
 * The contract under test:
 *   - the card is the `verify-email-status` card of `AuthCard`, carrying its status in `data-status`, and words each of
 *     the eight statuses of the page with `VERIFY_PAGE_KEYS[status]` (`email.verification.page.<status>`) in
 *     `verify-email-message`, a polite live region;
 *   - «back to the sign-in» (`verify-email-goto-login`, `auth.backToLogin`) goes to `/`, offered for every status but
 *     `checking` — a dead link is never the end: signing in offers a new one, and nothing sends anyone to an
 *     administrator;
 *   - «try again» (`verify-email-retry`, `common.retry`) only for `error`, and only when the page gave an `onretry`; a
 *     click calls it once and goes nowhere;
 *   - a blocked instance (lot E-10): `blocked` is worded like the others, `email.verification.page.blocked`, and offers
 *     the way back to the sign-in but no «try again», even with the `onretry` the page always gives: trying again
 *     changes nothing while the instance is blocked;
 *   - the card follows its props and the language: a new status, or a new translator, rewords it in place.
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

const STATUSES: VerifyPageStatus[] = ['checking', 'expired', 'consumed', 'revoked', 'unknown', 'missing', 'error', 'blocked'];
/** Every status but the wait: the card then offers the way back to the sign-in. */
const SETTLED = STATUSES.filter((status) => status !== 'checking');

const card = () => screen.getByTestId('verify-email-status');
const message = () => screen.getByTestId('verify-email-message');
const backToLogin = () => screen.queryByTestId('verify-email-goto-login');
const retry = () => screen.queryByTestId('verify-email-retry');

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

    it('VEC-02: while checking, there is nothing to do — no way back, no retry', () => {
        render(VerifyEmailCard, {props: {status: 'checking', onretry: vi.fn()}});

        expect(backToLogin()).toBeNull();
        expect(retry()).toBeNull();
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
        render(VerifyEmailCard, {props: {status, onretry: vi.fn()}});

        expect(retry()).toBeNull();
        expect(within(card()).getAllByRole('button')).toHaveLength(1);
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
