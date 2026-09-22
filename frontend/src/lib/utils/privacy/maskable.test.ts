/**
 * maskable — the substitution point of U2, unit tested in node (no DOM).
 *
 * This is the whole of the masking decision: everything downstream receives a
 * string and cannot tell whether it is real. So the properties asserted here are
 * not "the function returns the placeholder" — that is trivially true of a stub —
 * but the three that make the placeholder *safe*:
 *
 *  1. it is identical for every magnitude (no order-of-magnitude leak),
 *  2. it is identical for both signs (no up/down leak),
 *  3. an omitted classification masks, because forgetting to classify personal
 *     money must fail closed.
 *
 * Every assertion that something is *absent* is paired, in the same test, with
 * the privacy-off case that shows the same check seeing it present. An absence
 * assertion on its own passes just as well when the test is looking at the wrong
 * string, and that failure is silent.
 *
 * The shared `$app/environment` mock reports `browser: false`, so the store's
 * storage paths are inert here: `setPrivacyEnabled` still applies in memory,
 * which is the only thing this file needs. The storage behaviour is pinned by
 * privacyStore.test.ts / privacyStoreSsr.test.ts instead.
 */
import {afterEach, beforeEach, describe, expect, it} from 'vitest';

import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';

import {maskable, PRIVACY_PLACEHOLDER, shouldMaskAmount, type AmountSensitivity} from './maskable';

/** A formatted amount as a currency formatter would hand it over. */
const SMALL = '1,000.00';
const LARGE = '9,999,999.00';

/**
 * The store lives at module level and is shared with every other suite in the
 * run, so the flag is put back on both sides of each test: a leftover `true`
 * would silently mask the control cases, and a leftover `false` would make the
 * masked ones pass for the wrong reason.
 */
beforeEach(() => setPrivacyEnabled(false));
afterEach(() => setPrivacyEnabled(false));

describe('shouldMaskAmount', () => {
    it('is false while privacy is off, whatever the classification', () => {
        expect(isPrivacyEnabled()).toBe(false);
        expect(shouldMaskAmount()).toBe(false);
        expect(shouldMaskAmount('personal')).toBe(false);
        expect(shouldMaskAmount('public')).toBe(false);
    });

    it('turns on with the flag for personal amounts only', () => {
        setPrivacyEnabled(true);

        expect(shouldMaskAmount()).toBe(true);
        expect(shouldMaskAmount('personal')).toBe(true);
        // Same flag, same call, opposite answer: the `public` false below is a
        // property of the classification, not of a flag that failed to flip.
        expect(shouldMaskAmount('public')).toBe(false);
    });
});

describe('maskable — the off state', () => {
    it('returns the input unchanged, byte for byte', () => {
        expect(maskable(SMALL)).toBe(SMALL);
        expect(maskable(LARGE, 'personal')).toBe(LARGE);
        expect(maskable('-42.00', 'public')).toBe('-42.00');
    });

    it('does not touch an empty or already-placeholder-looking string', () => {
        expect(maskable('')).toBe('');
        expect(maskable(PRIVACY_PLACEHOLDER)).toBe(PRIVACY_PLACEHOLDER);
    });
});

describe('maskable — the on state', () => {
    it('replaces a personal amount with the placeholder', () => {
        // Control first: the same call before the flag, so the assertion below
        // is known to be reading a value the function does change.
        expect(maskable(SMALL)).toBe(SMALL);

        setPrivacyEnabled(true);
        expect(maskable(SMALL)).toBe(PRIVACY_PLACEHOLDER);
        expect(maskable(SMALL, 'personal')).toBe(PRIVACY_PLACEHOLDER);
    });

    it('never touches an amount classified public', () => {
        setPrivacyEnabled(true);

        expect(maskable(SMALL, 'public')).toBe(SMALL);
        // Positive control for the line above: with the flag in this exact
        // state, an unclassified amount *is* replaced. Without it, "public was
        // not masked" would also hold on a run where the flag never turned on.
        expect(maskable(SMALL)).toBe(PRIVACY_PLACEHOLDER);
    });

    it('treats an omitted classification exactly like personal', () => {
        const sensitivities: Array<AmountSensitivity | undefined> = [undefined, 'personal'];

        for (const sensitivity of sensitivities) {
            setPrivacyEnabled(false);
            expect(maskable(SMALL, sensitivity)).toBe(SMALL);

            setPrivacyEnabled(true);
            expect(maskable(SMALL, sensitivity)).toBe(PRIVACY_PLACEHOLDER);
        }

        // And the two are the same value in both states, not merely both
        // "something": a default that masked a *different* way would still pass
        // the loop above.
        setPrivacyEnabled(true);
        expect(maskable(LARGE, undefined)).toBe(maskable(LARGE, 'personal'));
    });
});

describe('maskable — what the placeholder must not carry', () => {
    it('gives two very different magnitudes the identical placeholder', () => {
        // Control: unmasked, these are two obviously different strings of
        // different length. If the assertions below ever passed because both
        // inputs had collapsed to the same thing upstream, this would fail.
        expect(maskable(SMALL)).not.toBe(maskable(LARGE));
        expect(SMALL.length).not.toBe(LARGE.length);

        setPrivacyEnabled(true);
        const small = maskable(SMALL);
        const large = maskable(LARGE);

        expect(small).toBe(PRIVACY_PLACEHOLDER);
        expect(large).toBe(PRIVACY_PLACEHOLDER);
        expect(small).toBe(large);
        // Width is the leak that survives an equality check on content in a
        // padded formatter, so it is asserted in its own right.
        expect(small.length).toBe(large.length);
    });

    it('gives the same placeholder to every order of magnitude', () => {
        const amounts = ['0.00', '9.99', '999.00', '1,000.00', '1,234,567.89', '9,999,999,999.00'];

        // Control: six distinct inputs, so the single-element set below means
        // "collapsed by masking", not "they were the same all along".
        expect(new Set(amounts.map((amount) => maskable(amount))).size).toBe(amounts.length);

        setPrivacyEnabled(true);
        const rendered = amounts.map((amount) => maskable(amount));

        expect(new Set(rendered).size).toBe(1);
        expect(rendered[0]).toBe(PRIVACY_PLACEHOLDER);
    });

    it('drops the sign, so the placeholder cannot say up or down', () => {
        // Control: the sign is genuinely part of these two inputs.
        expect(maskable('+1,000.00')).not.toBe(maskable('-1,000.00'));

        setPrivacyEnabled(true);
        expect(maskable('+1,000.00')).toBe(PRIVACY_PLACEHOLDER);
        expect(maskable('-1,000.00')).toBe(PRIVACY_PLACEHOLDER);
        expect(maskable('+1,000.00')).toBe(maskable('-1,000.00'));
    });

    it('contains no digit at all', () => {
        setPrivacyEnabled(true);

        expect(maskable(LARGE)).not.toMatch(/\d/);
        // The check is able to see a digit when there is one: the same regex on
        // the unmasked value.
        expect(LARGE).toMatch(/\d/);
        expect(maskable(LARGE, 'public')).toMatch(/\d/);
    });
});
