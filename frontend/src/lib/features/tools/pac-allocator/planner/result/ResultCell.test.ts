// @vitest-environment jsdom
/**
 * ResultCell — the R14 number cells of the result tables, followed live (Vitest + jsdom).
 *
 * Subject. ResultCell draws one cell of the planner's result tables, and R14 changed how its
 * computed numbers read:
 *   - `solver` (the proof panel's primal, dual and gap): a raw solver number formatted by the
 *     unit of its stage. Money is shown at the minor unit of its currency, with `≈` when the
 *     rounding changed it; a count goes to two decimals, is not wealth, and stays public;
 *   - `exactMoney` (the asset table's values): an amount the backend computed, as an exact
 *     decimal or an exact ratio, at the minor unit, with `≈` only when the rounding changed it;
 *   - `money` (posted flows: the order's cash debit and fee, the ledger) is the contrast. It
 *     keeps its digits and gets no `≈`.
 * The cell formats inside its template. Privacy must therefore mask it and unmask it in place,
 * both ways, on the same mount. A cell that kept its mount-time text would leak the amount.
 *
 * Expectations. The host locale decides separators and grouping, so a clear amount is the
 * shared `formatCurrencyAmountPlain` output for the rounded value (personal, with the currency's
 * minor unit as both fraction bounds), and `≈` in front where the rounding changed the value.
 * Its digits are checked against the value put in. A masked amount and a count have no locale,
 * so they are exact strings. Each cell is found by its `data-testid`; nothing here reads
 * translated text.
 *
 * Toggle. Each step checks two controls before the subject: `isPrivacyEnabled()` (the flag
 * moved), and that the cell is still the node first mounted (updated in place, not remounted).
 *
 * Catalogue. Not loaded: `$lib/api` is inert, as in StateNotice.test.ts, so the currency falls
 * back to its bare code (no symbol, no flag) on both sides of every comparison.
 *
 * Storage. The shared `$app/environment` mock reports `browser: false`, so `setPrivacyEnabled`
 * moves the in-memory rune and never touches `localStorage`.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';

// The formatter reads the currency catalogue store, which imports the API client. Nothing here
// loads the catalogue: every call resolves to nothing, and each comparison runs the shared
// formatter against the same, unloaded store.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import {cleanup, render, screen, setupI18n} from '$test/component';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {catalogCurrencyDigits} from '../format';
import type {PacExactNumber, PacObjectiveUnit} from '../types';
import ResultCell, {type ResultCellContent} from './ResultCell.svelte';

const P = PRIVACY_PLACEHOLDER;

const digits = catalogCurrencyDigits([
    {currency: 'EUR', minor_unit: '0.01'},
    {currency: 'JPY', minor_unit: '1'},
]);

const EUR_MONEY: PacObjectiveUnit = {kind: 'valuation_money', currency_code: 'EUR'};
const JPY_MONEY: PacObjectiveUnit = {kind: 'valuation_money', currency_code: 'JPY'};
const COUNT: PacObjectiveUnit = {kind: 'count'};

/** The three number variants this file mounts, each with the testid it is found by. */
type NumberCell = Extract<ResultCellContent, {type: 'solver' | 'exactMoney' | 'money'}> & {testid: string};

/** Solver money at 1234.5678 EUR: the minor unit drops two digits, so the clear text is approximate. */
const SOLVER_MONEY_CELL: NumberCell = {type: 'solver', value: '1234.5678', unit: EUR_MONEY, digits, testid: 'result-cell-solver-money'};

function finite(value: string): PacExactNumber {
    return {kind: 'finite_decimal', value};
}

/** An exact ratio as the backend sends it. The display projection is not authoritative. */
function ratio(numerator: string, denominator: string, display_decimal: string, display_scale = 6): PacExactNumber {
    return {kind: 'exact_ratio', numerator, denominator, display_decimal, display_scale, display_authority: 'non_authoritative'};
}

/** The shared formatter's clear output, as the cell must ask for it: personal money, fraction digits from minFraction to maxFraction. */
function shared(amount: number, code: string, minFraction: number, maxFraction = minFraction): string {
    return formatCurrencyAmountPlain(amount, code, {minFraction, maxFraction, showSign: false, sensitivity: 'personal'});
}

/** The digits of a formatted string, whatever separators the locale puts between them. */
function digitsOf(text: string): string {
    return text.replace(/\D/g, '');
}

async function mount(cell: NumberCell): Promise<HTMLElement> {
    render(ResultCell, {cell});
    flushSync();
    await tick();
    return screen.getByTestId(cell.testid);
}

/** Sets the flag, then flushes: synchronously, and once more through the microtask the app itself waits on. */
async function setPrivacy(value: boolean): Promise<void> {
    setPrivacyEnabled(value);
    flushSync();
    await tick();
}

/** One step: the flag is where the step says, the cell is still the node first mounted, and it shows `expected`. */
function expectCell(step: string, privacyOn: boolean, node: HTMLElement, expected: string): void {
    expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(privacyOn);
    expect(screen.getByTestId(node.dataset.testid as string), `${step} — control: the same node, updated in place`).toBe(node);
    expect(node.textContent, step).toBe(expected);
}

beforeAll(async () => {
    await setupI18n();
    setPrivacyEnabled(false);
    // Premise of the masked strings below: no catalogue, so the currency is its bare code.
    expect(getCurrencyInfo('EUR').symbol).toBe('EUR');
    expect(shared(1234.57, 'EUR', 2).endsWith(' EUR')).toBe(true);
    // The clear expectations are the shared formatter's own output, so check once that it
    // carries the digits put in, or a formatter that always masked would compare the placeholder with itself.
    expect(digitsOf(shared(1234.57, 'EUR', 2))).toBe('123457');
});

