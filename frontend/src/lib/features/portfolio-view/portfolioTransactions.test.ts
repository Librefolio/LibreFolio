/**
 * The Transactions tab's rows of the portfolio view (Y6-7, delivery 2; moved out of the Dashboard page, behaviour kept).
 *
 * What the old inline code did and a browser spec reaches only through a whole page: nothing is asked while the tab is not
 * the active one; the rows are asked once per broker/period key and again when the key moves (back on page 1); a broker
 * subset is asked one broker at a time and the answers merged by transaction id; no filter asks once without `broker_id`;
 * a pending "All" sends no start date; and a user who owns nothing gets no rows and no request (F2).
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({query: vi.fn(), partners: vi.fn(), tooltips: vi.fn()}));
vi.mock('$lib/api', () => ({zodiosApi: {query_transactions_api_v1_transactions_get: mocks.query}}));
vi.mock('$lib/features/transactions/loadTransactionRows', () => ({loadPartnerRows: mocks.partners, loadEventTooltipMap: mocks.tooltips}));

import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
import {PortfolioTransactions, type PortfolioTransactionsInputs} from './portfolioTransactions.svelte';
import type {TXReadItem} from '$lib/features/transactions/types';

const tx = (id: number) => ({id}) as unknown as TXReadItem;

interface Knobs {
    owned: number[];
    brokerIds: number[] | undefined;
    period: {historyStart: string; start: string; end: string; isMaxPending: boolean};
}

function make(overrides: Partial<Knobs> = {}, extra: Partial<PortfolioTransactionsInputs> = {}) {
    const knobs: Knobs = {owned: [1, 2], brokerIds: [1, 2], period: {historyStart: '2026-01-01', start: '2026-01-01', end: '2026-06-30', isMaxPending: false}, ...overrides};
    const inputs: PortfolioTransactionsInputs = {ownedBrokerIds: () => knobs.owned, brokerIds: () => knobs.brokerIds, period: () => knobs.period, ...extra};
    return {knobs, ctl: new PortfolioTransactions(inputs)};
}

const loaded = (ctl: PortfolioTransactions) => vi.waitFor(() => expect(ctl.loading).toBe(false));
const askedQueries = () => mocks.query.mock.calls.map((call) => (call[0] as {queries: Record<string, unknown>}).queries);

beforeEach(() => {
    mocks.query.mockReset();
    mocks.partners.mockReset().mockResolvedValue([]);
    mocks.tooltips.mockReset().mockResolvedValue(new Map());
    mocks.query.mockImplementation(async ({queries}: {queries: {broker_id?: number}}) => (queries.broker_id === 2 ? [tx(20), tx(21)] : [tx(10), tx(21)]));
});

describe('PortfolioTransactions', () => {
    it('asks nothing while the tab is not the active one', async () => {
        const {ctl} = make();
        ctl.sync(false);
        expect(mocks.query).not.toHaveBeenCalled();
        expect(ctl.mainRows).toEqual([]);
    });

    it('loads once per key: a second sync with nothing moved asks nothing', async () => {
        const {ctl} = make();
        ctl.sync(true);
        await vi.waitFor(() => expect(ctl.mainRows.length).toBeGreaterThan(0));
        await loaded(ctl);
        const asked = mocks.query.mock.calls.length;
        ctl.sync(true);
        ctl.sync(false);
        ctl.sync(true);
        expect(mocks.query.mock.calls.length).toBe(asked);
    });

    it('asks again, from page 1, when the period moves', async () => {
        const {ctl, knobs} = make();
        ctl.sync(true);
        await vi.waitFor(() => expect(ctl.mainRows.length).toBeGreaterThan(0));
        await loaded(ctl);
        ctl.currentPage = 3;
        const asked = mocks.query.mock.calls.length;
        knobs.period = {...knobs.period, end: '2026-07-31'};
        ctl.sync(true);
        expect(ctl.currentPage).toBe(1);
        await vi.waitFor(() => expect(mocks.query.mock.calls.length).toBeGreaterThan(asked));
    });

    it('asks a broker subset one broker at a time and merges the answers by transaction id', async () => {
        const {ctl} = make({brokerIds: [1, 2]});
        ctl.sync(true);
        await vi.waitFor(() => expect(ctl.mainRows.length).toBe(3));
        await loaded(ctl);
        expect(
            askedQueries()
                .map((queries) => queries.broker_id)
                .sort(),
        ).toEqual([1, 2]);
        expect(ctl.mainRows.map((row) => row.id).sort((a, b) => a - b)).toEqual([10, 20, 21]);
    });

    it('asks once, without a broker, when no filter is set', async () => {
        const {ctl} = make({brokerIds: undefined});
        ctl.sync(true);
        await vi.waitFor(() => expect(ctl.mainRows.length).toBeGreaterThan(0));
        expect(askedQueries()).toEqual([{date_start: '2026-01-01', date_end: '2026-06-30'}]);
    });

    it('sends no start date while "All" is pending', async () => {
        const {ctl} = make({brokerIds: undefined, period: {historyStart: 'min', start: '2000-01-01', end: '2026-06-30', isMaxPending: true}});
        ctl.sync(true);
        await vi.waitFor(() => expect(mocks.query).toHaveBeenCalled());
        expect(askedQueries()).toEqual([{date_end: '2026-06-30'}]);
    });

    it('shows nothing, and asks nothing, for a user who owns no broker', async () => {
        const {ctl} = make({owned: [], brokerIds: undefined});
        ctl.sync(true);
        await vi.waitFor(() => expect(ctl.loading).toBe(false));
        expect(mocks.query).not.toHaveBeenCalled();
        expect(ctl.mainRows).toEqual([]);
        expect(ctl.partnerRows).toEqual([]);
    });
});

describe('PortfolioTransactions · a broker page (delivery 3)', () => {
    const wholeHistory = {followsPeriod: () => false, busyKey: 'broker-transactions'};

    it('asks the broker alone, whole: no dates, whatever the period says', async () => {
        const {ctl} = make({owned: [7], brokerIds: [7]}, wholeHistory);
        ctl.sync(true);
        await vi.waitFor(() => expect(ctl.mainRows.length).toBeGreaterThan(0));
        await loaded(ctl);
        expect(askedQueries()).toEqual([{broker_id: 7}]);
    });

    it('does not ask again when the period moves: only the broker is in its key', async () => {
        const {ctl, knobs} = make({owned: [7], brokerIds: [7]}, wholeHistory);
        ctl.sync(true);
        await vi.waitFor(() => expect(ctl.mainRows.length).toBeGreaterThan(0));
        await loaded(ctl);
        const asked = mocks.query.mock.calls.length;
        knobs.period = {...knobs.period, end: '2026-07-31', start: '2026-02-01'};
        ctl.sync(true);
        expect(mocks.query.mock.calls.length).toBe(asked);
    });

    it('tells the page what it loaded, once the partners and the tooltips are in', async () => {
        const onLoaded = vi.fn();
        mocks.partners.mockResolvedValue([tx(99)]);
        const {ctl} = make({owned: [7], brokerIds: [7]}, {...wholeHistory, onLoaded});
        ctl.sync(true);
        await vi.waitFor(() => expect(onLoaded).toHaveBeenCalledTimes(1));
        const [main, partners] = onLoaded.mock.calls[0];
        expect((main as TXReadItem[]).map((row) => row.id).sort((a, b) => a - b)).toEqual([10, 21]);
        expect((partners as TXReadItem[]).map((row) => row.id)).toEqual([99]);
    });

    it('asks again on request, only when the tab was opened before (Refresh and the bulk workspace)', async () => {
        const {ctl} = make({owned: [7], brokerIds: [7]}, wholeHistory);
        await ctl.reload();
        expect(mocks.query).not.toHaveBeenCalled();
        ctl.sync(true);
        await vi.waitFor(() => expect(ctl.mainRows.length).toBeGreaterThan(0));
        await loaded(ctl);
        const asked = mocks.query.mock.calls.length;
        await ctl.reload();
        expect(mocks.query.mock.calls.length).toBe(asked + 1);
    });

    it("is tracked under the page's own busy key", async () => {
        const track = vi.spyOn(pageBusy, 'track');
        const {ctl} = make({owned: [7], brokerIds: [7]}, wholeHistory);
        ctl.sync(true);
        await vi.waitFor(() => expect(mocks.query).toHaveBeenCalled());
        expect(track.mock.calls.map((call) => call[0])).toContain('broker-transactions');
        track.mockRestore();
    });
});
