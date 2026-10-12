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
 *
 * formatExactDecimal (M-18 CP3a, last block). The figures `toFixed` never printed: the decimals the backend
 * sends as strings — quantities, FX rates, split ratios, scenario parameters — shown exact through
 * `formatDecimalForDisplay`, but always with a dot and no grouping, in every language. The cure:
 *
 *     formatExactDecimal(value, {minFrac = 0, maxFrac = 8, locale = uiLocale()})
 *
 *   - the digits are `formatDecimalForDisplay(value, {minFrac, maxFrac})`'s: cut at `maxFrac`, never rounded;
 *     trailing zeros dropped; padded to `minFrac`; `-0` is `0`;
 *   - that string — never a double — goes to `Intl.NumberFormat` with exactly its fraction digits, which reads it
 *     as an exact decimal (Intl.NumberFormat v3): Intl places only the decimal separator, the grouping and the minus;
 *   - what is not a plain decimal comes back as `formatDecimalForDisplay` returns it; `null`, `undefined` and `''`
 *     are `''`.
 * Expectations are Intl's own output for the same digits, handed over as a string too. The plain digits are typed,
 * since a plain decimal carries no locale, and each is checked against `formatDecimalForDisplay` first. The function
 * does not exist before CP3a, so it is read through the module namespace at call time: absent, the first case says
 * so and every other one fails on its assertion, never on a TypeError at import.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatDecimalForDisplay} from '../formatDecimal';
import * as formatFixedModule from '../formatFixed';
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

// ---------------------------------------------------------------------------
// formatExactDecimal — the exact decimals in the interface language (M-18 CP3a)
// ---------------------------------------------------------------------------

interface ExactDecimalOptions {
    minFrac?: number;
    maxFrac?: number;
    locale?: string;
}

/** The signature CP3a gives `formatExactDecimal`. */
type FormatExactDecimal = (value: string | number | null | undefined, options?: ExactDecimalOptions) => string;

/** What formatFixed.ts exports as `formatExactDecimal`, read when asked: nothing before CP3a. */
function exportedExactDecimal(): unknown {
    return (formatFixedModule as unknown as {formatExactDecimal?: unknown}).formatExactDecimal;
}

/** A call's answer while there is no such export: no expectation equals it, so a case fails on its assertion and names the absence. */
const NOT_EXPORTED = '‹formatExactDecimal is not exported by formatFixed.ts›';

/** `formatExactDecimal(value, options)`; NOT_EXPORTED until the function exists. */
function exactDecimal(value: string | number | null | undefined, options?: ExactDecimalOptions): string {
    const exported = exportedExactDecimal();
    return typeof exported === 'function' ? (exported as FormatExactDecimal)(value, options) : NOT_EXPORTED;
}

/**
 * What Intl writes for the plain decimal `text` in `locale`, with exactly its own fraction digits. Intl is handed
 * the string, which Intl.NumberFormat v3 reads as an exact decimal: no double in between, so no digit is lost.
 */
function intlExact(locale: string, text: string): string {
    const fractionDigits = text.split('.')[1]?.length ?? 0;
    return new Intl.NumberFormat(locale, {minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits}).format(text as Intl.StringNumericLiteral);
}

/** The digits of a text, whatever a locale writes between them. */
function digitsOf(text: string): string {
    return text.replace(/\D/g, '');
}

