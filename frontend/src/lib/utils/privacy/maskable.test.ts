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

import {maskable, maskableQuantity, maskCurrencyParts, maskFormattedNumber, PRIVACY_PLACEHOLDER, shouldMaskAmount, type AmountSensitivity} from './maskable';

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

/**
 * maskCurrencyParts — the same placeholder, applied to the parts of an `Intl` string.
 *
 * A formatter that lets `Intl` place the currency cannot mask its whole output
 * without hiding the currency too, and the product owner ruled that out on
 * 2026-09-22: privacy hides the number, not the currency. So only the magnitude
 * run of the parts becomes the placeholder; the currency, the sign and the
 * literals around the number stay.
 *
 * Properties 1 and 3 of the header hold unchanged. Property 2 holds for the
 * placeholder, not for the rendered string: `-$•••` and `$•••` differ, because
 * the sign stays outside the mask by decision D8 (see `maskable`).
 *
 * The parts come from a real `Intl.NumberFormat` with a pinned locale, because
 * where the currency and the sign sit is exactly what the locale decides.
 * Unmasked, the expectation is the same formatter's `format()`: that string is
 * the host's ICU data, not this function's output to pin. Masked, it is an exact
 * literal, measured with node (ICU 78.3): a placeholder has no locale, and what
 * surrounds it is the layout this function exists to preserve.
 */
