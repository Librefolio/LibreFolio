/**
 * formatFixed — `toFixed`, written the reader's way (M-18 CP1).
 *
 * Numbers follow the UI language (the developer's rule of 2026-10-12), and the 70 `toFixed` sites of
 * CP1 — byte sizes, durations, the other decimals on screen — go through one function:
 *
 *     formatFixed(value, digits, {signed = false, locale = uiLocale()})
 *
 *   - exactly `digits` fraction digits, and the very digits `toFixed(digits)` prints: every figure
 *     stays where it was, only the notation moves;
 *   - the locale's grouping and decimal separator — `1 234,57` in French, with a narrow no-break
 *     space; English gains only its thousands separator;
 *   - `-0` is a plain zero, never `-0,00`;
 *   - `signed` puts a `+` before a positive value, never before zero;
 *   - without `locale`, the UI's (`uiLocale()`): an Italian UI reads `1.234.567,89`.
 *
 * Expectations. Every localized string comes from `Intl.NumberFormat` in this runtime and is never typed:
 * separators are ICU data (Node puts U+202F between French thousands, and which space precedes what has
 * changed between ICU releases), so a typed copy would pin one ICU, not the rule. English is typed where it
 * is today's exact text. Locale cases also check that the notation differs from English: without the
 * locale's ICU data Intl falls back to English, and both sides would agree on nothing worth proving.
 *
 * Rounding. `Intl.NumberFormat` rounds the shortest decimal that reads back as the double — half up on
 * `1.45` — while `toFixed` rounds the double itself, which sits just below: `(1.45).toFixed(1)` is `1.4`,
 * Intl prints `1.5`. A localized `toFixed` keeps toFixed's digits: `formatElapsed(1450)` is pinned at
 * `1.4s` (syncToastHelpers.test.ts), and English must not move by one digit.
 *
 * The browser. The default locale is the UI language, regionalised by `navigator.language` when the two
 * agree (uiLocale.test.ts). Node's follows the host's ICU locale, so it is pinned to en-US before any
 * import, as jsdom's always is.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {formatFixed} from '../formatFixed';

type UiLanguage = 'en' | 'it' | 'fr' | 'es';

/** What Intl writes for `value` in `locale`, with exactly `digits` fraction digits. */
function intlFixed(locale: string, digits: number, value: number): string {
    return new Intl.NumberFormat(locale, {minimumFractionDigits: digits, maximumFractionDigits: digits}).format(value);
}

/** `text` with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
function spelled(text: string): string {
    return text.replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
}

/** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
async function uiLanguage(lang: UiLanguage): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
}

afterEach(async () => {
    // The language is module-level state shared by every test of the file.
    await uiLanguage('en');
});

describe('formatFixed — an explicit locale', () => {
    /** A small number, a negative, one with thousands and one with millions: none sits on a rounding tie. */
    const VALUES = [3.14159, -2.71828, 1234.5678, 1234567.891];
    const DIGITS = [0, 1, 2, 4];

    it.each(['en', 'it', 'fr'])('%s: exactly the requested digits — 0, 1, 2 and 4 — in the locale’s notation', (locale) => {
        for (const digits of DIGITS) {
            for (const value of VALUES) {
                const expected = intlFixed(locale, digits, value);
                expect(formatFixed(value, digits, {locale}), `${value} with ${digits} digits in ${locale}: ${spelled(expected)}`).toBe(expected);
            }
        }
    });

    it.each(['it', 'fr'])('%s really differs from English (control: this runtime carries the locale’s data)', (locale) => {
        expect(intlFixed(locale, 2, 0.5)).not.toBe(intlFixed('en', 2, 0.5));
        expect(formatFixed(0.5, 2, {locale})).toBe(intlFixed(locale, 2, 0.5));
    });

    it('English is toFixed’s text, grouped: 1,234,567.89 and 1,234.6', () => {
        expect(formatFixed(1234567.891, 2, {locale: 'en'})).toBe('1,234,567.89');
        expect(formatFixed(1234.5678, 1, {locale: 'en'})).toBe('1,234.6');
        expect(formatFixed(3.14159, 2, {locale: 'en'})).toBe('3.14');
        expect(formatFixed(1234.5678, 0, {locale: 'en'})).toBe('1,235');
    });

    it('groups thousands the way each locale does: a million in en, it and fr, three notations', () => {
        const locales = ['en', 'it', 'fr'];
        const written = locales.map((locale) => formatFixed(1234567.891, 2, {locale}));

        expect(written).toEqual(locales.map((locale) => intlFixed(locale, 2, 1234567.891)));
        expect(new Set(written).size, `three distinct notations: ${spelled(JSON.stringify(written))}`).toBe(3);
    });
});

