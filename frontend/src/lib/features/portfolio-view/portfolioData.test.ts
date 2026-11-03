/**
 * Y6-7 delivery 1 — the portfolio data controller: what the Dashboard and a broker's page both did, once.
 *
 * Both pages asked the report, the contribution and the candles, kept the cache on screen, asked again after a failure
 * (Y-24) and again after a price catch-up (Z-18). The behaviour does not change, so there is no product red: each case
 * below is the specification of a function that used to live twice in a page, written against fake requests and a fake
 * clock. Where the two pages differed, the Dashboard's behaviour is the one kept (the case says so).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import type {PortfolioReport} from '$lib/stores/portfolio/portfolioStore.svelte';
import {createPortfolioData, type PortfolioDataDeps, type PortfolioDataInputs} from './portfolioData';
import type {PortfolioScope, ReportCall} from './portfolioDataScope';

type Peeked = {report: PortfolioReport; stale: boolean} | null;

const baseScope: PortfolioScope = {brokerIds: [1, 2], start: '2026-01-01', end: '2026-10-28', currency: 'EUR', fullShare: false};

/** A report with the sections a case needs; the rest of the schema is not the controller's business. */
function report(fields: Record<string, unknown> = {}): PortfolioReport {
    return {summary: {net_worth: 1}, history: [{date: '1850-03-02'}], range: {start: '1850-03-02', end: '2026-10-28'}, ...fields} as unknown as PortfolioReport;
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((settle) => {
        resolve = settle;
    });
    return {promise, resolve};
}

/** What a controller needs from its page and from the network, all of it fake and all of it recorded. */
function setup(overrides: {scope?: Partial<PortfolioScope>; canAsk?: boolean; brokersKnown?: boolean} = {}) {
    const state = {scope: {...baseScope, ...overrides.scope}, canAsk: overrides.canAsk ?? true, brokersKnown: overrides.brokersKnown ?? true, alive: true, generation: 1, broker2: true};
    const calls: Array<{call: ReportCall; force: boolean}> = [];
    const answers: Array<(call: ReportCall) => Promise<PortfolioReport | null>> = [];
    const cache = new Map<string, Peeked>();
    const firstDays: Array<string | null> = [];
    const failures: number[] = [];

    const deps: PortfolioDataDeps = {
        fetchReport: (call, force) => {
            calls.push({call, force});
            const next = answers.shift();
            return next ? next(call) : Promise.resolve(report());
        },
        peekReport: (call) => cache.get(kindOf(call)) ?? null,
        session: {generation: () => state.generation, isCurrent: (generation) => generation === state.generation},
    };
    const inputs: PortfolioDataInputs = {
        scope: () => state.scope,
        canAsk: () => state.canAsk,
        brokersKnown: () => state.brokersKnown,
        alive: () => state.alive,
        wantsBrokerPnlHistory: () => (state.scope.brokerIds?.length ?? 0) >= 2,
        onFirstDay: (day) => firstDays.push(day),
        onRefreshFailed: () => failures.push(failures.length + 1),
    };
    const data = createPortfolioData(inputs, deps);
    return {data, state, calls, answers, cache, firstDays, failures};
}

/** The three questions, told apart the way the cache would: by what they ask. */
function kindOf(call: ReportCall): 'main' | 'contribution' | 'candles' {
    if (call.options?.includePnlCandles) return 'candles';
    return call.includeContribution ? 'contribution' : 'main';
}

beforeEach(() => {
    vi.useFakeTimers();
});
afterEach(() => {
    vi.useRealTimers();
});