describe('maskCurrencyParts', () => {
    const usd = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'});
    const eurIt = new Intl.NumberFormat('it-IT', {style: 'currency', currency: 'EUR'});
    /** The options of the lot comparison axis: in compact notation the suffix carries the scale. */
    const compactFormatter = (locale: string, currency: string) => new Intl.NumberFormat(locale, {style: 'currency', currency, notation: 'compact', currencyDisplay: 'narrowSymbol', maximumFractionDigits: 1});

    it('returns exactly what format() returns while privacy is off', () => {
        const cases: Array<[Intl.NumberFormat, number]> = [
            [usd, 1234.5],
            [usd, -1234.5],
            [eurIt, 1234.5],
            [eurIt, -1234.5],
        ];

        for (const [formatter, value] of cases) {
            expect(maskCurrencyParts(formatter.formatToParts(value))).toBe(formatter.format(value));
            expect(maskCurrencyParts(formatter.formatToParts(value), 'personal')).toBe(formatter.format(value));
        }
    });

    it('masks the digits of en-US USD and keeps the currency and the sign', () => {
        // Control: the same parts in the clear, so the two lines below are a
        // substitution and not a function that always returns a placeholder.
        expect(maskCurrencyParts(usd.formatToParts(1234.5))).toBe(usd.format(1234.5));

        setPrivacyEnabled(true);
        expect(maskCurrencyParts(usd.formatToParts(1234.5))).toBe('$•••');
        expect(maskCurrencyParts(usd.formatToParts(-1234.5))).toBe('-$•••');
    });

    it('keeps a currency written after the number, with its separator (it-IT)', () => {
        expect(maskCurrencyParts(eurIt.formatToParts(1234.5))).toBe(eurIt.format(1234.5));

        setPrivacyEnabled(true);
        // The separator is U+00A0 NO-BREAK SPACE, not the narrow U+202F that
        // fr-FR uses between digit groups. It sits outside the magnitude run,
        // so it stays with the currency.
        expect(maskCurrencyParts(eurIt.formatToParts(1234.5))).toBe('•••\u00A0€');
        expect(maskCurrencyParts(eurIt.formatToParts(-1234.5))).toBe('-•••\u00A0€');
    });

    it('swallows the compact suffix into one placeholder (de-DE)', () => {
        const formatter = compactFormatter('de-DE', 'EUR');
        const parts = formatter.formatToParts(1234567);

        // Control: in the clear the suffix and the digits are there, so the
        // absence checks below are able to see them.
        const clear = maskCurrencyParts(parts);
        expect(clear).toBe(formatter.format(1234567));
        expect(clear).toContain('Mio.');
        expect(clear).toMatch(/\d/);

        setPrivacyEnabled(true);
        const masked = maskCurrencyParts(parts);

        // `1,2 Mio.` is one run: the no-break space between the digits and the
        // suffix goes with it, the one before `€` (U+00A0 again) stays.
        expect(masked).toBe('•••\u00A0€');
        expect(masked.split(PRIVACY_PLACEHOLDER)).toHaveLength(2);
        expect(masked).not.toContain('Mio.');
        expect(masked).not.toMatch(/\d/);
        expect(masked).toContain('€');
    });

    it('keeps the sign of a compact loss and hides its suffix (en-US)', () => {
        const formatter = compactFormatter('en-US', 'USD');
        const parts = formatter.formatToParts(-1234567);

        const clear = maskCurrencyParts(parts);
        expect(clear).toBe(formatter.format(-1234567));
        expect(clear).toContain('M');

        setPrivacyEnabled(true);
        // `-$•••M` would still say "millions": the suffix is magnitude.
        expect(maskCurrencyParts(parts)).toBe('-$•••');
        expect(maskCurrencyParts(parts)).not.toContain('M');
    });

    it('keeps the symbol the locale actually prints (ja-JP)', () => {
        const jpy = new Intl.NumberFormat('ja-JP', {style: 'currency', currency: 'JPY'});
        expect(maskCurrencyParts(jpy.formatToParts(12345))).toBe(jpy.format(12345));

        setPrivacyEnabled(true);
        // U+FFE5 FULLWIDTH YEN SIGN, which is what ja-JP prints — not the
        // U+00A5 `¥` of other locales.
        expect(maskCurrencyParts(jpy.formatToParts(12345))).toBe('\uFFE5•••');
    });

    it('gives very different magnitudes the identical masked string, with no digit in it', () => {
        const small = usd.formatToParts(1);
        const large = usd.formatToParts(9876543210.98);
        // In compact notation the digits can be identical and the suffix alone
        // tells thousands from millions: `$1.2K` and `$1.2M`.
        const thousands = compactFormatter('en-US', 'USD').formatToParts(1234);
        const millions = compactFormatter('en-US', 'USD').formatToParts(1234567);

        // Control: in the clear the plain pair differs by content and length,
        // the compact pair by content only, and the digits are visible.
        expect(maskCurrencyParts(small)).not.toBe(maskCurrencyParts(large));
        expect(maskCurrencyParts(small).length).not.toBe(maskCurrencyParts(large).length);
        expect(maskCurrencyParts(thousands)).not.toBe(maskCurrencyParts(millions));
        expect(maskCurrencyParts(thousands).length).toBe(maskCurrencyParts(millions).length);
        expect(maskCurrencyParts(large)).toMatch(/\d/);

        setPrivacyEnabled(true);
        const rendered = [small, large, thousands, millions].map((parts) => maskCurrencyParts(parts));

        expect(new Set(rendered).size).toBe(1);
        expect(rendered[0]).toBe('$•••');
        expect(rendered[0]).not.toMatch(/\d/);
    });

    it('never masks an amount classified public', () => {
        setPrivacyEnabled(true);

        expect(maskCurrencyParts(usd.formatToParts(1234.5), 'public')).toBe(usd.format(1234.5));
        // Positive control: same flag, same parts, and a personal amount —
        // explicit or omitted — is masked. Without it, "public was not masked"
        // would also hold on a run where the flag never turned on.
        expect(maskCurrencyParts(usd.formatToParts(1234.5), 'personal')).toBe('$•••');
        expect(maskCurrencyParts(usd.formatToParts(1234.5))).toBe('$•••');
    });

    it('keeps a currency part that sits inside the magnitude run', () => {
        // Synthetic parts: they pin the rule, not a locale. A part typed
        // `currency` is the currency wherever it sits, so it survives after the
        // single placeholder instead of being swallowed with the digits.
        const parts: Intl.NumberFormatPart[] = [
            {type: 'integer', value: '12'},
            {type: 'currency', value: '$'},
            {type: 'fraction', value: '50'},
        ];
        expect(maskCurrencyParts(parts)).toBe('12$50');

        setPrivacyEnabled(true);
        expect(maskCurrencyParts(parts)).toBe('•••$');
    });

    it('returns the parts joined when there is no magnitude to hide', () => {
        setPrivacyEnabled(true);

        // Neither a sign nor a currency is a magnitude: nothing to replace, and
        // no placeholder conjured out of nothing.
        const noMagnitude: Intl.NumberFormatPart[] = [
            {type: 'minusSign', value: '-'},
            {type: 'currency', value: '€'},
        ];
        expect(maskCurrencyParts(noMagnitude)).toBe('-€');
        expect(maskCurrencyParts([])).toBe('');
        // Positive control: in this exact state, parts that do carry a
        // magnitude are masked.
        expect(maskCurrencyParts(usd.formatToParts(1))).toBe('$•••');
    });
});

