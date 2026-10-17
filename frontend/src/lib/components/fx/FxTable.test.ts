// @vitest-environment jsdom
/**
 * FxTable — component test (Vitest + jsdom): the FX list table's rate and its absolute Δ over the range keep their
 * significant digits, whichever way round a row shows its pair (C-97c-4, decision D-C97c-1 of the coordinator, 17/10).
 *
 * The table view of the FX list shows, per pair, the last rate (column `rate`) and the absolute Δ over the range on
 * screen (column `deltaAbs`: the backend's `rangeDeltas`, `direct` for a row shown as stored and `inverse` for one the
 * user inverted, `isCardInverted`). Both are written with four fixed decimals — `formatFixed(r, 4)` in the rate cell,
 * `formatFixed(val, 4, {signed: true})` in `formatDelta` (FxTable.svelte) — so a weak currency read against a strong one
 * loses its digits: IDR→USD (≈ 0.0000625) reads `0.0001`, LBP→USD (≈ 0.0000112) `0.0000`, USD-VND inverted to VND→USD
 * (≈ 0.0000412) `0.0000`, a Δ of 0.0000021 `+0.0000`. The contract: `formatPrice(r, {minDecimals: 4})` and
 * `formatPrice(val, {minDecimals: 4, signed: true})` — four decimals at least, as many as the first four significant
 * digits need (`priceFractionDigits`, formatFixed.ts), at most twelve; a `+` on a rise, no sign on a zero. Markup and
 * classes unchanged: each cell stays a `{type: 'html'}` span.
 *
 * Reds on HEAD, because the sites still write `formatFixed(…, 4)`: the rate cell of IDR-USD at 0.0000625 (today
 * `0.0001`), of LBP-USD at 0.0000112 (today `0.0000`) and of USD-VND at 24272 inverted, 1/24272 (today `0.0000`); the Δ
 * cell of IDR-USD's rise of 0.0000021 (today `+0.0000`) and of inverted USD-VND's fall of 0.0000021 (today `-0.0000`).
 * Guards, green today and after: EUR-USD at 1.0823, flat over the range (`1.0823`, and `0.0000` with no sign), and IDR-USD
 * inverted — USD→IDR at 16000, a fall of 556 (`16,000.0000`, `-556.0000`).
 *
 * Premises, checked in each case before a cell is read: the cure's formatter writes the expected text
 * (`formatPrice(x, {minDecimals: 4[, signed: true]})`, the oracle: the typed strings are its own, not guesses) and the
 * site's formatter today writes what the cell shows today (`formatFixed(x, 4[, {signed: true}])`, the barrier). A red
 * after them is the site's.
 *
 * The harness. The real table on the real DataTable, with real i18n and the real inversion store: an inverted row is one
 * the user inverted earlier, set in the store before the mount, and the store is emptied after each case. As in
 * `FxMissingRate.test.ts`, `goto` is a spy, the currency store answers a fixed flag and the provider-icon version is a
 * plain store. No row has a provider (the providers column is hidden by default).
 *
 * Reading. The cells carry no `data-testid`: each is read by the attributes DataTable stamps — the row by the slug it was
 * given (`tr[data-row-id]`), the cell by its column's id (`td[data-column-id]`) — and holds its figure alone, so it is
 * compared whole. The way round a row shows its pair is read off its pair cell: its currency codes, in order. English UI
 * on jsdom's en-US browser, checked before each case: the digits are typed.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`), next to
 * `FxMissingRate.test.ts`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';

vi.mock('$app/navigation', () => ({goto: vi.fn()}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: vi.fn(),
    getCurrencyInfo: (code: string) => ({code, flag_emoji: '🏳️'}),
}));
vi.mock('$lib/stores/currencyGraphStore', () => ({fxProvidersVersion: writable(0)}));

import {render, setupI18n, waitFor} from '$test/component';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {clearCardInversions, setCardInverted} from '$lib/stores/fx/fxCardInversionStore';
import {formatFixed, formatPrice} from '$lib/utils/core/formatFixed';
import type {RangeDelta} from '$lib/utils/rangeChange';
import FxTable, {type FxRow} from './FxTable.svelte';

/**
 * The premise of a case: the cure, `formatPrice(value, {minDecimals: 4})`, writes `cure`, and the site's formatter today,
 * `formatFixed(value, 4)`, writes `today` — both `signed` for the Δ column. Checked before the table is read, so a red
 * after them is the site's.
 */
