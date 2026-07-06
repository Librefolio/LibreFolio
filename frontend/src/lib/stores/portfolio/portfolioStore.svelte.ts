/**
 * portfolioStore — Session-level cache for unified portfolio report.
 *
 * Uses POST /api/v1/portfolio/report to run the engine once and get
 * summary + history + allocation_history + data_quality in a single call.
 *
 * Cache key = `broker_ids (sorted) | dateFrom | dateTo | targetCurrency`
 * Calling `invalidate()` clears the cache (used by [↻ Sync] and CRUD mutations).
 *
 * Architecture: Svelte 5 module-level $state() runes.
 *
 * @module stores/portfolio/portfolioStore
 */

import {zodiosApi} from '$lib/api';

// ============================================================================
// TYPES — derived from unified /report endpoint response
// ============================================================================

type ApiReturnType<T extends (...args: never[]) => Promise<unknown>> = Awaited<ReturnType<T>>;

export type PortfolioReport = ApiReturnType<typeof zodiosApi.get_portfolio_report_api_v1_portfolio_report_post>;

// Extract summary type from report response
type RawSummary = PortfolioReport['summary'];
export type PortfolioSummary = NonNullable<RawSummary> extends infer S ? (S extends {net_worth: unknown} ? S : never) : never;

// History point type — define inline (generated type is not exported)
export type PortfolioHistoryPoint = {
    date: string;
    cash_value: {code: string; amount: string};
    market_value: {code: string; amount: string};
    broker_nav_value?: {code: string; amount: string} | null;
    in_transit_cash_value?: {code: string; amount: string} | null;
    in_transit_asset_market_value?: {code: string; amount: string} | null;
    in_transit_market_value?: {code: string; amount: string} | null;
    nav_value: {code: string; amount: string};
    open_cost_basis?: {code: string; amount: string} | null;
    in_transit_asset_cost_basis?: {code: string; amount: string} | null;
    in_transit_book_value?: {code: string; amount: string} | null;
    book_value?: {code: string; amount: string} | null;
    capital_baseline: {code: string; amount: string};
    book_asset_like: {code: string; amount: string};
    cash_from_contributed_capital: {code: string; amount: string};
    cash_from_generated_returns: {code: string; amount: string};
    total_pnl: {code: string; amount: string};
    unrealized_gain_loss?: {code: string; amount: string} | null;
    twrr?: string | null;
    mwrr_annualized?: string | null;
    mwrr_cumulative?: string | null;
    roi?: string | null;
};

// For allocation history dimensions we use the report type (no separate direct endpoint)
type RawAlloc = PortfolioReport['allocation_history'];
export type AllocationHistoryDimensions = Extract<NonNullable<RawAlloc>, {type?: unknown}>;

// Data quality also from report
type RawDQ = PortfolioReport['data_quality'];
export type DataQualityReport = Extract<NonNullable<RawDQ>, {issues?: unknown}>;

// Positions contribution also from report
type RawContrib = PortfolioReport['positions_contribution'];
export type PositionsContribution = Extract<NonNullable<RawContrib>, {positions?: unknown}>;

// ============================================================================
// CACHE INFRASTRUCTURE
// ============================================================================

type CacheKey = string;

interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

// ============================================================================
// MODULE-LEVEL REACTIVE STATE (Svelte 5 runes)
// ============================================================================

let reportCache = $state(new Map<CacheKey, CacheEntry<PortfolioReport>>());

const reportInflight = new Map<CacheKey, Promise<PortfolioReport>>();

let _isLoading = $state(false);
let _error = $state<string | null>(null);

// ============================================================================
// HELPERS
// ============================================================================

function makeCacheKey(brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string): CacheKey {
    return [brokerIds ? [...brokerIds].sort().join(',') : 'all', dateFrom ?? '', dateTo ?? '', targetCurrency ?? ''].join('|');
}

// ============================================================================
// PUBLIC API
// ============================================================================

