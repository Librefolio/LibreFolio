// @vitest-environment jsdom
/**
 * KpiSection — component test (Vitest + jsdom).
 *
 * Subject: F5 — the parenthetical percentage next to the total P&L in the
 * Net Worth card (data-testid="kpi-total-pnl-delta") is the ABSOLUTE,
 * since-inception return (`total_gain_loss_percent`), not the period figure
 * (`simple_roi_percent`). Showing the period number next to the absolute
 * amount answers a question the user didn't ask; the two figures differ
 * precisely when the period is not the whole history, which is always.
 *
 * The test summary sets the two sources far apart (absolute +5%, period +50%)
 * so a mix-up cannot hide behind rounding. Asserted on the rendered DOM of the
 * delta element — the span is plain text, not tweened — and cross-checked on
 * Card 2, where the period ROI legitimately appears.
 *
 * No translated text is asserted; `kpi-total-pnl-delta` and `kpi-returns` are
 * the structural anchors.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {locale, waitLocale} from 'svelte-i18n';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import enCatalogue from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
// Namespace import on purpose: the hydration context (page cache, phase 1) is read by name below, so
// the F5 and V2 cases keep running while `TweenedValue.svelte` does not export it yet.
import * as Tweened from '$lib/components/ui/TweenedValue.svelte';
import {currentLanguage} from '$lib/stores/app/language';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import KpiSection from './KpiSection.svelte';

const EUR = (amount: string) => ({code: 'EUR', amount});

/** A summary where absolute (since-inception) and period returns DIFFER by 10×. */
function summary() {
    return {
        net_worth: EUR('10500'),
        market_value: EUR('10000'),
        period_market_value_start: EUR('9500'),
        open_cost_basis: EUR('10000'),
        period_book_value_start: EUR('9800'),
        cash_total: EUR('500'),
        net_deposited_capital: EUR('10000'),
        total_deposited: EUR('10000'),
        total_withdrawn: EUR('0'),
        period_pnl: EUR('500'),
        period_unrealized_gain_loss_delta: EUR('400'),
        period_realized_gain_loss: EUR('50'),
        period_income: EUR('60'),
        period_fees_taxes: EUR('10'),
        period_fees: EUR('6'),
        period_taxes: EUR('4'),
        total_gain_loss: EUR('500'),
        total_invested: EUR('10000'),
        total_gain_loss_percent: '0.05', // absolute, since inception → +5.00%
        simple_roi_percent: '0.50', // period → +50.00% (Card 2 only)
        twrr_percent: '0.40',
        mwrr_cumulative_percent: '0.45',
        mwrr_annualized_percent: '0.30',
        timing_effect_percent: '0.05', // mwrr_cumulative − twrr, as the backend sends it beside them (MF-P)
    };
}

/**
 * The day as the backend sends it in the summary (MF-P), made from two history points by its rule: the total P&L's
 * change, and that change over |the day before's total P&L| and over |the day before's NAV| — fractions with the
 * change's sign, null on a zero base. The V2 and M-18 blocks give the card both, the points and these fields, so what
 * they pin holds whichever source the card reads; the R17 block at the end of the file pins which one it reads.
 */
function dayFields(prevTotalPnl: string, lastTotalPnl: string, prevNav: string) {
    const change = parseFloat(lastTotalPnl) - parseFloat(prevTotalPnl);
    const share = (base: number): string | null => (base === 0 ? null : String(change / Math.abs(base)));
    return {
        pnl_change_1d: EUR(String(change)),
        pnl_change_1d_vs_total_pnl_percent: share(parseFloat(prevTotalPnl)),
        pnl_change_1d_vs_nav_percent: share(parseFloat(prevNav)),
    };
}

beforeAll(async () => {
    await setupI18n();
});

describe('KpiSection — absolute ROI next to total P&L (F5)', () => {
    it('shows total_gain_loss_percent in the Net Worth card parenthetical, not the period ROI', async () => {
        render(KpiSection, {summary: summary(), history: [], loading: false, displayCurrency: 'EUR'});

        await waitFor(() => expect(screen.getByTestId('kpi-total-pnl-delta')).toBeInTheDocument());

        const delta = screen.getByTestId('kpi-total-pnl-delta');
        // Absolute figure: 0.05 → "+5.00%".
        expect(delta.textContent).toContain('(+5.00%)');
        // The period figure must not leak here.
        expect(delta.textContent).not.toContain('50.00%');
    });

    it('keeps the period ROI on the Returns card (the two figures are not swapped)', async () => {
        render(KpiSection, {summary: summary(), history: [], loading: false, displayCurrency: 'EUR'});

        await waitFor(() => expect(screen.getByTestId('kpi-returns')).toBeInTheDocument());

        // Card 2 is the period-returns home: roiVal = simple_roi_percent × 100 → 50.00%.
        // (TweenedValue animates the metric bars, so poll the settled text.)
        const returnsCard = screen.getByTestId('kpi-returns');
        await waitFor(() => expect(returnsCard.textContent).toContain('50.00%'), {timeout: 3000});
        // …and the absolute figure does not take its place.
        expect(returnsCard.textContent).not.toContain('(+5.00%)');
    });

    it('omits the parenthetical when the absolute ROI is not parseable, keeping the amount', async () => {
        const broken = {...summary(), total_gain_loss_percent: 'not-a-number'};
        render(KpiSection, {summary: broken, history: [], loading: false, displayCurrency: 'EUR'});

        await waitFor(() => expect(screen.getByTestId('kpi-total-pnl-delta')).toBeInTheDocument());

        const delta = screen.getByTestId('kpi-total-pnl-delta');
        expect(delta.textContent).not.toContain('%');
        // The P&L amount itself still renders (no crash, no empty card).
        expect(delta.textContent?.trim().length).toBeGreaterThan(0);
    });
});

/**
 * V2 — the daily change and its percentage, on Card 1 (P&L) and Card 2 (Returns).
 *
 * Reported as «+91,31 € (+-16.36%)»: the `+` followed the amount while the number carried its
 * own sign, and against a negative base the quotient came out with the opposite sign to the
 * change. The rule, the developer's, the same on both cards:
 *   percentage = day change / |previous value| × 100;
 *   sign and colour follow the direction (up → `+`, down → `-`), never «+-»;
 *   hidden ONLY when the previous value is exactly 0.
 * Card 1's base is yesterday's total P&L, Card 2's is yesterday's NAV. The change is the total
 * P&L's from yesterday to today, the same on both cards.
 *
 * Since MF-P the backend applies this rule and sends the change and both shares with the summary
 * (`pnl_change_1d`, `pnl_change_1d_vs_total_pnl_percent`, `pnl_change_1d_vs_nav_percent`). Each case
 * gives the card yesterday and today twice — as the last two history points, and as the summary fields
 * the rule makes of them (`dayFields`) — so the readings below hold whichever source the card reads;
 * the R17 block at the end of the file pins that it reads the summary.
 *
 * Anchors: `kpi-pnl-delta-day-pct` carries exactly the formatted percentage (formatPercent: `+`
 * only above zero, two decimals); `data-direction` carries the direction, which is what drives
 * the colour — a CSS class is not a contract.
 */