function premise(value: number, cure: string, today: string, {signed = false}: {signed?: boolean} = {}): void {
    expect(formatPrice(value, {minDecimals: 4, signed}), `control: the cure, formatPrice(${value}, {minDecimals: 4${signed ? ', signed: true' : ''}}), writes ${cure}`).toBe(cure);
    expect(formatFixed(value, 4, {signed}), `barrier: the site today, formatFixed(${value}, 4${signed ? ', {signed: true}' : ''}), writes ${today}`).toBe(today);
}

/** A row of the pair `base`-`quote`, stored at `rate` on the last day of the range, with its Δs over the range or none. */
function pair(base: string, quote: string, rate: number, rangeDeltas: {direct: RangeDelta; inverse: RangeDelta} | null = null): FxRow {
    return {slug: `${base}-${quote}`, base, quote, data: [{date: '2026-10-16', rate, backwardFillInfo: null}], manualOnly: false, providers: [], rangeDeltas};
}

/** IDR→USD as stored: 0.0000604 → 0.0000625 over the range, a rise of 0.0000021; USD→IDR, inverted: 16556 → 16000, a fall of 556. */
const IDR_USD = pair('IDR', 'USD', 0.0000625, {direct: {abs: 0.0000021, pct: 3.48}, inverse: {abs: -556, pct: -3.36}});
/** LBP→USD as stored, with no Δ. */
const LBP_USD = pair('LBP', 'USD', 0.0000112);
/** USD→VND as stored: 23095 → 24272, a rise of 1177; VND→USD, inverted: 0.0000433 → 0.0000412, a fall of 0.0000021. */
const USD_VND = pair('USD', 'VND', 24272, {direct: {abs: 1177, pct: 5.1}, inverse: {abs: -0.0000021, pct: -4.85}});
/** EUR→USD as stored, flat over the range. */
const EUR_USD = pair('EUR', 'USD', 1.0823, {direct: {abs: 0, pct: 0}, inverse: {abs: 0, pct: 0}});

/** Mount the table on `rows` and wait for each of them; answer the mount. */
async function mountTable(rows: FxRow[]): Promise<HTMLElement> {
    const {container} = render(FxTable, {data: rows, loading: false});
    await waitFor(() => {
        for (const {slug} of rows) expect(container.querySelector(`tbody tr[data-row-id="${slug}"]`), `barrier: row ${slug} is rendered`).not.toBeNull();
    });
    return container;
}

