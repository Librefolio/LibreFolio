/**
 * format — the R14 money and solver display of the planner's privacy adapter (Vitest, node).
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
 *   - `formatObjectiveValue` for a money unit.
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
 * placeholder, and `formatDecimalForDisplay`), so those are exact literals.
 *
 * Privacy. Decision c: wealth is personal. With privacy on the number becomes the placeholder.
 * The `≈` marker, the sign and the currency (symbol, flag, code) stay outside the mask. A solver
 * count is not wealth and stays in the clear. Each masked case first proves that the flag is on,
 * then compares against an exact string, so an amount left in the clear cannot pass as masked.
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
import {catalogCurrencyDigits, exactMoneyDisplay, formatExactMoneyHtml, formatExactMoneyPlain, formatObjectiveValue, formatPlannerL2, formatPlannerMoneyPlain, formatSolverNumber} from './format';
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
        expect(exactMoneyDisplay(finite('-0.004'), 2), 'never -0').toEqual({text: '0', approx: true});
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

    it('puts ≈ before the sign, and never shows a negative zero', () => {
        const up = formatExactMoneyPlain(money(finite('2.345')), {digits, signed: true});
        expect(up).toBe('≈' + shared(2.35, 'EUR', 2, 2, true));
        expect(up.startsWith('≈+')).toBe(true);

        const down = formatExactMoneyPlain(money(finite('-1234.5678')), {digits, signed: true});
        expect(down).toBe('≈' + shared(-1234.57, 'EUR', 2, 2, true));
        expect(down.startsWith('≈-')).toBe(true);

        const zero = formatExactMoneyPlain(money(finite('-0.004')), {digits, signed: true});
        expect(zero).toBe('≈' + shared(0, 'EUR', 2, 2, true));
        expect(zero).not.toContain('-');
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
