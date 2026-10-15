/**
 * format — the R14 money and solver display, and the R7 plural counts, of the planner's privacy
 * adapter (Vitest, node).
 *
 * Subject. `format.ts` is the only place where the planner turns a value into text, and R14
 * changed how a computed amount looks. An amount the backend computed, sent as an exact decimal
 * or as an exact ratio of two integers, is shown at the minor unit of its currency. It is rounded
 * exactly, and carries `≈` only when that rounding changed the value. Under test:
 *   - `exactMoneyDisplay`: the rounded text, and whether it is approximate, for both wire shapes;
 *   - `formatExactMoneyPlain` / `formatExactMoneyHtml`: that rule composed with the shared
 *     currency formatter, in the clear and with privacy on;
 *   - `formatPlannerMoneyPlain`: a raw amount, rounded to the minor unit only when asked;
 *   - `formatSolverNumber`, by unit: money at the minor unit; a count or a penalty to two decimals,
 *     public; squared money through the L2 formatter;
 *   - `formatPlannerL2`: squared money has no minor unit, so it is shown to two decimals, rounded
 *     exactly, with `≈` only when the rounding changed the value, whichever wire shape it came in;
 *   - `formatObjectiveValue` for a money unit;
 *   - R7, the plural counts `plannerQuantityCount`, `exactQuantityCount` and
 *     `plannerPlainDecimalCount`. Each is the number an ICU plural selects on, the twin of a display
 *     function (`formatPlannerQuantity`, `formatExactQuantity`, `formatPlannerPlainDecimal`) with
 *     the same input and sensitivity. A count is read off the digits the user sees, never off
 *     `Number(value)`: the integer part without its sign (plural operands are absolute), plus 0.5
 *     when a fraction is shown. CLDR then gets the text's `i` and `v > 0`, so French reads 1.5 as
 *     singular and English as plural. Twenty fraction digits, which `Number()` rounds to 1, stay a
 *     fraction; a 21st digit is not shown, so it does not count. An exact ratio counts its display
 *     projection. Over valid, invalid and absent values, with privacy off and on, the count is the
 *     count of the shown text: the twin property.
 *
 * G3, below the minor unit. A nonzero amount whose rounding at the minor unit would give zero is
 * never shown as zero (`0`, `≈0.00`, `≈-0.00`): it keeps about two significant digits instead,
 * rounded half away from zero at one place past its first nonzero fraction digit (at most twenty
 * places), with `≈` only when that rounding changed the value. A ledger rounding residual of
 * -47/21700 EUR reads `≈-0.0022`, a residual of exactly -0.0021 reads `-0.0021`. A true zero,
 * `-0.00` included, is an exact `0`, and an amount whose rounding at the minor unit is not zero is
 * shown as before. The rule belongs to `exactMoneyDisplay` and the money formatters built on it.
 * An L2 distance and a raw solver number are not adaptive: `0.004` there is still `≈0`, and two
 * guards pin that.
 *
 * Expectations. The host locale decides digits, separators and grouping, so an expected amount
 * is never a literal. It is the output of the shared `formatCurrencyAmountPlain/Html` for the
 * rounded value, called with the options the adapter must pass (personal, with the currency's
 * minor unit as both fraction bounds), with `≈` in front where the rounding changed the value.
 * That would be circular if the shared formatter were broken. So the digits of the clear outputs
 * are checked once against the value put in, and each case that turns on the rounding also checks
 * that the dropped digits are gone. The L2 distance prints its digits with the plain number format
 * (`toLocaleString`, at most two decimals) of the interface locale — en-US in every case but the
 * M-18 block's, where the UI is English and the browser pinned to en-US — so its expected text is
 * that format applied to the rounded value, its digits are checked in every case, and its values
 * stay below 1000 so that no grouping separator is involved. Masked strings have no locale (a
 * placeholder), so those are exact literals. A solver count is written by the FX-rate formatter, so
 * since M-18 CP3a in the interface locale: below 1000 en-US writes the plain decimal, so those stay
 * literals; the one above 1000 is Intl's en-US output for its digits, grouped. The plural counts,
 * plain numbers, are exact literals too. `toBe` compares them with `Object.is`, so NaN matches NaN; a
 * plural rule reads -0 as 0, and the table of counts does too.
 *
 * Privacy. Decision c: wealth is personal. With privacy on the number becomes the placeholder.
 * The `≈` marker, the sign and the currency (symbol, flag, code) stay outside the mask. A solver
 * count is not wealth and stays in the clear. Each masked case first proves that the flag is on,
 * then compares against an exact string, so an amount left in the clear cannot pass as masked.
 * A plural count follows its display twin. A masked quantity counts NaN, which every plural rule
 * selects as `other`: a singular next to the placeholder would reveal a hidden 1. A public decimal
 * keeps its count.
 *
 * Catalogue. The currency catalogue answers with EUR and JPY, symbol and flag included, so every
 * optional part of the shared formatter is in the output. JPY has no minor unit (0 digits). The
 * fraction digits come from `catalogCurrencyDigits`, the way the planner builds them from the
 * backend catalogue.
 *
 * Storage. The shared `$app/environment` mock reports `browser: false`, so `setPrivacyEnabled`
 * moves the in-memory rune and never touches `localStorage`.
 *
 * The interface language (M-18 CP2). Every figure is written in the interface language — the
 * developer's rule of 2026-10-12 — through one source, `uiLocale()`: the UI language, regionalised by
 * the browser only when the two agree. Without a locale, the planner's calendar dates
 * (`formatPlannerDate`), timestamps (`formatPlannerTimestamp`), copy stamps (`formatCopyStamp`) and
 * the digits of an L2 distance follow it; until now they followed the browser (`locale ?? undefined`,
 * `toLocaleString(undefined, …)`). An explicit locale still wins. The browser is pinned to en-US
 * before any import, since Node's follows the host's ICU locale: an English UI is written en-US, an
 * Italian one bare `it` (an en-US browser lends no region to Italian, uiLocale.test.ts). The language
 * is switched as LanguageSelector does and put back to English after every case of that block.
 *
 * The exact decimals (M-18 CP3a, last block). A quantity (`formatPlannerQuantity`, personal), a
 * scenario parameter (`formatPlannerPlainDecimal`, public) and an FX rate (`formatPlannerFxRate`,
 * public; a solver count goes through it) are exact decimal strings, shown with every digit up to
 * twenty through `formatDecimalForDisplay`: a dot and no grouping in every language. The cure writes
 * the same digits in the interface locale through `formatExactDecimal`: an Italian UI reads
 * `12.345,678901234`, a French one the same with its own separators, and an English one now groups
 * from a thousand on, `12,345.678`, the new contract of English. `≈` stays in front, outside the
 * digits, and the privacy rule does not move. The plural counts stay plain: they are read off the
 * digits, never off the written text, so they do not move with the language (a guard), and the twin
 * property reads a text the way the interface language writes numbers, its grouping set aside and
 * its decimal separator marking the fraction: in English as before, in Italian and French red until
 * the text is theirs. Every expectation is Intl's output for the interface locale, handed the digits
 * as a string (exact, no double between); no localized literal is typed.
 *
 * The percentages (C-73, TP-2, last blocks). The planner's display rule is half away from zero,
 * exactly (`roundDecimal`, R14), and its two percentage formatters did not keep it: a share, a
 * fraction (`formatPlannerPercent`, and `formatExactPercent` through it), and a value already in
 * percent units (`formatPlannerPercentUnits`) went through `formatPercent(Number(…))` — the value
 * times the scale, then `toFixed`, in binary floating point. A tie the double holds just below
 * rounds down: an exact share of 0.30595 read 30.59%. Each expectation is computed in the test, in
 * integers (BigInt, never a double): the value rounded half away from zero, then written the way the
 * planner writes a percentage today (`formatPercent`'s `%` branch) — `≈` in front when approximate,
 * `+` before a positive value when signed, Intl's percent of the interface locale with exactly the
 * digits asked, handed the rounded fraction as a string, so Intl has nothing left to round. A few
 * en-US literals check that oracle, and each red case first proves that the double path errs on its
 * value. A percentage is public: privacy leaves it in the clear. Every tie at the fifth decimal of a
 * share between 0.1 and 0.9 is swept, 8 000 of them, each also checked against the arithmetic (a
 * share of 0.ABCD5 owes ABCD + 1 hundredths of a percent). A tie in percent units at no decimal place
 * (30.5) is a binary fraction, which `toFixed` already takes away from zero: that case is a guard,
 * like the values that are not ties and the missing or unreadable ones.
 */