/**
 * maskFormattedNumber — the placeholder for a number that is already a string.
 *
 * An axis tick built by a shared helper carries no currency and does not come
 * as `Intl` parts, so `maskCurrencyParts` has nothing to work on. Here the
 * leading sign run is kept and everything after it — digits, separators, the
 * compact suffix — becomes one placeholder.
 *
 * The sign is kept exactly as the locale wrote it, invisible bidi marks
 * included (D8, see `maskable`). Rebuilding it as an ASCII hyphen is what once
 * turned the unmasked Swedish axis from U+2212 into `-`. So the locale inputs
 * below are real `Intl` output, measured with node (ICU 78.3, CLDR 48), and
 * each masked expectation spells the measured prefix code point by code point.
 */
describe('maskFormattedNumber', () => {
    /** Digits in the three scripts the inputs are written in: ASCII, Arabic-Indic, Extended Arabic-Indic. */
    const ANY_DIGIT = /[\d\u0660-\u0669\u06F0-\u06F9]/;
    const svSE = new Intl.NumberFormat('sv-SE').format(-1234);
    const ar = new Intl.NumberFormat('ar').format(-1234);
    const arEG = new Intl.NumberFormat('ar-EG').format(-1234);
    const fa = new Intl.NumberFormat('fa').format(-1234);

    it('returns the formatted string unchanged while privacy is off', () => {
        for (const formatted of ['-1.2K', '1.2K', '+12', svSE, ar, arEG, fa]) {
            expect(maskFormattedNumber(formatted)).toBe(formatted);
            expect(maskFormattedNumber(formatted, 'personal')).toBe(formatted);
        }
    });

    it('keeps an ASCII sign and drops everything after it, compact suffix included (en-US)', () => {
        // Control: the same call in the clear, so the lines below are a
        // substitution and not a function that always returns a placeholder.
        expect(maskFormattedNumber('-1.2K')).toBe('-1.2K');

        setPrivacyEnabled(true);
        expect(maskFormattedNumber('-1.2K')).toBe('-•••');
        // `•••K` would still say "thousands": the suffix goes with the digits.
        expect(maskFormattedNumber('1.2K')).toBe('•••');
        expect(maskFormattedNumber('+12')).toBe('+•••');
    });

    it('keeps the U+2212 minus that sv-SE writes, instead of an ASCII hyphen', () => {
        // Precondition, measured rather than assumed: sv-SE starts with U+2212
        // MINUS SIGN, so the expectation below can tell it from a hyphen.
        expect(svSE.startsWith('\u2212')).toBe(true);

        setPrivacyEnabled(true);
        expect(maskFormattedNumber(svSE)).toBe('\u2212•••');
    });

    it('keeps the invisible bidi mark in front of the minus (ar, ar-EG)', () => {
        // Preconditions, measured: plain `ar` resolves to Latin digits on this
        // ICU and writes a left-to-right mark before the hyphen; ar-EG writes
        // Arabic-Indic digits behind an Arabic letter mark.
        expect(ar.startsWith('\u200E\u002D')).toBe(true);
        expect(arEG.startsWith('\u061C\u002D')).toBe(true);

        setPrivacyEnabled(true);
        // U+200E LEFT-TO-RIGHT MARK, U+002D HYPHEN-MINUS, then the placeholder.
        expect(maskFormattedNumber(ar)).toBe('\u200E\u002D•••');
        // U+061C ARABIC LETTER MARK, U+002D HYPHEN-MINUS, then the placeholder.
        expect(maskFormattedNumber(arEG)).toBe('\u061C\u002D•••');
    });

    it('never masks a number classified public', () => {
        setPrivacyEnabled(true);

        expect(maskFormattedNumber('-1.2K', 'public')).toBe('-1.2K');
        expect(maskFormattedNumber(svSE, 'public')).toBe(svSE);
        // Positive control: same flag, same input, and a personal number —
        // explicit or omitted — is masked. Without it, "public was not masked"
        // would also hold on a run where the flag never turned on.
        expect(maskFormattedNumber('-1.2K', 'personal')).toBe('-•••');
        expect(maskFormattedNumber('-1.2K')).toBe('-•••');
    });

    it('leaves no digit behind, whatever script the digits were written in', () => {
        const inputs = ['-1.2K', svSE, ar, arEG, fa];

        // Control: every input carries digits the regex can see — ASCII in the
        // first three, Arabic-Indic (U+0660–U+0669) in ar-EG and Extended
        // Arabic-Indic (U+06F0–U+06F9) in fa — so the absence below is not a
        // regex that sees nothing.
        for (const formatted of inputs) {
            expect(formatted).toMatch(ANY_DIGIT);
        }
        expect(arEG).toMatch(/[\u0660-\u0669]/);
        expect(fa).toMatch(/[\u06F0-\u06F9]/);

        setPrivacyEnabled(true);
        for (const formatted of inputs) {
            const masked = maskFormattedNumber(formatted);
            expect(masked).not.toMatch(ANY_DIGIT);
            expect(masked.endsWith(PRIVACY_PLACEHOLDER)).toBe(true);
        }
    });
});