/** Reactive loading indicator — true while a fetch is in-flight. */
export function portfolioIsLoading(): boolean {
    return _isLoading;
}

/** Last error message, or null if no error. */
export function portfolioError(): string | null {
    return _error;
}

/**
 * Fetch (or return cached) unified portfolio report.
 *
 * Returns summary + history + allocation_history + data_quality from a single engine run.
 *
 * @param brokerIds      — Filter by broker IDs. Omit or pass [] for all brokers.
 * @param dateFrom       — Start date for history (ISO string, e.g. '2024-01-01').
 * @param dateTo         — End date for history (ISO string).
 * @param targetCurrency — Override base currency (ISO 4217). Defaults to user setting.
 * @param force          — Bypass cache and re-fetch.
 * @param includeContribution — Also request positions_contribution (per-asset period P&L).
 * @param includeBreakdown     — Also request summary.by_broker (per-broker NAV/gain/cash breakdown).
 * @param includeHistory           — Request the daily history series. Defaults to true for
 *   backward compatibility — pass false for callers that only need `summary` (e.g. a broker list's
 *   breakdown-only fetch), since the daily series can be several MB for a long-lived portfolio and
 *   synchronously JSON-parsing it blocks the main thread for no benefit if it's never read.
 * @param includeAllocationHistory — Request allocation_history (type/sector/geography series).
 *   Same rationale as includeHistory — defaults to true, pass false when not consumed.
 */
export async function fetchReport(brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string, force = false, includeContribution = false, includeBreakdown = false, includeHistory = true, includeAllocationHistory = true): Promise<PortfolioReport | null> {
    const key = makeCacheKey(brokerIds, dateFrom, dateTo, targetCurrency) + (includeContribution ? '|contrib' : '') + (includeBreakdown ? '|breakdown' : '') + (includeHistory ? '' : '|nohist') + (includeAllocationHistory ? '' : '|noalloc');

    if (!force) {
        const cached = reportCache.get(key);
        if (cached) return cached.data;
    }

    // Deduplicate concurrent callers for the same key
    const existing = reportInflight.get(key);
    if (existing) return existing.catch(() => null);

    _isLoading = true;
    _error = null;

    const promise = (async () => {
        try {
            const body: Record<string, unknown> = {
                include_summary: true,
                include_history: includeHistory,
                include_allocation_history: includeAllocationHistory,
                include_positions_contribution: includeContribution,
                include_breakdown: includeBreakdown,
            };
            if (brokerIds && brokerIds.length > 0) body.broker_ids = brokerIds;
            if (dateFrom || dateTo) {
                body.date_range = {
                    ...(dateFrom ? {start: dateFrom} : {}),
                    ...(dateTo ? {end: dateTo} : {}),
                };
            }
            if (targetCurrency) body.target_currency = targetCurrency;

            const data = await zodiosApi.get_portfolio_report_api_v1_portfolio_report_post(body);
            reportCache = new Map(reportCache).set(key, {data, timestamp: Date.now()});
            return data;
        } catch (err) {
            _error = err instanceof Error ? err.message : 'Failed to fetch portfolio report';
            throw err;
        } finally {
            reportInflight.delete(key);
            if (reportInflight.size === 0) _isLoading = false;
        }
    })();

    reportInflight.set(key, promise);
    return promise.catch(() => null);
}

// Keep legacy exports for backward compatibility with any direct consumers of summary/history
export const fetchSummary = (brokerIds?: number[], _includeBreakdown = false, targetCurrency?: string, force = false) => fetchReport(brokerIds, undefined, undefined, targetCurrency, force).then((r) => r?.summary ?? null);

export const fetchHistory = (brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string, force = false) => fetchReport(brokerIds, dateFrom, dateTo, targetCurrency, force).then((r) => r?.history ?? []);

/**
 * Clear the entire portfolio cache.
 *
 * Call this after any transaction CRUD mutation or when the user clicks [↻ Sync].
 */
export function invalidate(): void {
    reportCache = new Map();
}