import {afterAll, afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

// The browser, pinned before any import: the interface locale takes its region from it.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

// The currency catalogue is the only request in this graph. It is answered so that the output
// carries a real symbol and flag; everything else is inert.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({
                        items: [
                            {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
                            {code: 'JPY', name: 'Japanese Yen', symbol: '¥', flag_emoji: '🇯🇵', country_codes: [], country_names: []},
                        ],
                    }));
                }
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {formatCurrencyAmountHtml, formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {defaultAsOf} from './defaults';
import {
    catalogCurrencyDigits,
    exactMoneyDisplay,
    exactQuantityCount,
    formatCopyStamp,
    formatExactFxRate,
    formatExactMoneyHtml,
    formatExactMoneyPlain,
    formatExactPercent,
    formatExactQuantity,
    formatObjectiveValue,
    formatPlannerDate,
    formatPlannerFxRate,
    formatPlannerL2,
    formatPlannerMoneyPlain,
    formatPlannerPercent,
    formatPlannerPercentUnits,
    formatPlannerPlainDecimal,
    formatPlannerQuantity,
    formatPlannerTimestamp,
    formatSolverNumber,
    plannerPlainDecimalCount,
    plannerQuantityCount,
} from './format';
import type {PacExactMoney, PacExactNumber, PacObjectiveUnit} from './types';

const P = PRIVACY_PLACEHOLDER;
const EMPTY = '—';

const digits = catalogCurrencyDigits([
    {currency: 'EUR', minor_unit: '0.01'},
    {currency: 'JPY', minor_unit: '1'},
]);

const EUR_MONEY: PacObjectiveUnit = {kind: 'valuation_money', currency_code: 'EUR'};
const JPY_MONEY: PacObjectiveUnit = {kind: 'valuation_money', currency_code: 'JPY'};
const EUR_SQUARED: PacObjectiveUnit = {kind: 'valuation_money_squared', currency_code: 'EUR'};
const COUNT: PacObjectiveUnit = {kind: 'count'};
const PENALTY: PacObjectiveUnit = {kind: 'ordinal_penalty'};

function finite(value: string): PacExactNumber {
    return {kind: 'finite_decimal', value};
}

/** An exact ratio as the backend sends it. The display projection is not authoritative. */
function ratio(numerator: string, denominator: string, display_decimal: string, display_scale = 6): PacExactNumber {
    return {kind: 'exact_ratio', numerator, denominator, display_decimal, display_scale, display_authority: 'non_authoritative'};
}

function money(value: PacExactNumber, currency = 'EUR'): PacExactMoney {
    return {value, currency};
}

/** The shared formatter's plain output, called the way the adapter must call it: personal money, fraction digits from minFraction to maxFraction. */
function shared(amount: number, code: string, minFraction: number, maxFraction = minFraction, showSign = false): string {
    return formatCurrencyAmountPlain(amount, code, {minFraction, maxFraction, showSign, sensitivity: 'personal'});
}

/** The markup twin of `shared`. */
function sharedHtml(amount: number, code: string, minFraction: number, maxFraction = minFraction, showSign = false): string {
    return formatCurrencyAmountHtml(amount, code, {minFraction, maxFraction, showSign, sensitivity: 'personal'});
}

/**
 * The interface locale of every case outside the M-18 block: an English UI on the pinned en-US
 * browser. M-18 rewrite: this helper used the host's locale (`toLocaleString(undefined, …)`), the
 * L2 formatter's own until the interface language decided its digits.
 */
const INTERFACE_LOCALE = 'en-US';

/** A plain number with at most two decimals in `locale`, the interface's by default: how the L2 formatter prints its digits. */
function plainNumber(amount: number, locale = INTERFACE_LOCALE): string {
    return amount.toLocaleString(locale, {maximumFractionDigits: 2});
}

/** The digits of a formatted string, whatever separators the locale puts between them. */
function digitsOf(text: string): string {
    return text.replace(/\D/g, '');
}

/**
 * What Intl writes for the plain decimal `text` in `locale`, with exactly its own fraction digits: how a quantity,
 * a plain decimal or a rate is written from M-18 CP3a on. Intl is handed the string, which Intl.NumberFormat v3
 * reads as an exact decimal: no double in between, so the twentieth fraction digit survives.
 */
function intlExact(locale: string, text: string): string {
    const fractionDigits = text.split('.')[1]?.length ?? 0;
    return new Intl.NumberFormat(locale, {minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits}).format(text as Intl.StringNumericLiteral);
}

/** The interface languages these cases switch to. */
type UiLanguage = 'en' | 'it' | 'fr';

/** The interface locale of each on the pinned en-US browser: English keeps the browser's region, the others are bare. */
const LOCALE_OF: Readonly<Record<UiLanguage, string>> = {en: INTERFACE_LOCALE, it: 'it', fr: 'fr'};

/** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
async function uiLanguage(lang: UiLanguage): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
}

/** Moves the flag, and proves it moved. */
function privacy(on: boolean): void {
    setPrivacyEnabled(on);
    expect(isPrivacyEnabled(), 'control: the flag').toBe(on);
}

beforeAll(async () => {
    await ensureCurrenciesLoaded('en');
    // Control: the catalogue is loaded, so every output below carries symbol and flag, not the bare-code fallback.
    expect(getCurrencyInfo('EUR').symbol).toBe('€');
    expect(getCurrencyInfo('JPY').symbol).toBe('¥');
    expect(digits('EUR'), 'minor unit 0.01').toBe(2);
    expect(digits('JPY'), 'minor unit 1').toBe(0);

    setPrivacyEnabled(false);
    // The expectations are the shared formatter's own output, so check once that the clear one
    // carries the digits put in. Otherwise a formatter that always masked would make every
    // "clear" case compare the placeholder with itself.
    expect(digitsOf(shared(1234.57, 'EUR', 2))).toBe('123457');
    expect(digitsOf(shared(1235, 'JPY', 0))).toBe('1235');
});

afterEach(() => {
    // The flag is module-level state shared by every test in this file.
    setPrivacyEnabled(false);
});

afterAll(() => {
    vi.unstubAllGlobals();
});

describe('exactMoneyDisplay — the text at the minor unit, and whether the rounding changed it', () => {
    it('rounds an exact decimal, and marks it approximate only when the rounding changed it', () => {
        expect(exactMoneyDisplay(finite('1234.5678'), 2)).toEqual({text: '1234.57', approx: true});
        expect(exactMoneyDisplay(finite('1.005'), 2), 'half away from zero, not the float 1.00').toEqual({text: '1.01', approx: true});
        expect(exactMoneyDisplay(finite('10.5'), 2)).toEqual({text: '10.5', approx: false});
        expect(exactMoneyDisplay(finite('10.50'), 2), 'dropping trailing zeros is not a rounding').toEqual({text: '10.5', approx: false});
        expect(exactMoneyDisplay(finite('-0.004'), 2), 'a nonzero amount below the minor unit keeps its digits').toEqual({text: '-0.004', approx: false});
        expect(exactMoneyDisplay(finite('1234.5'), 0), 'no minor unit, as JPY').toEqual({text: '1235', approx: true});
        expect(exactMoneyDisplay(finite('1234'), 0)).toEqual({text: '1234', approx: false});
    });

    it('rounds an exact ratio, and marks it approximate unless the rounded text is the ratio itself', () => {
        expect(exactMoneyDisplay(ratio('1', '3', '0.333333'), 2)).toEqual({text: '0.33', approx: true});
        expect(exactMoneyDisplay(ratio('-2', '3', '-0.666667'), 2)).toEqual({text: '-0.67', approx: true});
        expect(exactMoneyDisplay(ratio('1', '4', '0.25', 2), 2), 'a ratio that is exact at the minor unit').toEqual({text: '0.25', approx: false});
        expect(exactMoneyDisplay(ratio('5', '2', '2.5', 1), 0)).toEqual({text: '3', approx: true});
    });

    it('rounds the ratio itself, not its display projection', () => {
        // 0.125 is exactly 1/8, but at the minor unit it still has to round to ≈0.13.
        expect(exactMoneyDisplay(ratio('1', '8', '0.125', 3), 2)).toEqual({text: '0.13', approx: true});
        // A coarse projection does not leak into the result: 2/3 at two places is 0.67, whatever the projection says.
        expect(exactMoneyDisplay(ratio('2', '3', '0.6', 1), 2)).toEqual({text: '0.67', approx: true});
    });

    it('falls back to the rounded display projection when the ratio cannot be read, and always marks it approximate', () => {
        expect(exactMoneyDisplay(ratio('1', '0', '0.335', 3), 2)).toEqual({text: '0.34', approx: true});
        expect(exactMoneyDisplay(ratio('x', '3', '0.5', 1), 2), 'even when the rounding changes nothing').toEqual({text: '0.5', approx: true});
        expect(exactMoneyDisplay(ratio('x', '3', 'abc'), 2), 'an unreadable projection passes through').toEqual({text: 'abc', approx: true});
    });

    it('passes an unreadable decimal through, which the money formatter then renders as an empty cell', () => {
        expect(exactMoneyDisplay(finite('1e3'), 2)).toEqual({text: '1e3', approx: false});
        expect(formatExactMoneyPlain(money(finite('1e3')), {digits})).toBe(EMPTY);
        expect(formatExactMoneyPlain(money(ratio('x', '3', 'abc')), {digits}), 'no ≈ on an empty cell').toBe(EMPTY);
    });

    // G3. A PAC funded in another currency posts a rounding residual of a fraction of a cent: at the
    // minor unit it read ≈0.00, a nonzero amount shown as zero. Every amount below would round to
    // zero at `places`, so it keeps one place past its first nonzero fraction digit instead.
    it('G3: keeps about two significant digits of a nonzero amount that would round to zero at the minor unit', () => {
        expect(exactMoneyDisplay(ratio('-47', '21700', '-0.002166'), 2), 'a ledger rounding residual, -0.0021658…').toEqual({text: '-0.0022', approx: true});
        expect(exactMoneyDisplay(finite('0.00176'), 2), 'half away from zero at the fourth place').toEqual({text: '0.0018', approx: true});
        expect(exactMoneyDisplay(finite('-0.003365'), 2), 'half away from zero, on the negative side').toEqual({text: '-0.0034', approx: true});
        expect(exactMoneyDisplay(finite('-0.0021'), 2), 'already two significant digits: shown as it is').toEqual({text: '-0.0021', approx: false});
        expect(exactMoneyDisplay(finite('0.00095'), 2), 'the first nonzero digit is the fourth, so five places').toEqual({text: '0.00095', approx: false});
        expect(exactMoneyDisplay(finite('0.000951'), 2), 'a third significant digit is rounded away').toEqual({text: '0.00095', approx: true});
        expect(exactMoneyDisplay(ratio('1', '3000', '0.000333'), 2), 'an exact ratio is rounded itself').toEqual({text: '0.00033', approx: true});
        expect(exactMoneyDisplay(finite('0.4'), 0), 'no minor unit, as JPY: the same rule').toEqual({text: '0.4', approx: false});
        expect(exactMoneyDisplay(ratio('x', '3', '-0.0021659', 7), 2), 'the fallback on an unreadable ratio follows the rule, and stays approximate').toEqual({text: '-0.0022', approx: true});
    });

    it('G3 control: a true zero is an exact 0, and an amount that does not round to zero keeps the minor unit', () => {
        expect(exactMoneyDisplay(finite('0'), 2)).toEqual({text: '0', approx: false});
        expect(exactMoneyDisplay(finite('-0.00'), 2), 'a negative zero is a true zero, never -0').toEqual({text: '0', approx: false});
        expect(exactMoneyDisplay(finite('0.005'), 2), 'rounds to the minor unit, not to zero: the rule does not apply').toEqual({text: '0.01', approx: true});
        expect(exactMoneyDisplay(finite('0.01'), 2)).toEqual({text: '0.01', approx: false});
    });
});

describe('formatExactMoneyPlain / formatExactMoneyHtml — privacy off', () => {
    it('shows a computed amount at the minor unit, with ≈ because the rounding changed it', () => {
        const text = formatExactMoneyPlain(money(finite('1234.5678')), {digits});
        expect(text).toBe('≈' + shared(1234.57, 'EUR', 2));
        expect(digitsOf(text), 'the digits past the minor unit are gone').toBe('123457');
    });

    it('shows an amount already at the minor unit with the currency digits and no ≈', () => {
        const text = formatExactMoneyPlain(money(finite('10.5')), {digits});
        expect(text).toBe(shared(10.5, 'EUR', 2));
        expect(text).not.toContain('≈');
        expect(digitsOf(text), 'padded to the minor unit').toBe('1050');
    });

    it('shows an exact ratio at the minor unit: 1/3 EUR is ≈0.33, while 1/4 EUR is exactly 0.25', () => {
        const third = formatExactMoneyPlain(money(ratio('1', '3', '0.333333')), {digits});
        expect(third).toBe('≈' + shared(0.33, 'EUR', 2));
        expect(digitsOf(third)).toBe('033');

        const quarter = formatExactMoneyPlain(money(ratio('1', '4', '0.25', 2)), {digits});
        expect(quarter).toBe(shared(0.25, 'EUR', 2));
        expect(quarter).not.toContain('≈');
    });

    it("uses the minor unit of the amount's own currency: JPY has none", () => {
        const rounded = formatExactMoneyPlain(money(finite('1234.5'), 'JPY'), {digits});
        expect(rounded).toBe('≈' + shared(1235, 'JPY', 0));
        expect(digitsOf(rounded), 'half away from zero, no fraction digits').toBe('1235');

        expect(formatExactMoneyPlain(money(ratio('5', '2', '2.5', 1), 'JPY'), {digits})).toBe('≈' + shared(3, 'JPY', 0));

        const exact = formatExactMoneyPlain(money(finite('1234'), 'JPY'), {digits});
        expect(exact).toBe(shared(1234, 'JPY', 0));
        expect(exact).not.toContain('≈');
    });

    it('puts ≈ before the sign, and shows a nonzero amount below the minor unit with its own digits, never as zero', () => {
        const up = formatExactMoneyPlain(money(finite('2.345')), {digits, signed: true});
        expect(up).toBe('≈' + shared(2.35, 'EUR', 2, 2, true));
        expect(up.startsWith('≈+')).toBe(true);

        const down = formatExactMoneyPlain(money(finite('-1234.5678')), {digits, signed: true});
        expect(down).toBe('≈' + shared(-1234.57, 'EUR', 2, 2, true));
        expect(down.startsWith('≈-')).toBe(true);

        // G3: -0.004 EUR is exact at three places, so it is shown as it is: signed, no ≈.
        const small = formatExactMoneyPlain(money(finite('-0.004')), {digits, signed: true});
        expect(small).toBe(shared(-0.004, 'EUR', 2, 3, true));
        expect(small.startsWith('-'), 'a nonzero amount keeps its sign').toBe(true);
        expect(small).not.toContain('≈');
        expect(digitsOf(small), 'the third fraction digit is shown, not rounded away').toBe('0004');

        // G3: a rounding residual of -47/21700 EUR, two significant digits, approximate.
        const residual = formatExactMoneyPlain(money(ratio('-47', '21700', '-0.002166')), {digits, signed: true});
        expect(residual).toBe('≈' + shared(-0.0022, 'EUR', 2, 4, true));
        expect(residual.startsWith('≈-')).toBe(true);
        expect(digitsOf(residual)).toBe('00022');

        // A true zero stays an exact zero: no ≈, and never a negative zero.
        const zero = formatExactMoneyPlain(money(finite('0')), {digits, signed: true});
        expect(zero).toBe(shared(0, 'EUR', 2, 2, true));
        expect(zero).not.toContain('≈');
        expect(zero).not.toContain('-');
        expect(formatExactMoneyPlain(money(finite('-0.00')), {digits, signed: true}), 'a negative zero is a true zero').toBe(zero);
    });

    it("applies the same rule to markup: ≈ in front of the shared formatter's HTML, only when the rounding changed the value", () => {
        expect(formatExactMoneyHtml(money(finite('1234.5678')), {digits})).toBe('≈' + sharedHtml(1234.57, 'EUR', 2));
        expect(formatExactMoneyHtml(money(ratio('1', '3', '0.333333')), {digits})).toBe('≈' + sharedHtml(0.33, 'EUR', 2));
        expect(formatExactMoneyHtml(money(finite('1234.5'), 'JPY'), {digits})).toBe('≈' + sharedHtml(1235, 'JPY', 0));

        const exact = formatExactMoneyHtml(money(finite('10.5')), {digits});
        expect(exact).toBe(sharedHtml(10.5, 'EUR', 2));
        expect(exact).not.toContain('≈');
    });
});

describe('formatExactMoneyPlain / formatExactMoneyHtml — privacy on', () => {
    it('masks the number, keeping ≈, the sign and the currency outside the mask', () => {
        privacy(true);
        // Control: in this state the shared formatter masks personal money.
        expect(shared(1234.57, 'EUR', 2)).toBe(`${P} € 🇪🇺 EUR`);

        expect(formatExactMoneyPlain(money(finite('1234.5678')), {digits})).toBe(`≈${P} € 🇪🇺 EUR`);
        expect(formatExactMoneyPlain(money(finite('10.5')), {digits}), 'exact at the minor unit: no ≈').toBe(`${P} € 🇪🇺 EUR`);
        expect(formatExactMoneyPlain(money(ratio('1', '3', '0.333333')), {digits})).toBe(`≈${P} € 🇪🇺 EUR`);
        expect(formatExactMoneyPlain(money(finite('1234.5'), 'JPY'), {digits})).toBe(`≈${P} ¥ 🇯🇵 JPY`);
        expect(formatExactMoneyPlain(money(finite('-1234.5678')), {digits, signed: true})).toBe(`≈-${P} € 🇪🇺 EUR`);
        expect(formatExactMoneyPlain(money(finite('2.345')), {digits, signed: true})).toBe(`≈+${P} € 🇪🇺 EUR`);
    });

    it('G3: masks a nonzero amount below the minor unit with its sign, not as an unsigned zero', () => {
        privacy(true);
        // Control: in the same state a true zero masks with no sign, so the sign below comes from the value.
        expect(formatExactMoneyPlain(money(finite('0')), {digits, signed: true})).toBe(`${P} € 🇪🇺 EUR`);

        expect(formatExactMoneyPlain(money(ratio('-47', '21700', '-0.002166')), {digits, signed: true})).toBe(`≈-${P} € 🇪🇺 EUR`);
    });

    it('leaks no digit and no magnitude: amounts four orders of magnitude apart mask to one string', () => {
        privacy(true);
        const large = formatExactMoneyPlain(money(finite('1234.5678')), {digits});
        const small = formatExactMoneyPlain(money(ratio('1', '3', '0.333333')), {digits});
        expect(large).not.toMatch(/\d/);
        expect(small).not.toMatch(/\d/);
        expect(large).toBe(small);
    });

    it('masks the markup the same way: ≈ ahead of the masked amount, the currency still visible, no digit', () => {
        privacy(true);
        const html = formatExactMoneyHtml(money(finite('1234.5678')), {digits});
        expect(html).toBe('≈' + sharedHtml(1234.57, 'EUR', 2));
        expect(html.indexOf('≈'), '≈ leads, outside the masked amount').toBe(0);
        expect(html.indexOf(P)).toBeGreaterThan(0);
        expect(html).toContain('€');
        expect(html).toContain('🇪🇺');
        expect(html).toContain('EUR');
        expect(html).not.toMatch(/\d/);

        // Control for the masked expectation: in the clear the same call shows the digits.
        privacy(false);
        expect(digitsOf(formatExactMoneyHtml(money(finite('1234.5678')), {digits}))).toBe('123457');
    });
});

describe('formatPlannerMoneyPlain — a raw amount, rounded only when asked', () => {
    it('with minorUnit, rounds to the minor unit and marks the change with ≈', () => {
        const text = formatPlannerMoneyPlain('1234.5678', 'EUR', {digits, minorUnit: true});
        expect(text).toBe('≈' + shared(1234.57, 'EUR', 2));
        expect(digitsOf(text)).toBe('123457');
        expect(formatPlannerMoneyPlain('1234.5', 'JPY', {digits, minorUnit: true})).toBe('≈' + shared(1235, 'JPY', 0));
    });

    it('with minorUnit, adds no ≈ to an amount already at the minor unit, trailing zeros included', () => {
        expect(formatPlannerMoneyPlain('1234.5', 'EUR', {digits, minorUnit: true})).toBe(shared(1234.5, 'EUR', 2));
        expect(formatPlannerMoneyPlain('1234.50', 'EUR', {digits, minorUnit: true})).toBe(shared(1234.5, 'EUR', 2));
        expect(formatPlannerMoneyPlain('1234', 'JPY', {digits, minorUnit: true})).toBe(shared(1234, 'JPY', 0));
    });

    it('without minorUnit, keeps every digit and adds no ≈: a price or a typed value is not rounded', () => {
        const text = formatPlannerMoneyPlain('1234.5678', 'EUR', {digits});
        expect(text).toBe(shared(1234.5678, 'EUR', 2, 4));
        expect(text).not.toContain('≈');
        expect(digitsOf(text)).toBe('12345678');
        expect(formatPlannerMoneyPlain('1234.5', 'JPY', {digits})).toBe(shared(1234.5, 'JPY', 0, 1));
    });

    it('falls back to the CLDR digits of the currency when no catalogue digits are given', () => {
        expect(formatPlannerMoneyPlain('1234.5678', 'EUR', {minorUnit: true})).toBe('≈' + shared(1234.57, 'EUR', 2));
        expect(formatPlannerMoneyPlain('1234.5', 'JPY', {minorUnit: true})).toBe('≈' + shared(1235, 'JPY', 0));
    });

    it('renders a missing or unreadable amount as an empty cell, without ≈', () => {
        for (const amount of [null, undefined, '', '1e3', 'abc']) {
            expect(formatPlannerMoneyPlain(amount, 'EUR', {digits, minorUnit: true}), String(amount)).toBe(EMPTY);
        }
    });

    it('masks with privacy on, keeping ≈ and the currency outside', () => {
        privacy(true);
        expect(formatPlannerMoneyPlain('1234.5678', 'EUR', {digits, minorUnit: true})).toBe(`≈${P} € 🇪🇺 EUR`);
        expect(formatPlannerMoneyPlain('1234.5678', 'EUR', {digits})).toBe(`${P} € 🇪🇺 EUR`);
    });
});

describe('formatSolverNumber — a raw solver number, by the unit of its stage', () => {
    it("shows money at the minor unit of the unit's currency, with ≈ when the rounding changed it", () => {
        const text = formatSolverNumber('1234.5678', EUR_MONEY, digits);
        expect(text).toBe('≈' + shared(1234.57, 'EUR', 2));
        expect(digitsOf(text)).toBe('123457');
        expect(formatSolverNumber('1234.5', EUR_MONEY, digits)).toBe(shared(1234.5, 'EUR', 2));
        expect(formatSolverNumber('1234.5', JPY_MONEY, digits)).toBe('≈' + shared(1235, 'JPY', 0));
    });

    it('masks solver money with privacy on', () => {
        privacy(true);
        expect(formatSolverNumber('1234.5678', EUR_MONEY, digits)).toBe(`≈${P} € 🇪🇺 EUR`);
        expect(formatSolverNumber('1234.5', EUR_MONEY, digits)).toBe(`${P} € 🇪🇺 EUR`);
    });

    it('rounds solver money below the minor unit to zero as before: G3 is not for solver floats, so 0.004 EUR is ≈0', () => {
        expect(formatSolverNumber('0.004', EUR_MONEY, digits)).toBe('≈' + shared(0, 'EUR', 2));
        expect(formatSolverNumber('-0.004', EUR_MONEY, digits), 'and never a negative zero').toBe('≈' + shared(0, 'EUR', 2));
    });

    it.each([
        ['3.14159', '≈3.14'],
        ['2.5', '2.5'],
        ['2.50', '2.5'],
        ['7', '7'],
        ['2.005', '≈2.01'],
        ['-2.005', '≈-2.01'],
        ['-0.004', '≈0'],
        // M-18 CP3a: a count is written in the interface locale like every rate, so the English UI
        // (en-US browser) groups it from a thousand on; it read `≈1234.57`.
        ['1234.5678', '≈' + intlExact(INTERFACE_LOCALE, '1234.57')],
    ])('shows the count %s to two decimals as %s, with ≈ only when the rounding changed it', (value, expected) => {
        expect(formatSolverNumber(value, COUNT, digits)).toBe(expected);
    });

    it('treats an ordinal penalty like a count: two decimals, ≈ when rounded', () => {
        expect(formatSolverNumber('3.14159', PENALTY, digits)).toBe('≈3.14');
        expect(formatSolverNumber('4', PENALTY, digits)).toBe('4');
    });

    it('keeps a count public: privacy on leaves it in the clear, while money in the same state masks', () => {
        privacy(true);
        // Control: in the same state, money is masked.
        expect(formatSolverNumber('1234.5678', EUR_MONEY, digits)).toBe(`≈${P} € 🇪🇺 EUR`);

        expect(formatSolverNumber('3.14159', COUNT, digits)).toBe('≈3.14');
        expect(formatSolverNumber('2.5', COUNT, digits)).toBe('2.5');
        expect(formatSolverNumber('3.14159', PENALTY, digits)).toBe('≈3.14');
    });

    it('hands squared money to the L2 formatter: personal digits, then the currency squared', () => {
        expect(formatSolverNumber('1234.5678', EUR_SQUARED, digits)).toBe(formatPlannerL2(finite('1234.5678'), 'EUR'));

        const text = formatSolverNumber('1234.5', EUR_SQUARED, digits);
        expect(text).toBe(formatPlannerL2(finite('1234.5'), 'EUR'));
        expect(text.endsWith(' EUR²'), 'the unit follows the number').toBe(true);
        expect(digitsOf(text)).toBe('12345');

        privacy(true);
        expect(formatSolverNumber('1234.5', EUR_SQUARED, digits)).toBe(`${P} EUR²`);
    });

    it('renders a missing or unreadable solver number as an empty cell, whatever the unit', () => {
        for (const unit of [EUR_MONEY, EUR_SQUARED, COUNT, PENALTY]) {
            expect(formatSolverNumber(null, unit, digits), `${unit.kind}: null`).toBe(EMPTY);
            expect(formatSolverNumber(undefined, unit, digits), `${unit.kind}: undefined`).toBe(EMPTY);
            expect(formatSolverNumber('1e3', unit, digits), `${unit.kind}: exponent`).toBe(EMPTY);
        }
    });
});

describe('formatPlannerL2 — an L2 distance in squared valuation money', () => {
    // The ratios carry the display projection the backend emits (`wire_numbers._display_projection`).
    // The backend sends a terminating ratio as a finite decimal (`ratio_to_exact_number`), so `1/4` is
    // a shape the contract allows rather than one the planner produces today.

    it('rounds a finite decimal to two decimals, half away from zero, and marks it ≈', () => {
        const text = formatPlannerL2(finite('12.345'), 'EUR');
        expect(text).toBe('≈' + plainNumber(12.35) + ' EUR²');
        expect(text.startsWith('≈'), 'the mark leads').toBe(true);
        expect(text.endsWith(' EUR²'), 'the squared unit follows the number').toBe(true);
        expect(digitsOf(text), 'half away from zero: 12.35, neither 12.34 nor 12.345').toBe('1235');
    });

    it('shows a finite decimal with two decimals or fewer as it is, without ≈', () => {
        const text = formatPlannerL2(finite('12.5'), 'EUR');
        expect(text).toBe(plainNumber(12.5) + ' EUR²');
        expect(text.includes('≈'), 'nothing was rounded').toBe(false);
        expect(digitsOf(text)).toBe('125');
    });

    it('shows an exact ratio whose value has two decimals without ≈', () => {
        const text = formatPlannerL2(ratio('1', '4', '0.25', 2), 'EUR');
        expect(text).toBe(plainNumber(0.25) + ' EUR²');
        expect(text.includes('≈'), '1/4 is exactly 0.25').toBe(false);
        expect(digitsOf(text)).toBe('025');
    });

    it('rounds an inexact ratio to two decimals and marks it ≈', () => {
        const text = formatPlannerL2(ratio('1', '3', '0.333333333333333333', 18), 'EUR');
        expect(text).toBe('≈' + plainNumber(0.33) + ' EUR²');
        expect(text.startsWith('≈'), '1/3 has no finite decimal').toBe(true);
        expect(digitsOf(text)).toBe('033');
    });

    it('rounds the exact decimal text, not its float', () => {
        expect(Number('0.124999999999999999999'), 'control: as a double this is the half 0.125').toBe(0.125);
        expect(plainNumber(0.125), 'control: a float formatter rounds that half up').toBe(plainNumber(0.13));

        const text = formatPlannerL2(finite('0.124999999999999999999'), 'EUR');
        expect(text).toBe('≈' + plainNumber(0.12) + ' EUR²');
        expect(digitsOf(text), 'just below the half, so down').toBe('012');
    });

    it('gives a squared solver number the same rule', () => {
        const text = formatSolverNumber('12.345', EUR_SQUARED);
        expect(text).toBe('≈' + plainNumber(12.35) + ' EUR²');
        expect(text).toBe(formatPlannerL2(finite('12.345'), 'EUR'));
        expect(formatSolverNumber('12.5', EUR_SQUARED), 'nothing was rounded').toBe(plainNumber(12.5) + ' EUR²');
    });

    it('keeps two decimals for a distance below 0.01 too: G3 is not for squared money, so 0.004 EUR² is ≈0', () => {
        expect(formatPlannerL2(finite('0.004'), 'EUR')).toBe('≈' + plainNumber(0) + ' EUR²');
    });

    it('masks the digits with privacy on, keeping ≈ and the squared unit outside', () => {
        privacy(true);
        expect(formatPlannerL2(finite('12.345'), 'EUR')).toBe(`≈${P} EUR²`);
        expect(formatPlannerL2(finite('12.5'), 'EUR')).toBe(`${P} EUR²`);
        expect(formatPlannerL2(ratio('1', '3', '0.333333333333333333', 18), 'EUR')).toBe(`≈${P} EUR²`);
        expect(formatSolverNumber('12.345', EUR_SQUARED)).toBe(`≈${P} EUR²`);
    });
});

describe('without a locale, the interface language: dates, timestamps, copy stamps and L2 digits (M-18)', () => {
    /** `formatPlannerDate`'s options. */
    const DATE = {year: 'numeric', month: '2-digit', day: '2-digit'} as const;
    /** `formatCopyStamp`'s for data of today: the date and the time the copy ran. */
    const STAMP = {year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'} as const;
    /** `formatDateTime`'s, through which `formatPlannerTimestamp` writes. */
    const TIMESTAMP = {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'} as const;

    /** A local noon: its UTC day is its local day in every zone within twelve hours of UTC. */
    const NOW = new Date(2026, 9, 12, 12, 0);
    const TODAY = '2026-10-12';
    const EARLIER = '2026-10-09';
    /** When the copy ran: an instant, written in the run's time zone by the helper and the expectation alike. */
    const CAPTURED_AT = '2026-10-12T09:05:00Z';

    /** The UI in Italian on the pinned en-US browser: the interface locale is bare `it`. */
    async function italianUi(): Promise<void> {
        await uiLanguage('it');
        expect(uiLocale(), 'control: an Italian UI on an en-US browser is written bare it').toBe('it');
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('formatPlannerDate: a calendar date in the interface locale; an explicit locale still wins', async () => {
        const date = new Date(2026, 9, 12);
        const italian = date.toLocaleDateString('it', DATE);
        const american = date.toLocaleDateString('en-US', DATE);
        expect(italian, 'control: Italian writes the date otherwise than en-US').not.toBe(american);
        expect(formatPlannerDate(TODAY), 'control: an English UI on an en-US browser writes en-US').toBe(american);

        await italianUi();
        expect(formatPlannerDate(TODAY, 'en-US'), 'an explicit locale still wins').toBe(american);

        expect(formatPlannerDate(TODAY), 'without a locale, an Italian UI must read an Italian date').toBe(italian);
    });

    it('formatPlannerTimestamp: when a fact was copied, in the interface locale; an explicit locale still wins', async () => {
        const instant = new Date(CAPTURED_AT);
        const italian = instant.toLocaleDateString('it', TIMESTAMP);
        const american = instant.toLocaleDateString('en-US', TIMESTAMP);
        expect(italian, 'control: Italian writes the timestamp otherwise than en-US').not.toBe(american);
        expect(formatPlannerTimestamp(CAPTURED_AT), 'control: an English UI on an en-US browser writes en-US').toBe(american);

        await italianUi();
        expect(formatPlannerTimestamp(CAPTURED_AT, 'en-US'), 'an explicit locale still wins').toBe(american);

        expect(formatPlannerTimestamp(CAPTURED_AT), 'without a locale, an Italian UI must read an Italian timestamp').toBe(italian);
    });

    it('formatCopyStamp: data of today shows when the copy ran, data of an earlier day its date — both in the interface locale; an explicit locale still wins', async () => {
        expect(defaultAsOf(NOW), 'control: the as-of day of NOW is TODAY, so data of TODAY shows a time and data of EARLIER a date').toBe(TODAY);
        const written = (locale: string) => ({today: new Date(CAPTURED_AT).toLocaleString(locale, STAMP), earlier: new Date(2026, 9, 9).toLocaleDateString(locale, DATE)});
        const stamps = (locale?: string) => ({today: formatCopyStamp(TODAY, CAPTURED_AT, locale, NOW), earlier: formatCopyStamp(EARLIER, CAPTURED_AT, locale, NOW)});
        const italian = written('it');
        const american = written('en-US');
        expect(italian.today, 'control: Italian writes the date and time otherwise than en-US').not.toBe(american.today);
        expect(italian.earlier, 'control: Italian writes the date otherwise than en-US').not.toBe(american.earlier);
        expect(stamps(undefined), 'control: an English UI on an en-US browser writes en-US').toEqual(american);

        await italianUi();
        expect(stamps('en-US'), 'an explicit locale still wins').toEqual(american);

        expect(stamps(undefined), 'without a locale, an Italian UI must read Italian stamps').toEqual(italian);
    });

    it('formatPlannerL2: the digits of an L2 distance in the interface locale, through a squared solver number too', async () => {
        // 12345.678 is shown at two decimals, ≈12345.68: above a thousand, so the grouping is written as well.
        const italian = `≈${plainNumber(12345.68, 'it')} EUR²`;
        const american = `≈${plainNumber(12345.68, 'en-US')} EUR²`;
        expect(italian, 'control: Italian writes the digits otherwise than en-US').not.toBe(american);
        expect(formatPlannerL2(finite('12345.678'), 'EUR'), 'control: an English UI on an en-US browser writes en-US').toBe(american);

        await italianUi();

        expect({l2: formatPlannerL2(finite('12345.678'), 'EUR'), solver: formatSolverNumber('12345.678', EUR_SQUARED)}, 'an Italian UI must read Italian digits').toEqual({l2: italian, solver: italian});
    });
});

describe('formatObjectiveValue — an objective in valuation money', () => {
    it('shows the objective as a computed amount at the minor unit', () => {
        expect(formatObjectiveValue(finite('1234.5678'), EUR_MONEY, digits)).toBe('≈' + shared(1234.57, 'EUR', 2));
        expect(formatObjectiveValue(finite('10.5'), EUR_MONEY, digits)).toBe(shared(10.5, 'EUR', 2));
        expect(formatObjectiveValue(ratio('1', '3', '0.333333'), EUR_MONEY, digits)).toBe('≈' + shared(0.33, 'EUR', 2));
        expect(formatObjectiveValue(finite('1234.5'), JPY_MONEY, digits)).toBe('≈' + shared(1235, 'JPY', 0));
        // The same rule as the amount formatter, not a parallel copy of it.
        expect(formatObjectiveValue(ratio('2', '3', '0.666667'), EUR_MONEY, digits)).toBe(formatExactMoneyPlain(money(ratio('2', '3', '0.666667')), {digits}));
    });

    it('masks a valuation-money objective with privacy on', () => {
        privacy(true);
        expect(formatObjectiveValue(finite('1234.5678'), EUR_MONEY, digits)).toBe(`≈${P} € 🇪🇺 EUR`);
        expect(formatObjectiveValue(finite('1234.5'), JPY_MONEY, digits)).toBe(`≈${P} ¥ 🇯🇵 JPY`);
    });
});

// R7 — the plural counts. A count is only ever called inside a test: until the functions exist, a
// call fails that test alone, and the R14 cases above stay meaningful.

/** Twenty fraction digits: all shown, while `Number()` reads the value as 1. */
const TWENTY_DIGIT_ONE = '1.' + '0'.repeat(19) + '1';
/** Twenty nines: all shown, while `Number()` rounds the value up to 1. */
const TWENTY_NINES = '0.' + '9'.repeat(20);
/** A 21st fraction digit: the display truncates it, so the user sees 1. */
const TWENTY_ONE_DIGIT_ONE = '1.' + '0'.repeat(20) + '1';

/** A count as a plural rule reads it: -0 is 0. NaN stays NaN. */
function asPlural(count: number): number {
    return count === 0 ? 0 : count;
}

interface CountCase {
    input: string | null | undefined;
    count: number;
    why: string;
}

/** Privacy off, the same count for the three functions; `exactQuantityCount` reads a string input as an exact decimal. */
const COUNT_CASES: CountCase[] = [
    {input: '1', count: 1, why: 'one'},
    {input: '1.000', count: 1, why: 'trailing zeros are not shown'},
    {input: '1.', count: 1, why: 'a bare point is not shown'},
    {input: '0', count: 0, why: 'zero'},
    {input: '-0', count: 0, why: 'a negative zero is shown as 0'},
    {input: '2', count: 2, why: 'two'},
    {input: '1.5', count: 1.5, why: 'integer part 1, plus 0.5 for the fraction shown'},
    {input: '0.25', count: 0.5, why: 'integer part 0, plus 0.5 for the fraction shown'},
    {input: '123.456', count: 123.5, why: 'integer part 123, plus 0.5 for the fraction shown'},
    {input: '-1', count: 1, why: 'plural operands are absolute'},
    {input: '-1.5', count: 1.5, why: 'plural operands are absolute'},
    {input: TWENTY_DIGIT_ONE, count: 1.5, why: 'twenty fraction digits are shown, so the fraction counts'},
    {input: TWENTY_NINES, count: 0.5, why: 'twenty nines are shown, so the integer part is 0'},
    {input: TWENTY_ONE_DIGIT_ONE, count: 1, why: 'a 21st fraction digit is not shown, so it does not count'},
    {input: null, count: NaN, why: 'no value'},
    {input: undefined, count: NaN, why: 'no value'},
    {input: '', count: NaN, why: 'not a decimal'},
    {input: 'abc', count: NaN, why: 'not a decimal'},
    {input: '1e3', count: NaN, why: 'an exponent is not a plain decimal'},
    {input: '1,5', count: NaN, why: 'a comma is not a plain decimal'},
];

describe('plural counts — the count of the digits the user sees, privacy off', () => {
    it.each(COUNT_CASES)('$input counts $count: $why', ({input, count, why}) => {
        privacy(false);
        expect(asPlural(plannerQuantityCount(input)), `plannerQuantityCount: ${why}`).toBe(count);
        expect(asPlural(plannerPlainDecimalCount(input)), `plannerPlainDecimalCount: ${why}`).toBe(count);
        if (typeof input === 'string') expect(asPlural(exactQuantityCount(finite(input))), `exactQuantityCount of an exact decimal: ${why}`).toBe(count);
    });

    it('control: the precision cases test what they claim — Number() misreads two of them, the display drops the 21st digit', () => {
        // What a count read off `Number(value)` would see: 1, twice.
        expect(Number(TWENTY_DIGIT_ONE), 'as a double, twenty fraction digits are 1').toBe(1);
        expect(Number(TWENTY_NINES), 'as a double, twenty nines are 1').toBe(1);
        // What the user sees: every digit of the first two, and none past the twentieth.
        expect(formatPlannerPlainDecimal(TWENTY_DIGIT_ONE)).toBe(TWENTY_DIGIT_ONE);
        expect(formatPlannerQuantity(TWENTY_DIGIT_ONE)).toBe(TWENTY_DIGIT_ONE);
        expect(formatPlannerPlainDecimal(TWENTY_NINES)).toBe(TWENTY_NINES);
        expect(formatPlannerQuantity(TWENTY_NINES)).toBe(TWENTY_NINES);
        expect(formatPlannerPlainDecimal(TWENTY_ONE_DIGIT_ONE)).toBe('1');
        expect(formatPlannerQuantity(TWENTY_ONE_DIGIT_ONE)).toBe('1');
    });
});

describe('exactQuantityCount — an exact ratio counts its display projection, privacy off', () => {
    it.each([
        {name: '1/3', value: ratio('1', '3', '0.333333'), shown: '≈0.333333', count: 0.5},
        {name: '3/2', value: ratio('3', '2', '1.5'), shown: '1.5', count: 1.5},
        {name: '10000001/10000000', value: ratio('10000001', '10000000', '1'), shown: '≈1', count: 1},
    ])('$name, shown as $shown, counts $count', ({value, shown, count}) => {
        privacy(false);
        expect(formatExactQuantity(value), 'control: the text the count reads').toBe(shown);
        expect(exactQuantityCount(value)).toBe(count);
    });
});

describe('plural counts — privacy on: a masked quantity counts NaN, a public decimal keeps its count', () => {
    it('plannerQuantityCount: a personal quantity is masked, so it counts NaN, never a hidden 1', () => {
        privacy(true);
        expect(formatPlannerQuantity('1'), 'control: the quantity is masked').toBe(P);
        expect(plannerQuantityCount('1')).toBeNaN();
        expect(plannerQuantityCount('2')).toBeNaN();

        privacy(false);
        expect(plannerQuantityCount('1'), 'control: in the clear, the same value counts 1').toBe(1);
    });

    it('exactQuantityCount: masked like its display, approximate or not', () => {
        privacy(true);
        expect(formatExactQuantity(finite('1')), 'control: the quantity is masked').toBe(P);
        expect(exactQuantityCount(finite('1'))).toBeNaN();
        expect(formatExactQuantity(ratio('10000001', '10000000', '1')), 'control: masked, with ≈ outside the mask').toBe('≈' + P);
        expect(exactQuantityCount(ratio('10000001', '10000000', '1'))).toBeNaN();

        privacy(false);
        expect(exactQuantityCount(finite('1')), 'control: in the clear, the same value counts 1').toBe(1);
    });

    it('plannerPlainDecimalCount: a public decimal stays in the clear, and so does its count', () => {
        privacy(true);
        expect(formatPlannerPlainDecimal('1'), 'control: public, so in the clear').toBe('1');
        expect(plannerPlainDecimalCount('1')).toBe(1);
        expect(plannerPlainDecimalCount('1.5')).toBe(1.5);
    });
});

/** A count function with its display twin. */
interface CountTwin {
    name: string;
    /** The count and the shown text of one input; undefined when this twin takes no such input. */
    read(input: string | null | undefined): {count: number; text: string} | undefined;
}

/** Every count with its display. The exact one reads a string both as an exact decimal and as the display projection of a ratio. */
const COUNT_TWINS: CountTwin[] = [
    {name: 'plannerQuantityCount / formatPlannerQuantity', read: (input) => ({count: plannerQuantityCount(input), text: formatPlannerQuantity(input)})},
    {name: 'plannerPlainDecimalCount / formatPlannerPlainDecimal', read: (input) => ({count: plannerPlainDecimalCount(input), text: formatPlannerPlainDecimal(input)})},
    {name: 'exactQuantityCount / formatExactQuantity, exact decimal', read: (input) => (typeof input === 'string' ? {count: exactQuantityCount(finite(input)), text: formatExactQuantity(finite(input))} : undefined)},
    {name: 'exactQuantityCount / formatExactQuantity, ratio projection', read: (input) => (typeof input === 'string' ? {count: exactQuantityCount(ratio('1', '3', input)), text: formatExactQuantity(ratio('1', '3', input))} : undefined)},
];

/** Valid, invalid and absent values. Integer parts stay far below 2^52, where adding 0.5 is exact. */
const TWIN_INPUTS: (string | null | undefined)[] = ['0', '-0', '1', '1.', '1.000', '2', '1.5', '-1', '-1.5', '0.25', '.5', '-.5', '123.456', '1000000', ' 1.5 ', TWENTY_DIGIT_ONE, TWENTY_NINES, TWENTY_ONE_DIGIT_ONE, '', ' ', 'abc', '1e3', '1,5', '-', '.', null, undefined];

/**
 * Why a count is not the count of its text, or null when it is. NaN exactly when no digit is shown
 * (the empty cell and the placeholder carry none). Otherwise the integer part shown, its `≈` and
 * sign set aside, and a fraction counted exactly when a decimal separator is shown. The text is read
 * the way the interface locale writes numbers (M-18 CP3a): its grouping separators set aside, its
 * decimal separator marking the fraction — `1,000,000` is a million in English, `1,5` one and a
 * half in Italian.
 */
function twinMismatch(count: number, text: string, locale: string = uiLocale()): string | null {
    const digitShown = /\d/.test(text);
    if (Number.isNaN(count)) return digitShown ? 'NaN next to digits' : null;
    if (!digitShown) return 'a number next to no digit';
    const parts = new Intl.NumberFormat(locale).formatToParts(1234567.5);
    const group = parts.find((part) => part.type === 'group')?.value ?? '';
    const decimal = parts.find((part) => part.type === 'decimal')?.value ?? '.';
    const unsigned = text.replace(/^≈/, '').replace(/^[-\u2212]/, '');
    const [integerPart, fractionPart] = (group === '' ? unsigned : unsigned.split(group).join('')).split(decimal);
    if (Math.trunc(count) !== Number(integerPart)) return `integer part ${Math.trunc(count)}, shown ${integerPart} (read in ${locale})`;
    const fractionCounted = count % 1 !== 0;
    const fractionShown = fractionPart !== undefined;
    if (fractionCounted !== fractionShown) return fractionShown ? 'a fraction shown, none counted' : 'a fraction counted, none shown';
    return null;
}

/**
 * Every count twin over every input, in the interface language and privacy state of the moment: each
 * count must be the count of its shown text.
 */
function expectTwinProperty(on: boolean): void {
    privacy(on);
    const mismatches: string[] = [];
    const texts = new Set<string>();
    let read = 0;
    for (const twin of COUNT_TWINS) {
        for (const input of TWIN_INPUTS) {
            const pair = twin.read(input);
            if (pair === undefined) continue;
            read += 1;
            texts.add(pair.text);
            const mismatch = twinMismatch(pair.count, pair.text);
            if (mismatch !== null) mismatches.push(`${twin.name}, ${JSON.stringify(input)}: shown ${JSON.stringify(pair.text)}, counted ${pair.count}: ${mismatch}`);
        }
    }

    // The walk read what it claims: every input through the two plain twins, every string through the two exact ones.
    const strings = TWIN_INPUTS.filter((input) => typeof input === 'string').length;
    expect(read, 'pairs read').toBe(2 * TWIN_INPUTS.length + 2 * strings);
    // And it met every kind of text: digits, the empty cell, and the placeholder exactly when privacy is on.
    const digitsShown = [...texts].some((text) => /\d/.test(text));
    expect(digitsShown, 'some text shows digits').toBe(true);
    expect(texts.has(EMPTY), 'some text is the empty cell').toBe(true);
    expect(texts.has(P), 'the placeholder appears exactly when privacy is on').toBe(on);
    expect(mismatches).toEqual([]);
}

describe('plural counts — the count is the count of the shown text (twin property)', () => {
    it.each([
        {privacy: 'off', on: false},
        {privacy: 'on', on: true},
    ])('privacy $privacy', ({on}) => {
        expectTwinProperty(on);
    });
});

// ---------------------------------------------------------------------------
// M-18 CP3a — the exact decimals in the interface language
// ---------------------------------------------------------------------------

describe('formatPlannerQuantity, formatPlannerPlainDecimal, formatPlannerFxRate — the exact decimals in the interface language (M-18 CP3a)', () => {
    /** Thousands and more than eight fraction digits: every separator of a notation shows, and no digit may go. */
    const QUANTITY = '12345.678901234';
    /** A scenario parameter in the thousands. */
    const STEP = '25000.5';
    /** An FX rate with thirteen fraction digits. */
    const RATE = '1.0823456789012';
    /** A rate in the thousands (EUR → KRW): four integer digits, which Italian leaves ungrouped and French groups. */
    const LARGE_RATE = '1480.123456';

    /** Counts above a thousand, where a written text has grouping to misread. */
    const THOUSANDS_COUNT_CASES: CountCase[] = [
        {input: '12345.678', count: 12345.5, why: 'integer part 12345, plus 0.5 for the fraction shown'},
        {input: '1234567', count: 1234567, why: 'a million and more, no fraction'},
        {input: '-12345.5', count: 12345.5, why: 'plural operands are absolute'},
    ];

    /** The UI in `lang` on the pinned en-US browser; returns the interface locale that gives, checked. */
    async function interfaceUi(lang: UiLanguage): Promise<string> {
        await uiLanguage(lang);
        expect(uiLocale(), `control: a ${lang} UI on an en-US browser is written ${LOCALE_OF[lang]}`).toBe(LOCALE_OF[lang]);
        return LOCALE_OF[lang];
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it.each(['it', 'fr'] as const)('%s UI: a quantity, a plain decimal, an FX rate and a solver count keep every digit, written in the language’s notation', async (lang) => {
        const locale = await interfaceUi(lang);
        const expected = {
            quantity: intlExact(locale, QUANTITY),
            twentyDigits: intlExact(locale, TWENTY_DIGIT_ONE),
            negative: intlExact(locale, '-1234.5'),
            step: intlExact(locale, STEP),
            rate: intlExact(locale, RATE),
            largeRate: intlExact(locale, LARGE_RATE),
            solverCount: '≈' + intlExact(locale, '12345.68'),
        };
        // Controls: Intl keeps every digit it is handed, and the language really writes them otherwise than English.
        expect(digitsOf(expected.quantity), 'control: every digit of the quantity').toBe(digitsOf(QUANTITY));
        expect(digitsOf(expected.twentyDigits), 'control: all twenty fraction digits, which a double reads as 1').toBe(digitsOf(TWENTY_DIGIT_ONE));
        expect(expected.quantity, 'control: the quantity is written otherwise than in English').not.toBe(intlExact(INTERFACE_LOCALE, QUANTITY));
        expect(expected.rate, 'control: the rate is written otherwise than in English').not.toBe(intlExact(INTERFACE_LOCALE, RATE));

        expect({
            quantity: formatPlannerQuantity(QUANTITY),
            twentyDigits: formatPlannerQuantity(TWENTY_DIGIT_ONE),
            negative: formatPlannerQuantity('-1234.5'),
            step: formatPlannerPlainDecimal(STEP),
            rate: formatPlannerFxRate(RATE),
            largeRate: formatPlannerFxRate(LARGE_RATE),
            solverCount: formatSolverNumber('12345.678', COUNT, digits),
        }).toEqual(expected);
    });

    it.each(['it', 'fr'] as const)('%s UI: ≈ stays in front of an approximate quantity or rate, outside the digits', async (lang) => {
        const locale = await interfaceUi(lang);

        expect({
            quantity: formatPlannerQuantity(QUANTITY, {approx: true}),
            rate: formatPlannerFxRate(RATE, {approx: true}),
            exactQuantity: formatExactQuantity(ratio('1', '3', '0.333333')),
            exactRate: formatExactFxRate(ratio('2', '3', '0.666667')),
        }).toEqual({
            quantity: '≈' + intlExact(locale, QUANTITY),
            rate: '≈' + intlExact(locale, RATE),
            exactQuantity: '≈' + intlExact(locale, '0.333333'),
            exactRate: '≈' + intlExact(locale, '0.666667'),
        });
    });

    it('Italian UI, privacy on: a quantity stays masked, ≈ outside the mask; a plain decimal and an FX rate are public, written in Italian', async () => {
        const locale = await interfaceUi('it');
        privacy(true);

        expect({
            quantity: formatPlannerQuantity(QUANTITY),
            approxQuantity: formatPlannerQuantity(QUANTITY, {approx: true}),
            exactQuantity: formatExactQuantity(ratio('1', '3', '0.333333')),
            step: formatPlannerPlainDecimal(STEP),
            rate: formatPlannerFxRate(RATE),
            approxRate: formatPlannerFxRate(RATE, {approx: true}),
        }).toEqual({
            quantity: P,
            approxQuantity: '≈' + P,
            exactQuantity: '≈' + P,
            step: intlExact(locale, STEP),
            rate: intlExact(locale, RATE),
            approxRate: '≈' + intlExact(locale, RATE),
        });
    });

    it('English UI on an en-US browser: from 1,000 on, a quantity, a plain decimal, an FX rate and a solver count are now grouped — 12,345.678, the new contract of M-18 CP3a; below 1,000 nothing moves', async () => {
        const locale = await interfaceUi('en');
        const grouped = intlExact(locale, '12345.678');
        expect(grouped, 'control: en-US writes a thousands separator').not.toBe('12345.678');
        expect(digitsOf(grouped), 'control: and keeps every digit').toBe('12345678');
        expect(intlExact(locale, '123.456'), 'control: below 1,000, en-US writes the plain decimal').toBe('123.456');

        expect({
            quantity: formatPlannerQuantity('12345.678'),
            step: formatPlannerPlainDecimal(STEP),
            rate: formatPlannerFxRate(LARGE_RATE),
            solverCount: formatSolverNumber('1234.5678', COUNT, digits),
            belowThousand: formatPlannerQuantity('123.456'),
        }).toEqual({
            quantity: grouped,
            step: intlExact(locale, STEP),
            rate: intlExact(locale, LARGE_RATE),
            solverCount: '≈' + intlExact(locale, '1234.57'),
            belowThousand: '123.456',
        });
    });

    it.each(['en', 'it', 'fr'] as const)('%s UI: the plural counts do not move with the language — read off the plain digits, never off the written text (guard)', async (lang) => {
        await interfaceUi(lang);
        privacy(false);

        for (const {input, count, why} of [...COUNT_CASES, ...THOUSANDS_COUNT_CASES]) {
            const shown = JSON.stringify(input) ?? 'undefined';
            expect(asPlural(plannerQuantityCount(input)), `plannerQuantityCount(${shown}): ${why}`).toBe(count);
            expect(asPlural(plannerPlainDecimalCount(input)), `plannerPlainDecimalCount(${shown}): ${why}`).toBe(count);
            if (typeof input === 'string') expect(asPlural(exactQuantityCount(finite(input))), `exactQuantityCount(${shown}): ${why}`).toBe(count);
        }
    });

    it.each([
        {lang: 'it', privacy: 'off', on: false},
        {lang: 'it', privacy: 'on', on: true},
        {lang: 'fr', privacy: 'off', on: false},
        {lang: 'fr', privacy: 'on', on: true},
    ] as const)('$lang UI, privacy $privacy: the count is still the count of the shown text, read the way the language writes numbers (twin property)', async ({lang, on}) => {
        await interfaceUi(lang);

        expectTwinProperty(on);
    });
});

// ---------------------------------------------------------------------------
// C-73 (TP-2) — a percentage rounds a tie half away from zero, exactly
// ---------------------------------------------------------------------------

/** A plain decimal text as an integer count of 10^-scale: `-0.30595` is -30595 at scale 5. Integers only, no double. */
function scaledDecimal(text: string): {units: bigint; scale: number} {
    const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(text);
    if (match === null) throw new Error(`not a plain decimal: ${text}`);
    const [, sign, integer, fraction = ''] = match;
    const magnitude = BigInt(integer + fraction);
    return {units: sign === '-' ? -magnitude : magnitude, scale: fraction.length};
}

/** `units` × 10^-scale as a plain decimal text with exactly `scale` fraction digits: -3060 at scale 4 is `-0.3060`. */
function scaledText(units: bigint, scale: number): string {
    const digits = (units < 0n ? -units : units).toString().padStart(scale + 1, '0');
    const text = scale === 0 ? digits : `${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
    return units < 0n ? '-' + text : text;
}

/** One Intl percent format per locale and digit count: the sweep asks for the same one 8 000 times. */
const PERCENT_FORMATS = new Map<string, Intl.NumberFormat>();

function percentFormat(locale: string, digits: number): Intl.NumberFormat {
    const id = `${locale}|${digits}`;
    let format = PERCENT_FORMATS.get(id);
    if (format === undefined) {
        format = new Intl.NumberFormat(locale, {style: 'percent', minimumFractionDigits: digits, maximumFractionDigits: digits});
        PERCENT_FORMATS.set(id, format);
    }
    return format;
}

interface OwedPercentOptions {
    signed?: boolean;
    approx?: boolean;
    /** The interface locale of the case: en-US unless the UI language was switched. */
    locale?: string;
}

/**
 * The text owed for a percentage of `units` × 10^-scale percent: rounded to `digits` places half away from zero, in
 * integers, then written as the planner writes a percentage today (`formatPercent`'s `%` branch) — `≈` in front when
 * approximate, `+` before a positive value when signed, Intl's percent of the locale with exactly `digits` fraction
 * digits. Intl is handed the rounded fraction as a string, an exact decimal (Intl.NumberFormat v3): it has nothing
 * left to round, so its own rounding mode never decides a digit.
 */
function owedPercent(units: bigint, scale: number, digits: number, {signed = false, approx = false, locale = INTERFACE_LOCALE}: OwedPercentOptions = {}): string {
    let rounded: bigint; // the percentage × 10^digits
    if (scale <= digits) {
        rounded = units * 10n ** BigInt(digits - scale);
    } else {
        const divisor = 10n ** BigInt(scale - digits);
        const magnitude = units < 0n ? -units : units;
        // Half away from zero: the magnitude rounded half up, then the sign put back.
        const quotient = (2n * magnitude + divisor) / (2n * divisor);
        rounded = units < 0n ? -quotient : quotient;
    }
    // A percentage × 10^digits is its fraction × 10^(digits + 2).
    const text = percentFormat(locale, digits).format(scaledText(rounded, digits + 2) as Intl.StringNumericLiteral);
    return (approx ? '≈' : '') + (signed && rounded > 0n ? '+' : '') + text;
}

/** What `formatPlannerPercent(fraction, {digits, …})` owes: a fraction is its percentage two places along. */
function owedShare(fraction: string, digits = 2, options: OwedPercentOptions = {}): string {
    const {units, scale} = scaledDecimal(fraction);
    return owedPercent(units, scale - 2, digits, options);
}

/** What `formatPlannerPercentUnits(percent, digits)` owes. */
function owedUnits(percent: string, digits = 2, options: OwedPercentOptions = {}): string {
    const {units, scale} = scaledDecimal(percent);
    return owedPercent(units, scale, digits, options);
}

describe('formatPlannerPercent — a share rounds a tie half away from zero, exactly (C-73, TP-2)', () => {
    it('shows an exact share of 0.30595 as 30.60%, not 30.59%; so does an exact weight, decimal or ratio', () => {
        expect((Number('0.30595') * 100).toFixed(2), 'control: the double path rounds this tie down').toBe('30.59');
        const owed = owedShare('0.30595');
        expect(owed, 'control: the en-US text owed').toBe('30.60%');

        expect({
            share: formatPlannerPercent('0.30595'),
            weight: formatExactPercent(finite('0.30595')),
            ratioWeight: formatExactPercent(ratio('6119', '20000', '0.30595', 5)),
        }).toEqual({share: owed, weight: owed, ratioWeight: owed});
    });

    it('rounds a negative tie away from zero; signed puts + before a positive one, approx keeps ≈ in front; privacy leaves a share in the clear', () => {
        expect((Number('-0.30595') * 100).toFixed(2), 'control: the double path rounds this tie toward zero').toBe('-30.59');
        const owed = {
            negative: owedShare('-0.30595'),
            signed: owedShare('0.30595', 2, {signed: true}),
            negativeSigned: owedShare('-0.30595', 2, {signed: true}),
            approx: owedShare('0.30595', 2, {approx: true}),
            signedApprox: owedShare('0.30595', 2, {signed: true, approx: true}),
        };
        expect(owed, 'control: the en-US text owed').toEqual({negative: '-30.60%', signed: '+30.60%', negativeSigned: '-30.60%', approx: '≈30.60%', signedApprox: '≈+30.60%'});
        const shown = () => ({
            negative: formatPlannerPercent('-0.30595'),
            signed: formatPlannerPercent('0.30595', {signed: true}),
            negativeSigned: formatPlannerPercent('-0.30595', {signed: true}),
            approx: formatPlannerPercent('0.30595', {approx: true}),
            signedApprox: formatPlannerPercent('0.30595', {signed: true, approx: true}),
        });

        expect(shown(), 'privacy off').toEqual(owed);
        privacy(true);
        expect(shown(), 'privacy on: a percentage is public, so it stays in the clear').toEqual(owed);
    });

    it('rounds a tie at the places asked: 0.145 is 15% at none, 0.3065 is 30.7% at one', () => {
        expect({none: (Number('0.145') * 100).toFixed(0), one: (Number('0.3065') * 100).toFixed(1)}, 'control: the double path rounds both ties down').toEqual({none: '14', one: '30.6'});
        const owed = {none: owedShare('0.145', 0), one: owedShare('0.3065', 1)};
        expect(owed, 'control: the en-US text owed').toEqual({none: '15%', one: '30.7%'});

        expect({none: formatPlannerPercent('0.145', {digits: 0}), one: formatPlannerPercent('0.3065', {digits: 1})}).toEqual(owed);
    });

    it('sweep: every tie at the fifth decimal from 0.10005 to 0.89995, 8 000 shares, reads its exact rounding', () => {
        const mismatches: string[] = [];
        let read = 0;
        let oracleSlips = 0;
        for (let head = 1000; head <= 8999; head += 1) {
            // 0.10005 … 0.89995: five decimals, the last a 5, so a tie at two places of a percent.
            const fraction = `0.${head}5`;
            const owed = owedShare(fraction);
            // The oracle against the arithmetic, on every value: half away from zero takes 0.ABCD5 up to ABCD + 1 hundredths of a percent.
            if (digitsOf(owed) !== String(head + 1)) oracleSlips += 1;
            const shown = formatPlannerPercent(fraction);
            read += 1;
            if (shown !== owed) mismatches.push(`${fraction}: shown ${shown}, owed ${owed}`);
        }

        expect({read, oracleSlips}, 'control: 8 000 ties read, each owed the next hundredth of a percent').toEqual({read: 8000, oracleSlips: 0});
        expect({mismatches: mismatches.length, first: mismatches.slice(0, 5)}).toEqual({mismatches: 0, first: []});
    });

    it('guards: a share that is not a tie reads as before, one just below a tie is rounded once, and a missing or unreadable one is the empty cell', () => {
        const owed = {
            sixty: owedShare('0.6'),
            third: owedShare('0.333333333333'),
            belowTie: owedShare('0.305949999'),
            zero: owedShare('0'),
            negativeZero: owedShare('-0'),
            whole: owedShare('1'),
        };
        expect(owed, 'control: the en-US text owed').toEqual({sixty: '60.00%', third: '33.33%', belowTie: '30.59%', zero: '0.00%', negativeZero: '0.00%', whole: '100.00%'});

        expect({
            sixty: formatPlannerPercent('0.6'),
            third: formatPlannerPercent('0.333333333333'),
            belowTie: formatPlannerPercent('0.305949999'),
            zero: formatPlannerPercent('0'),
            negativeZero: formatPlannerPercent('-0'),
            whole: formatPlannerPercent('1'),
        }).toEqual(owed);
        for (const input of [null, undefined, '', ' ', 'abc', '1e3', '1,5']) expect(formatPlannerPercent(input), `${JSON.stringify(input) ?? 'undefined'} is not a share`).toBe(EMPTY);
        expect(formatPlannerPercent(null, {approx: true}), 'no ≈ on an empty cell').toBe(EMPTY);
    });
});

describe('formatPlannerPercentUnits — a value already in percent rounds a tie the same way (C-73, TP-2)', () => {
    it('shows 30.595 as 30.60%, and -30.595 as -30.60%', () => {
        expect({positive: Number('30.595').toFixed(2), negative: Number('-30.595').toFixed(2)}, 'control: the double path rounds both ties toward zero').toEqual({positive: '30.59', negative: '-30.59'});
        const owed = {positive: owedUnits('30.595'), negative: owedUnits('-30.595')};
        expect(owed, 'control: the en-US text owed').toEqual({positive: '30.60%', negative: '-30.60%'});

        expect({positive: formatPlannerPercentUnits('30.595'), negative: formatPlannerPercentUnits('-30.595')}).toEqual(owed);
    });

    it('at one place, 30.65 is 30.7% and 0.15 is 0.2%', () => {
        expect({thirty: Number('30.65').toFixed(1), small: Number('0.15').toFixed(1)}, 'control: the double path rounds both ties down').toEqual({thirty: '30.6', small: '0.1'});
        const owed = {thirty: owedUnits('30.65', 1), small: owedUnits('0.15', 1)};
        expect(owed, 'control: the en-US text owed').toEqual({thirty: '30.7%', small: '0.2%'});

        expect({thirty: formatPlannerPercentUnits('30.65', 1), small: formatPlannerPercentUnits('0.15', 1)}).toEqual(owed);
    });

    it('guard: at no place, 30.5 is 31% and -30.5 is -31% — right already: a tie at a whole percent is a binary fraction, which toFixed takes away from zero', () => {
        expect({half: Number('30.5').toFixed(0), negativeHalf: Number('-30.5').toFixed(0)}, 'control: the double path is exact here').toEqual({half: '31', negativeHalf: '-31'});
        const owed = {half: owedUnits('30.5', 0), negativeHalf: owedUnits('-30.5', 0)};
        expect(owed, 'control: the en-US text owed').toEqual({half: '31%', negativeHalf: '-31%'});

        expect({half: formatPlannerPercentUnits('30.5', 0), negativeHalf: formatPlannerPercentUnits('-30.5', 0)}).toEqual(owed);
    });

    it('guards: a value that is not a tie reads as before, and a missing or unreadable one is the empty cell', () => {
        const owed = {sixty: owedUnits('60'), third: owedUnits('33.333333'), belowTie: owedUnits('30.594999'), noPlace: owedUnits('12.34', 0)};
        expect(owed, 'control: the en-US text owed').toEqual({sixty: '60.00%', third: '33.33%', belowTie: '30.59%', noPlace: '12%'});

        expect({
            sixty: formatPlannerPercentUnits('60'),
            third: formatPlannerPercentUnits('33.333333'),
            belowTie: formatPlannerPercentUnits('30.594999'),
            noPlace: formatPlannerPercentUnits('12.34', 0),
        }).toEqual(owed);
        for (const input of [null, undefined, '', 'abc', '1e3']) expect(formatPlannerPercentUnits(input), `${JSON.stringify(input) ?? 'undefined'} is not a percentage`).toBe(EMPTY);
    });
});

describe('the percentages in the interface language: a tie rounds the same, written in the language’s notation (C-73, TP-2)', () => {
    /** The UI in `lang` on the pinned en-US browser; returns the interface locale that gives, checked. */
    async function percentUi(lang: 'it' | 'fr'): Promise<string> {
        await uiLanguage(lang);
        expect(uiLocale(), `control: a ${lang} UI on an en-US browser is written ${LOCALE_OF[lang]}`).toBe(LOCALE_OF[lang]);
        return LOCALE_OF[lang];
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it.each(['it', 'fr'] as const)('%s UI, guard: a share and a percentage that are not ties read as before, so the oracle writes the language as the planner does', async (lang) => {
        const locale = await percentUi(lang);

        expect({
            share: formatPlannerPercent('0.6'),
            signedNegative: formatPlannerPercent('-0.333333333333', {signed: true}),
            signedPositive: formatPlannerPercent('0.6', {signed: true}),
            units: formatPlannerPercentUnits('12.5', 1),
        }).toEqual({
            share: owedShare('0.6', 2, {locale}),
            signedNegative: owedShare('-0.333333333333', 2, {signed: true, locale}),
            signedPositive: owedShare('0.6', 2, {signed: true, locale}),
            units: owedUnits('12.5', 1, {locale}),
        });
    });

    it.each(['it', 'fr'] as const)('%s UI: a share of 0.30595 and a percentage of 30.595 both read 30.60, in the language', async (lang) => {
        const locale = await percentUi(lang);
        const owed = {share: owedShare('0.30595', 2, {locale}), units: owedUnits('30.595', 2, {locale})};
        expect(owed.share, 'control: the language writes a percentage otherwise than English').not.toBe(owedShare('0.30595'));
        expect(digitsOf(owed.share), 'control: with the digits of 30.60').toBe('3060');

        expect({share: formatPlannerPercent('0.30595'), units: formatPlannerPercentUnits('30.595')}).toEqual(owed);
    });
});
