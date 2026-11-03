/**
 * The portfolio data controller (Y6-7, delivery 1): what the Dashboard and a broker's page both did to get their figures.
 *
 * It asks the report, the contribution of the positions and the P&L candles for the scope a page shows, keeps the cache
 * on screen while a fresh answer comes, asks again after a failure (Y-24) and after a price catch-up (Z-18), and drops an
 * answer that is not for the scope, the page or the session any more. It computes nothing: every figure is the backend's.
 *
 * Its state is a Svelte store (`subscribe`), not rune state: the broker's page is a legacy-mode component, which does not
 * follow a rune read through a getter but follows `$controller` in both modes. The same applies to the per-position return
 * chart's controllers it owns (`positionsSeries`, `positionsRolling`).
 *
 * A guard that must wake a child's `$effect` (the candles loader of `GrowthChart`, the contribution loader of
 * `PositionsPanel`) reads the controller's state through `$controller` in the page's wrapper, before calling it: reading
 * a store with `get()` registers no dependency. The retry (`createLazyReportRetry`) and the page's own `canAsk` are
 * reactive reads of their own.
 *
 * @module features/portfolio-view/portfolioData
 */

import {get, writable, type Readable} from 'svelte/store';
import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
import {fetchReport as fetchStoreReport, peekReport as peekStoreReport, type AllocationHistoryDimensions, type PortfolioAcquisitionFundingSeries, type PortfolioBrokerPnlHistory, type PortfolioCostHistorySeries, type PortfolioDepositHistorySeries, type PortfolioHistoryPoint, type PortfolioIncomeHistorySeries, type PortfolioMwrrLinePoint, type PortfolioPnlCandleSeries, type PortfolioRange, type PortfolioReport, type PortfolioSummary, type PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';
import {createLazyReportRetry, type LazyReportRetry} from '$lib/stores/portfolio/lazyReportRetry.svelte';
import {createPositionsSeriesController, type PositionsSeriesController, type PositionsSeriesScope} from '$lib/features/dashboard/positionsSeriesController';
import {createPositionsRollingController, type PositionsRollingController, type RollingScope} from '$lib/features/dashboard/positionsRolling';
import {contributionCall, mainReportCall, pnlCandlesCall, scopeKey, type PortfolioScope, type ReportCall} from './portfolioDataScope';

/** What a page shows of its report. */
export interface PortfolioDataState {
    summary: PortfolioSummary | null;
    history: PortfolioHistoryPoint[];
    range: PortfolioRange | null;
    mwrrLine: PortfolioMwrrLinePoint[];
    brokerPnlHistory: PortfolioBrokerPnlHistory[];
    incomeHistory: PortfolioIncomeHistorySeries | undefined;
    costHistory: PortfolioCostHistorySeries | undefined;
    depositHistory: PortfolioDepositHistorySeries | undefined;
    acquisitionFunding: PortfolioAcquisitionFundingSeries | undefined;
    allocationHistory: AllocationHistoryDimensions | null;
    positionsContribution: PositionsContribution | null;
    pnlCandles: PortfolioPnlCandleSeries | null;
    /** The currency of the figures on screen: the one the last answer was asked in. Null before the first one. */
    appliedCurrency: string | null;
    /** The main report is on its way and the page says it is busy (a background load does not set it, Z-18). */
    reportLoading: boolean;
    /** The contribution is asked and none is on screen: the panel shows its skeleton. */
    contributionLoading: boolean;
    /** The contribution is asked again with the cached rows on screen. */
    contributionRefreshing: boolean;
    /** The same, after a price catch-up: the page does not say it is busy (Z-18). */
    contributionInBackground: boolean;
    pnlCandlesLoading: boolean;
}

/** What a controller reads from its page. Every function is read at the moment it is used, so a page passes getters of its own state. */
export interface PortfolioDataInputs {
    /** The scope on screen. */
    scope(): PortfolioScope;
    /** A request may leave: the scope is explicit and, on the Dashboard, the user owns a broker (F2). */
    canAsk(): boolean;
    /** The per-position chart may ask (default: `canAsk`). A broker's page asks its report at once but waits for the broker for this. */
    positionsReady?(): boolean;
    /** The brokers are known. False: `loadAll` does nothing at all, not even stopping the loading flag. Default true. */
    brokersKnown?(): boolean;
    /** The page is on screen. */
    alive(): boolean;
    /** The scope has two brokers or more: the P&L overlay per broker is worth asking (G1a). */
    wantsBrokerPnlHistory(): boolean;
    /** The period the Rolling view asks, as the picker shows it. */
    rollingPeriod?(): {start: string | undefined; end: string | undefined};
    /** "All" waits for its first real day: this is the first day of the history just applied, or null when there is none (FB-7). */
    onFirstDay?(day: string | null): void;
    /** A refresh that failed while figures are on screen: the page tells the user, the figures stay. */
    onRefreshFailed?(): void;
    /** The text of the error `loadAll(…, true)` throws. */
    failureMessage?(): string;
    /** The page shows its skeleton before the first answer: `reportLoading` starts true (the Dashboard). Default false. */
    initialLoading?: boolean;
}

/** The network and the session, injectable for the tests. */
export interface PortfolioDataDeps {
    fetchReport(call: ReportCall, force: boolean): Promise<PortfolioReport | null>;
    peekReport(call: ReportCall): {report: PortfolioReport; stale: boolean} | null;
    session: {generation(): number; isCurrent(generation: number): boolean};
    positionsSeries?: PositionsSeriesController;
    positionsRolling?: PositionsRollingController;
}

export interface PortfolioData extends Readable<PortfolioDataState> {
    /** The retries of the lazy sections, for the user’s Refresh to reset. */
    resetRetries(): void;
    /**
     * The main report of the scope on screen. The cache is shown at once, stale or not; only a stale or missing one is asked
     * again (or any, with `force`). `background` (after a price catch-up, Z-18): the page is not busy meanwhile.
     */
    loadAll(force?: boolean, propagateError?: boolean, options?: {background?: boolean}): Promise<void>;
    /** The contribution of the scope on screen. */
    loadContribution(options?: {background?: boolean}): Promise<void>;
    /** The synthetic P&L candles (G1b) of the scope on screen. */
    loadPnlCandles(): Promise<void>;
    /** Shows the cached report of the scope on screen, if any, and asks nothing. */
    hydrateFromCache(): void;
    /** The per-position return chart's controllers and the scope they follow: call it from an effect that reads the page's scope. */
    readonly positionsSeries: PositionsSeriesController;
    readonly positionsRolling: PositionsRollingController;
    syncPositions(version: number): void;
    /** The scope the per-position chart asks for, for the panel’s own requests. */
    positionsSeriesScope(version: number): PositionsSeriesScope;
    positionsRollingScope(version: number): RollingScope;
    /** The page is gone: a late answer is dropped and the retry timers stop. */
    dispose(): void;
}

const defaultDeps: PortfolioDataDeps = {
    fetchReport: (call, force) => fetchStoreReport(call.brokerIds, call.start, call.end, call.currency, force, call.includeContribution, call.includeBreakdown, call.includeHistory, call.includeAllocationHistory, call.options),
    peekReport: (call) => peekStoreReport(call.brokerIds, call.start, call.end, call.currency, call.includeContribution, call.includeBreakdown, call.includeHistory, call.includeAllocationHistory, call.options),
    session: {generation: getClientSessionGeneration, isCurrent: isClientSessionCurrent},
};

const EMPTY: PortfolioDataState = {
    summary: null,
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
    appliedCurrency: null,
    reportLoading: false,
    contributionLoading: false,
    contributionRefreshing: false,
    contributionInBackground: false,
    pnlCandlesLoading: false,
};

export function createPortfolioData(inputs: PortfolioDataInputs, deps: Partial<PortfolioDataDeps> = {}): PortfolioData {
    const api: PortfolioDataDeps = {...defaultDeps, ...deps};
    const state = writable<PortfolioDataState>({...EMPTY, reportLoading: inputs.initialLoading ?? false});
    const patch = (change: Partial<PortfolioDataState>) => state.update((current) => ({...current, ...change}));

    // Y-24: a failed candles or contribution request is asked again at most three times, 2, 4 and 8 s later, then not until
    // the scope changes or the user's Refresh.
    const candlesRetry: LazyReportRetry = createLazyReportRetry();
    const contributionRetry: LazyReportRetry = createLazyReportRetry();
    const positionsSeries = api.positionsSeries ?? createPositionsSeriesController();
    const positionsRolling = api.positionsRolling ?? createPositionsRollingController();

    let disposed = false;
    let loadSeq = 0;
    /** The report on screen: a page that finds the same cached report again leaves its charts alone. */
    let shownReport: PortfolioReport | null = null;
    let shownContribution: PortfolioReport['positions_contribution'] = null;

    const alive = () => inputs.alive() && !disposed;

    function applyReport(report: PortfolioReport | null, requested: string | undefined) {
        shownReport = report;
        const history = (report?.history as PortfolioHistoryPoint[] | null | undefined) ?? [];
        patch({
            summary: (report?.summary as PortfolioSummary | null | undefined) ?? null,
            history,
            range: (report?.range as PortfolioRange | null | undefined) ?? null,
            mwrrLine: (report?.mwrr_line as PortfolioMwrrLinePoint[] | null | undefined) ?? [],
            brokerPnlHistory: (report?.broker_pnl_history as PortfolioBrokerPnlHistory[] | null | undefined) ?? [],
            // Always reassigned (to null: the main report never asks for candles): this is what drops a candle series of a
            // past broker, period or currency. `loadPnlCandles` asks again once GrowthChart sees it missing in its candles view.
            pnlCandles: (report?.pnl_candles as PortfolioPnlCandleSeries | null | undefined) ?? null,
            // Eager (unlike the candles): asked on every ordinary load (plan §4.1's sparse-payload policy).
            incomeHistory: (report?.income_history as PortfolioIncomeHistorySeries | null | undefined) ?? undefined,
            costHistory: (report?.cost_history as PortfolioCostHistorySeries | null | undefined) ?? undefined,
            depositHistory: (report?.deposit_history as PortfolioDepositHistorySeries | null | undefined) ?? undefined,
            acquisitionFunding: (report?.acquisition_funding as PortfolioAcquisitionFundingSeries | null | undefined) ?? undefined,
            allocationHistory: (report?.allocation_history as AllocationHistoryDimensions | null | undefined) ?? null,
            appliedCurrency: requested ?? null,
        });
        inputs.onFirstDay?.(history.length > 0 ? history[0].date : null);
    }

    function setContribution(report: PortfolioReport | null) {
        const contribution = report?.positions_contribution ?? null;
        if (contribution === shownContribution) return;
        shownContribution = contribution;
        patch({positionsContribution: (contribution as PositionsContribution | null | undefined) ?? null});
    }

    /** The contribution of the scope as the cache holds it (null: never asked). Returns whether the cached one is stale. */
    function showCachedContribution(scope: PortfolioScope): boolean {
        const cached = api.peekReport(contributionCall(scope));
        setContribution(cached?.report ?? null);
        return cached?.stale === true;
    }

    function hydrateFromCache() {
        if (!inputs.canAsk()) return;
        const scope = inputs.scope();
        const cached = api.peekReport(mainReportCall(scope, {wantsBrokerPnlHistory: inputs.wantsBrokerPnlHistory()}));
        if (!cached) return;
        applyReport(cached.report, scope.currency);
        showCachedContribution(scope);
    }

    async function loadAll(force = false, propagateError = false, {background = false}: {background?: boolean} = {}) {
        const generation = api.session.generation();
        const current = () => alive() && api.session.isCurrent(generation);
        if (!current() || !(inputs.brokersKnown?.() ?? true)) return;
        if (!inputs.canAsk()) {
            patch({reportLoading: false});
            return;
        }
        const load = ++loadSeq;
        const scope = inputs.scope();
        const call = mainReportCall(scope, {wantsBrokerPnlHistory: inputs.wantsBrokerPnlHistory()});

        const cached = api.peekReport(call);
        if (cached && cached.report !== shownReport) applyReport(cached.report, scope.currency);
        const request = !cached || cached.stale || force ? api.fetchReport(call, force) : null;
        if (showCachedContribution(scope)) void loadContribution({background});
        if (!request) {
            patch({reportLoading: false});
            return;
        }

        if (!background) patch({reportLoading: true});
        try {
            const report = await request;
            if (!current() || load !== loadSeq) return;
            if (report) {
                if (report !== shownReport) applyReport(report, scope.currency);
            } else if (propagateError) {
                throw new Error(inputs.failureMessage?.() ?? 'The portfolio report could not be loaded');
            } else if (cached) {
                inputs.onRefreshFailed?.();
            } else {
                applyReport(null, scope.currency);
            }
        } finally {
            if (current() && load === loadSeq) patch({reportLoading: false});
        }
    }

    async function loadContribution({background = false}: {background?: boolean} = {}) {
        const generation = api.session.generation();
        const scope = inputs.scope();
        const askedScope = scopeKey(scope);
        // Read before the first await: the effect that called this depends on them (Y-24).
        const allowed = contributionRetry.canAsk(askedScope);
        const busy = get(state);
        if (!inputs.canAsk() || busy.contributionLoading || busy.contributionRefreshing || busy.contributionInBackground || !allowed) return;
        const call = contributionCall(scope);
        const cached = api.peekReport(call);
        if (cached && !cached.stale) {
            setContribution(cached.report);
            return;
        }
        if (cached && background) patch({contributionInBackground: true});
        else if (cached) patch({contributionRefreshing: true});
        else patch({contributionLoading: true});
        try {
            const report = await api.fetchReport(call, false);
            if (!alive() || !api.session.isCurrent(generation) || scopeKey(inputs.scope()) !== askedScope) return;
            // The outcome is recorded before the flags fall back in `finally`: the effect they wake reads it (Y-24).
            if (report) {
                contributionRetry.succeeded(askedScope);
                setContribution(report);
                patch({appliedCurrency: scope.currency ?? null});
            } else {
                contributionRetry.failed(askedScope);
                if (!cached) setContribution(null);
            }
        } finally {
            patch({contributionLoading: false, contributionRefreshing: false, contributionInBackground: false});
        }
    }

    async function loadPnlCandles() {
        const generation = api.session.generation();
        const scope = inputs.scope();
        const askedScope = scopeKey(scope);
        // Read before the first await, `canAsk` first: GrowthChart's effect depends on them, so a request ending or a retry
        // falling due wakes it (Y-16, Y-24).
        const canAsk = inputs.canAsk();
        const allowed = candlesRetry.canAsk(askedScope);
        const busy = get(state);
        if (!canAsk || busy.pnlCandles || busy.pnlCandlesLoading || !allowed) return;
        patch({pnlCandlesLoading: true});
        try {
            const report = await api.fetchReport(pnlCandlesCall(scope), false);
            // An answer of another scope is not this one's: the scope on screen asks for its own.
            if (!alive() || !api.session.isCurrent(generation) || scopeKey(inputs.scope()) !== askedScope) return;
            if (report) candlesRetry.succeeded(askedScope);
            else candlesRetry.failed(askedScope);
            patch({pnlCandles: (report?.pnl_candles as PortfolioPnlCandleSeries | null | undefined) ?? null});
        } finally {
            patch({pnlCandlesLoading: false});
        }
    }

    function positionsSeriesScope(version: number): PositionsSeriesScope {
        const scope = inputs.scope();
        return {brokerIds: scope.brokerIds, start: scope.start, end: scope.end, currency: scope.currency, ready: inputs.positionsReady?.() ?? inputs.canAsk(), version, fullShare: scope.fullShare};
    }

    function positionsRollingScope(version: number): RollingScope {
        const period = inputs.rollingPeriod?.() ?? {start: undefined, end: undefined};
        return {start: period.start, end: period.end, ready: inputs.positionsReady?.() ?? inputs.canAsk(), version};
    }

    function syncPositions(version: number) {
        positionsSeries.sync(positionsSeriesScope(version));
        positionsRolling.sync(positionsRollingScope(version));
    }

    return {
        subscribe: state.subscribe,
        resetRetries() {
            candlesRetry.reset();
            contributionRetry.reset();
        },
        loadAll,
        loadContribution,
        loadPnlCandles,
        hydrateFromCache,
        positionsSeries,
        positionsRolling,
        syncPositions,
        positionsSeriesScope,
        positionsRollingScope,
        dispose() {
            disposed = true;
            candlesRetry.dispose();
            contributionRetry.dispose();
            positionsSeries.dispose();
            positionsRolling.dispose();
        },
    };
}
