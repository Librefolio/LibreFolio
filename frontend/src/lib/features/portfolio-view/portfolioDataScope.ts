/**
 * What a page asks the report routes, in one place (Y6-7, delivery 1).
 *
 * The Dashboard and a broker's page both ask the same three questions of `POST /portfolio/report` — the main report, the
 * contribution of the positions, the P&L candles — for a scope (brokers, period, currency). Since FB-14 the backend
 * answers them from one engine run when their flags are equal, so the three have to carry the same scope; MF6-3 adds
 * the flag that counts the brokers whole (the broker's page, D4). One builder makes the questions, so they cannot drift.
 *
 * Pure: no store, no network.
 *
 * @module features/portfolio-view/portfolioDataScope
 */

import type {ReportOptions} from '$lib/stores/portfolio/portfolioStore.svelte';

/** The scope a page shows: its brokers, its period and its currency. */
export interface PortfolioScope {
    /** The brokers asked; none or empty = every broker the user can read (a page that must not widen the scope never passes none). */
    brokerIds: number[] | undefined;
    /** The first day, or the "min" sentinel while "All" waits for its first real day (FB-7). */
    start: string | undefined;
    end: string | undefined;
    currency: string | undefined;
    /** MF6-3: count every broker whole, as an editor sees it, instead of the owner's share. The broker page asks for it. */
    fullShare: boolean;
}

/** One call of `fetchReport` / `peekReport`: the scope and what is asked of it. */
export interface ReportCall {
    brokerIds: number[] | undefined;
    start: string | undefined;
    end: string | undefined;
    currency: string | undefined;
    includeContribution: boolean;
    includeBreakdown: boolean;
    includeHistory: boolean;
    includeAllocationHistory: boolean;
    options: ReportOptions | undefined;
}

/** Two scopes are the same question when this is equal. An answer of another scope is dropped by comparing it. */
export function scopeKey(scope: PortfolioScope): string {
    return [scope.brokerIds?.join(',') ?? 'all', scope.start ?? '', scope.end ?? '', scope.currency ?? '', scope.fullShare ? 'whole' : 'share'].join('|');
}

/** The flag goes into the options only when it is on: the questions of the owner's share stay as they have always been. */
function share(scope: PortfolioScope): Pick<ReportOptions, 'fullShare'> {
    return scope.fullShare ? {fullShare: true} : {};
}

function call(scope: PortfolioScope, fields: Omit<ReportCall, 'brokerIds' | 'start' | 'end' | 'currency'>): ReportCall {
    return {brokerIds: scope.brokerIds, start: scope.start, end: scope.end, currency: scope.currency, ...fields};
}

/** The main report: the eager sections, no contribution and no candles. `wantsBrokerPnlHistory`: the scope has two brokers or more (G1a). */
export function mainReportCall(scope: PortfolioScope, {wantsBrokerPnlHistory}: {wantsBrokerPnlHistory: boolean}): ReportCall {
    return call(scope, {
        includeContribution: false,
        includeBreakdown: false,
        includeHistory: true,
        includeAllocationHistory: true,
        options: {includeBrokerPnlHistory: wantsBrokerPnlHistory, includeIncomeHistory: true, includeCostHistory: true, includeDepositHistory: true, includeAcquisitionFunding: true, ...share(scope)},
    });
}

/** The contribution of the positions: only `positions_contribution` is read, so the heavy series are off. */
export function contributionCall(scope: PortfolioScope): ReportCall {
    return call(scope, {includeContribution: true, includeBreakdown: false, includeHistory: false, includeAllocationHistory: false, options: scope.fullShare ? share(scope) : undefined});
}

/** The synthetic P&L candles (G1b): lazy, and only `pnl_candles` is read. */
export function pnlCandlesCall(scope: PortfolioScope): ReportCall {
    return call(scope, {includeContribution: false, includeBreakdown: false, includeHistory: false, includeAllocationHistory: false, options: {includePnlCandles: true, ...share(scope)}});
}
