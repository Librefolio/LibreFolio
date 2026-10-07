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
import {beforeAll, describe, expect, it, vi} from 'vitest';

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

import {render, screen, setupI18n, waitFor, within} from '$test/component';
// Namespace import on purpose: the hydration context (page cache, phase 1) is read by name below, so
// the F5 and V2 cases keep running while `TweenedValue.svelte` does not export it yet.
import * as Tweened from '$lib/components/ui/TweenedValue.svelte';
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
 * Card 1's base is yesterday's total P&L, Card 2's is yesterday's NAV. The change is the
 * difference between the total P&L of the last two history points on both cards.
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

    /** Yesterday then today, as the dashboard's history ends. */
    function renderDay(prev: {totalPnl: string; nav?: string}, last: {totalPnl: string; nav?: string}) {
        const history = [point('2026-10-05', prev.totalPnl, prev.nav ?? '10000'), point('2026-10-06', last.totalPnl, last.nav ?? '10000')];
        return render(KpiSection, {summary: summary(), history, loading: false, displayCurrency: 'EUR'});
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

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+20000.00%');
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
