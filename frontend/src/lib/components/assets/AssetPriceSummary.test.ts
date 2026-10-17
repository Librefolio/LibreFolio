// @vitest-environment jsdom
/**
 * AssetPriceSummary — component test (Vitest + jsdom): the asset page's price and its absolute Δ over the range keep
 * their significant digits (C-97c-3, decision D-C97c-1 of the coordinator, 17/10).
 *
 * The summary beside the asset page's date picker shows the last price (`asset-detail-live-price`) and, in brackets
 * after it, the absolute Δ over the range on screen (`asset-price-summary-range-delta-abs`). Both are written with two
 * fixed decimals today — `formatFixed(lastPrice, 2)` and `formatFixed(deltaAbs, 2, {signed: true})` — so a token priced
 * 0.0000034573 reads `0.00`, one priced 1.234 reads `1.23`, and a Δ of 1.2e-7 reads `(+0.00)`. The contract:
 * `formatPrice(lastPrice)` and `formatPrice(deltaAbs, {signed: true})` — two decimals at least, as many as the first four
 * significant digits need (`priceFractionDigits`, formatFixed.ts), at most twelve; a `+` on a rise, no sign on a zero.
 *
 * Reds: a price of 0.0000034573 (today `0.00`) and of 1.234 (today `1.23`); a Δ of 1.2e-7 (today `(+0.00)`) and of
 * -0.0000012 (today `(-0.00)`). Guards, green today and after: prices of 123.45 and 65000.1234 (`65,000.12`), Δs of 1.5,
 * -12.5 and 0 (`(+1.50)`, `(-12.50)`, `(0.00)`, the zero with no sign).
 *
 * The harness. The real component, with real i18n. Its currency selector (`CurrencySearchSelect`) reads the currency
 * and FX-route stores, which would ask the API: both are stubbed to resolve at once with a fixed list, as in
 * `CompactCashCell.test.ts`; nothing about the price depends on them. `goto` is the shared `$app/navigation` mock (the
 * Vitest alias). The live-price flash is neutral and no FX link is given.
 *
 * Reading. Each span is read by its test id; it holds its figure alone (the Δ inside its literal brackets), so it is
 * compared whole. English UI on jsdom's en-US browser, checked before each case: the digits are typed.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`), next to
 * `AssetTable.test.ts`.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {render, setupI18n, within} from '$test/component';

// CurrencySearchSelect (embedded) talks to the currency and FX-route stores, which hit the API — jsdom has no server.
// Stub the loaders to resolve and serve a fixed currency list; nothing about the price depends on them.
vi.mock('$lib/stores/reference/currencyStore', () => ({
    currencyStoreVersion: writable(0),
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getAllCurrencies: vi.fn(() => [
        {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
        {code: 'USD', name: 'US Dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: [], country_names: []},
    ]),
    getCurrencyInfo: vi.fn((code: string) => ({code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []})),
}));
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));

import {uiLocale} from '$lib/stores/app/uiLocale';
import AssetPriceSummary from './AssetPriceSummary.svelte';

/** Mount the summary of a USD asset shown in USD, with `lastPrice` and the absolute Δ `deltaAbs`, and no Δ%; answer its container. */
function mountSummary(lastPrice: number, deltaAbs: number | null = null): HTMLElement {
    return render(AssetPriceSummary, {lastPrice, deltaPercent: null, deltaAbs, displayCurrency: 'USD', assetCurrency: 'USD', layoutMode: 'oneRow', filtersStacked: false}).container;
}

/** The text of the element `testId` in `summary` — one mounted summary of the case, never another's — whitespace runs collapsed. */
function textOf(summary: HTMLElement, testId: string): string {
    return (within(summary).getByTestId(testId).textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** The price shown. */
function priceFor(lastPrice: number): string {
    return textOf(mountSummary(lastPrice), 'asset-detail-live-price');
}

/** The absolute Δ shown, brackets included, beside a price of 100. */
function deltaFor(deltaAbs: number): string {
    return textOf(mountSummary(100, deltaAbs), 'asset-price-summary-range-delta-abs');
}

beforeAll(async () => {
    await setupI18n();
});

describe('AssetPriceSummary — the price and its absolute Δ keep their significant digits (C-97c-3, D-C97c-1)', () => {
    beforeEach(() => {
        // The expected digits are typed: the premise that the summary writes en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    it('a price of 0.0000034573 reads 0.000003457: four significant digits, not 0.00', () => {
        expect(priceFor(0.0000034573), 'the price (today 0.00)').toBe('0.000003457');
    });

    it('a price of 1.234 reads 1.234: four significant digits, not 1.23', () => {
        expect(priceFor(1.234), 'the price (today 1.23)').toBe('1.234');
    });

    it('guard: prices of 123.45 and 65000.1234 read 123.45 and 65,000.12, as today', () => {
        expect({plain: priceFor(123.45), grouped: priceFor(65000.1234)}).toEqual({plain: '123.45', grouped: '65,000.12'});
    });

    it('a Δ of 1.2e-7 over the range reads (+0.00000012), not (+0.00)', () => {
        expect(deltaFor(1.2e-7), 'the absolute Δ of a rise (today (+0.00))').toBe('(+0.00000012)');
    });

    it('a Δ of -0.0000012 over the range reads (-0.0000012), not (-0.00)', () => {
        expect(deltaFor(-0.0000012), 'the absolute Δ of a fall (today (-0.00))').toBe('(-0.0000012)');
    });

    it('guard: Δs of 1.5, -12.5 and 0 read (+1.50), (-12.50) and (0.00) — the zero with no sign — as today', () => {
        expect({rise: deltaFor(1.5), fall: deltaFor(-12.5), flat: deltaFor(0)}).toEqual({rise: '(+1.50)', fall: '(-12.50)', flat: '(0.00)'});
    });
});