afterEach(() => {
    // The flag is module-level state shared by every test in this file: a leftover `true` would
    // mount the next cell masked.
    setPrivacyEnabled(false);
    cleanup();
});

describe('ResultCell — a solver number in valuation money', () => {
    it('shows the value at the minor unit with ≈, and masks then unmasks it in place (off → on → off)', async () => {
        const clear = '≈' + shared(1234.57, 'EUR', 2);
        expect(digitsOf(clear), 'control: the clear text carries the rounded digits, not the raw ones').toBe('123457');

        const node = await mount(SOLVER_MONEY_CELL);
        expectCell('mount, privacy off', false, node, clear);

        await setPrivacy(true);
        expectCell('off → on', true, node, `≈${P} EUR`);

        await setPrivacy(false);
        expectCell('on → off', false, node, clear);
    });

    it('mounted masked: unmasks, then masks again, in place (on → off → on)', async () => {
        const clear = '≈' + shared(1234.57, 'EUR', 2);

        await setPrivacy(true);
        const node = await mount(SOLVER_MONEY_CELL);
        expectCell('mount, privacy on', true, node, `≈${P} EUR`);

        await setPrivacy(false);
        expectCell('on → off', false, node, clear);

        await setPrivacy(true);
        expectCell('off → on', true, node, `≈${P} EUR`);
    });

    it('uses the minor unit of the stage currency: JPY has none', async () => {
        const node = await mount({type: 'solver', value: '1234.5', unit: JPY_MONEY, digits, testid: 'result-cell-solver-yen'});
        const clear = '≈' + shared(1235, 'JPY', 0);
        expect(digitsOf(clear), 'half away from zero, no fraction digits').toBe('1235');
        expectCell('privacy off', false, node, clear);

        await setPrivacy(true);
        expectCell('privacy on', true, node, `≈${P} JPY`);
    });
});

describe('ResultCell — a solver count', () => {
    it('shows two decimals, with ≈ only when the rounding changed the value, and stays public with privacy on', async () => {
        const rounded = await mount({type: 'solver', value: '3.14159', unit: COUNT, testid: 'result-cell-count-rounded'});
        const exact = await mount({type: 'solver', value: '2.5', unit: COUNT, testid: 'result-cell-count-exact'});
        // The control: a money cell in the same document, which privacy must mask.
        const money = await mount(SOLVER_MONEY_CELL);
        const clear = '≈' + shared(1234.57, 'EUR', 2);

        expectCell('privacy off: a rounded count', false, rounded, '≈3.14');
        expectCell('privacy off: an exact count', false, exact, '2.5');
        expectCell('privacy off: the money control', false, money, clear);

        await setPrivacy(true);
        expectCell('privacy on — control: money in the same document is masked', true, money, `≈${P} EUR`);
        expectCell('privacy on: a rounded count is public', true, rounded, '≈3.14');
        expectCell('privacy on: an exact count is public', true, exact, '2.5');

        await setPrivacy(false);
        expectCell('privacy off again: the money control', false, money, clear);
        expectCell('privacy off again: a rounded count', false, rounded, '≈3.14');
        expectCell('privacy off again: an exact count', false, exact, '2.5');
    });

    it('renders a value the stage did not report as an empty cell', async () => {
        const count = await mount({type: 'solver', value: null, unit: COUNT, testid: 'result-cell-count-missing'});
        const money = await mount({type: 'solver', value: null, unit: EUR_MONEY, digits, testid: 'result-cell-money-missing'});
        expectCell('count', false, count, '—');
        expectCell('money', false, money, '—');
    });
});

describe('ResultCell — an exact computed amount', () => {
    it('shows 1/3 EUR as ≈0.33 and 10.5 EUR at the minor unit with no ≈, and masks both in place', async () => {
        const third = await mount({type: 'exactMoney', money: {value: ratio('1', '3', '0.333333'), currency: 'EUR'}, digits, testid: 'result-cell-exact-third'});
        const exact = await mount({type: 'exactMoney', money: {value: finite('10.5'), currency: 'EUR'}, digits, testid: 'result-cell-exact-ten'});

        const thirdClear = '≈' + shared(0.33, 'EUR', 2);
        const exactClear = shared(10.5, 'EUR', 2);
        expect(digitsOf(thirdClear), 'control: 1/3 at the minor unit').toBe('033');
        expect(digitsOf(exactClear), 'control: padded to the minor unit').toBe('1050');
        expect(exactClear).not.toContain('≈');

        expectCell('privacy off: the ratio', false, third, thirdClear);
        expectCell('privacy off: the decimal', false, exact, exactClear);

        await setPrivacy(true);
        expectCell('privacy on: the ratio keeps ≈ outside the mask', true, third, `≈${P} EUR`);
        expectCell('privacy on: the decimal has no ≈ to keep', true, exact, `${P} EUR`);

        await setPrivacy(false);
        expectCell('privacy off again: the ratio', false, third, thirdClear);
        expectCell('privacy off again: the decimal', false, exact, exactClear);
    });
});

describe('ResultCell — a posted amount (contrast)', () => {
    it('keeps every digit of a posted flow and adds no ≈: it is not a computed amount', async () => {
        const node = await mount({type: 'money', amount: '1234.5678', currency: 'EUR', digits, testid: 'result-cell-posted'});
        const clear = shared(1234.5678, 'EUR', 2, 4);
        expect(digitsOf(clear), 'control: no digit dropped').toBe('12345678');
        expectCell('privacy off', false, node, clear);

        await setPrivacy(true);
        expectCell('privacy on', true, node, `${P} EUR`);
    });
});
