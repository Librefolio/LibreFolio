// @vitest-environment jsdom
/**
 * FxPriceSummary — component test (Vitest + jsdom): the FX detail page's rate keeps its significant digits (C-97c-4,
 * decision D-C97c-1 of the coordinator, 17/10).
 *
 * The summary beside the FX detail page's date picker shows the pair's last rate, written with four fixed decimals —
 * `formatFixed(lastRate, 4)` (FxPriceSummary.svelte) — so a weak currency read against a strong one loses its digits:
 * VND→USD (≈ 0.0000412) reads `0.0000`, IDR→USD (≈ 0.0000625) reads `0.0001`, 60 % off. C-97c-3 moved the asset sites
 * and the shared charts to `formatPrice`; the FX side stayed behind. The contract: `formatPrice(lastRate, {minDecimals:
 * 4})` — four decimals at least, as a rate always had, and as many as its first four significant digits need
 * (`priceFractionDigits`, formatFixed.ts), at most twelve. Markup and classes unchanged.
 *
 * Reds on HEAD, because the site still writes `formatFixed(lastRate, 4)`: 0.0000412 (today `0.0000`) and 0.0000625
 * (today `0.0001`). Guards, green today and after: 1.0823 (`1.0823`) and 16000.5 (`16,000.5000`).
 *
 * Premises, checked in each case before the summary is read: the cure's formatter writes the expected text
 * (`formatPrice(x, {minDecimals: 4})`, the oracle: the typed strings are its own, not guesses) and the site's formatter
 * today writes what the page shows today (`formatFixed(x, 4)`, the barrier). A red after them is the site's.
 *
 * The harness. The real component, with real i18n; it reads no store that asks the API, so nothing is mocked.
 *
 * Reading. The rate has no handle of its own: its span carries no `data-testid`, nor does the summary's root — only the
 * Δ (`fx-price-summary-range-delta`) and the missing state (`fx-price-summary-missing`) have one. Mounted with no Δ, the
 * summary renders the rate alone, so the text of its mount (`render`'s container) is the rate, compared whole. English UI
 * on jsdom's en-US browser, checked before each case: the digits are typed.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`), next to
 * `FxMissingRate.test.ts`.
 */
import {beforeAll, beforeEach, describe, expect, it} from 'vitest';
import {render, setupI18n} from '$test/component';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatFixed, formatPrice} from '$lib/utils/core/formatFixed';
import FxPriceSummary from './FxPriceSummary.svelte';

/**
 * The premise of a case: the cure, `formatPrice(value, {minDecimals: 4})`, writes `cure`, and the site's formatter today,
 * `formatFixed(value, 4)`, writes `today`. Checked before the summary is read, so a red after them is the site's.
 */
function premise(value: number, cure: string, today: string): void {
    expect(formatPrice(value, {minDecimals: 4}), `control: the cure, formatPrice(${value}, {minDecimals: 4}), writes ${cure}`).toBe(cure);
    expect(formatFixed(value, 4), `barrier: the site today, formatFixed(${value}, 4), writes ${today}`).toBe(today);
}

/** The rate the summary shows for `lastRate`: the text of its mount, with no Δ beside it, whitespace runs collapsed. */
function rateFor(lastRate: number): string {
    const {container} = render(FxPriceSummary, {lastRate, deltaPercent: null, layoutMode: 'oneRow', filtersStacked: false});
    return (container.textContent ?? '').replace(/\s+/g, ' ').trim();
}

beforeAll(async () => {
    await setupI18n();
});

describe('FxPriceSummary — the rate keeps its significant digits (C-97c-4, D-C97c-1)', () => {
    beforeEach(() => {
        // The expected digits are typed: the premise that the summary writes en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    it('a VND→USD rate of 0.0000412 reads 0.0000412, not 0.0000', () => {
        premise(0.0000412, '0.0000412', '0.0000');

        expect(rateFor(0.0000412), 'the rate (today 0.0000)').toBe('0.0000412');
    });

    it('an IDR→USD rate of 0.0000625 reads 0.0000625, not 0.0001 — 60 % off', () => {
        premise(0.0000625, '0.0000625', '0.0001');

        expect(rateFor(0.0000625), 'the rate (today 0.0001)').toBe('0.0000625');
    });

    it('guard: rates of 1.0823 and 16000.5 read 1.0823 and 16,000.5000 — four decimals, as today', () => {
        premise(1.0823, '1.0823', '1.0823');
        premise(16000.5, '16,000.5000', '16,000.5000');

        expect({eurUsd: rateFor(1.0823), usdIdr: rateFor(16000.5)}).toEqual({eurUsd: '1.0823', usdIdr: '16,000.5000'});
    });
});