describe('formatFixed — the sign', () => {
    it('puts a + before a positive value only when asked', () => {
        expect(formatFixed(1.5, 1, {locale: 'fr'}), 'unsigned by default').toBe(intlFixed('fr', 1, 1.5));
        expect(formatFixed(1.5, 1, {locale: 'fr', signed: true})).toBe(`+${intlFixed('fr', 1, 1.5)}`);
        expect(formatFixed(1234.5, 1, {locale: 'it', signed: true})).toBe(`+${intlFixed('it', 1, 1234.5)}`);
        expect(formatFixed(2.5, 2, {locale: 'en', signed: true})).toBe('+2.50');
    });

    it('never before zero, and a negative keeps its own minus — no "+-"', () => {
        expect(formatFixed(0, 2, {locale: 'fr', signed: true})).toBe(intlFixed('fr', 2, 0));
        expect(formatFixed(-1.5, 1, {locale: 'fr', signed: true})).toBe(intlFixed('fr', 1, -1.5));
        expect(formatFixed(-1.5, 1, {locale: 'fr', signed: true})).not.toContain('+');
    });
});

describe('formatFixed — negative zero', () => {
    it.each(['en', 'it', 'fr'])('writes -0 as a plain zero in %s, signed or not, however it was produced', (locale) => {
        // Intl alone keeps the minus of -0: the guard has to run before the number reaches it.
        expect(intlFixed(locale, 2, -0), 'control: Intl prints a minus on -0').toMatch(/^[-\u2212]/);

        for (const digits of [0, 2]) {
            const zero = intlFixed(locale, digits, 0);
            expect(formatFixed(-0, digits, {locale}), `-0, ${digits} digits`).toBe(zero);
            expect(formatFixed(-0, digits, {locale, signed: true}), `-0, ${digits} digits, signed`).toBe(zero);
            // A rounding that lands on -0, as a display computation does.
            expect(formatFixed(Math.round(-0.4), digits, {locale}), `Math.round(-0.4), ${digits} digits`).toBe(zero);
        }
    });
});

describe('formatFixed — the digits are toFixed’s, not Intl’s rounding', () => {
    it.each([
        // formatElapsed(1450) is pinned at "1.4s".
        [1.45, 1],
        // formatPercent's own example of a value sitting just below its midpoint.
        [1.005, 2],
        [2.675, 2],
    ])('%d to %i fraction digit(s): the digits toFixed prints, in every notation', (value, digits) => {
        const toFixedDigits = Number(value.toFixed(digits));
        for (const locale of ['en', 'it', 'fr']) {
            const expected = intlFixed(locale, digits, toFixedDigits);
            // Control: the case really tells the two roundings apart.
            expect(intlFixed(locale, digits, value), `control: Intl rounds ${value} its own way in ${locale}`).not.toBe(expected);
            expect(formatFixed(value, digits, {locale}), `${value} in ${locale}: ${spelled(expected)}`).toBe(expected);
        }
        // English, exactly today's text.
        expect(formatFixed(value, digits, {locale: 'en'})).toBe(value.toFixed(digits));
    });
});

describe('formatFixed — without a locale, the UI language', () => {
    const MILLION = 1234567.891;

    it('English UI on an en-US browser: en-US, toFixed’s text grouped', async () => {
        await uiLanguage('en');

        expect(formatFixed(MILLION, 2)).toBe(intlFixed('en-US', 2, MILLION));
        expect(formatFixed(3.14159, 2)).toBe('3.14');
    });

    it('Italian UI: Italian notation, without passing a locale', async () => {
        await uiLanguage('it');
        const expected = intlFixed('it', 2, MILLION);
        expect(expected, 'control: Italian differs from English').not.toBe(intlFixed('en-US', 2, MILLION));

        expect(formatFixed(MILLION, 2), spelled(expected)).toBe(expected);
        expect(formatFixed(1.5, 1, {signed: true})).toBe(`+${intlFixed('it', 1, 1.5)}`);
    });

    it('follows the UI language from one call to the next: it → fr → en', async () => {
        const written: Record<string, string> = {};
        for (const lang of ['it', 'fr', 'en'] as const) {
            await uiLanguage(lang);
            written[lang] = formatFixed(MILLION, 2);
        }

        expect(written).toEqual({it: intlFixed('it', 2, MILLION), fr: intlFixed('fr', 2, MILLION), en: intlFixed('en-US', 2, MILLION)});
    });

    it('an explicit locale still wins over the UI language', async () => {
        await uiLanguage('it');

        expect(formatFixed(MILLION, 2, {locale: 'fr'})).toBe(intlFixed('fr', 2, MILLION));
        expect(formatFixed(MILLION, 2, {locale: 'en'})).toBe('1,234,567.89');
    });
});