describe('the main report', () => {
    it('asks once, with the main question, and shows the answer', async () => {
        const {data, calls, answers} = setup();
        answers.push(() => Promise.resolve(report({mwrr_line: [{date: '2026-01-02'}]})));
        await data.loadAll();
        expect(calls).toHaveLength(1);
        expect(kindOf(calls[0].call)).toBe('main');
        expect(calls[0].force).toBe(false);
        const state = get(data);
        expect(state.summary).toMatchObject({net_worth: 1});
        expect(state.history).toHaveLength(1);
        expect(state.mwrrLine).toEqual([{date: '2026-01-02'}]);
        expect(state.appliedCurrency).toBe('EUR');
    });

    it('says it is loading while the request is on its way, and stops after', async () => {
        const {data, answers} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadAll();
        expect(get(data).reportLoading).toBe(true);
        pending.resolve(report());
        await load;
        expect(get(data).reportLoading).toBe(false);
    });

    it('shows a stale cache at once, asks again, and the figures move when the answer lands', async () => {
        const {data, cache, answers} = setup();
        cache.set('main', {report: report({summary: {net_worth: 10}}), stale: true});
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadAll();
        expect(get(data).summary).toMatchObject({net_worth: 10});
        pending.resolve(report({summary: {net_worth: 20}}));
        await load;
        expect(get(data).summary).toMatchObject({net_worth: 20});
    });

    it('a fresh cache is not asked again, unless forced', async () => {
        const {data, cache, calls} = setup();
        cache.set('main', {report: report(), stale: false});
        await data.loadAll();
        expect(calls).toHaveLength(0);
        expect(get(data).reportLoading).toBe(false);
        await data.loadAll(true);
        expect(calls).toHaveLength(1);
        expect(calls[0].force).toBe(true);
    });

    it('in background (Z-18, after a price catch-up) the page is not busy: reportLoading stays off', async () => {
        const {data, cache, answers} = setup();
        cache.set('main', {report: report(), stale: true});
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadAll(false, false, {background: true});
        expect(get(data).reportLoading).toBe(false);
        pending.resolve(report({summary: {net_worth: 5}}));
        await load;
        expect(get(data).summary).toMatchObject({net_worth: 5});
        expect(get(data).reportLoading).toBe(false);
    });

    it('the answer of an older request does not replace the newest one', async () => {
        const {data, answers} = setup();
        const first = deferred<PortfolioReport | null>();
        const second = deferred<PortfolioReport | null>();
        answers.push(() => first.promise, () => second.promise);
        const older = data.loadAll(true);
        const newer = data.loadAll(true);
        second.resolve(report({summary: {net_worth: 2}}));
        await newer;
        first.resolve(report({summary: {net_worth: 1}}));
        await older;
        expect(get(data).summary).toMatchObject({net_worth: 2});
        expect(get(data).reportLoading).toBe(false);
    });

    it('a failure keeps what is on screen and says so once', async () => {
        const {data, cache, answers, failures} = setup();
        cache.set('main', {report: report({summary: {net_worth: 7}}), stale: true});
        answers.push(() => Promise.resolve(null));
        await data.loadAll();
        expect(get(data).summary).toMatchObject({net_worth: 7});
        expect(failures).toEqual([1]);
    });

    it('a failure with nothing on screen shows the empty state, and does not toast', async () => {
        const {data, answers, failures} = setup();
        answers.push(() => Promise.resolve(null));
        await data.loadAll();
        expect(get(data).summary).toBeNull();
        expect(get(data).history).toEqual([]);
        expect(failures).toEqual([]);
    });

    it('a failure the caller asked to see is thrown (the FX sync waits for the answer)', async () => {
        const {data, answers} = setup();
        answers.push(() => Promise.resolve(null));
        await expect(data.loadAll(true, true)).rejects.toThrow();
        expect(get(data).reportLoading).toBe(false);
    });

    it('asks nothing while the brokers are not known, and does not touch the loading flag', async () => {
        const {data, calls} = setup({brokersKnown: false, canAsk: false});
        await data.loadAll();
        expect(calls).toHaveLength(0);
    });

    it('asks nothing for a user with no broker to ask, and is not loading', async () => {
        const {data, calls} = setup({canAsk: false});
        await data.loadAll();
        expect(calls).toHaveLength(0);
        expect(get(data).reportLoading).toBe(false);
    });

    it('drops an answer that lands after the page left', async () => {
        const {data, state, answers} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadAll();
        state.alive = false;
        pending.resolve(report());
        await load;
        expect(get(data).summary).toBeNull();
    });

    it('drops an answer that lands in another session (a log-out and a log-in under it)', async () => {
        const {data, state, answers} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadAll();
        state.generation += 1;
        pending.resolve(report());
        await load;
        expect(get(data).summary).toBeNull();
    });

    it('the page that was disposed ignores a late answer', async () => {
        const {data, answers} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadAll();
        data.dispose();
        pending.resolve(report());
        await load;
        expect(get(data).summary).toBeNull();
    });

    it('"All": the first real day comes from the report’s history, before the year 2000 too (FB-7)', async () => {
        const {data, firstDays} = setup({scope: {start: 'min'}});
        await data.loadAll();
        expect(firstDays).toEqual(['1850-03-02']);
    });

    it('no history, no first day', async () => {
        const {data, answers, firstDays} = setup({scope: {start: 'min'}});
        answers.push(() => Promise.resolve(report({history: []})));
        await data.loadAll();
        expect(firstDays).toEqual([null]);
    });

    it('brokers counted whole (MF6-3): the question carries the flag', async () => {
        const {data, calls} = setup({scope: {fullShare: true}});
        await data.loadAll();
        expect(calls[0].call.options?.fullShare).toBe(true);
    });

    it('hydrating from the cache shows it without asking anything', () => {
        const {data, cache, calls} = setup();
        cache.set('main', {report: report({summary: {net_worth: 3}}), stale: false});
        data.hydrateFromCache();
        expect(get(data).summary).toMatchObject({net_worth: 3});
        expect(calls).toHaveLength(0);
    });
});

