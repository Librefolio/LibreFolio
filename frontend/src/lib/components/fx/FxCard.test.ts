// @vitest-environment jsdom
/**
 * FxCard — component test (Vitest + jsdom): the FX list card's rate keeps its significant digits, whichever way round
 * the card shows the pair (C-97c-4, decision D-C97c-1 of the coordinator, 17/10).
 *
 * The card of a pair on the FX list shows its last rate the way the card shows the pair: as stored, or inverted by the
 * swap button (`fx-swap-btn`, remembered in `fxCardInversionStore`). The rate is written with four fixed decimals —
 * `formatFixed(lastRate, 4)` (FxCard.svelte) — so a weak currency read against a strong one loses its digits: LBP→USD
 * (≈ 0.0000112) reads `0.0000`, IDR→USD (≈ 0.0000625) `0.0001`, USD-VND swapped to VND→USD (≈ 0.0000412) `0.0000`. The
 * contract: `formatPrice(lastRate, {minDecimals: 4})` — four decimals at least, as many as the first four significant
 * digits need (`priceFractionDigits`, formatFixed.ts), at most twelve. Markup and classes unchanged.
 *
 * Reds on HEAD, because the site still writes `formatFixed(lastRate, 4)`: LBP-USD at 0.0000112 (today `0.0000`), IDR-USD
 * at 0.0000625 (today `0.0001`), USD-VND at 24272 swapped to VND→USD, 1/24272 ≈ 0.0000411997 (today `0.0000`). Guards,
 * green today and after: EUR-USD at 1.0823 (`1.0823`), and USD-VND before the swap (`24,272.0000`).
 *
 * Premises, checked in each case before the card is read: the cure's formatter writes the expected text
 * (`formatPrice(x, {minDecimals: 4})`, the oracle: the typed strings are its own, not guesses) and the site's formatter
 * today writes what the card shows today (`formatFixed(x, 4)`, the barrier). A red after them is the site's.
 *
 * The harness. The real card, with real i18n and the real inversion store, emptied after each case (the swap writes it,
 * and it outlives the card). As in `FxMissingRate.test.ts`, `goto` is a spy and the currency store, which would ask the
 * API, answers a fixed flag. The mini chart is stood in, as `AssetSetRiskReturnSection.test.ts` stands in its scatter:
 * the real one draws through ECharts on a canvas jsdom does not have, and it is not the subject. The stand-in renders
 * nothing, so it adds no figure to the card.
 *
 * Reading. The rate has no handle of its own: its span carries no `data-testid` — only the card (`fx-card-<slug>`), the
 * pair label (`fx-pair-label`), the swap button (`fx-swap-btn`) and the Δ (`fx-range-delta`) have one. As
 * `AssetTable.test.ts` reads the asset card's live price, the rate is read in its card, mounted with no Δ so that the
 * rate is the only figure there, and matched as a whole number token. The way round is read off the pair label: its
 * currency codes, in order. English UI on jsdom's en-US browser, checked before each case: the digits are typed.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`), next to
 * `FxMissingRate.test.ts`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The mini chart, stood in. A compiled Svelte 5 component is a function of `(anchor, props)`; this one renders nothing,
 * so the card's text holds no figure of the chart's.
 */
vi.mock('$lib/components/charts/PriceChartCompact.svelte', () => ({default: function PriceChartCompactStandIn(): void {}}));
vi.mock('$app/navigation', () => ({goto: vi.fn()}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: vi.fn(),
    getCurrencyInfo: (code: string) => ({code, flag_emoji: '🏳️'}),
}));

import {fireEvent, render, setupI18n, within} from '$test/component';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {clearCardInversions} from '$lib/stores/fx/fxCardInversionStore';
import {formatFixed, formatPrice} from '$lib/utils/core/formatFixed';
import FxCard from './FxCard.svelte';

/**
 * The premise of a case: the cure, `formatPrice(value, {minDecimals: 4})`, writes `cure`, and the site's formatter today,
 * `formatFixed(value, 4)`, writes `today`. Checked before the card is read, so a red after them is the site's.
 */