describe('formatExactDecimal — an exact decimal string, written in the interface language (M-18 CP3a)', () => {
    /** The notation of an English UI on the pinned en-US browser, and of an Italian, a French and a Spanish one. */
    const LOCALES = ['en-US', 'it', 'fr', 'es'] as const;

    it('is exported by formatFixed.ts, as a function', () => {
        expect(typeof exportedExactDecimal(), 'formatFixed.ts exports formatExactDecimal').toBe('function');
    });

    it.each(LOCALES)('%s: every digit of a decimal beyond float precision — Intl is handed the string, never a double', (locale) => {
        const value = '12345678901234.123456789012';
        expect(String(Number(value)), 'control: as a double, the value loses digits').not.toBe(value);
        const expected = intlExact(locale, value);
        expect(digitsOf(expected), `control: this runtime's Intl reads the string exactly: ${spelled(expected)}`).toBe(digitsOf(value));

        expect(exactDecimal(value, {maxFrac: 20, locale}), spelled(expected)).toBe(expected);
    });

    it.each(LOCALES)('%s: the digits of formatDecimalForDisplay — cut at maxFrac, eight by default, leaving no trailing zero behind', (locale) => {
        const cases: Array<[string, ExactDecimalOptions, string, string]> = [
            ['191.5059166043', {maxFrac: 7}, '191.5059166', 'cut at the seventh digit'],
            ['191.5059166043', {}, '191.5059166', 'cut at the default eighth, a zero, which goes too'],
            ['1.234567891234', {}, '1.23456789', 'the default maximum is eight'],
        ];
        for (const [value, options, digits, why] of cases) {
            expect(formatDecimalForDisplay(value, options), `control: formatDecimalForDisplay, ${why}`).toBe(digits);
            const expected = intlExact(locale, digits);
            expect(exactDecimal(value, {...options, locale}), `${value}, ${why}: ${spelled(expected)}`).toBe(expected);
        }
    });

    it.each(LOCALES)('%s: cuts, never rounds — 1.99999999999 stays 1.99999999, and 2.675 at two digits 2.67, where Intl alone rounds', (locale) => {
        const cases: Array<[string, number, string]> = [
            ['1.99999999999', 8, '1.99999999'],
            ['2.675', 2, '2.67'],
        ];
        for (const [value, maxFrac, digits] of cases) {
            expect(formatDecimalForDisplay(value, {maxFrac}), `control: formatDecimalForDisplay cuts ${value}`).toBe(digits);
            const expected = intlExact(locale, digits);
            const rounded = new Intl.NumberFormat(locale, {maximumFractionDigits: maxFrac}).format(value as Intl.StringNumericLiteral);
            expect(rounded, `control: Intl alone rounds ${value} otherwise in ${locale}, so the case tells the two apart`).not.toBe(expected);

            expect(exactDecimal(value, {maxFrac, locale}), `${value} at ${maxFrac} digits: ${spelled(expected)}`).toBe(expected);
        }
    });

    it.each(LOCALES)('%s: drops insignificant trailing zeros — 6.000000 is 6, 6.500000 is 6.5', (locale) => {
        const cases: Array<[string, string]> = [
            ['6.000000', '6'],
            ['6.500000', '6.5'],
            ['-0.250', '-0.25'],
            ['42.00', '42'],
        ];
        for (const [value, digits] of cases) {
            expect(formatDecimalForDisplay(value), `control: formatDecimalForDisplay of ${value}`).toBe(digits);
            const expected = intlExact(locale, digits);
            expect(exactDecimal(value, {locale}), `${value}: ${spelled(expected)}`).toBe(expected);
        }
    });

    it.each(LOCALES)('%s: pads to minFrac — 6 with two is 6.00, 6.5 is 6.50, and a longer fraction keeps its digits', (locale) => {
        const cases: Array<[string, string]> = [
            ['6', '6.00'],
            ['6.5', '6.50'],
            ['6.125', '6.125'],
        ];
        for (const [value, digits] of cases) {
            expect(formatDecimalForDisplay(value, {minFrac: 2}), `control: formatDecimalForDisplay of ${value} with minFrac 2`).toBe(digits);
            const expected = intlExact(locale, digits);
            expect(exactDecimal(value, {minFrac: 2, locale}), `${value} with minFrac 2: ${spelled(expected)}`).toBe(expected);
        }
    });

    it.each(LOCALES)('%s: a negative keeps its minus; -0, and a negative cut down to zero, are a plain 0', (locale) => {
        for (const value of ['-0.00000123', '-1234.5']) {
            const expected = intlExact(locale, value);
            expect(exactDecimal(value, {locale}), `${value}: ${spelled(expected)}`).toBe(expected);
        }

        // Intl alone keeps the minus of a negative zero: the guard has to act on the digits, before Intl.
        expect(intlExact(locale, '-0'), 'control: Intl prints a minus on -0').toMatch(/^[-\u2212]/);
        const zero = intlExact(locale, '0');
        for (const value of ['-0', '-0.000', '-0.000000001']) {
            expect(formatDecimalForDisplay(value), `control: formatDecimalForDisplay reads ${value} as 0`).toBe('0');
            expect(exactDecimal(value, {locale}), `${value} is a plain zero`).toBe(zero);
        }
    });

    it('groups the thousands the way each language does: 12345.678 in en-US, it, fr and es', () => {
        const value = '12345.678';
        const expected: Record<string, string> = Object.fromEntries(LOCALES.map((locale) => [locale, intlExact(locale, value)]));
        for (const locale of LOCALES) expect(digitsOf(expected[locale]), `control: ${locale} keeps the digits`).toBe(digitsOf(value));
        for (const locale of ['it', 'fr', 'es']) expect(expected[locale], `control: ${locale} differs from en-US (this runtime carries its data)`).not.toBe(expected['en-US']);

        const written = Object.fromEntries(LOCALES.map((locale) => [locale, exactDecimal(value, {locale})]));
        expect(written, spelled(JSON.stringify(expected))).toEqual(expected);
    });

    it('a four-digit integer part: en-US and fr group it, it and es do not — Intl’s own grouping, never a forced one', () => {
        const value = '1234.5';
        const expected: Record<string, string> = Object.fromEntries(LOCALES.map((locale) => [locale, intlExact(locale, value)]));
        // Controls: what this runtime's data says, and that the case tells Intl's default grouping from a forced one.
        expect(expected.it, 'control: Italian puts no separator in a four-digit integer part').toHaveLength(value.length);
        expect(expected.es, 'control: Spanish neither').toHaveLength(value.length);
        expect(expected['en-US'], 'control: English groups it').toHaveLength(value.length + 1);
        expect(expected.fr, 'control: French groups it').toHaveLength(value.length + 1);
        const forced = new Intl.NumberFormat('it', {minimumFractionDigits: 1, maximumFractionDigits: 1, useGrouping: 'always'}).format(value as Intl.StringNumericLiteral);
        expect(forced, 'control: a forced grouping would write a separator in Italian').not.toBe(expected.it);

        const written = Object.fromEntries(LOCALES.map((locale) => [locale, exactDecimal(value, {locale})]));
        expect(written, spelled(JSON.stringify(expected))).toEqual(expected);
    });

    it.each(LOCALES)('%s: a number is written from the digits formatDecimalForDisplay reads in it', (locale) => {
        const cases: Array<[number, string, string]> = [
            [1234.5, '1234.5', 'thousands and a fraction'],
            [-0.25, '-0.25', 'a negative'],
            [0.1 + 0.2, '0.3', 'the float noise past the eighth digit is cut'],
            [-0, '0', 'a negative zero'],
        ];
        for (const [value, digits, why] of cases) {
            expect(formatDecimalForDisplay(value), `control: formatDecimalForDisplay, ${why}`).toBe(digits);
            const expected = intlExact(locale, digits);
            expect(exactDecimal(value, {locale}), `${value}, ${why}: ${spelled(expected)}`).toBe(expected);
        }
    });

    it.each(LOCALES)('%s: what is not a plain decimal comes back as formatDecimalForDisplay returns it; null, undefined and "" are empty', (locale) => {
        for (const value of ['abc', '1,5', '1e3', '12 345']) {
            expect(formatDecimalForDisplay(value), `control: ${value} is not a plain decimal`).toBe(value);
            expect(exactDecimal(value, {locale}), `${value} comes back unchanged`).toBe(value);
        }
        for (const value of [null, undefined, '']) {
            expect(exactDecimal(value, {locale}), `${JSON.stringify(value) ?? 'undefined'} is empty`).toBe('');
        }
    });

    it('without a locale, the interface language, from one call to the next: English (en-US browser) → Italian → French → Spanish', async () => {
        const LOCALE_OF = {en: 'en-US', it: 'it', fr: 'fr', es: 'es'} as const;
        const value = '12345.678';
        const written: Record<string, string> = {};
        for (const lang of ['en', 'it', 'fr', 'es'] as const) {
            await uiLanguage(lang);
            expect(uiLocale(), `control: the interface locale of a ${lang} UI on an en-US browser`).toBe(LOCALE_OF[lang]);
            written[lang] = exactDecimal(value);
        }

        expect(written).toEqual({en: intlExact('en-US', value), it: intlExact('it', value), fr: intlExact('fr', value), es: intlExact('es', value)});
    });

    it('Italian UI: Italian notation without a locale, the digit options still applied', async () => {
        await uiLanguage('it');
        const expected = {grouped: intlExact('it', '12345.678'), padded: intlExact('it', '6.00'), cut: intlExact('it', '191.5059166')};
        expect(expected.grouped, 'control: Italian differs from English').not.toBe(intlExact('en-US', '12345.678'));

        expect({grouped: exactDecimal('12345.678'), padded: exactDecimal('6', {minFrac: 2}), cut: exactDecimal('191.5059166043', {maxFrac: 7})}).toEqual(expected);
    });

    it('an explicit locale still wins over the interface language', async () => {
        await uiLanguage('it');

        expect(exactDecimal('12345.678', {locale: 'fr'})).toBe(intlExact('fr', '12345.678'));
        expect(exactDecimal('12345.678', {locale: 'en-US'})).toBe(intlExact('en-US', '12345.678'));
    });
});