/**
 * maskableQuantity — a quantity the user holds, where it sits next to a price.
 *
 * Decision D5′ of the product owner, 2026-09-23: a quantity is masked in
 * positions and lots, because quantity × public price rebuilds what the user
 * owns, and stays visible in transactions. The class of a quantity is decided by
 * its context, not by its formatter, so this function has no sensitivity
 * parameter at all: a site that must show a quantity simply does not call it.
 *
 * It masks like `maskFormattedNumber` — the leading sign, as the locale wrote
 * it, stays outside the placeholder — so a short position keeps its direction.
 */
describe('maskableQuantity', () => {
    const svSE = new Intl.NumberFormat('sv-SE').format(-1234);

    it('returns the formatted quantity unchanged while privacy is off', () => {
        for (const formatted of ['12.5', '-3', '1,000.5', svSE]) {
            expect(maskableQuantity(formatted)).toBe(formatted);
        }
    });

    it('masks a quantity to the bare placeholder', () => {
        // Control: the same call in the clear, so the line below is a
        // substitution and not a function that always returns a placeholder.
        expect(maskableQuantity('12.5')).toBe('12.5');

        setPrivacyEnabled(true);
        expect(maskableQuantity('12.5')).toBe('•••');
    });

    it('keeps the sign, so a short position keeps its direction', () => {
        setPrivacyEnabled(true);

        expect(maskableQuantity('-3')).toBe('-•••');
        expect(maskableQuantity('-3')).not.toBe(maskableQuantity('3'));
    });

    it('keeps the U+2212 minus that sv-SE writes', () => {
        // Precondition, measured rather than assumed: sv-SE starts with U+2212
        // MINUS SIGN, so the expectation below can tell it from a hyphen.
        expect(svSE.startsWith('\u2212')).toBe(true);

        setPrivacyEnabled(true);
        expect(maskableQuantity(svSE)).toBe('\u2212•••');
    });

    it('leaves no digit behind', () => {
        const inputs = ['12.5', '-3', '1,000.5', svSE];
        // Control: every input carries a digit the check can see.
        for (const formatted of inputs) {
            expect(formatted).toMatch(/\d/);
        }

        setPrivacyEnabled(true);
        for (const formatted of inputs) {
            expect(maskableQuantity(formatted)).not.toMatch(/\d/);
        }
    });

    it('has no notion of public: the call site decides, and under privacy it always masks', () => {
        // Arity 1: there is no second parameter to pass a classification through.
        expect(maskableQuantity.length).toBe(1);

        setPrivacyEnabled(true);
        // The general number mask can be told a figure is public; a quantity
        // beside a price cannot, so the same input comes back masked here.
        expect(maskFormattedNumber('12.5', 'public')).toBe('12.5');
        expect(maskableQuantity('12.5')).toBe('•••');
    });
});