describe('KpiSection — daily change percentage (V2)', () => {
    /** A history point with every field the cards read; only P&L and NAV vary between cases. */
    function point(date: string, totalPnl: string, navValue: string) {
        return {
            date,
            through: date,
            cash_value: EUR('500'),
            market_value: EUR('10000'),
            nav_value: EUR(navValue),
            capital_baseline: EUR('10000'),
            book_asset_like: EUR('10000'),
            cash_from_contributed_capital: EUR('400'),
            cash_from_generated_returns: EUR('100'),
            total_pnl: EUR(totalPnl),
        };
    }

    /** Yesterday then today, as the dashboard's history ends — and as the summary carries them (MF-P). */
    function renderDay(prev: {totalPnl: string; nav?: string}, last: {totalPnl: string; nav?: string}) {
        const history = [point('2026-10-05', prev.totalPnl, prev.nav ?? '10000'), point('2026-10-06', last.totalPnl, last.nav ?? '10000')];
        const day = dayFields(prev.totalPnl, last.totalPnl, prev.nav ?? '10000');
        return render(KpiSection, {summary: {...summary(), ...day}, history, loading: false, displayCurrency: 'EUR'});
    }

    async function dayLine() {
        await waitFor(() => expect(screen.getByTestId('kpi-pnl-delta-day')).toBeInTheDocument());
        return screen.getByTestId('kpi-pnl-delta-day');
    }

    describe('Card 1 — share of yesterday’s total P&L', () => {
        it('a loss that shrinks is a rise: + and up, never «+-»', async () => {
            renderDay({totalPnl: '-558.10'}, {totalPnl: '-466.79'});
            const line = await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+16.36%');
            expect(line).toHaveAttribute('data-direction', 'up');
            expect(line.textContent).not.toContain('+-');
        });

        it('a loss that grows is a fall: - and down', async () => {
            renderDay({totalPnl: '-558.10'}, {totalPnl: '-649.41'});
            const line = await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('-16.36%');
            expect(line).toHaveAttribute('data-direction', 'down');
            expect(line.textContent).not.toContain('+-');
        });

        it('keeps the positive-base reading unchanged', async () => {
            renderDay({totalPnl: '2950.00'}, {totalPnl: '3041.45'});
            const line = await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+3.10%');
            expect(line).toHaveAttribute('data-direction', 'up');
        });

        it('a day without change is flat, with an unsigned zero', async () => {
            renderDay({totalPnl: '-558.10'}, {totalPnl: '-558.10'});
            const line = await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('0.00%');
            expect(line).toHaveAttribute('data-direction', 'flat');
        });

        it('hides the percentage when yesterday’s total P&L is exactly zero, keeping the amount', async () => {
            renderDay({totalPnl: '0'}, {totalPnl: '50'});
            const line = await dayLine();

            // Positive barrier: the line is rendered under the new contract (it has a direction)…
            expect(line).toHaveAttribute('data-direction', 'up');
            // …and only the share of a zero base is missing.
            expect(screen.queryByTestId('kpi-pnl-delta-day-pct')).toBeNull();
            expect(line.textContent?.trim().length).toBeGreaterThan(0);
        });

        it('shows the percentage for a tiny base that is not zero', async () => {
            renderDay({totalPnl: '0.005'}, {totalPnl: '1.005'});
            await dayLine();

            // Above a thousand percent the share is grouped the way the UI locale writes it (M-18): en-US here,
            // jsdom's browser under the English UI.
            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+20,000.00%');
        });
    });

    describe('Card 2 — share of yesterday’s NAV', () => {
        async function returnsPct() {
            await waitFor(() => expect(screen.getByTestId('kpi-returns')).toBeInTheDocument());
            return screen.queryByTestId('kpi-returns-delta-pct');
        }

        it('shows a rise against a negative NAV as +, never «+-»', async () => {
            renderDay({totalPnl: '-500', nav: '-1000'}, {totalPnl: '-450'});
            const pct = await returnsPct();

            expect(pct).not.toBeNull();
            expect(pct!.textContent?.trim()).toBe('+5.00%');
            expect(pct).toHaveAttribute('data-direction', 'up');
        });

        it('shows a fall against a positive NAV as - and down', async () => {
            renderDay({totalPnl: '1000', nav: '10000'}, {totalPnl: '900'});
            const pct = await returnsPct();

            expect(pct).not.toBeNull();
            expect(pct!.textContent?.trim()).toBe('-1.00%');
            expect(pct).toHaveAttribute('data-direction', 'down');
        });

        it('hides the percentage only when yesterday’s NAV is exactly zero', async () => {
            renderDay({totalPnl: '-558.10', nav: '0'}, {totalPnl: '-466.79'});
            const pct = await returnsPct();

            // Positive barrier in the same render: Card 1, whose base is not zero, shows its share.
            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+16.36%');
            expect(pct).toBeNull();
        });
    });
});

/**
 * Page cache, phase 1 (R2 / N, decision E1 of 06/10): a figure already known does not count up from 0.
 *
 * `TweenedValue` starts every value from `tweened(0)`, so returning to the Dashboard with the report
 * in cache still shows each KPI counting from zero for ~1 s — on screen it looks like a recompute.
 * The page that hydrates from the cache says so through a Svelte context, `TWEEN_HYDRATION_CONTEXT`
 * (set by `setTweenHydration(isHydrated)`, both exported by `TweenedValue.svelte`'s module script):
 * while `isHydrated()` is true, a tweened value appears at its final value on the first frame, and a
 * later change still tweens from the old value to the new one. Without the context nothing changes:
 * the first load counts from zero, as today.
 *
 * The subject is Card 1's hero (`kpi-period-pnl` → `kpi-value`), formatted by the same formatter the
 * card uses, so the comparison carries no translated text and no locale assumption.
 */
describe('KpiSection — hydration from the cache (page cache, phase 1)', () => {
    const hydration = Tweened as unknown as {TWEEN_HYDRATION_CONTEXT?: unknown; setTweenHydration?: (isHydrated: () => boolean) => void};
    const hero = () => within(screen.getByTestId('kpi-period-pnl')).getByTestId('kpi-value');
    /** Card 1's hero exactly as KpiSection formats it. */
    const heroText = (amount: number) => formatCurrencyAmountPlain(amount, 'EUR', {showSign: true});
    const props = (periodPnl = '500') => ({summary: {...summary(), period_pnl: EUR(periodPnl)}, history: [], loading: false, displayCurrency: 'EUR'});

    function hydratedContext(): Map<unknown, () => boolean> {
        expect(hydration.TWEEN_HYDRATION_CONTEXT, 'TweenedValue.svelte exports no TWEEN_HYDRATION_CONTEXT: a page hydrated from the cache cannot tell its figures to start from their value').toBeDefined();
        return new Map([[hydration.TWEEN_HYDRATION_CONTEXT, () => true]]);
    }

    it('exports the context key and its setter from TweenedValue’s module script', () => {
        expect(hydration.TWEEN_HYDRATION_CONTEXT, 'TweenedValue.svelte exports no TWEEN_HYDRATION_CONTEXT').toBeDefined();
        expect(typeof hydration.setTweenHydration, 'TweenedValue.svelte exports no setTweenHydration(isHydrated)').toBe('function');
    });

    it('without the context, counts up: the first frame is the formatted zero, then the final value (the first load, unchanged)', async () => {
        render(KpiSection, props());

        // Read synchronously after render: before any animation frame.
        expect(hero().textContent?.trim()).toBe(heroText(0));
        await waitFor(() => expect(hero().textContent?.trim()).toBe(heroText(500)), {timeout: 3000});
    });

    it('with the context, shows the final value on the first frame, before any animation frame', () => {
        render(KpiSection, {props: props(), context: hydratedContext()});

        expect(hero().textContent?.trim(), 'a figure served from the cache still counts up from zero').toBe(heroText(500));
    });

    it('with the context, still moves to a new value when the summary changes', async () => {
        const {rerender} = render(KpiSection, {props: props('500'), context: hydratedContext()});
        expect(hero().textContent?.trim(), 'precondition: the cached figure is on screen at once').toBe(heroText(500));

        await rerender(props('800'));

        await waitFor(() => expect(hero().textContent?.trim(), 'the refreshed figure never replaced the cached one').toBe(heroText(800)), {timeout: 3000});
    });
});

