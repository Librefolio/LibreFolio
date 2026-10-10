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
 * that the dropped digits are gone. The L2 distance prints its digits with the host's plain number
 * format (`toLocaleString`, at most two decimals), so its expected text is that format applied to
 * the rounded value, its digits are checked in every case, and its values stay below 1000 so that
 * no grouping separator is involved. Masked strings and solver counts have no locale (a
 * placeholder, and `formatDecimalForDisplay`), so those are exact literals. So are the plural
 * counts, plain numbers. `toBe` compares them with `Object.is`, so NaN matches NaN; a plural rule
 * reads -0 as 0, and the table of counts does too.
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
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

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
import {
    catalogCurrencyDigits,
    exactMoneyDisplay,
    exactQuantityCount,
    formatExactMoneyHtml,
    formatExactMoneyPlain,
    formatExactQuantity,
    formatObjectiveValue,
    formatPlannerL2,
    formatPlannerMoneyPlain,
    formatPlannerPlainDecimal,
    formatPlannerQuantity,
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

/** The host's plain number with at most two decimals: how the L2 formatter prints its digits. */
function plainNumber(amount: number): string {
    return amount.toLocaleString(undefined, {maximumFractionDigits: 2});
}

/** The digits of a formatted string, whatever separators the locale puts between them. */
function digitsOf(text: string): string {
    return text.replace(/\D/g, '');
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
        ['1234.5678', '≈1234.57'],
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
 * sign set aside, and a fraction counted exactly when a point is shown.
 */
function twinMismatch(count: number, text: string): string | null {
    const digitShown = /\d/.test(text);
    if (Number.isNaN(count)) return digitShown ? 'NaN next to digits' : null;
    if (!digitShown) return 'a number next to no digit';
    const integerPart = text.replace(/^≈/, '').replace(/^-/, '').split('.')[0];
    if (Math.trunc(count) !== Number(integerPart)) return `integer part ${Math.trunc(count)}, shown ${integerPart}`;
    const fractionCounted = count % 1 !== 0;
    const fractionShown = text.includes('.');
    if (fractionCounted !== fractionShown) return fractionShown ? 'a fraction shown, none counted' : 'a fraction counted, none shown';
    return null;
}

describe('plural counts — the count is the count of the shown text (twin property)', () => {
    it.each([
        {privacy: 'off', on: false},
        {privacy: 'on', on: true},
    ])('privacy $privacy', ({on}) => {
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
    });
});