describe('the contribution', () => {
    it('is not asked by the main load when nothing of it is cached (the panel asks when a view needs it)', async () => {
        const {data, calls} = setup();
        await data.loadAll();
        expect(calls.map((entry) => kindOf(entry.call))).toEqual(['main']);
        expect(get(data).positionsContribution).toBeNull();
    });

    it('asks the contribution question, shows it, and says it is loading meanwhile', async () => {
        const {data, answers, calls} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadContribution();
        expect(get(data).contributionLoading).toBe(true);
        pending.resolve(report({positions_contribution: {positions: []}}));
        await load;
        expect(kindOf(calls[0].call)).toBe('contribution');
        expect(get(data).positionsContribution).toEqual({positions: []});
        expect(get(data).contributionLoading).toBe(false);
    });

    it('a fresh cached one is shown without asking', async () => {
        const {data, cache, calls} = setup();
        cache.set('contribution', {report: report({positions_contribution: {positions: [1]}}), stale: false});
        await data.loadContribution();
        expect(calls).toHaveLength(0);
        expect(get(data).positionsContribution).toEqual({positions: [1]});
    });

    it('a stale cached one stays on screen while it is asked again: refreshing, not loading', async () => {
        const {data, cache, answers} = setup();
        cache.set('contribution', {report: report({positions_contribution: {positions: [1]}}), stale: true});
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadContribution();
        expect(get(data).contributionRefreshing).toBe(true);
        expect(get(data).contributionLoading).toBe(false);
        pending.resolve(report({positions_contribution: {positions: [2]}}));
        await load;
        expect(get(data).positionsContribution).toEqual({positions: [2]});
        expect(get(data).contributionRefreshing).toBe(false);
    });

    it('after a price catch-up it is asked in background: the page does not say it is busy (Z-18)', async () => {
        const {data, cache, answers} = setup();
        cache.set('contribution', {report: report({positions_contribution: {positions: [1]}}), stale: true});
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadContribution({background: true});
        expect(get(data).contributionInBackground).toBe(true);
        expect(get(data).contributionRefreshing).toBe(false);
        pending.resolve(report({positions_contribution: {positions: [3]}}));
        await load;
        expect(get(data).contributionInBackground).toBe(false);
    });

    it('the main load shows the cached contribution of the scope and asks it again in background when it is stale', async () => {
        const {data, cache, calls, answers} = setup();
        cache.set('main', {report: report(), stale: false});
        cache.set('contribution', {report: report({positions_contribution: {positions: [1]}}), stale: true});
        answers.push(() => Promise.resolve(report({positions_contribution: {positions: [9]}})));
        await data.loadAll(false, false, {background: true});
        await vi.advanceTimersByTimeAsync(0);
        expect(get(data).positionsContribution).toEqual({positions: [9]});
        expect(calls.map((entry) => kindOf(entry.call))).toEqual(['contribution']);
    });

    it('a second request while one is on its way is not sent', async () => {
        const {data, answers, calls} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const first = data.loadContribution();
        await data.loadContribution();
        expect(calls).toHaveLength(1);
        pending.resolve(report());
        await first;
    });

    it('asks nothing while the page cannot ask', async () => {
        const {data, calls} = setup({canAsk: false});
        await data.loadContribution();
        expect(calls).toHaveLength(0);
    });

    it('after a failure it is asked again 2, 4 and 8 seconds later, then never (Y-24)', async () => {
        const {data, answers, calls} = setup();
        for (let i = 0; i < 6; i += 1) answers.push(() => Promise.resolve(null));
        await data.loadContribution();
        await data.loadContribution();
        expect(calls).toHaveLength(1);
        await vi.advanceTimersByTimeAsync(2_000);
        await data.loadContribution();
        expect(calls).toHaveLength(2);
        await vi.advanceTimersByTimeAsync(4_000);
        await data.loadContribution();
        expect(calls).toHaveLength(3);
        await vi.advanceTimersByTimeAsync(8_000);
        await data.loadContribution();
        expect(calls).toHaveLength(4);
        await vi.advanceTimersByTimeAsync(60_000);
        await data.loadContribution();
        expect(calls).toHaveLength(4);
    });

    it('the user’s Refresh lets it be asked again at once', async () => {
        const {data, answers, calls} = setup();
        answers.push(() => Promise.resolve(null));
        await data.loadContribution();
        data.resetRetries();
        await data.loadContribution();
        expect(calls).toHaveLength(2);
    });

    it('the answer of a past scope is not applied, and its failure counts for its own scope only', async () => {
        const {data, state, answers, calls} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadContribution();
        state.scope = {...state.scope, start: '2026-02-01'};
        pending.resolve(report({positions_contribution: {positions: [1]}}));
        await load;
        expect(get(data).positionsContribution).toBeNull();
        await data.loadContribution();
        expect(calls).toHaveLength(2);
    });
});