/**
 * P9 — Card 1's «Unrealized change» bar explains itself (issue #32, D11).
 *
 * The backend splits `period_unrealized_gain_loss_delta` by asset currency into
 * `summary.period_unrealized_breakdown`: `asset` rows (what the assets did in their own currency),
 * `fx` rows (what the exchange rate did to their cost), `unsplit` rows (positions that could not be
 * split). The rows add up to the bar's figure exactly, in an order the backend owns. Contract:
 *
 *   - rows present → the bar's tooltip is HTML, with one
 *     `<tr data-testid="kpi-unrealized-breakdown-{kind}-{asset_currency}">` per row, in the order
 *     received: the frontend never adds a row (no `fx` row for the report currency) nor drops one;
 *   - each row's value cell — its last cell, as in every tooltip table of this card — is the row's
 *     `period_delta` formatted like the cash tooltip: signed money through `formatCurrencyAmountPlain`,
 *     so masked by the privacy toggle exactly as every personal amount is;
 *   - no rows (empty or absent) → today's plain text tooltip, and no breakdown row.
 *
 * The bar is found by structure, not by its label: Card 1's metric bars follow its hero figure
 * (`kpi-value`), and each one's tooltip trigger is the `[role="button"]` wrapper Tooltip renders
 * (the header's DocsLink comes before the hero and is a native `<button>`), so the first trigger
 * after the hero is the «Unrealized change» bar. It is opened with Enter — the keyboard path opens
 * the same tooltip as a hover, without the hover delay. Labels are never asserted: their i18n keys
 * have not landed yet.
 */
describe('KpiSection — unrealized change breakdown tooltip (P9)', () => {
    type BreakdownKind = 'asset' | 'fx' | 'unsplit';
    const row = (kind: BreakdownKind, assetCurrency: string, amount: string) => ({kind, asset_currency: assetCurrency, period_delta: EUR(amount)});

    /** Four rows adding up to the fixture's `period_unrealized_gain_loss_delta` (400), in the backend's order. */
    const ROWS = [row('asset', 'EUR', '250.50'), row('asset', 'USD', '120'), row('fx', 'USD', '-30.25'), row('unsplit', 'ISK', '59.75')];

    const norm = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();
    const testIdOf = (r: {kind: string; asset_currency: string}) => `kpi-unrealized-breakdown-${r.kind}-${r.asset_currency}`;
    /** What the value cell must read: the cash tooltip's formatter, signed, in the amount's own currency. */
    const signedMoney = (r: {period_delta: {code: string; amount: string}}) => norm(formatCurrencyAmountPlain(parseFloat(r.period_delta.amount), r.period_delta.code, {showSign: true}));

    function renderWith(extra: Record<string, unknown>) {
        return render(KpiSection, {summary: {...summary(), ...extra}, history: [], loading: false, displayCurrency: 'EUR'});
    }

    /** Card 1's first metric bar trigger: the first Tooltip wrapper after the hero figure. */
    function unrealizedBarTrigger(): HTMLElement {
        const card = screen.getByTestId('kpi-period-pnl');
        const hero = within(card).getByTestId('kpi-value');
        const trigger = Array.from(card.querySelectorAll<HTMLElement>('[role="button"]')).find((element) => element.tagName !== 'BUTTON' && Boolean(hero.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING));
        if (!trigger) throw new Error('Card 1 renders no tooltip trigger after its hero figure: the metric bars are gone');
        return trigger;
    }

    async function openUnrealizedTooltip(): Promise<HTMLElement> {
        await fireEvent.keyDown(unrealizedBarTrigger(), {key: 'Enter'});
        return screen.findByTestId('tooltip-content');
    }

    function breakdownRowIds(tooltip: HTMLElement): string[] {
        return Array.from(tooltip.querySelectorAll<HTMLElement>('[data-testid^="kpi-unrealized-breakdown-"]')).map((element) => element.getAttribute('data-testid') ?? '');
    }

    function valueCell(tooltip: HTMLElement, r: {kind: string; asset_currency: string}): string {
        const tableRow = within(tooltip).getByTestId(testIdOf(r));
        expect(tableRow.tagName, `${testIdOf(r)} is a table row`).toBe('TR');
        const cells = tableRow.querySelectorAll('td');
        return norm(cells[cells.length - 1]?.textContent);
    }

    afterEach(() => {
        // Module-level flag shared by every test of the file: a leftover `true` would mount the next card masked.
        setPrivacyEnabled(false);
    });

    it('lists one row per breakdown row, in the order received, each with its signed amount', async () => {
        renderWith({period_unrealized_breakdown: ROWS});

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual(ROWS.map(testIdOf));
        for (const r of ROWS) expect(valueCell(tooltip, r), testIdOf(r)).toBe(signedMoney(r));
    });

    it('keeps the order it receives even when it is not the one it would choose: the backend owns it', async () => {
        const scrambled = [ROWS[2], ROWS[3], ROWS[1], ROWS[0]];
        renderWith({period_unrealized_breakdown: scrambled});

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual(scrambled.map(testIdOf));
    });

    it('shows exactly the rows it receives: a single-currency portfolio has one asset row, no fx row of its own making', async () => {
        const single = [row('asset', 'EUR', '400')];
        renderWith({period_unrealized_breakdown: single});

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual(['kpi-unrealized-breakdown-asset-EUR']);
        expect(valueCell(tooltip, single[0])).toBe(signedMoney(single[0]));
    });

    it('masks every amount with privacy on, as the formatter masks any personal amount', async () => {
        setPrivacyEnabled(true);
        // Control: the expected values really are masked — equality below is not digits against digits.
        for (const r of ROWS) expect(signedMoney(r), `control: ${testIdOf(r)} masked by the formatter`).not.toMatch(/\d/);
        renderWith({period_unrealized_breakdown: ROWS});

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual(ROWS.map(testIdOf));
        for (const r of ROWS) expect(valueCell(tooltip, r), testIdOf(r)).toBe(signedMoney(r));
    });

    it.each([
        ['empty', {period_unrealized_breakdown: []}],
        ['absent', {}],
    ])('keeps today’s plain text tooltip when the breakdown is %s', async (_label, extra) => {
        renderWith(extra);

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual([]);
        expect(tooltip.querySelector('table'), 'a plain text tooltip has no table').toBeNull();
        expect(norm(tooltip.textContent).length).toBeGreaterThan(0);
    });
});