/** The text of the `column` cell in the row `slug` of `table`, whitespace runs collapsed. */
function cellOf(table: HTMLElement, slug: string, column: 'pair' | 'rate' | 'deltaAbs'): string {
    const cell = table.querySelector<HTMLElement>(`tbody tr[data-row-id="${slug}"] td[data-column-id="${column}"]`);
    if (!cell) throw new Error(`row ${slug} has no ${column} cell`);
    return (cell.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** The currency codes of the row `slug`'s pair cell, in the order the row shows them. */
function pairOf(table: HTMLElement, slug: string): string[] {
    return cellOf(table, slug, 'pair').match(/\b[A-Z]{3}\b/g) ?? [];
}

beforeAll(async () => {
    await setupI18n();
});

describe('FxTable — the rate and the absolute Δ keep their significant digits, either way round (C-97c-4, D-C97c-1)', () => {
    beforeEach(() => {
        // The expected digits are typed: the premise that the table writes en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    afterEach(() => {
        // The inversions a case sets live in a module-level store that outlives the table: empty it for the next case.
        clearCardInversions();
    });

    it('the rate cell: IDR→USD at 0.0000625 reads 0.0000625 and LBP→USD at 0.0000112 reads 0.0000112, not 0.0001 and 0.0000', async () => {
        premise(0.0000625, '0.0000625', '0.0001');
        premise(0.0000112, '0.0000112', '0.0000');
        const table = await mountTable([IDR_USD, LBP_USD]);
        expect({idr: pairOf(table, 'IDR-USD'), lbp: pairOf(table, 'LBP-USD')}, 'barrier: both rows show the pair as stored').toEqual({idr: ['IDR', 'USD'], lbp: ['LBP', 'USD']});

        expect.soft(cellOf(table, 'IDR-USD', 'rate'), 'IDR→USD (today 0.0001)').toBe('0.0000625');
        expect.soft(cellOf(table, 'LBP-USD', 'rate'), 'LBP→USD (today 0.0000)').toBe('0.0000112');
    });

    it('the rate cell of a row shown inverted: USD-VND at 24272, as VND→USD, reads 0.0000412, not 0.0000', async () => {
        premise(1 / 24272, '0.0000412', '0.0000');
        setCardInverted('USD-VND', true);
        const table = await mountTable([USD_VND]);
        expect(pairOf(table, 'USD-VND'), 'barrier: the row shows the pair inverted, VND→USD').toEqual(['VND', 'USD']);

        expect(cellOf(table, 'USD-VND', 'rate'), 'VND→USD (today 0.0000)').toBe('0.0000412');
    });

    it('the Δ Abs cell: a rise of 0.0000021 over the range reads +0.0000021, not +0.0000', async () => {
        premise(0.0000021, '+0.0000021', '+0.0000', {signed: true});
        const table = await mountTable([IDR_USD]);
        expect(pairOf(table, 'IDR-USD'), 'barrier: the row shows the pair as stored, so its Δ is the direct one').toEqual(['IDR', 'USD']);

        expect(cellOf(table, 'IDR-USD', 'deltaAbs'), 'the Δ of IDR→USD (today +0.0000)').toBe('+0.0000021');
    });

    it('the Δ Abs cell of a row shown inverted reads its inverse Δ: a fall of 0.0000021 reads -0.0000021, not -0.0000', async () => {
        premise(-0.0000021, '-0.0000021', '-0.0000', {signed: true});
        setCardInverted('USD-VND', true);
        const table = await mountTable([USD_VND]);
        expect(pairOf(table, 'USD-VND'), 'barrier: the row shows the pair inverted, so its Δ is the inverse one').toEqual(['VND', 'USD']);

        expect(cellOf(table, 'USD-VND', 'deltaAbs'), 'the Δ of VND→USD (today -0.0000)').toBe('-0.0000021');
    });

    it('guard: EUR→USD at 1.0823, flat, reads 1.0823 and 0.0000 with no sign; IDR-USD inverted, USD→IDR at 16000, reads 16,000.0000 and -556.0000 — as today', async () => {
        premise(1.0823, '1.0823', '1.0823');
        premise(0, '0.0000', '0.0000', {signed: true});
        premise(1 / 0.0000625, '16,000.0000', '16,000.0000');
        premise(-556, '-556.0000', '-556.0000', {signed: true});
        setCardInverted('IDR-USD', true);
        const table = await mountTable([EUR_USD, IDR_USD]);
        expect({eur: pairOf(table, 'EUR-USD'), idr: pairOf(table, 'IDR-USD')}, 'barrier: EUR-USD as stored, IDR-USD inverted').toEqual({eur: ['EUR', 'USD'], idr: ['USD', 'IDR']});

        expect({
            eurUsd: {rate: cellOf(table, 'EUR-USD', 'rate'), delta: cellOf(table, 'EUR-USD', 'deltaAbs')},
            usdIdr: {rate: cellOf(table, 'IDR-USD', 'rate'), delta: cellOf(table, 'IDR-USD', 'deltaAbs')},
        }).toEqual({eurUsd: {rate: '1.0823', delta: '0.0000'}, usdIdr: {rate: '16,000.0000', delta: '-556.0000'}});
    });
});