describe('the P&L candles', () => {
    it('asks the candles question once, and keeps the answer', async () => {
        const {data, answers, calls} = setup();
        answers.push(() => Promise.resolve(report({pnl_candles: {points: []}})));
        await data.loadPnlCandles();
        expect(kindOf(calls[0].call)).toBe('candles');
        expect(get(data).pnlCandles).toEqual({points: []});
        await data.loadPnlCandles();
        expect(calls).toHaveLength(1);
    });

    it('says it is loading meanwhile, and the flag falls back after', async () => {
        const {data, answers} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadPnlCandles();
        expect(get(data).pnlCandlesLoading).toBe(true);
        pending.resolve(report({pnl_candles: {points: []}}));
        await load;
        expect(get(data).pnlCandlesLoading).toBe(false);
    });

    it('a new main report forgets the candles of the old scope, so they are asked for the new one', async () => {
        const {data, answers, calls} = setup();
        answers.push(() => Promise.resolve(report({pnl_candles: {points: [1]}})));
        await data.loadPnlCandles();
        await data.loadAll(true);
        expect(get(data).pnlCandles).toBeNull();
        await data.loadPnlCandles();
        expect(calls.filter((entry) => kindOf(entry.call) === 'candles')).toHaveLength(2);
    });

    it('a cached contribution does not cancel them', async () => {
        const {data, cache, calls} = setup();
        cache.set('contribution', {report: report({positions_contribution: {positions: []}}), stale: false});
        await data.loadAll();
        await data.loadPnlCandles();
        expect(calls.map((entry) => kindOf(entry.call))).toContain('candles');
    });

    it('asks nothing while the page cannot ask (Y-16: a saved Candles view waits for the brokers)', async () => {
        const {data, calls, state} = setup({canAsk: false});
        await data.loadPnlCandles();
        expect(calls).toHaveLength(0);
        state.canAsk = true;
        await data.loadPnlCandles();
        expect(calls).toHaveLength(1);
    });

    it('after a failure it is asked again 2 seconds later (Y-24)', async () => {
        const {data, answers, calls} = setup();
        answers.push(() => Promise.resolve(null));
        await data.loadPnlCandles();
        await data.loadPnlCandles();
        expect(calls).toHaveLength(1);
        await vi.advanceTimersByTimeAsync(2_000);
        await data.loadPnlCandles();
        expect(calls).toHaveLength(2);
    });

    it('the answer of a past scope is not applied', async () => {
        const {data, state, answers} = setup();
        const pending = deferred<PortfolioReport | null>();
        answers.push(() => pending.promise);
        const load = data.loadPnlCandles();
        state.scope = {...state.scope, currency: 'USD'};
        pending.resolve(report({pnl_candles: {points: [1]}}));
        await load;
        expect(get(data).pnlCandles).toBeNull();
    });
});

describe('the three questions of one scope are the same scope (FB-14)', () => {
    it('main, contribution and candles carry the same brokers, period and currency', async () => {
        const {data, calls} = setup();
        await data.loadAll();
        await data.loadContribution();
        await data.loadPnlCandles();
        const scopes = calls.map(({call}) => JSON.stringify([call.brokerIds, call.start, call.end, call.currency]));
        expect(new Set(scopes).size).toBe(1);
    });
});

describe('the positions chart follows the same scope', () => {
    it('hands its controllers the scope, the readiness and the whole-broker flag of the page', () => {
        const series = {sync: vi.fn(), request: vi.fn(), dispose: vi.fn(), subscribe: vi.fn()};
        const rolling = {sync: vi.fn(), request: vi.fn(), dispose: vi.fn(), subscribe: vi.fn()};
        const inputs: PortfolioDataInputs = {scope: () => ({...baseScope, fullShare: true}), canAsk: () => true, alive: () => true, wantsBrokerPnlHistory: () => false, rollingPeriod: () => ({start: '2026-01-02', end: '2026-10-28'})};
        const data = createPortfolioData(inputs, {positionsSeries: series as never, positionsRolling: rolling as never});
        data.syncPositions(4);
        expect(series.sync).toHaveBeenCalledWith({brokerIds: [1, 2], start: '2026-01-01', end: '2026-10-28', currency: 'EUR', ready: true, version: 4, fullShare: true});
        expect(rolling.sync).toHaveBeenCalledWith({start: '2026-01-02', end: '2026-10-28', ready: true, version: 4});
        data.dispose();
        expect(series.dispose).toHaveBeenCalled();
        expect(rolling.dispose).toHaveBeenCalled();
    });
});