/**
 * Card 2 «Returns» — a return the backend did not compute reads «—», never 0.
 *
 * `twrr_percent`, `mwrr_cumulative_percent` and `mwrr_annualized_percent` are optional and nullable
 * in the schema: TWRR is None when it cannot be calculated, MWRR when its solver does not converge.
 * A figure nobody computed is not a zero return. The defect pinned here parsed each missing one as 0:
 * its bar read «0.00%», and Timing effect subtracted that invented zero — a missing MWRR cumulative
 * came out as «-40.00 pp», labelled unfavourable. Contract:
 *
 *   - a missing TWRR / MWRR cumulative / MWRR annualized reads «—» (U+2014) as its bar value: no digits;
 *   - Timing effect is `mwrr_cumulative − twrr` in percentage points, signed, two decimals; when either
 *     input is missing it reads «—», and its label claims nothing — neither favourable, neutral nor
 *     unfavourable. Since MF-P the backend makes that difference, `timing_effect_percent`, null when
 *     either input is missing: every fixture here carries the field the backend would send beside its
 *     returns, so the readings hold whichever the card takes (the R17 block pins which);
 *   - MWRR annualized is not an input of Timing effect: its absence leaves Timing effect untouched;
 *   - `null` and an absent key are the same «missing»: every case runs with both.
 *
 * Read through `kpi-return-{roi,twrr-cum,mwrr-cum,mwrr-ann}-value`, `kpi-timing-effect-value` and
 * `kpi-timing-effect-label`, inside `kpi-returns`. The bars tween for 700 ms, so every assertion also
 * requires ROI — required by the schema, never missing here — at its settled «50.00%»: a «—» counts
 * only once the card has stopped moving. The anchors are compared together, so a red lists every one
 * that disagrees. Timing effect is locale-formatted with a translated unit, so only its sign and
 * digits are matched; the label is translated, so it is only read as empty or not.
 */
describe('KpiSection — Returns card: a missing return reads «—», never 0 (Card 2)', () => {
    const EM_DASH = '\u2014';
    /** ±5.00 pp: the decimal separator is the locale's and the unit is translated, so only sign and digits are matched. */
    const PLUS_5_PP = expect.stringMatching(/^\+5[.,]00(?!\d)/);
    const MINUS_5_PP = expect.stringMatching(/^-5[.,]00(?!\d)/);
    /** A label that claims a reading (favourable, neutral or unfavourable): its wording is translated, so only its presence is read. */
    const A_CLAIM = expect.stringMatching(/\S/);

    const ANCHORS = {
        roi: 'kpi-return-roi-value',
        twrrCum: 'kpi-return-twrr-cum-value',
        mwrrCum: 'kpi-return-mwrr-cum-value',
        mwrrAnn: 'kpi-return-mwrr-ann-value',
        timing: 'kpi-timing-effect-value',
        timingLabel: 'kpi-timing-effect-label',
    } as const;
    type Anchor = keyof typeof ANCHORS;

    type ReturnField = 'twrr_percent' | 'mwrr_cumulative_percent' | 'mwrr_annualized_percent';
    type Missing = 'null' | 'absent';
    /** The fixture as the schema types it: the three returns and the timing effect are optional and nullable. */
    type ReturnsSummary = Omit<ReturnType<typeof summary>, ReturnField | 'timing_effect_percent'> & Partial<Record<ReturnField | 'timing_effect_percent', string | null>>;
    /** The two returns the timing effect is made of. */
    const TIMING_INPUTS: readonly ReturnField[] = ['twrr_percent', 'mwrr_cumulative_percent'];

    const norm = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();

    /** The fixture with `fields` missing — set to null, or with their keys removed — and the timing effect with them when it loses an input, as the backend leaves it. */
    function summaryMissing(fields: readonly ReturnField[], how: Missing): ReturnsSummary {
        const s: ReturnsSummary = summary();
        const missing = fields.some((field) => TIMING_INPUTS.includes(field)) ? [...fields, 'timing_effect_percent' as const] : fields;
        for (const field of missing) {
            if (how === 'null') s[field] = null;
            else delete s[field];
        }
        return s;
    }

    function renderReturns(s: ReturnsSummary): void {
        render(KpiSection, {summary: s, history: [], loading: false, displayCurrency: 'EUR'});
    }

    /** What the Returns card shows at each anchor. Every value must be on screen; a label that is not rendered claims nothing either, so it reads as empty. */
    function readReturns(anchors: readonly Anchor[]): Record<string, string> {
        const card = within(screen.getByTestId('kpi-returns'));
        const read = (anchor: Anchor): string => norm((anchor === 'timingLabel' ? card.queryByTestId(ANCHORS[anchor]) : card.getByTestId(ANCHORS[anchor]))?.textContent);
        return Object.fromEntries(anchors.map((anchor) => [anchor, read(anchor)]));
    }

    /** Polls until the card reads `expected` at its anchors, with ROI settled at «50.00%» as the barrier. On timeout the diff is the whole reading, not only its first mismatch. */
    async function expectReturnsCard(expected: Partial<Record<Anchor, unknown>>): Promise<void> {
        const want: Partial<Record<Anchor, unknown>> = {roi: '50.00%', ...expected};
        await waitFor(() => expect(readReturns(Object.keys(want) as Anchor[])).toEqual(want), {timeout: 3000, onTimeout: (error) => error});
    }

    it.each([
        {reading: 'favourable', twrr: '0.40', mwrrCum: '0.45', timingEffect: '0.05', twrrBar: '40.00%', mwrrCumBar: '45.00%', timing: PLUS_5_PP},
        {reading: 'unfavourable', twrr: '0.45', mwrrCum: '0.40', timingEffect: '-0.05', twrrBar: '45.00%', mwrrCumBar: '40.00%', timing: MINUS_5_PP},
    ])('control, every return present ($reading): each bar reads its value; Timing effect is mwrr_cum − twrr in pp, signed, with a claim', async ({twrr, mwrrCum, timingEffect, twrrBar, mwrrCumBar, timing}) => {
        renderReturns({...summary(), twrr_percent: twrr, mwrr_cumulative_percent: mwrrCum, timing_effect_percent: timingEffect});

        await expectReturnsCard({twrrCum: twrrBar, mwrrCum: mwrrCumBar, mwrrAnn: '30.00%', timing, timingLabel: A_CLAIM});
    });

    describe.each<Missing>(['null', 'absent'])('a return missing as %s', (how) => {
        it('mwrr_cumulative_percent: its bar reads «—»; Timing effect reads «—» and claims nothing', async () => {
            renderReturns(summaryMissing(['mwrr_cumulative_percent'], how));

            await expectReturnsCard({twrrCum: '40.00%', mwrrCum: EM_DASH, mwrrAnn: '30.00%', timing: EM_DASH, timingLabel: ''});
        });

        it('twrr_percent: its bar reads «—»; Timing effect reads «—» and claims nothing', async () => {
            renderReturns(summaryMissing(['twrr_percent'], how));

            await expectReturnsCard({twrrCum: EM_DASH, mwrrCum: '45.00%', mwrrAnn: '30.00%', timing: EM_DASH, timingLabel: ''});
        });

        it('mwrr_annualized_percent: its bar reads «—», the other bars keep their values', async () => {
            renderReturns(summaryMissing(['mwrr_annualized_percent'], how));

            await expectReturnsCard({twrrCum: '40.00%', mwrrCum: '45.00%', mwrrAnn: EM_DASH});
        });

        it('mwrr_annualized_percent: Timing effect does not read it, still +5.00 pp with its claim', async () => {
            renderReturns(summaryMissing(['mwrr_annualized_percent'], how));

            await expectReturnsCard({timing: PLUS_5_PP, timingLabel: A_CLAIM});
        });

        it('twrr_percent and mwrr_cumulative_percent: both bars read «—»; Timing effect reads «—» and claims nothing', async () => {
            renderReturns(summaryMissing(['twrr_percent', 'mwrr_cumulative_percent'], how));

            await expectReturnsCard({twrrCum: EM_DASH, mwrrCum: EM_DASH, mwrrAnn: '30.00%', timing: EM_DASH, timingLabel: ''});
        });
    });
});

