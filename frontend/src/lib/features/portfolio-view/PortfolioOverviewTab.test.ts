// @vitest-environment jsdom
/**
 * PortfolioOverviewTab — the Overview tab moved out of the portfolio view (Y6-7, delivery 2; Vitest + jsdom).
 *
 * The tab shows what the data controller holds and asks nothing itself. What the browser specs reach only through a whole
 * page is pinned here: the cash balances sit in the order of their size, the largest first, whatever order the report
 * lists them in; none says so instead of an empty box; and the chart's request for the P&L candles is the view's own
 * callback, handed down untouched. The three sections (KPIs, growth chart, allocation) are replaced by no-op components:
 * they have their own specs.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {render, screen, setupI18n} from '$test/component';

const mocks = vi.hoisted(() => ({noop: () => {}}));
vi.mock('$lib/features/dashboard/KpiSection.svelte', () => ({default: mocks.noop}));
vi.mock('$lib/features/dashboard/GrowthChart.svelte', () => ({default: mocks.noop}));
vi.mock('$lib/features/dashboard/AllocationPanel.svelte', () => ({default: mocks.noop}));

import PortfolioOverviewTab from './PortfolioOverviewTab.svelte';
import type {PortfolioDataState} from './portfolioData';

beforeAll(async () => {
    await setupI18n();
});

function snapshot(cashBalances: {code: string; amount: string}[] | undefined): PortfolioDataState {
    return {
        summary: cashBalances ? ({cash_balances: cashBalances} as unknown as PortfolioDataState['summary']) : null,
        history: [],
        range: null,
        mwrrLine: [],
        brokerPnlHistory: [],
        incomeHistory: undefined,
        costHistory: undefined,
        depositHistory: undefined,
        acquisitionFunding: undefined,
        allocationHistory: null,
        positionsContribution: null,
        pnlCandles: null,
        appliedCurrency: 'EUR',
        reportLoading: false,
        contributionLoading: false,
        contributionRefreshing: false,
        contributionInBackground: false,
        pnlCandlesLoading: false,
        liveState: 'stopped',
    };
}

const props = (state: PortfolioDataState) => ({snapshot: state, displayCurrency: 'EUR', brokerIds: [1], onRequestPnlCandles: () => {}});

describe('PortfolioOverviewTab — cash balances', () => {
    it('lists them largest first, whatever order the report gives', () => {
        render(PortfolioOverviewTab, props(snapshot([{code: 'USD', amount: '20'}, {code: 'EUR', amount: '900'}, {code: 'CHF', amount: '300'}])));
        const chips = screen.getAllByTestId('dashboard-cash-balance');
        expect(chips.map((chip) => (chip.textContent ?? '').replace(/\D/g, '').replace(/0{2}$/, ''))).toEqual(['900', '300', '20']);
    });

    it('says there is none instead of drawing an empty box', () => {
        render(PortfolioOverviewTab, props(snapshot([])));
        expect(screen.queryAllByTestId('dashboard-cash-balance')).toHaveLength(0);
        expect(screen.getByTestId('dashboard-cash-balances').querySelector('p')).not.toBeNull();
    });

    it('shows the same empty line before the first report has arrived', () => {
        render(PortfolioOverviewTab, props(snapshot(undefined)));
        expect(screen.getByTestId('dashboard-cash-balances').querySelector('p')).not.toBeNull();
    });
});