function premise(value: number, cure: string, today: string): void {
    expect(formatPrice(value, {minDecimals: 4}), `control: the cure, formatPrice(${value}, {minDecimals: 4}), writes ${cure}`).toBe(cure);
    expect(formatFixed(value, 4), `barrier: the site today, formatFixed(${value}, 4), writes ${today}`).toBe(today);
}

/** `digits` as a whole number in a text: no digit, decimal mark, group separator or sign glued to either side. */
function numberToken(digits: string): RegExp {
    return new RegExp(`(?<![\\d.,+\\-\\u2212])${digits.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![.,]?\\d)`);
}

/** Mount the card of the pair `base`-`quote`, stored at `rate` on the last day of the range, with no Δ; answer its root. */
function mountCard(base: string, quote: string, rate: number): HTMLElement {
    const slug = `${base}-${quote}`;
    const {container} = render(FxCard, {base, quote, slug, data: [{date: '2026-10-16', rate, backwardFillInfo: null}]});
    return within(container).getByTestId(`fx-card-${slug}`);
}

/** The currency codes of the card's pair label, in the order the card shows them. */
function pairOf(card: HTMLElement): string[] {
    return (within(card).getByTestId('fx-pair-label').textContent ?? '').match(/\b[A-Z]{3}\b/g) ?? [];
}

/** The card's text, whitespace runs collapsed: mounted with no Δ, its rate is the only figure in it. */
function textOf(card: HTMLElement): string {
    return (card.textContent ?? '').replace(/\s+/g, ' ').trim();
}

beforeAll(async () => {
    await setupI18n();
});

describe('FxCard — the rate keeps its significant digits, either way round (C-97c-4, D-C97c-1)', () => {
    beforeEach(() => {
        // The expected digits are typed: the premise that the card writes en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    afterEach(() => {
        // The swap writes the module-level inversion store, which outlives the card: empty it for the next case.
        clearCardInversions();
    });

    it('LBP→USD at 0.0000112 reads 0.0000112, not 0.0000', () => {
        premise(0.0000112, '0.0000112', '0.0000');
        const card = mountCard('LBP', 'USD', 0.0000112);

        expect(pairOf(card), 'barrier: the card shows the pair as stored').toEqual(['LBP', 'USD']);
        expect(textOf(card), 'the rate (today 0.0000)').toMatch(numberToken('0.0000112'));
    });

    it('IDR→USD at 0.0000625 reads 0.0000625, not 0.0001 — 60 % off', () => {
        premise(0.0000625, '0.0000625', '0.0001');
        const card = mountCard('IDR', 'USD', 0.0000625);

        expect(pairOf(card), 'barrier: the card shows the pair as stored').toEqual(['IDR', 'USD']);
        expect(textOf(card), 'the rate (today 0.0001)').toMatch(numberToken('0.0000625'));
    });

    it('USD-VND at 24272, swapped to VND→USD, reads 1/24272 as 0.0000412, not 0.0000', async () => {
        premise(24272, '24,272.0000', '24,272.0000');
        premise(1 / 24272, '0.0000412', '0.0000');
        const card = mountCard('USD', 'VND', 24272);
        expect(pairOf(card), 'barrier: the card opens on the pair as stored').toEqual(['USD', 'VND']);
        expect(textOf(card), 'guard: USD→VND, before the swap, reads 24,272.0000 as today').toMatch(numberToken('24,272.0000'));

        await fireEvent.click(within(card).getByTestId('fx-swap-btn'));

        expect(pairOf(card), 'barrier: the swap shows the pair the other way round').toEqual(['VND', 'USD']);
        expect(textOf(card), 'the rate, VND→USD (today 0.0000)').toMatch(numberToken('0.0000412'));
    });

    it('guard: EUR→USD at 1.0823 reads 1.0823 — four decimals, as today', () => {
        premise(1.0823, '1.0823', '1.0823');
        const card = mountCard('EUR', 'USD', 1.0823);

        expect(pairOf(card), 'barrier: the card shows the pair as stored').toEqual(['EUR', 'USD']);
        expect(textOf(card), 'the rate').toMatch(numberToken('1.0823'));
    });
});
