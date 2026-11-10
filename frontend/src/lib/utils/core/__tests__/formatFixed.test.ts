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
 *
 * priceFractionDigits and formatPrice (C-97c-1, decision D-C97c-1 of the coordinator, 17/10; the last two blocks). A
 * price was written with a fixed 2–4 decimals, so a tiny one read `0.00`. A price now carries the decimals its first four
 * significant digits need, between a floor and a cap of twelve:
 *
 *     priceFractionDigits(value, {minDecimals = 2, floorDecimals = minDecimals}) → {min, max}
 *         min = minDecimals
 *         max = min(12, max(floorDecimals, 3 − ⌊log10 |value|⌋)), and for 0: min(12, max(floorDecimals, minDecimals))
 *     formatPrice(value, {minDecimals, floorDecimals, signed = false, locale = uiLocale()})
 *
 *   - Intl writes the value with those fraction digits: a string as the exact decimal it writes (an Intl string
 *     literal, half-expand on its own digits), a number as a number; trailing zeros drop down to `min`;
 *   - `signed` puts a `+` before a positive value; `-0` prints as `0`;
 *   - `null`, `undefined`, `''`, a non-numeric or a non-finite input give `''`: it never echoes its input.
 * The cases are the contract's table, in English through the `locale` option, and its one Italian case — by the option
 * and by the interface language. The few rows derived from the definition rather than copied from the table say so.
 * Both functions are read through the module namespace, as formatExactDecimal was: absent, each case fails on its
 * assertion and names the absence.
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

// ---------------------------------------------------------------------------
// priceFractionDigits and formatPrice — a price with the digits it needs (C-97c-1, D-C97c-1)
// ---------------------------------------------------------------------------

/** The decimals of a price (D-C97c-1). */
interface PriceDecimalsOptions {
    minDecimals?: number;
    floorDecimals?: number;
}

/** What `formatPrice` takes besides the decimals. */
interface FormatPriceOptions extends PriceDecimalsOptions {
    signed?: boolean;
    locale?: string;
}

/** The signatures C-97c-1 gives the two functions. */
type PriceFractionDigits = (value: number | string, options?: PriceDecimalsOptions) => {min: number; max: number};
type FormatPrice = (value: number | string | null | undefined, options?: FormatPriceOptions) => string;

/** What formatFixed.ts exports under `name`, read when asked: nothing before C-97c-1. */
function exportedPriceHelper(name: 'priceFractionDigits' | 'formatPrice'): unknown {
    return (formatFixedModule as unknown as Record<string, unknown>)[name];
}

/** `priceFractionDigits(value, options)`; while it is not exported, a marker no expectation equals, naming the absence. */
function fractionDigitsOf(value: number | string, options?: PriceDecimalsOptions): unknown {
    const exported = exportedPriceHelper('priceFractionDigits');
    return typeof exported === 'function' ? (exported as PriceFractionDigits)(value, options) : '‹priceFractionDigits is not exported by formatFixed.ts›';
}

/** `formatPrice(value, options)`; while it is not exported, a marker no expectation equals, naming the absence. */
function price(value: number | string | null | undefined, options?: FormatPriceOptions): string {
    const exported = exportedPriceHelper('formatPrice');
    return typeof exported === 'function' ? (exported as FormatPrice)(value, options) : '‹formatPrice is not exported by formatFixed.ts›';
}

/** The three sites of D-C97c-1 that pass options of their own. */
const FX_RATE: PriceDecimalsOptions = {minDecimals: 4};
const DATA_EDITOR: PriceDecimalsOptions = {minDecimals: 0, floorDecimals: 4};
const RUNNING_WAC: PriceDecimalsOptions = {minDecimals: 2, floorDecimals: 4};

interface DigitsCase {
    value: number | string;
    options?: PriceDecimalsOptions;
    expected: {min: number; max: number};
    why: string;
}

interface PriceCase {
    value: number | string;
    en: string;
    why: string;
}

describe('priceFractionDigits — the fraction digits of a price: its first four significant ones, between a floor and 12 (C-97c-1)', () => {
    it('is exported by formatFixed.ts, as a function', () => {
        expect(typeof exportedPriceHelper('priceFractionDigits'), 'formatFixed.ts exports priceFractionDigits').toBe('function');
    });

    it.each<DigitsCase>([
        {value: 0.0000034573, expected: {min: 2, max: 9}, why: 'a tiny price: 3 − ⌊log10⌋ = 3 + 6'},
        {value: 123.45, expected: {min: 2, max: 2}, why: 'a price that needs fewer keeps the floor'},
        {value: 0.5, expected: {min: 2, max: 4}, why: 'below one: 3 + 1'},
        {value: 123.4567, options: RUNNING_WAC, expected: {min: 2, max: 4}, why: 'the running WAC’s floor of four'},
        // Derived from the definition, not rows of the contract's table.
        {value: 0, expected: {min: 2, max: 2}, why: 'zero needs just minDecimals (derived)'},
        {value: 1e-13, expected: {min: 2, max: 12}, why: 'sixteen needed, capped at twelve (derived)'},
        {value: '0.000000123456789012', expected: {min: 2, max: 10}, why: 'a string, read as the decimal it writes (derived)'},
    ])('priceFractionDigits($value, $options) is $expected — $why', ({value, options, expected}) => {
        expect(fractionDigitsOf(value, options)).toEqual(expected);
    });
});