/**
 * M-18 CP1: the KPI percentages in the UI language.
 *
 * Numbers follow the UI language (the developer's rule of 2026-10-12). The Returns card prints its bars
 * with a template literal around `toFixed(2)` (`fmtPct`: ROI, TWRR, MWRR), the Net Worth card its absolute
 * ROI the same way (`absRoiPct`), so a French reader gets `50.00%` where French writes `50,00 %`. The two
 * daily-change shares go through `formatPercent` without a `locale`, which until now meant the fixed
 * English shape. The cure: the formatters' locale defaults to `uiLocale()`, and the hand-written sites go
 * through them; same digits and same signs — no `+` where today's text has none — only the notation moves.
 *
 * Fixture. The file's summary: ROI 50%, TWRR 40%, absolute ROI 5%. A day whose total P&L rises from
 * -558.10 to -466.79 on a NAV of 10 000, in the history and in the summary fields MF-P sends for it
 * (`dayFields`): Card 1's share of yesterday's |P&L| and Card 2's share of yesterday's NAV, both signed,
 * both mirrored from the rule (change / |base|) rather than restated.
 *
 * Expectations. French strings come from `Intl.NumberFormat('fr', {style: 'percent', …})` in this runtime,
 * never typed: Node puts U+00A0 before the `%`, a browser may put U+202F. English is today's exact text,
 * typed: jsdom's browser is en-US, so the English UI keeps en-US notation.
 *
 * Language. Switched as LanguageSelector does — `currentLanguage.set`, which also drives svelte-i18n — with
 * both dictionaries loaded first. KpiSection is a runes component, so its template, and TweenedValue's
 * `format` call inside each bar, track whatever the formatter reads: the in-place test is what proves the
 * default is read reactively, not merely right at mount. The bars tween; the page cache's hydration context
 * puts every figure at its value on the first frame, so no read waits on an animation.
 *
 * Selection. By `data-testid`; the absolute ROI is the bracketed figure inside `kpi-total-pnl-delta`, beside
 * an amount whose notation is not this block's subject and is not read. Timing effect (`… pp`) is left alone
 * too. Nothing here reads translated text.
 */
describe('KpiSection — percentages in the UI language (M-18)', () => {
    const hydration = Tweened as unknown as {TWEEN_HYDRATION_CONTEXT?: unknown};

    /** Yesterday's and today's total P&L, and the NAV both days. */
    const PREV_TOTAL_PNL = '-558.10';
    const LAST_TOTAL_PNL = '-466.79';
    const NAV = '10000';

    /** The rule's arithmetic: the day change as a share of |base|, in percent. */
    const dayChange = Number(LAST_TOTAL_PNL) - Number(PREV_TOTAL_PNL);
    const SHARE_OF_PNL = (dayChange / Math.abs(Number(PREV_TOTAL_PNL))) * 100;
    const SHARE_OF_NAV = (dayChange / Math.abs(Number(NAV))) * 100;

    type Reading = {roi: string; twrr: string; dayVsPnl: string; dayVsNav: string; absoluteRoi: string};

    /** Today's English text, exactly. */
    const ENGLISH: Reading = {roi: '50.00%', twrr: '40.00%', dayVsPnl: '+16.36%', dayVsNav: '+0.91%', absoluteRoi: '(+5.00%)'};

    /** French notation, two digits, of a fraction. */
    const french = (fraction: number): string => new Intl.NumberFormat('fr', {style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2}).format(fraction);
    const FRENCH: Reading = {
        roi: french(Number(summary().simple_roi_percent)),
        twrr: french(Number(summary().twrr_percent)),
        dayVsPnl: `+${french(SHARE_OF_PNL / 100)}`,
        dayVsNav: `+${french(SHARE_OF_NAV / 100)}`,
        absoluteRoi: `(+${french(Number(summary().total_gain_loss_percent))})`,
    };

    /** `text` with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
    function spelled(value: unknown): string {
        return JSON.stringify(value).replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
    }

    function historyPoint(date: string, totalPnl: string) {
        return {
            date,
            through: date,
            cash_value: EUR('500'),
            market_value: EUR('10000'),
            nav_value: EUR(NAV),
            capital_baseline: EUR('10000'),
            book_asset_like: EUR('10000'),
            cash_from_contributed_capital: EUR('400'),
            cash_from_generated_returns: EUR('100'),
            total_pnl: EUR(totalPnl),
        };
    }

    /** The KPI row with yesterday and today in its history, every figure at its value on the first frame. */
    function mountKpis(): void {
        expect(hydration.TWEEN_HYDRATION_CONTEXT, 'control: TweenedValue exports its hydration context').toBeDefined();
        render(KpiSection, {
            props: {summary: {...summary(), ...dayFields(PREV_TOTAL_PNL, LAST_TOTAL_PNL, NAV)}, history: [historyPoint('2026-10-05', PREV_TOTAL_PNL), historyPoint('2026-10-06', LAST_TOTAL_PNL)], loading: false, displayCurrency: 'EUR'},
            context: new Map([[hydration.TWEEN_HYDRATION_CONTEXT, () => true]]),
        });
    }

    /** Every percentage of this block, as the reader sees it. Trimmed only: a no-break space inside is the notation. */
    function readPercentages(): Reading {
        const text = (testId: string): string => (screen.getByTestId(testId).textContent ?? '').trim();
        const bracketed = (screen.getByTestId('kpi-total-pnl-delta').textContent ?? '').match(/\([^()]*%\)/);
        return {
            roi: text('kpi-return-roi-value'),
            twrr: text('kpi-return-twrr-cum-value'),
            dayVsPnl: text('kpi-pnl-delta-day-pct'),
            dayVsNav: text('kpi-returns-delta-pct'),
            absoluteRoi: bracketed ? bracketed[0] : '(no bracketed percentage)',
        };
    }

    /** Change the UI language as LanguageSelector does, then flush. The controls name the layer if the language did not move. */
    async function switchLanguage(lang: 'en' | 'fr'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        flushSync();
        await tick();
        expect(get(currentLanguage), `control: the app language is ${lang}`).toBe(lang);
        expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
    }

    beforeAll(async () => {
        // English was loaded by the file's own beforeAll; French joins it, so a switch never waits on a loader.
        await waitLocale('fr');
        // Control: this runtime has French ICU data, so every French figure differs from today's text.
        for (const key of Object.keys(ENGLISH) as Array<keyof Reading>) {
            expect(FRENCH[key], `${key}: French notation differs from English`).not.toBe(ENGLISH[key]);
        }
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await switchLanguage('en');
    });

    it('English UI (control): every percentage prints exactly today’s text', () => {
        mountKpis();

        expect(readPercentages()).toEqual(ENGLISH);
    });

    it('mounted with the UI in French: every percentage in French notation', async () => {
        await switchLanguage('fr');
        mountKpis();

        expect(readPercentages(), `French notation, ${spelled(FRENCH)}`).toEqual(FRENCH);
    });

    it('follows an in-place switch of the UI language, en → fr → en', async () => {
        mountKpis();
        expect(readPercentages(), 'en, mount — today’s text').toEqual(ENGLISH);

        await switchLanguage('fr');
        expect(readPercentages(), `en → fr in place — French notation, ${spelled(FRENCH)}`).toEqual(FRENCH);

        await switchLanguage('en');
        expect(readPercentages(), 'fr → en in place — today’s text again').toEqual(ENGLISH);
    });
});

