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

import {render, screen, setupI18n, waitFor} from '$test/component';
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