describe('formatPrice — a price written with the digits it needs, in the interface language (C-97c-1)', () => {
    it('is exported by formatFixed.ts, as a function', () => {
        expect(typeof exportedPriceHelper('formatPrice'), 'formatFixed.ts exports formatPrice').toBe('function');
    });

    it.each<PriceCase>([
        {value: 0.0000034573, en: '0.000003457', why: 'a tiny price keeps four significant digits, where 2–4 decimals read 0.00'},
        {value: 1.23456, en: '1.235', why: 'four significant digits, rounded'},
        {value: 123.45, en: '123.45', why: 'the floor of two'},
        {value: 65000.123, en: '65,000.12', why: 'grouped, at the floor of two'},
        {value: 0.5, en: '0.50', why: 'padded to minDecimals'},
        {value: 0, en: '0.00', why: 'zero: minDecimals'},
        {value: -0.000123, en: '-0.000123', why: 'a negative keeps its minus, the trailing zero drops'},
        {value: '1.2345', en: '1.235', why: 'a string: half-expand on the exact decimal'},
        {value: '0.000000123456789012', en: '0.0000001235', why: 'a string with more digits than a double holds'},
        {value: 1e-13, en: '0.00', why: 'capped at twelve decimals, the zeros beyond two dropped'},
    ])('default options: $value is $en — $why', ({value, en}) => {
        expect(price(value, {locale: 'en'})).toBe(en);
    });

    it.each<PriceCase>([
        {value: 1.5, en: '+1.50', why: 'a positive value gains a +'},
        {value: -1.5, en: '-1.50', why: 'a negative keeps its own minus'},
        {value: 0, en: '0.00', why: 'zero gains no sign'},
    ])('signed: $value is $en — $why', ({value, en}) => {
        expect(price(value, {signed: true, locale: 'en'})).toBe(en);
    });

    it.each<PriceCase>([
        {value: 1.0834, en: '1.0834', why: 'four decimals, as a rate always had'},
        {value: 1.08345678, en: '1.0835', why: 'rounded at the fourth'},
        {value: 0.000123456, en: '0.0001235', why: 'a tiny rate keeps four significant digits, where four decimals read 0.0001'},
    ])('an FX rate, {minDecimals: 4}: $value is $en — $why', ({value, en}) => {
        expect(price(value, {...FX_RATE, locale: 'en'})).toBe(en);
    });

    it.each<PriceCase>([
        {value: 1.5, en: '1.5', why: 'no padding'},
        {value: 1.23456, en: '1.2346', why: 'the floor of four, rounded'},
        {value: 0.000003457312, en: '0.000003457', why: 'four significant digits, where four decimals read 0'},
        {value: 1234567, en: '1,234,567', why: 'an integer stays one'},
    ])('the data editor, {minDecimals: 0, floorDecimals: 4}: $value is $en — $why', ({value, en}) => {
        expect(price(value, {...DATA_EDITOR, locale: 'en'})).toBe(en);
    });

    it.each<PriceCase>([
        {value: 123.4567, en: '123.4567', why: 'the floor of four'},
        {value: 123.5, en: '123.50', why: 'padded to two, the trailing zeros beyond dropped'},
    ])('a running WAC, {minDecimals: 2, floorDecimals: 4}: $value is $en — $why', ({value, en}) => {
        expect(price(value, {...RUNNING_WAC, locale: 'en'})).toBe(en);
    });

    it('-0 prints as 0, signed or not — never -0.00', () => {
        // Intl alone keeps the minus of -0: the guard has to act before the value reaches it.
        expect(new Intl.NumberFormat('en', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(-0), 'control: Intl prints a minus on -0').toBe('-0.00');

        expect({unsigned: price(-0, {locale: 'en'}), signed: price(-0, {signed: true, locale: 'en'})}).toEqual({unsigned: '0.00', signed: '0.00'});
    });

    it('a string is written as the exact decimal it is, a number as a number: 0.12344999999999999999 is 0.1234, its double 0.1235', () => {
        const text = '0.12344999999999999999';
        expect(Number(text), 'control: as a double the string reads 0.12345').toBe(0.12345);
        const fourDecimals = new Intl.NumberFormat('en', {minimumFractionDigits: 2, maximumFractionDigits: 4});
        expect({string: fourDecimals.format(text as Intl.StringNumericLiteral), number: fourDecimals.format(Number(text))}, 'control: at four decimals Intl tells the decimal from its double').toEqual({string: '0.1234', number: '0.1235'});

        expect({string: price(text, {locale: 'en'}), number: price(Number(text), {locale: 'en'})}).toEqual({string: '0.1234', number: '0.1235'});
    });

    it.each([
        {value: null, label: 'null'},
        {value: undefined, label: 'undefined'},
        {value: '', label: "''"},
        {value: 'abc', label: "'abc'"},
        {value: NaN, label: 'NaN'},
        {value: Infinity, label: 'Infinity'},
        {value: -Infinity, label: '-Infinity'},
        {value: 'Infinity', label: "'Infinity'"},
    ])('$label gives "" — nothing to write, and the input is never echoed', ({value}) => {
        expect(price(value, {locale: 'en'})).toBe('');
    });

    it('Italian: 65000.123 is 65.000,12 — by the locale option, and by the interface language without one', async () => {
        const italian = intlFixed('it', 2, 65000.12);
        expect(italian, 'control: this runtime writes the contract’s Italian').toBe('65.000,12');

        expect(price(65000.123, {locale: 'it'}), 'the locale option').toBe(italian);
        await uiLanguage('it');
        expect(uiLocale(), 'control: an Italian UI on the en-US browser is written it').toBe('it');
        expect(price(65000.123), 'no locale: the interface language').toBe(italian);
    });

    it('without a locale, an English UI on the en-US browser writes en-US', async () => {
        await uiLanguage('en');
        expect(uiLocale(), 'control: an English UI on the en-US browser is written en-US').toBe('en-US');

        expect({grouped: price(65000.123), tiny: price(0.0000034573)}).toEqual({grouped: '65,000.12', tiny: '0.000003457'});
    });
});