/**
 * M-18 CP2: the KPI amounts and the timing effect in the UI language.
 *
 * Amounts follow the UI language like the percentages of CP1 (the developer's rule of 2026-10-12). Every
 * money figure of the row goes through `formatCurrencyAmountPlain`, which wrote its number with
 * `toLocaleString(undefined, …)` — the browser's notation, never the UI's. Timing effect
 * (`kpi-timing-effect-value`, `mwrr_cum − twrr` in percentage points) is written by hand in the template
 * the same way, and puts a `+` before every value not below zero, zero included. The cure: the
 * formatter's number defaults to `uiLocale()`, the timing effect takes its number from the same source,
 * and zero carries no sign (CP1's rule); the unit stays `dashboard.pp`.
 *
 * Fixture. The file's summary: net worth 10 500 EUR; TWRR 40% and MWRR cumulative 45%, a timing effect of
 * +5 pp; and a variant with both returns at 40%, a timing effect of exactly zero — each timing effect also
 * sent as `timing_effect_percent`, as the backend does since MF-P.
 *
 * Subjects. Card 3's hero (`kpi-net-worth` → `kpi-value`), the net worth through
 * `formatCurrencyAmountPlain(…, 'EUR')`: no currency cache is loaded here, so the amount is followed by
 * its code alone, a composition the English control pins on today's exact text. Timing effect, read
 * whole: sign and number, then the unit read from the shipped catalogue of the step's language.
 *
 * Expectations. Italian digits come from `Intl.NumberFormat('it', …)` in this runtime, never typed;
 * English is today's exact text, typed — jsdom's browser is en-US, so the English UI keeps en-US notation.
 *
 * Language. Switched as LanguageSelector does — `currentLanguage.set` — with both catalogues loaded first.
 * KpiSection is a runes component: the in-place test is what proves the figures read the UI language
 * reactively, not merely right at mount. The page cache's hydration context puts every figure at its
 * value on the first frame, so no read waits on an animation.
 */
describe('KpiSection — amounts and the timing effect in the UI language (M-18 CP2)', () => {
    const hydration = Tweened as unknown as {TWEEN_HYDRATION_CONTEXT?: unknown};
    type UiLanguage = 'en' | 'it';
    /** The interface locale of each language here: jsdom's browser is en-US. */
    const LOCALE_OF: Record<UiLanguage, string> = {en: 'en-US', it: 'it'};
    const CATALOGUES = {en: enCatalogue, it: itCatalogue};

    const NET_WORTH = Number(summary().net_worth.amount);
    /** mwrr_cumulative − twrr of the file's summary, in percentage points: 45 − 40. */
    const TIMING_PP = 5;

    type Reading = {netWorth: string; timing: string};

    /** Today's English text, exactly. */
    const ENGLISH: Reading = {netWorth: '10,500.00 EUR', timing: '+5.00 pp'};

    /** Two decimals, in `locale`'s notation. */
    const twoDecimals = (locale: string, value: number): string => new Intl.NumberFormat(locale, {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(value);
    /** The unit of the timing effect, as the shipped catalogue of `lang` writes it. */
    const ppIn = (lang: UiLanguage): string => CATALOGUES[lang].dashboard.pp;
    /** What the two figures read in `lang`. */
    const readingIn = (lang: UiLanguage): Reading => ({
        netWorth: `${twoDecimals(LOCALE_OF[lang], NET_WORTH)} EUR`,
        timing: `+${twoDecimals(LOCALE_OF[lang], TIMING_PP)} ${ppIn(lang)}`,
    });
    const ITALIAN = readingIn('it');

    const netWorthHero = (): HTMLElement => within(screen.getByTestId('kpi-net-worth')).getByTestId('kpi-value');
    const timingEffect = (): HTMLElement => within(screen.getByTestId('kpi-returns')).getByTestId('kpi-timing-effect-value');
    /** Trimmed only: a no-break space inside is the notation. */
    const shown = (element: HTMLElement): string => (element.textContent ?? '').trim();
    const readFigures = (): Reading => ({netWorth: shown(netWorthHero()), timing: shown(timingEffect())});

    /** The KPI row, every figure at its value on the first frame. */
    function mountKpis(overrides: Partial<ReturnType<typeof summary>> = {}): void {
        expect(hydration.TWEEN_HYDRATION_CONTEXT, 'control: TweenedValue exports its hydration context').toBeDefined();
        render(KpiSection, {
            props: {summary: {...summary(), ...overrides}, history: [], loading: false, displayCurrency: 'EUR'},
            context: new Map([[hydration.TWEEN_HYDRATION_CONTEXT, () => true]]),
        });
    }

    /** Change the UI language as LanguageSelector does, then flush. The controls name the layer if the language did not move. */
    async function switchLanguage(lang: UiLanguage): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        flushSync();
        await tick();
        expect(get(currentLanguage), `control: the app language is ${lang}`).toBe(lang);
        expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
    }

    beforeAll(async () => {
        // English was loaded by the file's own beforeAll; Italian joins it, so a switch never waits on a loader.
        await waitLocale('it');
        // Controls: today's English is what Intl writes for en-US, and this runtime has Italian ICU data.
        expect(readingIn('en'), 'English, from Intl and the catalogue').toEqual(ENGLISH);
        expect(ITALIAN.netWorth, 'the Italian net worth differs from English').not.toBe(ENGLISH.netWorth);
        expect(ITALIAN.timing, 'the Italian timing effect differs from English').not.toBe(ENGLISH.timing);
    });

    beforeEach(() => {
        // A masked amount has no notation: privacy is module-level state, off for this block.
        setPrivacyEnabled(false);
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await switchLanguage('en');
    });

    it('English UI (control): the net worth and the timing effect print exactly today’s text', () => {
        mountKpis();

        expect(readFigures()).toEqual(ENGLISH);
    });

    it('mounted with the UI in Italian: the net worth and the timing effect in Italian notation', async () => {
        await switchLanguage('it');
        mountKpis();

        expect(readFigures()).toEqual(ITALIAN);
    });

    it('follows an in-place switch of the UI language, en → it → en', async () => {
        mountKpis();
        expect(readFigures(), 'en, mount — today’s text').toEqual(ENGLISH);

        await switchLanguage('it');
        expect(readFigures(), 'en → it in place — Italian notation').toEqual(ITALIAN);

        await switchLanguage('en');
        expect(readFigures(), 'it → en in place — today’s text again').toEqual(ENGLISH);
    });

    it.each(['en', 'it'] as const)('a timing effect of exactly zero carries no sign (%s)', async (lang) => {
        await switchLanguage(lang);
        // Both returns at 40%: mwrr_cum − twrr is exactly 0, and so is the timing effect the backend sends.
        mountKpis({twrr_percent: '0.40', mwrr_cumulative_percent: '0.40', timing_effect_percent: '0'});

        expect(shown(timingEffect())).toBe(`${twoDecimals(LOCALE_OF[lang], 0)} ${ppIn(lang)}`);
    });
});

/**
 * R17 / W8 / P4 — the day change, its two shares and the timing effect are the summary's (MF-P).
 *
 * The backend now sends with the summary what the cards used to work out:
 *   - `pnl_change_1d`: the total P&L's change from the CALENDAR day before the valuation date to it;
 *   - `pnl_change_1d_vs_total_pnl_percent` and `pnl_change_1d_vs_nav_percent`: that change over |the day
 *     before's total P&L| and over |its NAV|, fractions with the change's sign, null on a zero base;
 *   - `timing_effect_percent`: MWRR cumulative − TWRR, a fraction, null when either is missing.
 * The cards write them — the change as money, the fractions ×100 — and derive none of them: not the change
 * from the last two `history` points, which need not be a calendar day apart; not a share from its base; not
 * the timing effect from the two bars. A null field shows nothing — no day line, no share — and Timing effect
 * reads «—» and claims nothing, even where the history, or both returns, would give a figure.
 *
 * Fixture. The file's summary — TWRR 40% and MWRR cumulative 45%, bars that subtract to +5 pp — and a history
 * whose last two points are a week apart: a fall of 100 on a total P&L of 1 000 and a NAV of 20 000, which the
 * cards would show as -100.00, -10.00% and -0.50%, down. The summary's day says otherwise on every figure:
 * +12.34, +5.00%, +0.10%, up, and a timing effect of -1.23 pp — so whatever the cards show names its source.
 * Every missing field is tried null and absent: a report cached before MF-P has none of them.
 *
 * Read by `data-testid` in both cards, every figure at its value on the first frame (the page cache's hydration
 * context), so no read waits on a tween. Card 1's hero and Card 2's ROI bar are the barrier that both cards are
 * drawn, so a figure missing here is missing from a drawn card. Timing effect's unit and its label are
 * translated: the value is matched on its sign and digits, the label only read as claiming something or not.
 */
describe('KpiSection — the day change and the timing effect come from the summary (R17 / W8 / P4)', () => {
    const hydration = Tweened as unknown as {TWEEN_HYDRATION_CONTEXT?: unknown};
    const EM_DASH = '\u2014';

    type Missing = 'null' | 'absent';
    type DayField = 'pnl_change_1d' | 'pnl_change_1d_vs_total_pnl_percent' | 'pnl_change_1d_vs_nav_percent' | 'timing_effect_percent';
    /** The file's summary with the MF-P fields, optional and nullable as the schema types them. */
    type DaySummary = Omit<ReturnType<typeof summary>, 'timing_effect_percent'> & {
        pnl_change_1d?: {code: string; amount: string} | null;
        pnl_change_1d_vs_total_pnl_percent?: string | null;
        pnl_change_1d_vs_nav_percent?: string | null;
        timing_effect_percent?: string | null;
    };

    /** The calendar day the backend reports: not one of these figures is what the history gives. */
    const DAY = {pnl_change_1d: EUR('12.34'), pnl_change_1d_vs_total_pnl_percent: '0.05', pnl_change_1d_vs_nav_percent: '0.001'};

    function historyPoint(date: string, totalPnl: string) {
        return {
            date,
            through: date,
            cash_value: EUR('500'),
            market_value: EUR('19500'),
            nav_value: EUR('20000'),
            capital_baseline: EUR('19000'),
            book_asset_like: EUR('19000'),
            cash_from_contributed_capital: EUR('400'),
            cash_from_generated_returns: EUR('100'),
            total_pnl: EUR(totalPnl),
        };
    }

    /** The history's last two points, a week apart: a week's fall of 100, not the calendar day's change. */
    const WEEK = [historyPoint('2026-10-09', '1000'), historyPoint('2026-10-16', '900')];

    const norm = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();

    /** The file's summary with the backend's day, and `fields` missing: set to null, or with their keys removed. */
    function summaryWithout(fields: readonly DayField[], how: Missing): DaySummary {
        const s: DaySummary = {...summary(), ...DAY};
        for (const field of fields) {
            if (how === 'null') s[field] = null;
            else delete s[field];
        }
        return s;
    }

    /** The KPI row over `s` and the week, every figure at its value on the first frame; then the barrier that both cards are drawn. */
    function mountDay(s: DaySummary): void {
        expect(hydration.TWEEN_HYDRATION_CONTEXT, 'control: TweenedValue exports its hydration context').toBeDefined();
        render(KpiSection, {
            props: {summary: s, history: WEEK, loading: false, displayCurrency: 'EUR'},
            context: new Map([[hydration.TWEEN_HYDRATION_CONTEXT, () => true]]),
        });
        expect(norm(within(screen.getByTestId('kpi-period-pnl')).getByTestId('kpi-value').textContent), 'barrier: Card 1’s hero is drawn').toBe(norm(formatCurrencyAmountPlain(500, 'EUR', {showSign: true})));
        expect(norm(within(screen.getByTestId('kpi-returns')).getByTestId('kpi-return-roi-value').textContent), 'barrier: Card 2’s ROI bar is drawn').toBe('50.00%');
    }

    /** What the cards show of the day, null where an element is not rendered. The day line's amount is its text without the bracketed share. */
    function readDay() {
        const line = screen.queryByTestId('kpi-pnl-delta-day');
        const totalShare = screen.queryByTestId('kpi-pnl-delta-day-pct');
        const navShare = screen.queryByTestId('kpi-returns-delta-pct');
        return {
            amount: line ? norm(line.textContent).replace(/\s*\([^()]*\)$/, '') : null,
            direction: line ? line.getAttribute('data-direction') : null,
            shareOfTotalPnl: totalShare ? norm(totalShare.textContent) : null,
            shareOfNav: navShare ? norm(navShare.textContent) : null,
            shareOfNavDirection: navShare ? navShare.getAttribute('data-direction') : null,
            timing: norm(screen.getByTestId('kpi-timing-effect-value').textContent),
        };
    }

    beforeEach(() => {
        // Module-level state the other blocks move: amounts are read in the clear, every figure in English notation.
        setPrivacyEnabled(false);
        expect(uiLocale(), 'control: the interface locale is en-US').toBe('en-US');
    });

    it('shows the summary’s day change, its two shares and its timing effect — not the history’s, not the bars’ difference', () => {
        mountDay({...summary(), ...DAY, timing_effect_percent: '-0.0123'});

        expect(readDay()).toEqual({
            amount: norm(formatCurrencyAmountPlain(12.34, 'EUR', {showSign: true})),
            direction: 'up',
            shareOfTotalPnl: '+5.00%',
            shareOfNav: '+0.10%',
            shareOfNavDirection: 'up',
            timing: expect.stringMatching(/^-1\.23(?!\d)/),
        });
    });

    describe.each<Missing>(['null', 'absent'])('a figure missing from the summary as %s', (how) => {
        it('pnl_change_1d and its shares: no day line and no share, though the history’s last two points give a change', () => {
            mountDay(summaryWithout(['pnl_change_1d', 'pnl_change_1d_vs_total_pnl_percent', 'pnl_change_1d_vs_nav_percent'], how));

            const {amount, shareOfTotalPnl, shareOfNav} = readDay();
            expect({amount, shareOfTotalPnl, shareOfNav}).toEqual({amount: null, shareOfTotalPnl: null, shareOfNav: null});
        });

        it('pnl_change_1d_vs_total_pnl_percent: the day line without its share, while the NAV share stays', () => {
            mountDay(summaryWithout(['pnl_change_1d_vs_total_pnl_percent'], how));

            // The day line and Card 2's share are drawn: only Card 1's share is missing.
            const {amount, shareOfTotalPnl, shareOfNav} = readDay();
            expect({amount, shareOfTotalPnl, shareOfNav}).toEqual({amount: expect.any(String), shareOfTotalPnl: null, shareOfNav: expect.any(String)});
        });

        it('pnl_change_1d_vs_nav_percent: no share on the Returns card, while the day line keeps its own', () => {
            mountDay(summaryWithout(['pnl_change_1d_vs_nav_percent'], how));

            // The day line and its share are drawn: only Card 2's share is missing.
            const {amount, shareOfTotalPnl, shareOfNav} = readDay();
            expect({amount, shareOfTotalPnl, shareOfNav}).toEqual({amount: expect.any(String), shareOfTotalPnl: expect.any(String), shareOfNav: null});
        });

        it('timing_effect_percent, both returns present: Timing effect reads «—» and claims nothing', () => {
            mountDay(summaryWithout(['timing_effect_percent'], how));

            // TWRR and MWRR cumulative are on screen with their values: only the timing effect is missing.
            const card = within(screen.getByTestId('kpi-returns'));
            expect({
                twrrCum: norm(card.getByTestId('kpi-return-twrr-cum-value').textContent),
                mwrrCum: norm(card.getByTestId('kpi-return-mwrr-cum-value').textContent),
                timing: norm(card.getByTestId('kpi-timing-effect-value').textContent),
                timingLabel: norm(card.queryByTestId('kpi-timing-effect-label')?.textContent),
            }).toEqual({twrrCum: '40.00%', mwrrCum: '45.00%', timing: EM_DASH, timingLabel: ''});
        });
    });
});

/**
 * Round 3, §1.7 — the timing effect publishes its direction, and has no colour of its own.
 *
 * The designer: the timing effect takes the sign tokens of the other KPIs, with no function making a green of its own.
 * Until round 3 its value and its label carried an inline `style`, a `color-mix` of the gain or the loss role, stronger
 * the larger the effect (`timingEffectColor`, removed). Now the card publishes the reading as `data-direction`, on
 * `kpi-timing-effect-value` and on `kpi-timing-effect-label` alike: `favorable` above +0.05 pp, `unfavorable` below
 * −0.05 pp, `neutral` within, and none at all when the backend sends no timing effect, where the value reads «—». The
 * colour follows the direction through the sign classes of the other KPIs; a class is not a contract (the design
 * system's rule 10, «state for tests, not colours»), so what is asserted is the state, and that neither element keeps
 * an inline colour.
 *
 * `timing_effect_percent` is a fraction: '0.05' is +5 pp, '0.0004' is +0.04 pp, inside the neutral band. Read on the
 * first frame (the page cache's hydration context, as in the R17 block above), so no read waits on a tween; the
 * Returns card's ROI bar is the barrier that the card is drawn.
 */
describe('KpiSection — the timing effect publishes its direction, and has no colour of its own (round 3, §1.7)', () => {
    const hydration = Tweened as unknown as {TWEEN_HYDRATION_CONTEXT?: unknown};
    const EM_DASH = '\u2014';
    const norm = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();

    /** The KPI row with the file's summary and `timing` as its timing effect; then the timing effect's value and label. */
    function mountTiming(timing: string | null): {value: HTMLElement; label: HTMLElement} {
        expect(hydration.TWEEN_HYDRATION_CONTEXT, 'control: TweenedValue exports its hydration context').toBeDefined();
        render(KpiSection, {
            props: {summary: {...summary(), timing_effect_percent: timing}, history: [], loading: false, displayCurrency: 'EUR'},
            context: new Map([[hydration.TWEEN_HYDRATION_CONTEXT, () => true]]),
        });
        const card = within(screen.getByTestId('kpi-returns'));
        expect(norm(card.getByTestId('kpi-return-roi-value').textContent), 'barrier: the Returns card is drawn').toBe('50.00%');
        return {value: card.getByTestId('kpi-timing-effect-value'), label: card.getByTestId('kpi-timing-effect-label')};
    }

    beforeEach(() => {
        // Module-level state the other blocks move: the figures in the clear, in English notation.
        setPrivacyEnabled(false);
        expect(uiLocale(), 'control: the interface locale is en-US').toBe('en-US');
    });

    it.each([
        {timing: '0.05', direction: 'favorable', figure: /^\+5\.00(?!\d)/},
        {timing: '-0.05', direction: 'unfavorable', figure: /^-5\.00(?!\d)/},
        {timing: '0.0004', direction: 'neutral', figure: /^\+0\.04(?!\d)/},
        {timing: '-0.0004', direction: 'neutral', figure: /^-0\.04(?!\d)/},
        {timing: '0', direction: 'neutral', figure: /^0\.00(?!\d)/},
    ])('timing_effect_percent $timing: data-direction="$direction" on the value and on its label', ({timing, direction, figure}) => {
        const {value, label} = mountTiming(timing);

        expect(norm(value.textContent), 'barrier: the value shows the figure it was given').toMatch(figure);
        expect({value: value.getAttribute('data-direction'), label: label.getAttribute('data-direction')}).toEqual({value: direction, label: direction});
    });

    it('timing_effect_percent null: no data-direction on the value or on its label, and the value reads «—»', () => {
        const {value, label} = mountTiming(null);

        expect(norm(value.textContent)).toBe(EM_DASH);
        expect({value: value.hasAttribute('data-direction'), label: label.hasAttribute('data-direction')}).toEqual({value: false, label: false});
    });

    it.each(['0.05', '-0.05', '0.0004', null])('timing_effect_percent %s: no inline colour on the value or on its label', (timing) => {
        const {value, label} = mountTiming(timing);

        expect([value, label].map((element) => ({testid: element.getAttribute('data-testid'), inlineColour: element.style.color, style: element.getAttribute('style') ?? ''}))).toEqual([
            {testid: 'kpi-timing-effect-value', inlineColour: '', style: expect.not.stringMatching(/color/i)},
            {testid: 'kpi-timing-effect-label', inlineColour: '', style: expect.not.stringMatching(/color/i)},
        ]);
    });
});
